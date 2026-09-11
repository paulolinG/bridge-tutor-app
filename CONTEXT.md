# Bridge AI

An educational platform matching volunteer tutors with students in underserved communities. Single context — one FastAPI backend, one Next.js frontend, one Supabase database.

## Language

### Certification

**Certification** (`tutor_certifications` row):
A single attempt by a tutor at the AI-simulated teaching assessment for one microtopic. Scored on a 100-point rubric across four categories; passing (≥70) grants a **Competency**.
_Avoid_: Assessment (used loosely elsewhere), exam, test.

**Competency** (`tutor_microtopic_competencies` row):
The durable record that a tutor has passed certification for a specific microtopic. What the Matching Engine's domain filter checks — a tutor without a Competency for a microtopic is never in that microtopic's domain.
_Avoid_: Qualification, certification (that's the attempt, this is the outcome).

**Microtopic**:
The atomic unit of subject matter a tutor certifies in and a student requests (e.g. "Physics: Kinematics"). Certifications, Competencies, and Session Requests are all scoped to exactly one microtopic.

### Matching Engine

**Session Request** (`session_requests` row):
A Coordinator-entered ask on behalf of a student: one microtopic, one fixed time window (`starts_at` + a duration), and a computed urgency. Lives as `pending` until a batch run either matches it (→ `matched`) or its window passes unmatched (→ `expired`). Once expired, it appears in exactly one Coordinator Digest and never again.
_Avoid_: Booking, ticket (that's the post-session exit ticket, a different concept).

**Domain**:
The set of tutors eligible for a given pending Session Request at the moment a batch run evaluates it: certified (has a Competency) in the request's microtopic, has a recurring Availability Window covering the request's time, and has remaining daily *and* weekly capacity for the request's duration with no overlapping Session already scheduled. Recomputed fresh on every batch run — never cached.

**Batch Run**:
The hourly execution of the Matching Engine, triggered externally via `pg_cron`/`pg_net` against a shared-secret-protected endpoint. Each run has three phases: it expires any `pending` Session Request whose window has passed and matches the rest (ordered by Urgency Score, ties broken by oldest first, one tutor drawn randomly from each request's Domain); it generates any missing Diagnostic Forms; and it sends the Coordinator Digest. A later phase's failure never undoes an earlier one.

**Coordinator Digest**:
The single plain-text email a Batch Run sends to the one Coordinator address, listing Sessions newly matched and Session Requests newly expired. Each appears in exactly one digest ever — a run with nothing outstanding sends nothing. It is the only thing that tells a Coordinator to act, and therefore the only path by which a student learns they have been matched.
_Avoid_: Notification (vague — it has also meant student messaging, which does not exist).

**Urgency Score**:
A per-Session-Request ranking value computed at batch-run time as the requesting student's academic average multiplied by their Region's funding deficit multiplier (both default to a neutral constant when unset). Determines processing order within a Batch Run when tutor capacity is scarce — never stored, always recomputed.
_Avoid_: Priority score.

**Availability Window** (`tutor_availability` row):
A tutor's recurring weekly commitment to be reachable for a session: a day-of-week plus a local start/end minute range in `America/Toronto`. Distinct from a Session Request's window, which is a single absolute `timestamptz`, not recurring.

**Capacity**:
A tutor's self-declared daily and weekly ceiling on volunteered minutes (`tutor_profiles.daily_cap_minutes` / `weekly_cap_minutes`). Remaining capacity is never stored — always derived by summing the durations of that tutor's already-scheduled Sessions within the relevant local calendar day or Monday–Sunday week.

**Region**:
A Coordinator-defined grouping of students (e.g. a school board catchment) carrying a `funding_deficit_multiplier` used in Urgency Score. A student's Region is optional; unset means the neutral multiplier applies.

**Coordinator**:
A human operating the platform on students' behalf: entering Session Requests, defining Regions, and contacting students when a match is made or a request expires. Not a role in the system — a Coordinator is someone with direct database access, and there is no Coordinator login, account, or dashboard. Tutors are the only authenticated identity in the product.
_Avoid_: Admin (implies a role and a permissions surface that do not exist).

### Sessions

**Session** (`sessions` row):
The scheduled outcome of a successful match: one tutor, one Session Request (via `request_id`), a start/end time, and a Join Token. Moves from `scheduled` to exactly one terminal state — `completed`, `no_show`, or `cancelled` — set by the tutor, never inferred. The anchor object live video, whiteboard, and Delta Growth hang off. Once created, it appears in exactly one Coordinator Digest and never again.
_Avoid_: Booking, lesson, appointment.

**Join Link**:
The unauthenticated URL a student uses to reach a Session, carrying an unguessable Join Token. Durable, not single-use: it is loaded repeatedly across one Session's lifetime — Baseline Diagnostic, the call itself, reconnects after a dropped connection, and the Exit Ticket. Valid only in a window around the Session's scheduled time. Its security rests on the token being unguessable, never on being consumed.

**Session Chat** (`session_messages` row):
The text conversation between tutor and student during a Session, owned by the platform rather than by the video provider — because the AI reads it. Distinct from the certification simulation's messages, which are a tutor talking to a simulated student.

**Error Flag** *(not yet built)*:
A technical mistake or pedagogical misstep the AI identifies during a live Session by reading the whiteboard and Session Chat. Surfaced to the tutor as it happens and persisted for the Session Score Sheet. Never visible to the student.

**Diagnostic Form** (`session_diagnostic_forms` row):
A set of five auto-scored multiple-choice items belonging to one Session, plus the student's answers once submitted. Each Session has exactly two, generated together as a matched pair from the same Concept Blueprint so their scores are comparable. A form is answered once and never revised.
_Avoid_: Quiz, test, assessment (that's Certification).

**Concept Blueprint** (`microtopics.concepts`):
The five concepts a Microtopic's Diagnostic Forms measure, fixed on the Microtopic rather than chosen per Session — so every Session on the same Microtopic measures the same things and their Delta Growths can be averaged together.

**Baseline Diagnostic**:
The Diagnostic Form taken before a Session, on the Join Link page. Offered exactly once and never blocking: a student may skip it, and skipping is permanent.

**Exit Ticket**:
The Diagnostic Form taken after a Session, on the Join Link page. Its difference from the Baseline Diagnostic is Delta Growth.
_Avoid_: "ticket" alone (ambiguous with support-ticket senses).

**Delta Growth**:
For one Session, the percentage-point difference between its Baseline Diagnostic and Exit Ticket — a single number, since a Session covers exactly one microtopic. Computed only for a `completed` Session, and null — never zero — if either Diagnostic Form went unanswered. Never stored; always derived from the two forms. Aggregated by (student, microtopic) it shows a student's progress over time; aggregated by tutor it becomes that tutor's volunteer impact record — which the platform attests to itself and does not claim is externally verified.

**Session Score Sheet** *(not yet built)*:
The per-Session artifact a tutor receives afterwards: the Session's Delta Growth, the Exit Ticket breakdown, and the Session's Error Flags. Distinct from the Certification score, which records one assessment attempt and never changes in response to live Sessions.
