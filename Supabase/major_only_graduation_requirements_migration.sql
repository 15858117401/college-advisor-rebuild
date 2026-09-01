begin;

alter table public.graduation_requirement_documents
    drop constraint if exists graduation_requirement_document_scope_is_valid;

update public.graduation_requirement_documents
set parent_document_key = null
where parent_document_key = 'UIUC-LAS-BSLAS-2026-2027';

delete from public.graduation_requirement_documents
where document_key = 'UIUC-LAS-BSLAS-2026-2027';

drop index if exists public.graduation_requirement_shared_version_idx;

alter table public.graduation_requirement_documents
    drop column if exists college_code;

alter table public.graduation_requirement_documents
    drop constraint if exists graduation_requirement_documents_document_type_check;

alter table public.graduation_requirement_documents
    add constraint graduation_requirement_documents_document_type_check
    check (document_type = 'program'),
    add constraint graduation_requirement_document_scope_is_valid
    check (
        document_type = 'program'
        and program_code is not null
        and program_name is not null
        and parent_document_key is null
    );

commit;
