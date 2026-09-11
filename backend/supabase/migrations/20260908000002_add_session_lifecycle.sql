-- sessions.status had no constraint at all (unlike session_requests.status),
-- and nothing recorded where a session's Daily room lives or when it ended.
alter table sessions add column daily_room_name text;
alter table sessions add column completed_at timestamptz;
alter table sessions add constraint sessions_status_check
  check (status in ('scheduled', 'completed', 'no_show', 'cancelled'));
