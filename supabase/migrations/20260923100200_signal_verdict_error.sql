-- A detector that fails (API error, invalid evidence, token limit) is stored
-- as verdict 'error' so the dashboard can show it instead of dropping the row.

alter table public.signals drop constraint if exists signals_verdict_check;

alter table public.signals
    add constraint signals_verdict_check
    check (verdict in ('present', 'absent', 'insufficient_evidence', 'error'));
