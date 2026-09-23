-- User-created detectors. Built-in signals stay in the app catalog.
-- Findings still live in public.signals; this table only stores the definition
-- (title + prompt) until a later job evaluates it.

create table public.signal_definitions (
    id          uuid primary key default gen_random_uuid(),
    title       text not null check (char_length(btrim(title)) between 1 and 80),
    prompt      text not null check (char_length(btrim(prompt)) > 0),
    slug        text not null unique check (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    created_at  timestamptz not null default now()
);

create index signal_definitions_created_idx
    on public.signal_definitions (created_at);

alter table public.signal_definitions enable row level security;

grant select, insert on table public.signal_definitions to anon, authenticated;

create policy "signal definitions are readable"
    on public.signal_definitions
    for select
    to anon, authenticated
    using (true);

create policy "signal definitions are insertable"
    on public.signal_definitions
    for insert
    to anon, authenticated
    with check (true);
