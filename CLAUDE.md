# Project Description: Bridge AI: Technical Specification & Project Architecture

## Executive Summary

Bridge AI is an educational platform designed to democratize access to tutoring in underserved and underfunded communities (such as low-income and Indigenous areas in Ontario). The platform mitigates systemic resource barriers—such as unreliable Wi-Fi, language differences, and a lack of hardware—by leveraging an AI assistant that acts as a co-pilot for high school volunteer tutors and generates highly accessible, low-data offline learning materials.

A core differentiator of Bridge AI is its **Delta Growth Tracking System**, which quantitatively measures a student’s academic progress over time. This progress is aggregated into a tutor impact record — sessions completed, volunteer minutes, students helped, and average Delta Growth per microtopic — that high school tutors can show on college applications. The platform records and attests to its own measurements; it does not claim external verification of them.

-----

## System Architecture & Technical Stack

* **Frontend:** Next.js (App Router) styled with Tailwind CSS, hosted via Vercel.
  * *State Management & Data Fetching:* TanStack Query calling FastAPI endpoints only; Supabase Auth SDK used directly for authentication. The frontend never queries Supabase directly for data — all data access routes through FastAPI. Two deliberate direct-use exceptions: the Auth SDK, and Supabase Realtime as an ephemeral transport for live session state (see `docs/adr/0002-supabase-realtime-whiteboard-transport.md`). Neither reads or writes application tables from the client.
* **Backend:** FastAPI (Python) — the single server-side gateway for all data access, AI calls, and third-party integrations.
  * *Integration:* Meta WhatsApp Cloud API via stateless HTTP webhooks (Feature 4 — designed and decided, deferred until the live session product is built out).
  * *Security Note:* All generative AI API interactions and administrative tasks execute strictly server-side to protect operational API keys.
* **Database & Auth:** Supabase
  * Stores tutor profiles, verification states, availability matrices, and lesson history.
  * **Auth:** Supabase Auth, magic-link (passwordless) sign-in. **Tutors are the only authenticated identity in the product.** Students have no login anywhere and are identified by phone number. Coordinators have no login either — a coordinator is a human with direct database access, not a role in the system, and there is no admin dashboard (see `docs/adr/0003-no-coordinator-role.md`).
