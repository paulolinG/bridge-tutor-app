create table microtopics (
  id uuid primary key default gen_random_uuid(),
  subject text not null,
  topic text not null,
  label text not null unique,
  created_at timestamptz not null default now()
);

alter table microtopics enable row level security;
