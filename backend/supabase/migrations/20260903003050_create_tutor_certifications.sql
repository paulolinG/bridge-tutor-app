create table tutor_certifications (
  id uuid primary key default gen_random_uuid(),
  tutor_id uuid not null references tutor_profiles (id),
  microtopic_id uuid not null references microtopics (id),
  persona_key text not null,
  transcript jsonb not null default '[]',
  version int not null default 0,
  status text not null default 'in_progress'
    check (status in ('in_progress', 'completed')),
  subject_knowledge_score int check (subject_knowledge_score between 0 and 20),
  subject_knowledge_rationale text,
  instructional_quality_score int check (instructional_quality_score between 0 and 40),
  instructional_quality_rationale text,
  pedagogical_adaptability_score int check (pedagogical_adaptability_score between 0 and 20),
  pedagogical_adaptability_rationale text,
  organization_score int check (organization_score between 0 and 20),
  organization_rationale text,
  total_score int generated always as (
    coalesce(subject_knowledge_score, 0)
    + coalesce(instructional_quality_score, 0)
    + coalesce(pedagogical_adaptability_score, 0)
    + coalesce(organization_score, 0)
  ) stored,
  passed boolean generated always as (
    (
      coalesce(subject_knowledge_score, 0)
      + coalesce(instructional_quality_score, 0)
      + coalesce(pedagogical_adaptability_score, 0)
      + coalesce(organization_score, 0)
    ) >= 70
  ) stored,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

alter table tutor_certifications enable row level security;
