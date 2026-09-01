begin;

create table public.graduation_requirement_documents (
    document_key text primary key,
    document_type text not null
        check (document_type = 'program'),
    institution_code text not null,
    degree_code text not null,
    program_code text,
    program_name text,
    catalog_year text not null
        check (catalog_year ~ '^[0-9]{4}-[0-9]{4}$'),
    parent_document_key text
        references public.graduation_requirement_documents(document_key)
        on update cascade
        on delete restrict,
    source_url text not null,
    content_markdown text not null
        check (btrim(content_markdown) <> ''),
    updated_at timestamptz not null default now(),
    constraint graduation_requirement_document_scope_is_valid check (
        document_type = 'program'
        and program_code is not null
        and program_name is not null
        and parent_document_key is null
    )
);

create index graduation_requirement_parent_idx
    on public.graduation_requirement_documents (parent_document_key);

create unique index graduation_requirement_program_version_idx
    on public.graduation_requirement_documents (
        institution_code,
        program_code,
        degree_code,
        catalog_year
    )
    where document_type = 'program';

create or replace function public.touch_graduation_requirement_document_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, public
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger graduation_requirement_documents_touch_updated_at
before update on public.graduation_requirement_documents
for each row
execute function public.touch_graduation_requirement_document_updated_at();

alter table public.graduation_requirement_documents enable row level security;
revoke all on table public.graduation_requirement_documents
    from public, anon, authenticated;
grant select, insert, update, delete
    on table public.graduation_requirement_documents
    to service_role;

commit;
