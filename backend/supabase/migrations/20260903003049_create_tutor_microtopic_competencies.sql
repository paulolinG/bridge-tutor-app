create table tutor_microtopic_competencies (
  id uuid primary key default gen_random_uuid(),
  tutor_id uuid not null references tutor_profiles (id),
  microtopic_id uuid not null references microtopics (id),
  certification_id uuid not null references tutor_certifications (id),
  certified_at timestamptz not null default now(),
  unique (tutor_id, microtopic_id)
);

alter table tutor_microtopic_competencies enable row level security;
