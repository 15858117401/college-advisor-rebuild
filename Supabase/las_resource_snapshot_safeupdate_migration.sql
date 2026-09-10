-- Keep the atomic snapshot replacement compatible with Supabase safeupdate.
begin;
create or replace function public.commit_las_resource_import(p_import_id uuid, p_expected jsonb)
returns jsonb
language plpgsql
security invoker
set search_path = pg_catalog, public, extensions
set statement_timeout = '120s'
as $$
begin
    if p_import_id is null or p_expected is null
       or jsonb_typeof(p_expected->'course_codes') is distinct from 'array'
       or jsonb_typeof(p_expected->'document_keys') is distinct from 'array' then
        raise exception 'expected course and document identities are required';
    end if;
    perform pg_advisory_xact_lock(hashtextextended(p_import_id::text, 0));
    -- Typed temporary copies validate NOT NULL, CHECK, uniqueness, and vector dimensions
    -- before any production DELETE/INSERT/UPDATE. Foreign keys are checked below.
    create temporary table las_courses (like public.courses including all) on commit drop;
    create temporary table las_instructors (like public.course_instructor_stats including all) on commit drop;
    create temporary table las_requirements (like public.graduation_requirement_documents including all) on commit drop;
    insert into pg_temp.las_courses (course_code, subject, course_number, course_name, credits, description, prerequisites, credit_restrictions, gen_ed, total_students, total_sections, overall_gpa, embedding)
    select payload->>'course_code',
        payload->>'subject',
        (payload->>'course_number')::integer,
        payload->>'course_name',
        payload->>'credits',
        payload->>'description',
        payload->>'prerequisites',
        payload->>'credit_restrictions',
        payload->>'gen_ed',
        (payload->>'total_students')::integer,
        (payload->>'total_sections')::integer,
        (payload->>'overall_gpa')::numeric,
        (payload->>'embedding')::extensions.vector(1536)
    from public.las_resource_import_batches b
    cross join lateral jsonb_array_elements(b.rows) as r(payload)
    where b.import_id = p_import_id and b.resource_type = 'courses';
    insert into pg_temp.las_instructors (course_id, course_code, subject, course_number, instructor_name, instructor_avg_gpa, gpa_delta_from_course)
    select c.id, payload->>'course_code',
        payload->>'subject',
        (payload->>'course_number')::integer,
        payload->>'instructor_name',
        (payload->>'instructor_avg_gpa')::numeric,
        (payload->>'gpa_delta_from_course')::numeric
    from public.las_resource_import_batches b
    cross join lateral jsonb_array_elements(b.rows) as r(payload)
    left join pg_temp.las_courses c on c.course_code = payload->>'course_code'
        and c.subject = payload->>'subject'
        and c.course_number = (payload->>'course_number')::integer
    where b.import_id = p_import_id and b.resource_type = 'instructors';
    insert into pg_temp.las_requirements (document_key, document_type, institution_code, degree_code, program_code, program_name, catalog_year, parent_document_key, source_url, content_markdown)
    select payload->>'document_key',
        payload->>'document_type',
        payload->>'institution_code',
        payload->>'degree_code',
        payload->>'program_code',
        payload->>'program_name',
        payload->>'catalog_year',
        payload->>'parent_document_key',
        payload->>'source_url',
        payload->>'content_markdown'
    from public.las_resource_import_batches b
    cross join lateral jsonb_array_elements(b.rows) as r(payload)
    where b.import_id = p_import_id and b.resource_type = 'requirements';

    if (select count(*) <> 3834 or count(distinct subject) <> 58
            or count(embedding) <> 3833 or count(overall_gpa) <> 1325
            or count(total_students) <> 22 or count(total_sections) <> 22
            or count(*) filter (where subject = 'STAT') <> 41
        from pg_temp.las_courses)
       or (select count(*) <> 3986 or count(distinct course_code) <> 1333
            or count(distinct subject) <> 51
            or count(*) filter (where gpa_delta_from_course is null) <> 952
            or count(*) filter (where subject = 'STAT') <> 117
        from pg_temp.las_instructors)
       or (select count(*) <> 61 from pg_temp.las_requirements) then
        raise exception 'LAS snapshot counts do not match expected complete snapshot';
    end if;
    if exists (select 1 from pg_temp.las_courses where
            subject !~ '^[A-Z]+$' or course_number not between 100 and 599
            or btrim(course_name) = '' or btrim(credits) = ''
            or (embedding is null) <> (course_code = 'CWL 593')
            or (description = '') <> (course_code = 'CWL 593')
            or (embedding is not null and extensions.vector_norm(embedding) = 0))
       or exists (select 1 from pg_temp.las_instructors where
            btrim(instructor_name) = '' or lower(btrim(instructor_name)) = 'all sections') then
        raise exception 'invalid course/embedding/instructor identity';
    end if;
    if jsonb_array_length(p_expected->'course_codes') <> 3834
       or jsonb_array_length(p_expected->'document_keys') <> 61
       or (select count(distinct value) from jsonb_array_elements_text(p_expected->'course_codes')) <> 3834
       or (select count(distinct value) from jsonb_array_elements_text(p_expected->'document_keys')) <> 61
       or exists (select course_code from pg_temp.las_courses
                  except select value from jsonb_array_elements_text(p_expected->'course_codes'))
       or exists (select document_key from pg_temp.las_requirements
                  except select value from jsonb_array_elements_text(p_expected->'document_keys')) then
        raise exception 'LAS snapshot identities do not match local manifest';
    end if;
    if (select count(*) from pg_temp.las_requirements where document_key in
        ('UIUC-MATH-BSLAS-2026-2027','UIUC-STAT-BSLAS-2026-2027') and degree_code='BSLAS' and document_type='program') <> 2
       or (select count(*) from pg_temp.las_requirements where document_key='UIUC-BIOLOGY-REDIRECT-2026-2027'
        and document_type='program_redirect' and degree_code is null) <> 1
       or (select count(*) from pg_temp.las_requirements where
        document_key='UIUC-INDIVIDUAL-PLANS-OF-STUDY-BALAS-OR-BSLAS-2026-2027'
        and degree_code='BALAS_OR_BSLAS') <> 1
       or exists (select 1 from pg_temp.las_requirements where institution_code <> 'UIUC'
           or catalog_year <> '2026-2027' or source_url not like 'https://catalog.illinois.edu/%'
           or (degree_code='BALAS_OR_BSLAS' and document_key<>'UIUC-INDIVIDUAL-PLANS-OF-STUDY-BALAS-OR-BSLAS-2026-2027')) then
        raise exception 'invalid requirement metadata';
    end if;

    -- Serialize complete snapshots and protect ordinary writers during replacement.
    lock table public.courses, public.course_instructor_stats,
        public.graduation_requirement_documents in exclusive mode;
    delete from public.course_instructor_stats where true;
    insert into public.courses (course_code, subject, course_number, course_name, credits, description, prerequisites, credit_restrictions, gen_ed, total_students, total_sections, overall_gpa, embedding)
    select course_code, subject, course_number, course_name, credits, description, prerequisites, credit_restrictions, gen_ed, total_students, total_sections, overall_gpa, embedding from pg_temp.las_courses
    on conflict (course_code) do update set
        subject = excluded.subject,
        course_number = excluded.course_number,
        course_name = excluded.course_name,
        credits = excluded.credits,
        description = excluded.description,
        prerequisites = excluded.prerequisites,
        credit_restrictions = excluded.credit_restrictions,
        gen_ed = excluded.gen_ed,
        total_students = excluded.total_students,
        total_sections = excluded.total_sections,
        overall_gpa = excluded.overall_gpa,
        embedding = excluded.embedding;
    delete from public.courses c where not exists
        (select 1 from pg_temp.las_courses s where s.course_code = c.course_code);
    insert into public.course_instructor_stats (course_id, course_code, subject, course_number, instructor_name, instructor_avg_gpa, gpa_delta_from_course)
    select c.id, s.course_code, s.subject, s.course_number, s.instructor_name, s.instructor_avg_gpa, s.gpa_delta_from_course from pg_temp.las_instructors s
    join public.courses c on c.course_code = s.course_code;
    delete from public.graduation_requirement_documents where true;
    insert into public.graduation_requirement_documents (document_key, document_type, institution_code, degree_code, program_code, program_name, catalog_year, parent_document_key, source_url, content_markdown)
    select document_key, document_type, institution_code, degree_code, program_code, program_name, catalog_year, parent_document_key, source_url, content_markdown from pg_temp.las_requirements;
    delete from public.las_resource_import_batches where import_id = p_import_id;
    return jsonb_build_object('courses', 3834, 'instructors', 3986, 'requirements', 61);
end;
$$;

commit;
