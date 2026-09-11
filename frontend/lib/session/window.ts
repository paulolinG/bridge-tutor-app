import type { UpcomingSession } from "@/lib/types/session";

// Mirrors app/services/sessions.py's JOIN_OPENS_BEFORE_MINUTES /
// JOIN_CLOSES_AFTER_MINUTES — the backend is the source of truth and
// re-checks this itself, so a mismatch here only affects when the button
// enables, never whether the call actually connects.
const JOIN_OPENS_BEFORE_MINUTES = 15;
const JOIN_CLOSES_AFTER_MINUTES = 180;
const MINUTE_MS = 60_000;

export function isJoinOpen(startsAt: string, endsAt: string, now: number = Date.now()): boolean {
  const windowStart = new Date(startsAt).getTime() - JOIN_OPENS_BEFORE_MINUTES * MINUTE_MS;
  const windowEnd = new Date(endsAt).getTime() + JOIN_CLOSES_AFTER_MINUTES * MINUTE_MS;
  return now >= windowStart && now <= windowEnd;
}

// Deliberately narrower than `isJoinOpen`: the join link stays valid for
// hours after a session ends so a student on bad Wi-Fi can still reach their
// exit ticket, but a session that has run past `ends_at` is no longer one
// the tutor is sitting in.
export function isOngoing(startsAt: string, endsAt: string, now: number = Date.now()): boolean {
  const windowStart = new Date(startsAt).getTime() - JOIN_OPENS_BEFORE_MINUTES * MINUTE_MS;
  return now >= windowStart && now <= new Date(endsAt).getTime();
}

export function findOngoing(
  sessions: UpcomingSession[],
  now: number = Date.now(),
): UpcomingSession | undefined {
  return sessions.find((session) => isOngoing(session.starts_at, session.ends_at, now));
}
