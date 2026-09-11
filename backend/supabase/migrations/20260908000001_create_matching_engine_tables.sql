-- Needed for join_token generation below (gen_random_uuid() is core Postgres,
-- but gen_random_bytes() is pgcrypto).
create extension if not exists pgcrypto with schema extensions;

-- Regions carry the funding-deficit multiplier used in urgency scoring.
create table regions (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  funding_deficit_multiplier numeric not null default 1.0,
  created_at timestamptz not null default now()
);

alter table regions enable row level security;

-- Students never authenticate (see docs/adr/0001-student-profiles-not-auth-users.md):
-- drop the auth.users FK and identify students by phone number instead.
alter table student_profiles drop constraint student_profiles_pkey;
alter table student_profiles alter column id set default gen_random_uuid();
alter table student_profiles add primary key (id);
alter table student_profiles add column phone_number text not null unique;
alter table student_profiles add column academic_average numeric;
alter table student_profiles add column region_id uuid references regions (id);

-- Nullable caps double as the "has completed onboarding" marker: a tutor with
-- no caps set has not filled in the availability + capacity form yet, and is
-- therefore never a match candidate.
alter table tutor_profiles add column daily_cap_minutes int;
alter table tutor_profiles add column weekly_cap_minutes int;

create table tutor_availability (
  id uuid primary key default gen_random_uuid(),
  tutor_id uuid not null references tutor_profiles (id),
  day_of_week int not null check (day_of_week between 0 and 6),
  start_minute int not null,
  end_minute int not null,
  check (start_minute >= 0 and start_minute < end_minute and end_minute <= 1440)
);

alter table tutor_availability enable row level security;

create index tutor_availability_tutor_day_idx on tutor_availability (tutor_id, day_of_week);

create table session_requests (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references student_profiles (id),
  microtopic_id uuid not null references microtopics (id),
  starts_at timestamptz not null,
  duration_minutes int not null check (duration_minutes = 60),
  status text not null default 'pending'
    check (status in ('pending', 'matched', 'expired')),
  created_at timestamptz not null default now()
);

alter table session_requests enable row level security;

create index session_requests_status_starts_at_idx on session_requests (status, starts_at);

create table sessions (
  id uuid primary key default gen_random_uuid(),
  request_id uuid not null references session_requests (id),
  tutor_id uuid not null references tutor_profiles (id),
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  join_token text not null unique default encode(extensions.gen_random_bytes(16), 'hex'),
  status text not null default 'scheduled',
  created_at timestamptz not null default now()
);

alter table sessions enable row level security;

create index sessions_tutor_starts_at_idx on sessions (tutor_id, starts_at);
