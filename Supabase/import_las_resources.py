"""Validate, stage, atomically replace, and verify the complete LAS snapshot.

Run from the repository root: .venv/bin/python -m Supabase.import_las_resources
{validate,upload,verify}. Apply las_resource_snapshot_migration.sql first.
The cache is removed only by an explicit cleanup after remote checks/advisors.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any
from uuid import uuid4

from client.embedding_client import (
    EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, create_embedding_client,
)
from Supabase.import_stat_resources import (
    PROJECT_ROOT, COURSE_HEADERS, INSTRUCTOR_HEADERS, ResourceData,
    create_supabase_client, load_resource_data,
)
from Supabase.import_graduation_requirements import load_requirement_documents

CATALOG_DIR = PROJECT_ROOT / "Resource/las_course_catalog"
INSTRUCTOR_DIR = PROJECT_ROOT / "Resource/LASsectionGPA"
CACHE_DIR = Path("/tmp/college_advisor_las_supabase_upload")
MAX_REQUEST_BYTES = 750 * 1024
BATCH_LIMITS = {"courses": 25, "instructors": 500, "requirements": 25}
EXPECTED_COUNTS = {
    "courses": 3834, "course_subjects": 58, "embeddings": 3833,
    "overall_gpa": 1325, "paired_counts": 22, "instructors": 3986,
    "instructor_courses": 1333, "instructor_subjects": 51,
    "null_deltas": 952, "stat_courses": 41, "stat_instructors": 117,
}


def load_las_resource_data(catalog_dir=CATALOG_DIR, instructor_dir=INSTRUCTOR_DIR):
    files = sorted(catalog_dir.glob("*_courses.csv"))
    expected_files = {p.name.replace("_courses.csv", "_course_instructor_stats.csv") for p in files}
    if len(files) != 58 or expected_files != {p.name for p in instructor_dir.glob("*_course_instructor_stats.csv")}:
        raise ValueError("expected exactly 58 matching catalog/instructor files")
    courses, instructors = [], []
    for path in files:
        data = load_resource_data(path, instructor_dir / path.name.replace("_courses.csv", "_course_instructor_stats.csv"), check_counts=False)
        courses.extend(data.courses)
        instructors.extend(data.instructors)
    data = ResourceData(courses, instructors)
    if len({r['course_code'] for r in courses}) != len(courses):
        raise ValueError("duplicate course codes across catalog files")
    if snapshot_counts(data) != EXPECTED_COUNTS:
        raise ValueError(f"snapshot count mismatch: {snapshot_counts(data)}")
    if [r['course_code'] for r in courses if r['description'] == ''] != ['CWL 593']:
        raise ValueError("only CWL 593 may have an empty description")
    return data


def snapshot_counts(data):
    c, i = data.courses, data.instructors
    return {
        "courses": len(c), "course_subjects": len({r['subject'] for r in c}),
        "embeddings": sum(r['description'] != '' for r in c),
        "overall_gpa": sum(r['overall_gpa'] is not None for r in c),
        "paired_counts": sum(r['total_students'] is not None and r['total_sections'] is not None for r in c),
        "instructors": len(i), "instructor_courses": len({r['course_code'] for r in i}),
        "instructor_subjects": len({r['subject'] for r in i}),
        "null_deltas": sum(r['gpa_delta_from_course'] is None for r in i),
        "stat_courses": sum(r['subject'] == 'STAT' for r in c),
        "stat_instructors": sum(r['subject'] == 'STAT' for r in i),
    }


def file_checksums(folder, pattern):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob(pattern))}


def validate_inventory(cache_dir=CACHE_DIR):
    inventory = json.loads((cache_dir / 'resource_inventory.json').read_text())
    for key, folder, pattern in [
        ('catalog', CATALOG_DIR, '*_courses.csv'),
        ('instructors', INSTRUCTOR_DIR, '*_course_instructor_stats.csv'),
        ('requirements', PROJECT_ROOT / 'Resource/LASmajor_requirement', '*.md'),
    ]:
        if file_checksums(folder, pattern) != inventory[key]['sha256']:
            raise ValueError(f"{key} resource inventory checksum mismatch")
    return {key: value['files'] for key, value in inventory.items()}


def validate_vector(vector):
    if not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError("embedding must have 1536 dimensions")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector):
        raise ValueError("embedding contains a non-finite or invalid value")
    if not any(vector):
        raise ValueError("zero embedding cannot be used for cosine search")


def load_embedding_cache(data, cache_dir=CACHE_DIR):
    audit = json.loads((cache_dir / 'audit.json').read_text())
    if audit['file_sha256'] != file_checksums(CATALOG_DIR, '*_courses.csv'):
        raise ValueError("catalog checksum mismatch against audit.json")
    with gzip.open(cache_dir / 'course_embeddings.json.gz', 'rt', encoding='utf-8') as source:
        cache = json.load(source)
    for metadata in (audit, cache):
        if metadata['model'] != EMBEDDING_MODEL or metadata['dimensions'] != EMBEDDING_DIMENSIONS:
            raise ValueError("embedding model/dimensions mismatch")
    if (audit['course_files'], audit['course_rows'], audit['embedded_rows'], audit['blank_descriptions']) != (58, 3834, 3833, ['CWL 593']):
        raise ValueError("embedding audit counts mismatch")
    rows = {r['course_code']: r for r in cache['rows']}
    expected = {r['course_code'] for r in data.courses if r['description'] != ''}
    if len(rows) != len(cache['rows']) or set(rows) != expected:
        raise ValueError("embedding cache identities mismatch")
    vectors = {}
    for course in data.courses:
        code, description = course['course_code'], course['description']
        if description == '':
            vectors[code] = None
            continue
        row = rows[code]
        if row['description_sha256'] != hashlib.sha256(description.encode('utf-8')).hexdigest():
            raise ValueError(f"description checksum mismatch: {code}")
        validate_vector(row['embedding'])
        vectors[code] = row['embedding']
    return vectors


def regenerate_embedding_cache(data, cache_dir=CACHE_DIR):
    """Called only if a cache is absent/invalid; send exact descriptions unchanged."""
    client = create_embedding_client()
    courses = [r for r in data.courses if r['description'] != '']
    rows = []
    for start in range(0, len(courses), 25):
        batch = courses[start:start + 25]
        response = client.embeddings.create(model=EMBEDDING_MODEL,
            dimensions=EMBEDDING_DIMENSIONS, encoding_format='float',
            input=[r['description'] for r in batch])
        items = sorted(response.data, key=lambda r: r.index)
        if [r.index for r in items] != list(range(len(batch))):
            raise ValueError("embedding response indexes mismatch")
        for course, item in zip(batch, items, strict=True):
            vector = list(item.embedding)
            validate_vector(vector)
            rows.append({'course_code': course['course_code'],
                'description_sha256': hashlib.sha256(course['description'].encode()).hexdigest(),
                'embedding': vector})
    cache_dir.mkdir(parents=True, exist_ok=True)
    with gzip.open(cache_dir / 'course_embeddings.json.gz', 'wt', encoding='utf-8') as target:
        json.dump({'model': EMBEDDING_MODEL, 'dimensions': EMBEDDING_DIMENSIONS, 'rows': rows}, target)
    (cache_dir / 'audit.json').write_text(json.dumps({
        'model': EMBEDDING_MODEL, 'dimensions': EMBEDDING_DIMENSIONS,
        'course_files': 58, 'course_rows': len(data.courses), 'embedded_rows': len(rows),
        'blank_descriptions': ['CWL 593'], 'file_sha256': file_checksums(CATALOG_DIR, '*_courses.csv'),
    }))
    return load_embedding_cache(data, cache_dir)


def request_size(params):
    # Default JSON separators + ASCII escaping overestimate supabase-py's compact UTF-8 body.
    return len(json.dumps(params, ensure_ascii=True, allow_nan=False).encode('utf-8'))


def stage_batches(import_id, resource_type, rows):
    batch, index = [], 0
    def payload(items):
        return {'p_import_id': import_id, 'p_resource_type': resource_type,
                'p_batch_index': index, 'p_rows': items}
    for row in rows:
        if batch and (len(batch) >= BATCH_LIMITS[resource_type] or request_size(payload(batch + [row])) >= MAX_REQUEST_BYTES):
            yield payload(batch)
            index += 1
            batch = []
        batch.append(row)
        if request_size(payload(batch)) >= MAX_REQUEST_BYTES:
            raise ValueError(f"single {resource_type} row exceeds request size limit")
    if batch:
        yield payload(batch)


def upload_snapshot(data, vectors, documents, *, supabase_client, progress=print):
    if snapshot_counts(data) != EXPECTED_COUNTS or len(documents) != 61:
        raise ValueError('refusing incomplete LAS snapshot')
    course_rows = []
    for row in data.courses:
        vector = vectors[row['course_code']]
        if vector is None:
            if row['course_code'] != 'CWL 593' or row['description'] != '':
                raise ValueError('unexpected null embedding')
        else:
            validate_vector(vector)
        course_rows.append({**row, 'embedding': vector})
    datasets = {'courses': course_rows, 'instructors': data.instructors,
                'requirements': [d.database_row() for d in documents]}
    import_id = str(uuid4())
    progress(f"Staging import {import_id}")
    try:
        for kind, rows in datasets.items():
            staged = 0
            for params in stage_batches(import_id, kind, rows):
                result = supabase_client.rpc('stage_las_resource_import_batch', params).execute().data
                if result != len(params['p_rows']):
                    raise RuntimeError(f'unexpected staging response for {kind}')
                staged += result
                if params['p_batch_index'] % 20 == 0 or staged == len(rows):
                    progress(f"{kind}: {staged}/{len(rows)} staged")
    except BaseException:
        # No commit has been attempted, so production is untouched.
        supabase_client.rpc('discard_las_resource_import', {'p_import_id': import_id}).execute()
        raise
    expected = {'course_codes': sorted(r['course_code'] for r in data.courses),
                'document_keys': sorted(d.document_key for d in documents)}
    # Do not retry an uncertain commit. The caller can use verify to resolve it.
    result = supabase_client.rpc('commit_las_resource_import',
        {'p_import_id': import_id, 'p_expected': expected}).execute().data
    if result != {'courses': 3834, 'instructors': 3986, 'requirements': 61}:
        raise RuntimeError(f'unexpected commit response for {import_id}; run verify')
    return result


def paginated_rows(client, table, fields, order, page_size=500):
    rows, offset = [], 0
    while True:
        batch = client.table(table).select(fields).order(order).range(offset, offset + page_size - 1).execute().data or []
        rows.extend(batch)
        if len(batch) < page_size:
            return rows
        offset += page_size


def verify_snapshot(data, vectors, documents, *, supabase_client, progress=print):
    stored = paginated_rows(supabase_client, 'courses', ','.join(COURSE_HEADERS) + ',id,embedding', 'course_code', 100)
    if len(stored) != len(data.courses):
        raise RuntimeError('remote course count mismatch')
    local = {r['course_code']: r for r in data.courses}
    ids = {}
    null_codes = []
    semantic_vectors = {}
    for row in stored:
        code = row['course_code']
        if {k: row[k] for k in COURSE_HEADERS} != local.get(code):
            raise RuntimeError(f'non-vector course mismatch: {code}')
        ids[code] = row['id']
        vector = row['embedding']
        if vector is None:
            null_codes.append(code)
        else:
            vector = json.loads(vector) if isinstance(vector, str) else vector
            validate_vector(vector)
            if vectors is not None and any(not math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-8) for a, b in zip(vector, vectors[code], strict=True)):
                raise RuntimeError(f'stored embedding differs: {code}')
            if code in ['AAS 100', 'CS 100', 'MATH 241', 'STAT 100']:
                semantic_vectors[code] = vector
    if null_codes != ['CWL 593']:
        raise RuntimeError('unexpected null embeddings')
    progress('All 3834 course values match local sources; vector checks passed')
    stored_i = paginated_rows(supabase_client, 'course_instructor_stats', ','.join(INSTRUCTOR_HEADERS) + ',course_id,id', 'id')
    if any(r['course_id'] != ids.get(r['course_code']) for r in stored_i):
        raise RuntimeError('instructor foreign key mismatch')
    if Counter(tuple(r[k] for k in INSTRUCTOR_HEADERS) for r in stored_i) != Counter(tuple(r[k] for k in INSTRUCTOR_HEADERS) for r in data.instructors):
        raise RuntimeError('stored instructor rows differ from source')
    fields = list(documents[0].database_row())
    stored_d = paginated_rows(supabase_client, 'graduation_requirement_documents', ','.join(fields), 'document_key')
    if {r['document_key']: r for r in stored_d} != {d.document_key: d.database_row() for d in documents}:
        raise RuntimeError('stored Markdown or requirement metadata differs from source')
    if any(r['content_markdown'].encode('utf-8') != next(d for d in documents if d.document_key == r['document_key']).content_markdown.encode('utf-8') for r in stored_d):
        raise RuntimeError('stored Markdown bytes differ')
    progress('All 3986 instructor rows and 61 Markdown documents match local sources')
    matches = {}
    for code in ['AAS 100', 'CS 100', 'MATH 241', 'STAT 100']:
        found = supabase_client.rpc('match_courses', {'query_embedding': semantic_vectors[code], 'match_count': 5, 'match_threshold': 0.99}).execute().data
        self_match = next((r for r in found or [] if r['course_code'] == code and r['similarity'] > 0.99999), None)
        if self_match is None or (found[0]['similarity'] - self_match['similarity']) > 1e-6:
            raise RuntimeError(f'semantic self-match failed: {code}')
        matches[code] = {'rank': next(i + 1 for i, r in enumerate(found) if r['course_code'] == code), 'similarity': self_match['similarity']}
    staging = paginated_rows(supabase_client, 'las_resource_import_batches', 'import_id', 'import_id')
    if staging:
        raise RuntimeError('staging rows remain')
    return {**snapshot_counts(data), 'requirements': len(stored_d), 'all_values_verified': True,
            'markdown_bytes_verified': True, 'cached_vectors_compared': vectors is not None,
            'semantic_checks': matches, 'staging_rows': 0}


def run_upload(*, documents=None, cache_dir=CACHE_DIR):
    data = load_las_resource_data()
    documents = documents if documents is not None else load_requirement_documents()
    if (cache_dir / 'resource_inventory.json').exists():
        validate_inventory(cache_dir)
    try:
        vectors = load_embedding_cache(data, cache_dir)
        print('All catalog checksums, description SHA-256 hashes, and cached vectors verified', flush=True)
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f'Embedding cache validation failed ({type(exc).__name__}); regenerating exact descriptions', flush=True)
        vectors = regenerate_embedding_cache(data, cache_dir)
    client = create_supabase_client()
    upload_snapshot(data, vectors, documents, supabase_client=client,
                    progress=lambda message: print(message, flush=True))
    return verify_snapshot(data, vectors, documents, supabase_client=client,
                           progress=lambda message: print(message, flush=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['validate', 'upload', 'verify'])
    args = parser.parse_args()
    if args.command == 'upload':
        result = run_upload()
    else:
        data = load_las_resource_data()
        documents = load_requirement_documents()
        vectors = load_embedding_cache(data) if (CACHE_DIR / 'course_embeddings.json.gz').exists() else None
        if args.command == 'verify':
            result = verify_snapshot(data, vectors, documents, supabase_client=create_supabase_client())
        else:
            result = {**snapshot_counts(data), 'requirements': len(documents),
                      'inventory_files': validate_inventory() if (CACHE_DIR / 'resource_inventory.json').exists() else None,
                      'cache_verified': vectors is not None}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
