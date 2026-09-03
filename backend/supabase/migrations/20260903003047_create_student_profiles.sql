create table student_profiles (
  id uuid primary key references auth.users (id),
  display_name text not null,
  grade_level text,
  created_at timestamptz not null default now()
);

alter table student_profiles enable row level security;
