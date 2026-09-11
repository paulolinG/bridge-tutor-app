create table session_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions (id),
  sender_role text not null check (sender_role in ('tutor', 'student')),
  content text not null,
  created_at timestamptz not null default now()
);

alter table session_messages enable row level security;

create index session_messages_session_created_idx on session_messages (session_id, created_at);

alter table sessions add column whiteboard_snapshot jsonb;
