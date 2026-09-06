create table tutor_profiles (
  id uuid primary key references auth.users (id),
  display_name text not null,
  email text not null,
  certification_status text not null default 'not_started'
    check (certification_status in ('not_started', 'in_progress', 'passed', 'failed')),
  created_at timestamptz not null default now()
);

alter table tutor_profiles enable row level security;
