-- Fresh database bootstrap only. After this and graduation_requirements_schema.sql,
-- apply las_resource_snapshot_migration.sql for the complete atomic LAS importer.
begin;

create extension if not exists vector with schema extensions;

create table public.courses (
    id bigint generated always as identity primary key,
    course_code text not null unique,
    subject text not null,
    course_number integer not null,
    course_name text not null,
    credits text not null,
    description text not null,
    prerequisites text,
    credit_restrictions text,
    gen_ed text,
    total_students integer check (total_students >= 0),
    total_sections integer check (total_sections >= 0),
    overall_gpa numeric(3, 2) check (overall_gpa between 0 and 4),
    embedding extensions.vector(1536),
    constraint courses_full_identity_key unique (
        id,
        course_code,
        subject,
        course_number
    ),
    constraint courses_code_matches_subject_number check (
        course_code = subject || ' ' || course_number::text
    ),
    constraint courses_gpa_summary_is_complete check (
        (total_students is null and total_sections is null)
        or
        (total_students is not null and total_sections is not null and overall_gpa is not null)
    )
);

create index courses_subject_number_idx
    on public.courses (subject, course_number);

create index courses_embedding_hnsw_idx
    on public.courses
    using hnsw (embedding extensions.vector_cosine_ops)
    where embedding is not null;

create table public.course_instructor_stats (
    id bigint generated always as identity primary key,
    course_id bigint not null,
    course_code text not null,
    subject text not null,
    course_number integer not null,
    instructor_name text not null,
    instructor_avg_gpa numeric(3, 2)
        check (instructor_avg_gpa between 0 and 4),
    gpa_delta_from_course numeric(4, 2)
        check (gpa_delta_from_course between -4 and 4),
    constraint course_instructor_stats_course_identity_fkey
        foreign key (course_id, course_code, subject, course_number)
        references public.courses (id, course_code, subject, course_number)
        on update cascade
        on delete cascade
);

create index course_instructor_stats_course_identity_idx
    on public.course_instructor_stats (
        course_id,
        course_code,
        subject,
        course_number
    );

create index course_instructor_stats_course_code_idx
    on public.course_instructor_stats (course_code);

create index course_instructor_stats_subject_number_idx
    on public.course_instructor_stats (subject, course_number);

create unique index course_instructor_stats_exact_row_idx
    on public.course_instructor_stats (
        course_id,
        instructor_name,
        coalesce(instructor_avg_gpa, -1.00),
        coalesce(gpa_delta_from_course, -9.00)
    );

alter table public.courses enable row level security;
alter table public.course_instructor_stats enable row level security;
revoke all on table public.courses from public, anon, authenticated;
revoke all on table public.course_instructor_stats from public, anon, authenticated;
revoke all on sequence public.courses_id_seq from public, anon, authenticated;
revoke all on sequence public.course_instructor_stats_id_seq from public, anon, authenticated;
grant select, insert, update, delete on table public.courses to service_role;
grant select, insert, update, delete on table public.course_instructor_stats to service_role;
grant usage, select on sequence public.courses_id_seq to service_role;
grant usage, select on sequence public.course_instructor_stats_id_seq to service_role;

create function public.match_courses(
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

revoke all on function public.match_courses(extensions.vector, integer, double precision)
    from public, anon, authenticated;
grant execute on function public.match_courses(extensions.vector, integer, double precision)
    to service_role;

commit;
