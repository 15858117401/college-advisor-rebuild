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
    embedding extensions.vector(1536) not null,
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
        (total_students is null and total_sections is null and overall_gpa is null)
        or
        (total_students is not null and total_sections is not null and overall_gpa is not null)
    )
);

create index courses_subject_number_idx
    on public.courses (subject, course_number);

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
revoke all on sequence public.course_instructor_stats_id_seq
    from public, anon, authenticated;
grant select, insert, update, delete on table public.courses to service_role;
grant select, insert, update, delete on table public.course_instructor_stats
    to service_role;
grant usage, select on sequence public.courses_id_seq to service_role;
grant usage, select on sequence public.course_instructor_stats_id_seq
    to service_role;

create function public.replace_stat_resource_snapshot(
    course_rows jsonb,
    instructor_rows jsonb
)
returns table (courses_upserted bigint, instructor_rows_inserted bigint)
language plpgsql
security invoker
set search_path = pg_catalog, public, extensions
as $$
declare
    imported_courses bigint;
    imported_instructors bigint;
begin
    if jsonb_typeof(course_rows) <> 'array'
       or jsonb_typeof(instructor_rows) <> 'array' then
        raise exception 'course_rows and instructor_rows must be JSON arrays';
    end if;

    insert into public.courses (
        course_code,
        subject,
        course_number,
        course_name,
        credits,
        description,
        prerequisites,
        credit_restrictions,
        gen_ed,
        total_students,
        total_sections,
        overall_gpa,
        embedding
    )
    select
        payload->>'course_code',
        payload->>'subject',
        (payload->>'course_number')::integer,
        payload->>'course_name',
        payload->>'credits',
        payload->>'description',
        nullif(payload->>'prerequisites', ''),
        nullif(payload->>'credit_restrictions', ''),
        nullif(payload->>'gen_ed', ''),
        nullif(payload->>'total_students', '')::integer,
        nullif(payload->>'total_sections', '')::integer,
        nullif(payload->>'overall_gpa', '')::numeric,
        (payload->>'embedding')::extensions.vector(1536)
    from jsonb_array_elements(course_rows) as item(payload)
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
    get diagnostics imported_courses = row_count;

    if exists (
        select 1
        from jsonb_array_elements(instructor_rows) as item(payload)
        left join public.courses as course
          on course.course_code = payload->>'course_code'
         and course.subject = payload->>'subject'
         and course.course_number = (payload->>'course_number')::integer
        where course.id is null
    ) then
        raise exception 'instructor_rows contain inconsistent course identifiers';
    end if;

    delete from public.course_instructor_stats as stats
    using public.courses as course
    where stats.course_id = course.id
      and course.course_code in (
          select payload->>'course_code'
          from jsonb_array_elements(course_rows) as item(payload)
      );

    insert into public.course_instructor_stats (
        course_id,
        course_code,
        subject,
        course_number,
        instructor_name,
        instructor_avg_gpa,
        gpa_delta_from_course
    )
    select
        course.id,
        course.course_code,
        course.subject,
        course.course_number,
        payload->>'instructor_name',
        nullif(payload->>'instructor_avg_gpa', '')::numeric,
        nullif(payload->>'gpa_delta_from_course', '')::numeric
    from jsonb_array_elements(instructor_rows) as item(payload)
    join public.courses as course
      on course.course_code = payload->>'course_code'
     and course.subject = payload->>'subject'
     and course.course_number = (payload->>'course_number')::integer;
    get diagnostics imported_instructors = row_count;

    return query select imported_courses, imported_instructors;
end;
$$;

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
    where 1 - (course.embedding <=> query_embedding)
        >= coalesce(match_threshold, 0.0)
    order by course.embedding <=> query_embedding
    limit greatest(1, least(coalesce(match_count, 5), 20));
$$;

revoke all on function public.replace_stat_resource_snapshot(jsonb, jsonb)
    from public, anon, authenticated;
revoke all on function public.match_courses(
    extensions.vector, integer, double precision
) from public, anon, authenticated;
grant execute on function public.replace_stat_resource_snapshot(jsonb, jsonb)
    to service_role;
grant execute on function public.match_courses(
    extensions.vector, integer, double precision
) to service_role;

commit;
