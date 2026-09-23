-- Findings for user-created signals live in public.signals next to the built-in
-- ones. Such a row has signal_type = the definition's slug and points at the
-- definition, so deleting the definition deletes its findings. Built-in rows
-- keep signal_definition_id null and one of the three fixed types.

alter table public.signals
    add column signal_definition_id uuid
        references public.signal_definitions (id) on delete cascade;

alter table public.signals drop constraint if exists signals_signal_type_check;

alter table public.signals
    add constraint signals_signal_type_check check (
        (signal_definition_id is null
            and signal_type in ('user_frustration', 'task_failure', 'forgetting'))
        or signal_definition_id is not null
    );

create index signals_definition_idx on public.signals (signal_definition_id)
    where signal_definition_id is not null;
