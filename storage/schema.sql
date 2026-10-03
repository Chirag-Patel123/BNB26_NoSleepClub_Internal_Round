-- BLACK BOX - shared Supabase PostgreSQL schema
-- P3 owns database migration changes. All other roles consume this schema.

create extension if not exists "uuid-ossp";

create table if not exists runs (
  run_id uuid primary key default uuid_generate_v4(),
  parent_run_id uuid null,
  task text not null,
  scenario_id text not null,
  status text not null,
  agent_version text,
  environment_version text,
  start_time timestamptz,
  end_time timestamptz,
  root_checkpoint_id uuid null,
  created_at timestamptz not null default now()
);

create table if not exists steps (
  id bigserial primary key,
  run_id uuid not null references runs(run_id) on delete cascade,
  step_id text not null,
  parent_step_id text null,
  step_index integer not null,
  step_type text not null,
  input_summary jsonb,
  output_summary jsonb,
  state_before jsonb,
  state_after jsonb,
  tool text,
  model text,
  latency_ms integer,
  tokens integer,
  status text not null,
  error_type text,
  error_message text,
  retry_count integer not null default 0,
  dependency_ids jsonb not null default '[]'::jsonb,
  checkpoint_id uuid null,
  created_at timestamptz not null default now()
);

create table if not exists checkpoints (
  checkpoint_id uuid primary key default uuid_generate_v4(),
  run_id uuid not null references runs(run_id) on delete cascade,
  step_id text not null,
  step_index integer not null,
  state_snapshot jsonb not null,
  context_snapshot jsonb not null,
  completed_steps jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists diagnoses (
  id bigserial primary key,
  run_id uuid not null references runs(run_id) on delete cascade,
  model_version text not null,
  ranked_steps jsonb not null,
  diagnosis_latency_ms integer,
  created_at timestamptz not null default now()
);

create table if not exists experiments (
  experiment_id uuid primary key default uuid_generate_v4(),
  parent_run_id uuid not null references runs(run_id) on delete cascade,
  checkpoint_id uuid not null references checkpoints(checkpoint_id) on delete restrict,
  modified_step text not null,
  modification_type text not null,
  modification_payload jsonb not null,
  new_run_id uuid not null references runs(run_id) on delete restrict,
  result_status text not null,
  created_at timestamptz not null default now()
);

create table if not exists benchmark_cases (
  benchmark_id uuid primary key default uuid_generate_v4(),
  scenario_id text not null,
  failure_type text not null,
  target_step_id text not null,
  split text not null check (split in ('train','validation','test')),
  seed integer not null,
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists model_versions (
  model_version text primary key,
  model_type text not null,
  feature_version text not null,
  metrics jsonb not null default '{}'::jsonb,
  artifact_path text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_runs_status on runs(status);
create index if not exists idx_steps_run_id on steps(run_id);
create index if not exists idx_steps_run_step on steps(run_id, step_index);
create index if not exists idx_diagnoses_run_id on diagnoses(run_id);
create index if not exists idx_experiments_parent on experiments(parent_run_id);
