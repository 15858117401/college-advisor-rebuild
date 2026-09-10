import csv
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from Supabase import import_las_resources as las
from Supabase.import_stat_resources import (
    COURSE_HEADERS, INSTRUCTOR_HEADERS, _optional_text, load_resource_data,
)
from Supabase.import_graduation_requirements import load_requirement_documents


def test_complete_local_snapshot():
    data = las.load_las_resource_data()
    assert las.snapshot_counts(data) == las.EXPECTED_COUNTS
    assert len(load_requirement_documents()) == 61


def write_pair(tmp_path, courses, instructors):
    for name, headers, rows in [
        ('stat_courses.csv', COURSE_HEADERS, courses),
        ('stat_course_instructor_stats.csv', INSTRUCTOR_HEADERS, instructors),
    ]:
        with (tmp_path / name).open('w', newline='', encoding='utf-8') as target:
            writer = csv.DictWriter(target, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
    return tmp_path / 'stat_courses.csv', tmp_path / 'stat_course_instructor_stats.csv'


def rows():
    c = dict.fromkeys(COURSE_HEADERS, '')
    c.update(course_code='STAT 100', subject='STAT', course_number='100',
             course_name='  Unicode — title  ', credits='3 hours.',
             description='  exact\n  description – 中文\n', overall_gpa='3.25')
    i = dict.fromkeys(INSTRUCTOR_HEADERS, '')
    i.update(course_code='STAT 100', subject='STAT', course_number='100',
             instructor_name='  Instructor, A.  ', instructor_avg_gpa='3.50')
    return c, i


def test_preserves_text_and_gpa_only_rows(tmp_path):
    c, i = rows()
    data = load_resource_data(*write_pair(tmp_path, [c], [i]), check_counts=False)
    assert data.courses[0]['description'] == c['description']
    assert data.courses[0]['course_name'] == c['course_name']
    assert data.instructors[0]['instructor_name'] == i['instructor_name']
    assert data.courses[0]['overall_gpa'] == 3.25
    assert data.courses[0]['total_students'] is None
    assert _optional_text('  ') == '  '
    assert _optional_text('') is None
    assert _optional_text('N/A') == 'N/A'


@pytest.mark.parametrize('fault', ['duplicate_course', 'orphan', 'duplicate_instructor', 'blank', 'all_sections', 'identifier', 'counts'])
def test_rejects_invalid_rows(tmp_path, fault):
    c, i = rows()
    courses, instructors = [c], [i]
    if fault == 'duplicate_course': courses.append(dict(c))
    if fault == 'orphan': i['course_code'] = 'STAT 101'
    if fault == 'duplicate_instructor': instructors.append(dict(i))
    if fault == 'blank': i['instructor_name'] = '  '
    if fault == 'all_sections': i['instructor_name'] = ' All Sections '
    if fault == 'identifier': c['subject'] = 'CS'
    if fault == 'counts': c['total_students'] = '5'
    with pytest.raises(ValueError):
        load_resource_data(*write_pair(tmp_path, courses, instructors), check_counts=False)


def test_same_instructor_different_delta_is_preserved(tmp_path):
    c, i = rows()
    other = {**i, 'gpa_delta_from_course': '0.25'}
    data = load_resource_data(*write_pair(tmp_path, [c], [i, other]), check_counts=False)
    assert len(data.instructors) == 2


def test_request_batches_bound_utf8_and_row_counts():
    for kind, limit in las.BATCH_LIMITS.items():
        source = [{'text': '中文\n' * 2500} for _ in range(limit + 3)]
        batches = list(las.stage_batches('00000000-0000-0000-0000-000000000000', kind, source))
        assert [r for b in batches for r in b['p_rows']] == source
        assert all(len(b['p_rows']) <= limit and las.request_size(b) < 750 * 1024 for b in batches)
    with pytest.raises(ValueError, match='single'):
        list(las.stage_batches('id', 'courses', [{'text': 'x' * las.MAX_REQUEST_BYTES}]))


def test_staging_failure_discards_and_never_commits():
    c, i = rows()
    c['description'] = 'text'
    data = SimpleNamespace(courses=[c], instructors=[i])
    documents = [SimpleNamespace(database_row=lambda: {})] * 61
    calls = []
    class Client:
        def rpc(self, name, params):
            calls.append(name)
            if name.startswith('stage_'):
                raise RuntimeError('staging failed')
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=1))
    with patch.object(las, 'snapshot_counts', return_value=las.EXPECTED_COUNTS):
        with pytest.raises(RuntimeError, match='staging failed'):
            las.upload_snapshot(data, {'STAT 100': [1.0] * 1536}, documents,
                                supabase_client=Client(), progress=lambda _: None)
    assert calls == ['stage_las_resource_import_batch', 'discard_las_resource_import']


