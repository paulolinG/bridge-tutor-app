-- Feature 5: the Baseline Diagnostic / Exit Ticket pair and Delta Growth.
--
-- `microtopics.concepts` fixes the five concepts a microtopic is measured on.
-- Letting the AI pick concepts per session would mean two sessions on the same
-- microtopic measured two different things, and the tutor impact page's
-- "average Delta Growth per microtopic" would be averaging incomparable
-- numbers. Seeded here for the existing microtopics; a coordinator-added
-- microtopic leaves it null and gets a blueprint derived and backfilled on
-- first use.

alter table microtopics add column concepts jsonb;

update microtopics
set concepts = '["Equivalent fractions", "Common denominators", "Adding and subtracting fractions", "Multiplying and dividing fractions", "Simplifying to lowest terms"]'::jsonb
where label = 'Math: Fractions';

update microtopics
set concepts = '["Distance versus displacement", "Speed versus velocity", "Acceleration", "Uniform-acceleration equations", "Interpreting motion graphs"]'::jsonb
where label = 'Physics: Kinematics';

update microtopics
set concepts = '["Identifying the main idea", "Locating supporting details", "Drawing inferences", "Vocabulary in context", "Author''s purpose and tone"]'::jsonb
where label = 'English: Reading Comprehension';

-- One row per form rather than one row per session: the two forms are
-- generated together but answered hours apart, so each needs its own
-- lifecycle. The unique constraint is what makes the hourly generation sweep
-- idempotent — a re-run inserts nothing instead of duplicating a form.
create table session_diagnostic_forms (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions (id),
  kind text not null check (kind in ('baseline', 'exit')),
  items jsonb not null,
  answers jsonb,
  score_percent numeric,
  skipped boolean not null default false,
  generated_at timestamptz not null default now(),
  submitted_at timestamptz,
  unique (session_id, kind)
);

alter table session_diagnostic_forms enable row level security;

create index session_diagnostic_forms_session_idx on session_diagnostic_forms (session_id);
