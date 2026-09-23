-- Detector output: per-run signal findings and the grouped issues they roll up into.
--
-- These are the tables the `signals` and `issues` edge functions read. They
-- start empty; the detector and grouping stages write them. Findings are kept
-- separate from signal_labels so evaluation compares two independent sources.

create table public.issues (
    id                     uuid primary key default gen_random_uuid(),
    signal_type            text not null check (
        signal_type in ('user_frustration', 'task_failure', 'forgetting')
    ),
    pattern                text not null,
    title                  text not null,
    description            text,
    root_cause_hypothesis  text,
    affected_run_count     integer not null default 0,
    representative_run_ids text[] not null default '{}',
    created_at             timestamptz not null default now(),
    updated_at             timestamptz not null default now(),
    unique (signal_type, pattern)
);

create table public.signals (
    id                  uuid primary key default gen_random_uuid(),
    run_id              text not null references public.runs (run_id) on delete cascade,
    signal_type         text not null check (
        signal_type in ('user_frustration', 'task_failure', 'forgetting')
    ),
    verdict             text not null check (
        verdict in ('present', 'absent', 'insufficient_evidence')
    ),
    explanation         text not null,
    evidence_event_ids  text[] not null default '{}',
    pattern             text,
    issue_id            uuid references public.issues (id) on delete set null,
    detector_version    text not null,
    created_at          timestamptz not null default now(),
    unique (run_id, signal_type, detector_version)
);

create index signals_type_created_idx on public.signals (signal_type, created_at desc);
create index signals_issue_idx on public.signals (issue_id);

alter table public.issues  enable row level security;
alter table public.signals enable row level security;

create policy "issues are readable" on public.issues
    for select to anon, authenticated using (true);
create policy "signals are readable" on public.signals
    for select to anon, authenticated using (true);