def test_pagination_reads_beyond_api_default():
    all_rows = [{'id': i} for i in range(1333)]
    class Query:
        def table(self, _): return self
        def select(self, _): return self
        def order(self, _): return self
        def range(self, start, end):
            self.result = all_rows[start:end + 1]
            return self
        def execute(self): return SimpleNamespace(data=self.result)
    assert las.paginated_rows(Query(), 'table', 'id', 'id') == all_rows


def test_regeneration_sends_description_exactly(tmp_path):
    c, _ = rows()
    seen = []
    class Embeddings:
        def create(self, **params):
            seen.append(params)
            return SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[1.0] * 1536)])
    with patch.object(las, 'create_embedding_client', return_value=SimpleNamespace(embeddings=Embeddings())), \
         patch.object(las, 'load_embedding_cache', return_value={}):
        las.regenerate_embedding_cache(SimpleNamespace(courses=[c]), tmp_path)
    assert seen[0]['input'] == [c['description']]
    assert seen[0]['model'] == 'text-embedding-3-small'
    assert seen[0]['dimensions'] == 1536


@pytest.mark.parametrize('fault', [None, 'catalog', 'description', 'duplicate', 'model', 'dimensions'])
def test_cache_validates_provenance_before_use(tmp_path, fault):
    import gzip
    import hashlib
    c, _ = rows()
    audit = {'file_sha256': {'stat_courses.csv': 'abc'},
             'model': 'text-embedding-3-small', 'dimensions': 1536,
             'course_files': 58, 'course_rows': 3834, 'embedded_rows': 3833,
             'blank_descriptions': ['CWL 593']}
    row = {'course_code': c['course_code'], 'description_sha256': hashlib.sha256(c['description'].encode()).hexdigest(),
           'embedding': [1.0] * 1536}
    cache = {'model': audit['model'], 'dimensions': 1536, 'rows': [row]}
    if fault == 'catalog': audit['file_sha256'] = {}
    if fault == 'description': row['description_sha256'] = 'wrong'
    if fault == 'duplicate': cache['rows'].append(dict(row))
    if fault == 'model': cache['model'] = 'wrong'
    if fault == 'dimensions': row['embedding'] = [1.0]
    (tmp_path / 'audit.json').write_text(json.dumps(audit))
    with gzip.open(tmp_path / 'course_embeddings.json.gz', 'wt') as target:
        json.dump(cache, target)
    with patch.object(las, 'file_checksums', return_value={'stat_courses.csv': 'abc'}):
        if fault:
            with pytest.raises(ValueError):
                las.load_embedding_cache(SimpleNamespace(courses=[c]), tmp_path)
        else:
            assert las.load_embedding_cache(SimpleNamespace(courses=[c]), tmp_path)[c['course_code']] == row['embedding']


def test_all_datasets_stage_before_single_commit():
    c, i = rows()
    data = SimpleNamespace(courses=[c], instructors=[i])
    documents = [SimpleNamespace(document_key=f'doc-{n}', database_row=lambda: {}) for n in range(61)]
    calls = []
    class Client:
        def rpc(self, name, params):
            calls.append((name, params))
            result = (len(params['p_rows']) if name.startswith('stage_') else
                      {'courses': 3834, 'instructors': 3986, 'requirements': 61})
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=result))
    with patch.object(las, 'snapshot_counts', return_value=las.EXPECTED_COUNTS):
        las.upload_snapshot(data, {'STAT 100': [1.0] * 1536}, documents,
                            supabase_client=Client(), progress=lambda _: None)
    assert calls[-1][0] == 'commit_las_resource_import'
    assert sum(name == 'commit_las_resource_import' for name, _ in calls) == 1
    assert {params['p_resource_type'] for _, params in calls[:-1]} == {'courses', 'instructors', 'requirements'}
    assert len({params['p_import_id'] for _, params in calls}) == 1