* **Backend Hosting:** Render, free web-service tier. The Matching Engine's hourly batch run is triggered by Supabase's `pg_cron` + `pg_net` extensions calling a backend endpoint over HTTP, protected by a shared-secret header (it's reachable from the public internet).
* **Core Data Structures:** Student and tutor profiles mapping microtopic competencies (e.g., `"Physics: Kinematics"`).
* **Realtime/Video:** Daily.co, free tier (10,000 participant-minutes/month, no credit card required) — comfortably covers pilot-scale volume.
* **Shared Whiteboard:** tldraw, embedded rather than a custom-built canvas. Multiplayer sync does *not* come with the library — document deltas are broadcast over **Supabase Realtime** (free tier: 200 concurrent connections, 2M messages/month), which is already provisioned. Self-hosting tldraw's sync server was rejected: it needs a long-lived websocket service, and Render's free tier sleeps after 15 minutes idle.
* **Text-to-Speech / Speech-to-Text:** Google Cloud TTS — permanent free tier (4M chars/month), used for WhatsApp voice-note *replies*. **Speech-to-text is not wired.** The STT free tier is 60 minutes/month total across all users — roughly 120 short voice notes — which cannot support inbound audio at pilot scale. Students send text and photos; the bot may reply with audio.
* **AI Integration:** 
    * *Implementation:* Utilize LangGraph or conversational retrieval chains. The AI is injected with a SystemMessage detailing the student's constraints (e.g., "Act as an 8th grader struggling with fractions. You do not understand common denominators").

    * *Scoring Engine:* Use Claude API and the python Instructor library to force the LLM to output the final 100-point rubric strictly as a validated Pydantic JSON schema at the end of the simulation, rather than parsing raw text.

-----

## Core Features & Workflows

### 1\. Reverse-AI Tutor Assessment & Certification

Before volunteers can accept tutoring sessions, they must pass an automated teaching simulation to ensure safety and quality control.

  * **The Simulation:** A text-based chat exchange where the AI dynamically simulates a student with a specific learning profile (e.g., a language barrier, a specific learning disability, or deep conceptual confusion). Not a voice conversation for v1.
  * **Evaluation Parameters (Weighted out of 100):**
      * **Subject Knowledge (20 pts):** Conceptual accuracy and depth of comprehension.
      * **Instructional Quality (40 pts):** Verbal fluency, pacing, and clarity of explanation, evaluated from the tutor's written responses.
      * **Pedagogical Adaptability (20 pts):** Active checking for understanding (e.g., asking the student to re-explain concepts), patience, and motivational alignment.
      * **Organization (20 pts):** Structure of the lesson plan and scheduling reliability.
  * **Development bypass:** A local-only endpoint can pass a certification without running the assessment, gated on `DEV_ALLOW_CERTIFICATION_BYPASS` and **off by default**. It is enforced server-side — with the flag off, no caller can pass a certification through it regardless of what the frontend shows — and answers 404 rather than 403 when disabled; a bypassed attempt stores rationales stating plainly that nothing was assessed. Never set this flag in a deployed environment — certification is the gate that exists because tutors work with minors.
  * **Onboarding Threshold:** A simulation score of 70/100 or higher is the pass gate. Academic grade, test performance, and extracurricular standing are informational fields a coordinator can read in the database, not folded into the score.
  * **Certification score is immutable.** It records one assessment attempt and is never revised in response to live sessions. Per-session tutor feedback is a separate artifact (Feature 5's Session Score Sheet) — a single bad session must not silently change a tutor's standing with no appeal path.
  * **Out of Scope:** Identity verification and background-check vetting are handled by a separate manual/external process, not modeled in this system.
  * **Post-Certification Onboarding:** A certified tutor must complete a one-time availability + capacity form (also editable later in account settings) before entering the Matching Engine's pool.

### 2\. Algorithmic Matching Engine

To prevent first-come, first-served inefficiencies, matching runs on an hourly batch schedule governed by a randomized domain-selection algorithm: the **domain** is the set of tutors available during the student's requested window, with remaining weekly capacity, and certified in the request's exact microtopic (via `tutor_microtopic_competencies`); a tutor is then selected **randomly** from that domain to ensure fairness rather than favoring whoever responds fastest.

  * **Priority Scoring:** Students are assigned an urgency score derived from a multiplier of their current grades and local school board funding deficits (a coordinator-entered value per region for v1, not an automated external dataset). When multiple pending requests compete for scarce tutor capacity in a batch run, higher-urgency requests are processed first. Tutors are assigned a quality score based on their certification performance — informational only, never used to bias tutor selection.
  * **Time Normalization:** All inputs are converted into a standardized runtime index of absolute minutes in **`America/Toronto`** (e.g., 1:30 AM–3:30 AM maps to `90-210`). The service area is Ontario; Eastern is the only zone the engine reasons in. Each request carries exactly one fixed window, not a range or set of candidate windows.
  * **Capacity Constraints:** Tutors define daily and weekly caps on volunteer minutes. **Both caps gate the domain.** The algorithm dynamically filters out any tutor whose current commitments or preferred hours conflict with a student's window.
  * **Session Requests (v1):** Coordinator-mediated — a coordinator enters a student's request (microtopic, window) directly into the database via the Supabase table editor. WhatsApp-based request intake is explicitly out of scope for the WhatsApp feature too (see Feature 4).
  * **Minimum Lead Time:** A request's window must be at least 2 hours out at entry, so a batch cycle has a realistic chance to match it before it arrives.
  * **Unmatched Requests:** A request with an empty domain stays `pending` and is re-evaluated on every subsequent hourly run — no special retry logic needed. Once its window passes unmatched, it flips to `expired`; it's never silently dropped.
  * **Notification (v1):** No automated student messaging. Each batch run emails a single coordinator address a **Coordinator Digest** of matches and expirations not yet reported; a run with nothing outstanding — which is most runs — sends nothing. The digest carries the student's name and phone number, the microtopic, the `America/Toronto` start time, and the join link itself, so the coordinator can act without opening the database. The coordinator then contacts the student and passes on the link. There is no dashboard to poll, and messaging students directly over WhatsApp would be business-initiated and cost money per message; students have no email address recorded anywhere, so the coordinator is the only path to them.
    * *Delivery:* Resend's HTTPS API on the free tier (3,000/month, no credit card). Render's free tier blocks outbound SMTP ports, so raw SMTP — including Gmail — is not an option. The shared `onboarding@resend.dev` sender needs no domain and no DNS, but **can only deliver to the Resend account owner's own address**, which is exactly the single-coordinator design. Supporting a second coordinator address would require verifying a domain first.
    * *Delivery is tracked, not fire-and-forget:* `coordinator_notified_at` on `sessions` and `session_requests` is stamped only after a successful send, all-or-nothing per digest, so an email failure retries on the next run instead of silently costing a student their session. A duplicate digest is a far better failure than a lost one.

### 3\. Real-Time Session Interaction

Built in four slices, in this order — slice 1 alone makes the product real, and everything after enhances a working session.

  * **Session Access:** No student login — a matched session is joined via an unauthenticated **join link**, passed to the student by the coordinator. The link is **durable, not single-use**: it is loaded repeatedly over one session's life (baseline diagnostic, the call, reconnects on flaky Wi-Fi, exit ticket), and is valid only from ~15 minutes before `starts_at` until a few hours after `ends_at`. Its security rests on an unguessable 128-bit token, never on being consumed — one-shot consumption would fail hardest for exactly the students on unreliable connections this platform exists to serve.
  * **Video:** Daily's prebuilt embeddable UI (a single iframe), not a custom video UI. The room is created **lazily on first join** and its name stored on the session, so cancelled sessions never provision one. The tutor joins from `/dashboard` (authenticated, owns the session); the student joins via the join link. **Both sides get a short-lived meeting token minted server-side** — a room name alone is never enough to enter, so a leaked name is not a way into a live session with a minor. Rooms expire automatically a few hours past `ends_at`.
  * **Session Lifecycle:** `scheduled` → exactly one of `completed`, `no_show`, `cancelled`, set by the tutor from the dashboard. Never inferred from call duration — a tutor can state in one click what a webhook integration would only guess at. Delta Growth is computed only for `completed`.
  * **Shared Workspace:** A collaborative tldraw whiteboard, synced over Supabase Realtime (see the stack section). Both tutor and student can draw.
  * **Session Chat:** A text chat **the platform owns**, persisted to `session_messages` and living in the page around the video iframe. Daily's built-in prebuilt chat is **disabled** — two message boxes on one phone screen is confusing, and a split conversation would silently degrade error flagging by hiding half of it from the AI.
  * **AI Teaching Assistant:** Renders visual assets server-side (matplotlib/plotly) — graphs, worked diagrams, translated terms. **The AI never writes to the whiteboard.** It uploads the image and announces it on the session channel; it surfaces in the tutor's side panel as an "Insert" action, and the tutor's own client performs the document mutation. This keeps the tutor in control of what a student sees, and means the backend needs no headless tldraw runtime to write into a document it is not a participant in.
  * **Live Error Flagging:** The AI identifies technical mistakes or pedagogical missteps by analyzing whiteboard content and session chat only (v1 does not transcribe or analyze live audio). Flags are shown to the **tutor** live in a quiet side panel *and* persisted for the Session Score Sheet — both, not either. **The student never sees a flag**: a mid-lesson "your tutor is wrong" notice would be corrosive to the tutoring relationship.
  * **Error-flagging cost ceiling (the product's only always-on AI cost):** Haiku 4.5; a 45-second floor between calls; a hard **20-call ceiling per session enforced server-side**, not in the client; and a call is skipped entirely when nothing changed since the last one. The payload is a *text* summary of whiteboard shapes plus recent chat — not a rendered board image, which would multiply token cost for little gain on what is mostly text and equations. Ceiling is roughly a cent per session.

### 4\. High-Accessibility / Low-Data Offline Learning

**Status: designed and decided, deferred.** Not built until the live session product (Feature 3) and Post-Session Evaluation (Feature 5) are in place. The decisions below are settled so the work can start cold when it is scheduled.

To serve the \~40% of urban low-income households and \>60% of Indigenous communities lacking reliable high-speed internet, Bridge AI acts as an asynchronous learning bridge:

  * **WhatsApp-Based Tutoring:** Leverages the Meta WhatsApp Cloud API for extreme low-data environments. Students send photos of problems or text questions directly to the Bridge AI bot. The backend receives the media via webhooks and returns AI-generated voice notes or text explanations entirely within the free 24-hour user-initiated service window, eliminating MMS/SMS telecom fees.
  * **Scope:** Asynchronous AI help **only**. The bot never takes session requests. Extracting a microtopic and a valid time window from a conversation with a student who may not know what a microtopic is is a substantially harder problem than answering a photographed math question, and it stays out of scope.
  * **Blocking prerequisite:** Confirm the Meta account path *before* this feature is scheduled, not during it. The free test number reaches only a handful of manually-added recipients; serving real students requires business verification, which involves business documentation rather than a config toggle. If that needs a registered entity this project does not have, the feature is blocked on paperwork regardless of the code.
  * **Student Identity:** A student's phone number is their entire identity — there's no student login system anywhere in the product. A message from an unrecognized number auto-creates a minimal student record rather than requiring prior registration. `display_name` is seeded from the WhatsApp profile name on the inbound webhook, falling back to a masked number ("Student ···4821"); the column stays `not null` rather than spreading a fallback across every surface. Such a student has no academic average and no region, so their urgency score is the neutral constant — **a WhatsApp-originated student ranks below a coordinator-entered student with a known grade average.** That is a real fairness property of the design, not an oversight.
  * **Low-Data Data Packages:** After a session, the system compiles highly compressed, downloadable text packages containing fill-in-the-blank summaries, core concept PDFs, and digital flashcards. Claude generates the content as structured JSON; the backend renders it to PDF with WeasyPrint (free, open-source, no external service). **Delivered on the join link page after the exit ticket, as a download** — never pushed over WhatsApp, which outside a 24-hour service window would be a paid business-initiated message. If the student later writes to the bot within a service window, the link can be sent for free then, but delivery never *depends* on that happening.

### 5\. Post-Session Evaluation & The "Continue-Learning" Program

The session workflow does not conclude when the video call disconnects:

1.  **Diagnostic format:** Exactly five **auto-scored multiple-choice** items, scored deterministically in Python. Exact-numeric answers were considered and rejected: `0.5` / `.5` / `1/2` / `2.5 m/s` normalization is grading hidden in a regex, which defeats the determinism the format exists for. A fixed five also keeps both forms on the same denominator — mismatched counts would make the two percentages incomparable. Delta Growth is a measurement, and an instrument whose readings drift between runs is not one — so the AI's judgement is spent *generating* good items, not grading five multiple-choice answers. Submitting is a plain database write: no AI latency and no per-submission cost for a student on a bad connection.
2.  **Parallel forms:** The baseline and the exit ticket are generated as a **matched pair in a single Claude call** — same concept blueprint, different numbers and wording. Identical questions would inflate every tutor's impact metric through answer recall; independently generated ones would make the delta partly noise. Both are generated **before the session**, from the microtopic and the student's grade level — never from the session transcript, which would make the exit ticket incomparable to the baseline. Items are stored per session; there is no reusable item bank (that needs difficulty calibration, a feature in its own right).
3.  **Pre-Session Baseline:** Delivered as a web form on the join link page, right before the student enters the call — not via WhatsApp, so it doesn't depend on the student having WhatsApp open at that moment. **Shown first but never blocking**: a visible "Skip and join now" is always present. Gating a scarce tutoring session behind a quiz inverts who the diagnostic is meant to serve. **Skipping is permanent** — answering the baseline later, having just been taught the material, would make Delta Growth meaningless. The tutor sees the baseline **score only**, never the items: the two forms share a blueprint, so seeing one is effectively seeing the other, and a tutor who teaches to those items inflates their own impact record.
4.  **Exit Ticket:** When the tutor marks the session `completed`, the student's join link page flips from the video to the exit ticket. The flip is broadcast by the **tutor's own client** over the Realtime channel already open for the whiteboard — supabase-py cannot broadcast, so the backend cannot push it — with a time-based fallback once `ends_at` passes, which also covers a student who never entered and therefore has no channel. Availability is gated on the join window being open and the session not being `cancelled`; it deliberately does **not** require `completed`, unlike chat and whiteboard writes. The tutor's "End session" control says plainly that it sends the student their exit ticket — the tutor is the one person reliably present at that moment.
5.  **Delta Growth:** The percentage-point difference between baseline and exit ticket. Because a session covers exactly one microtopic, a session's Delta Growth is **a single number**; "per microtopic" is the *aggregate across sessions*. Computed only for a `completed` session. **If the baseline was skipped, Delta Growth is null, never zero** — imputing a zero baseline would manufacture an enormous fake delta in precisely the number tutors put on college applications.
6.  **Session Score Sheet:** Per session, the tutor receives the session's Delta Growth, the exit ticket item breakdown, and the session's error flags. Surfaced on the tutor's in-app dashboard. *Not* included: time-management analysis — v1 captures no audio and no per-topic timing, so there is nothing to base it on. This sheet is distinct from the immutable certification score (Feature 1).
7.  **Tutor Impact:** An aggregate view — sessions completed, total volunteer minutes, students helped, and average Delta Growth per microtopic — laid out to print cleanly. A page, not a certificate: nothing external attests to any of it, and handing a student a document claiming verification it does not have would be worse than handing them an honest one.
8.  **Next-Step Logic:** The AI generates a recommendation on whether the student should move to independent practice, schedule a reinforcing lesson on a sub-topic, or advance to the next chapter. **Tutor-facing in v1**, on the Session Score Sheet; it reaches the student through the coordinator, or through the low-data package once Feature 4 exists.


# Project Status
Features 1 (Reverse-AI Tutor Assessment & Certification) and 2 (Algorithmic Matching Engine) are implemented end-to-end, on real Supabase magic-link auth. The matching endpoint is live but its `pg_cron`/`pg_net` hourly trigger is wired by hand after backend deployment.

**Next: Feature 3 (Real-Time Session Interaction)**, in four slices:

1. Join link page + Daily embed + tutor join from `/dashboard` + the session status lifecycle. *This slice alone makes the product real* — two people can hold an actual tutoring session, and the "Copy join link" button already shipped on `/dashboard` stops pointing at a 404. It also exercises the riskiest external dependency (Daily rooms and meeting tokens) before anything is built on top of it.
2. Whiteboard over Supabase Realtime + session chat.
3. Feature 5: baseline/exit ticket + Delta Growth + tutor impact page.
4. Error flags + AI-rendered visuals + session score sheet.

Slices 1, 2 and 3 are built. Diagnostics are generated inside the hourly batch run (see `docs/adr/0004-diagnostics-generated-in-batch-run.md`), capped per run so a persistent failure can never become an unbounded number of AI calls.

Feature 4 (WhatsApp / Low-Data Learning) is designed and decided but deliberately deferred behind all of the above.

# Project Layout
Single repo, no monorepo tooling: `/frontend` (Next.js) and `/backend` (FastAPI) are independent apps with their own dependencies, run separately.

# Development Commands
```bash
# /frontend
npm run dev      # Start development server
npm run build    # Build for production
npm start        # Start production server (after build)
npm run lint      # Lint the codebase
npm run postinstall  # Apply patches after dependency changes
```

```bash
# /backend
uvicorn app.main:app --reload   # Start the FastAPI dev server
ruff check . && black .         # Lint/format
pytest                          # Run tests
```

### User-facing Capitalization

Use sentence case for user-facing copy. Never use fully capitalized words or CSS/Tailwind uppercase transformations unless the capitalization is part of an official tool, product, acronym, initialism, standard, protocol, currency code, or established technical concept name.

### Describe pull requests plainly

Write pull request titles and descriptions in friendly, problem-focused language. Name the user or developer problem, explain why it matters, and describe how the change solves it. Avoid invented taxonomies, severity jargon, or abstract architecture labels when ordinary language explains the issue more clearly.

Prefer "Search could show stale results after navigation" over "Client cache coherence contract violation." Preserve precise technical detail in the implementation and verification sections, but make the problem and the reason for the change easy to understand first.

### Documentation Guidelines

The code should be the single source of truth. Documentation should never restate what the code is doing, as the code should be self-explanatory.

### Core AI Behavior & Output Style

- **Directness:** Omit introductory filler, pleasantries, and apologies. Jump straight into the solution.
- **Code First:** Prioritize writing code over explaining what you are about to do.
- **Show Your Work:** For complex algorithms, architectural decisions, or debugging, wrap your thought process in `<thinking>` tags before outputting the final code.
- **Surgical Edits:** When modifying existing files, only output the changed functions or blocks. Use `...` to represent unchanged code. Do not rewrite the entire file.
- **Self-Correction:** If you realize a proposed approach has edge cases (e.g., race conditions), pivot and address them before finishing the response.


### General Coding Style
All constants should have type hints. Additionally, avoid the use of magic constants. A python example is provided below.
```python3
# Magic constant
if score >= 70:
    return False

# No magic constant with typing hinting
PASSING_SCORE: int = 70
if score >= PASSING_SCORE:
    return False
```

### General Function Documentation Guidelines
Use the common convention for adding docstrings for functions and classes depending on the programming langugage.

A python example is provided below:
```python3
def divide(a: float, b: float) -> float:
    """
    Divide two numbers.

    Args:
        a: The dividend.
        b: The divisor.

    Returns:
        The quotient of a divided by b.

    Raises:
        ZeroDivisionError: If b is zero.
    """
    return a / b
```

### Python Coding Style

- **Strict Typing:** Enforce strict type hints for all function signatures, return types, and complex variables.
- **Performance:** Favor vectorized operations (via NumPy/Pandas) over standard Python `for` loops when handling large datasets or math-heavy simulations.
- **Clean Code:** Follow PEP 8 conventions. Assume code will be formatted by Black and linted by Ruff.
- **Modularity:** Keep functions small and deterministic. When designing simulation frameworks or APIs, separate data ingestion from business logic. 

### TypeScript, React & Next.js Coding Style

- **No Implicit Any:** Strictly type all variables, component props, and API responses using `interface` or `type`. Use `unknown` instead of `any` when data structure is uncertain.
- **React Patterns:** Default to functional components. Avoid unnecessary `useEffect` hooks—derive state during render whenever possible.
- **Next.js App Router:** Explicitly declare `"use client"` only when browser APIs or interactivity are required. Default to Server Components for data fetching and layout.
- **Error Handling:** Use early returns to handle loading states or errors, keeping the happy path un-nested at the bottom of the component.

### Testing

Backend: pytest, focused on the matching algorithm and rubric scoring logic — the two places with real business logic worth protecting. Frontend: no test framework for now; revisit once there's UI complexity that justifies it.

### Low to no cost

This is a near-zero-budget project. Default every service choice to its most generous free tier (hosting, database, video/whiteboard infra, TTS/STT, etc.). Before implementing anything that isn't free — including AI API usage beyond free credits — explicitly call out the cost before making the change.