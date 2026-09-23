grant delete on table public.signal_definitions to anon, authenticated;

create policy "signal definitions are deletable"
    on public.signal_definitions
    for delete
    to anon, authenticated
    using (true);
