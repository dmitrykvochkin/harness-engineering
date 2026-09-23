-- Recorded conversations (detector input) and human-reviewed labels (ground truth).
--
-- Mirrors data/conversations/{traces,labels}.jsonl and split.json. Detector
-- inputs (runs, events) are readable with the publishable key; labels are
-- readable only with the secret key so held-out ground truth never reaches a
-- client or a detector that uses the public API.

create table public.datasets (
    name         text primary key,
    split_rule   text,
    frozen_at    timestamptz,
    imported_at  timestamptz not null default now()
);

create table public.runs (
    run_id          text primary key,
    dataset         text not null references public.datasets (name) on delete cascade,
    split           text check (split in ('development', 'held_out')),
    trace_id        text not null unique,
    session_id      text,
    user_id         text not null,
    name            text not null,
    agent_version   text not null,
    release         text,
    environment     text not null,
    synthetic       boolean not null default true,
    schema_version  text not null,
    start_time      timestamptz,
    end_time        timestamptz,
    duration_ms     integer,
    tags            text[] not null default '{}',
    metadata        jsonb not null default '{}',
    model           jsonb,
    usage           jsonb,
    imported_at     timestamptz not null default now()
);

create index runs_dataset_split_idx on public.runs (dataset, split);
create index runs_agent_version_idx on public.runs (agent_version);

create table public.events (
    id              text primary key,
    run_id          text not null references public.runs (run_id) on delete cascade,
    seq             integer not null,
    span_id         text,
    parent_span_id  text,
    type            text not null check (
        type in ('system_message', 'user_message', 'generation', 'tool_call', 'tool_result', 'event')
    ),
    role            text not null,
    name            text,
    "timestamp"     timestamptz not null,
    end_timestamp   timestamptz,
    latency_ms      integer,
    content         text not null default '',
    level           text not null default 'default' check (level in ('default', 'warning', 'error')),
    status          text,
    model           text,
    usage           jsonb,
    finish_reason   text,
    tool_name       text,
    tool_call_id    text references public.events (id) on delete cascade deferrable initially deferred,
    tool_call_ids   text[],
    tool_arguments  jsonb,
    tool_result     jsonb,
    attributes      jsonb not null default '{}',
    unique (run_id, seq)
);

create index events_run_seq_idx on public.events (run_id, seq);
create index events_tool_name_idx on public.events (tool_name) where tool_name is not null;

create table public.run_labels (
    run_id            text primary key references public.runs (run_id) on delete cascade,
    scenario_key      text not null unique,
    primary_family    text not null check (
        primary_family in ('user_frustration', 'task_failure', 'forgetting')
    ),
    primary_verdict   text not null check (
        primary_verdict in ('present', 'absent', 'insufficient_evidence')
    ),
    task_expectation  text not null,
    synthetic         boolean not null default true,
    reviewed_by       text not null,
    reviewed_at       timestamptz not null,
    notes             text
);

create table public.signal_labels (
    run_id              text not null references public.run_labels (run_id) on delete cascade,
    signal              text not null check (
        signal in ('user_frustration', 'task_failure', 'forgetting')
    ),
    verdict             text not null check (
        verdict in ('present', 'absent', 'insufficient_evidence')
    ),
    rationale           text not null,
    evidence_event_ids  text[] not null default '{}',
    earlier_event_ids   text[] not null default '{}',
    later_event_ids     text[] not null default '{}',
    grouping_pattern    text,
    recovery_note       text,
    primary key (run_id, signal)
);

create index signal_labels_pattern_idx on public.signal_labels (grouping_pattern)
    where grouping_pattern is not null;

alter table public.datasets      enable row level security;
alter table public.runs          enable row level security;
alter table public.events        enable row level security;
alter table public.run_labels    enable row level security;
alter table public.signal_labels enable row level security;

create policy "datasets are readable" on public.datasets
    for select to anon, authenticated using (true);
create policy "runs are readable" on public.runs
    for select to anon, authenticated using (true);
create policy "events are readable" on public.events
    for select to anon, authenticated using (true);
-- run_labels and signal_labels: no policies, so only the secret key (service_role) can read them.
