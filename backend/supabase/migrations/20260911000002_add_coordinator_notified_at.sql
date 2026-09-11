-- The Coordinator Digest: tracks which matches and expirations have already
-- been reported to the coordinator, so an hourly run reports only what is
-- outstanding rather than what changed in that specific run. This makes
-- delivery retriable — a failed send simply leaves items un-notified for the
-- next run to pick up, instead of losing them.

alter table sessions add column coordinator_notified_at timestamptz;
alter table session_requests add column coordinator_notified_at timestamptz;

-- Everything that already exists is treated as already reported. Without
-- this, the first run after deploying would email a digest of every
-- historical match and expiration at once — noise the coordinator cannot
-- act on, since those sessions are long past.
update sessions set coordinator_notified_at = now();
update session_requests set coordinator_notified_at = now();

create index sessions_unnotified_idx
  on sessions (created_at) where coordinator_notified_at is null;
create index session_requests_unnotified_idx
  on session_requests (status) where coordinator_notified_at is null;
