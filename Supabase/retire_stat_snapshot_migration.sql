-- Apply only after the complete LAS importer has passed remote verification.
-- The runtime tools use create_supabase_client; no callers of this RPC remain.
begin;
drop function if exists public.replace_stat_resource_snapshot(jsonb, jsonb);
commit;
