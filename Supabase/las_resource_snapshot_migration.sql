-- Apply using Supabase MCP apply_migration. Production rows change only at commit RPC.
begin;
alter table public.courses alter column embedding drop not null;
alter table public.courses drop constraint courses_gpa_summary_is_complete;
alter table public.courses add constraint courses_gpa_counts_are_paired check (
    (total_students is null and total_sections is null) or
    (total_students is not null and total_sections is not null and overall_gpa is not null)
);
create index if not exists courses_embedding_hnsw_idx on public.courses
    using hnsw (embedding extensions.vector_cosine_ops) where embedding is not null;

alter table public.graduation_requirement_documents alter column degree_code drop not null;
alter table public.graduation_requirement_documents
    drop constraint graduation_requirement_documents_document_type_check,
    drop constraint graduation_requirement_document_scope_is_valid;
alter table public.graduation_requirement_documents
    add constraint graduation_requirement_documents_document_type_check
        check (document_type in ('program', 'program_redirect')),
    add constraint graduation_requirement_document_scope_is_valid check (
        program_code is not null and program_name is not null and parent_document_key is null
        and ((document_type = 'program' and degree_code is not null
              and degree_code in ('BALAS', 'BSLAS', 'BS', 'BALAS_OR_BSLAS'))
          or (document_type = 'program_redirect' and degree_code is null
              and document_key = 'UIUC-BIOLOGY-REDIRECT-2026-2027'))
    );
create table public.las_resource_import_batches (
    import_id uuid not null,
    resource_type text not null
        check (resource_type in ('courses', 'instructors', 'requirements')),
    batch_index integer not null check (batch_index >= 0),
    rows jsonb not null
        check (jsonb_typeof(rows) = 'array' and jsonb_array_length(rows) > 0),
    created_at timestamptz not null default now(),
    primary key (import_id, resource_type, batch_index)
);

create index las_resource_import_batches_created_at_idx
    on public.las_resource_import_batches (created_at);

create function public.stage_las_resource_import_batch(
    p_import_id uuid,
    p_resource_type text,
    p_batch_index integer,
    p_rows jsonb
)
returns integer
language plpgsql
security invoker
set search_path = pg_catalog, public
as $$
declare
    staged_row_count integer;
begin
    if p_import_id is null then
        raise exception 'p_import_id must not be null';
    end if;

    if p_resource_type is null
       or p_resource_type not in ('courses', 'instructors', 'requirements') then
        raise exception 'p_resource_type must be courses, instructors, or requirements';
    end if;

    if p_batch_index is null or p_batch_index < 0 then
        raise exception 'p_batch_index must be a nonnegative integer';
    end if;

    if p_rows is null
       or jsonb_typeof(p_rows) <> 'array'
       or jsonb_array_length(p_rows) = 0 then
        raise exception 'p_rows must be a nonempty JSON array';
    end if;

    if exists (
        select 1
        from jsonb_array_elements(p_rows) as item(payload)
        where jsonb_typeof(payload) <> 'object'
    ) then
        raise exception 'every staged row must be a JSON object';
    end if;

    if jsonb_array_length(p_rows) > (case when p_resource_type = 'instructors' then 500 else 25 end)
       or octet_length(p_rows::text) >= 750 * 1024 then
        raise exception 'staging batch exceeds size limit';
    end if;
    perform pg_advisory_xact_lock(hashtextextended(p_import_id::text, 0));
    insert into public.las_resource_import_batches (
        import_id,
        resource_type,
        batch_index,
        rows
    )
    values (
        p_import_id,
        p_resource_type,
        p_batch_index,
        p_rows
    )
    on conflict (import_id, resource_type, batch_index) do update set
        rows = excluded.rows,
        created_at = now();

    staged_row_count := jsonb_array_length(p_rows);
    return staged_row_count;
end;
$$;

create function public.discard_las_resource_import(p_import_id uuid)
returns bigint
language plpgsql
security invoker
set search_path = pg_catalog, public
as $$
declare
    deleted_batches bigint;
begin
    if p_import_id is null then
        raise exception 'p_import_id must not be null';
    end if;

    perform pg_advisory_xact_lock(hashtextextended(p_import_id::text, 0));
    delete from public.las_resource_import_batches
    where import_id = p_import_id;
    get diagnostics deleted_batches = row_count;

    return deleted_batches;
end;
$$;

create function public.commit_las_resource_import(p_import_id uuid, p_expected jsonb)
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
create or replace function public.match_courses(
    query_embedding extensions.vector(1536),
    match_count integer default 5,
    match_threshold double precision default 0.0
)
returns table (
    id bigint,
    course_code text,
    course_name text,
    credits text,
    description text,
    prerequisites text,
    credit_restrictions text,
    gen_ed text,
    overall_gpa numeric,
    similarity double precision
)
language sql
stable
security invoker
set search_path = pg_catalog, public, extensions
as $$
    select
        course.id,
        course.course_code,
        course.course_name,
        course.credits,
        course.description,
        course.prerequisites,
        course.credit_restrictions,
        course.gen_ed,
        course.overall_gpa,
        1 - (course.embedding <=> query_embedding) as similarity
    from public.courses as course
    where course.embedding is not null
      and 1 - (course.embedding <=> query_embedding)
        >= coalesce(match_threshold, 0.0)
    order by course.embedding <=> query_embedding
    limit greatest(1, least(coalesce(match_count, 5), 20));
$$;

alter table public.courses enable row level security;
revoke all on table public.courses from public, anon, authenticated;
grant select, insert, update, delete on table public.courses to service_role;
alter table public.course_instructor_stats enable row level security;
revoke all on table public.course_instructor_stats from public, anon, authenticated;
grant select, insert, update, delete on table public.course_instructor_stats to service_role;
alter table public.graduation_requirement_documents enable row level security;
revoke all on table public.graduation_requirement_documents from public, anon, authenticated;
grant select, insert, update, delete on table public.graduation_requirement_documents to service_role;
alter table public.las_resource_import_batches enable row level security;
revoke all on table public.las_resource_import_batches from public, anon, authenticated;
grant select, insert, update, delete on table public.las_resource_import_batches to service_role;
revoke all on function public.stage_las_resource_import_batch(uuid, text, integer, jsonb) from public, anon, authenticated;
grant execute on function public.stage_las_resource_import_batch(uuid, text, integer, jsonb) to service_role;
revoke all on function public.discard_las_resource_import(uuid) from public, anon, authenticated;
grant execute on function public.discard_las_resource_import(uuid) to service_role;
revoke all on function public.commit_las_resource_import(uuid, jsonb) from public, anon, authenticated;
grant execute on function public.commit_las_resource_import(uuid, jsonb) to service_role;
revoke all on function public.match_courses(extensions.vector, integer, double precision) from public, anon, authenticated;
grant execute on function public.match_courses(extensions.vector, integer, double precision) to service_role;

-- Event triggers run internally; this helper is not a public RPC.
revoke all on function public.rls_auto_enable() from public, anon, authenticated;

commit;
