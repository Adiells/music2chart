create table if not exists public.chart_feedback (
    feedback_id uuid primary key,
    created_at timestamptz not null default now(),
    task_id text,
    rating smallint not null check (rating between 1 and 5),
    tags text[] not null default '{}',
    comment text,
    song_name text,
    artist text,
    preset_used text,
    task_metadata jsonb
);

alter table public.chart_feedback enable row level security;
grant usage on schema public to service_role;
grant insert on table public.chart_feedback to service_role;
