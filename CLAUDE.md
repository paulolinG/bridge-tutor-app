# Project Description: Bridge AI: Technical Specification & Project Architecture

## Executive Summary

Bridge AI is an educational platform designed to democratize access to tutoring in underserved and underfunded communities (such as low-income and Indigenous areas in Ontario). The platform mitigates systemic resource barriers—such as unreliable Wi-Fi, language differences, and a lack of hardware—by leveraging an AI assistant that acts as a co-pilot for high school volunteer tutors and generates highly accessible, low-data offline learning materials.

A core differentiator of Bridge AI is its **Delta Growth Tracking System**, which quantitatively measures a student’s academic progress over time. This progress is converted into verified proof of volunteer impact, allowing high school tutors to showcase tangible leadership and community metrics on college applications.

-----

## System Architecture & Technical Stack

* **Frontend:** Next.js (App Router) styled with Tailwind CSS, hosted via Vercel.
  * *State Management & Data Fetching:* TanStack Query calling FastAPI endpoints only; Supabase Auth SDK used directly for authentication. The frontend never queries Supabase directly for data — all data access routes through FastAPI.
* **Backend:** FastAPI (Python) — the single server-side gateway for all data access, AI calls, and third-party integrations.
  * *Integration:* Meta WhatsApp Cloud API via stateless HTTP webhooks.
  * *Security Note:* All generative AI API interactions and administrative tasks execute strictly server-side to protect operational API keys.
* **Database & Auth:** Supabase
  * Stores tutor profiles, verification states, availability matrices, and lesson history.
  * **Auth:** Supabase Auth, magic-link (passwordless) sign-in. Tutor accounts only for now — students have no login anywhere in the product and are identified by WhatsApp phone number instead.
* **Backend Hosting:** Render, free web-service tier. The Matching Engine's hourly batch run is triggered by Supabase's `pg_cron` + `pg_net` extensions calling a backend endpoint over HTTP, protected by a shared-secret header (it's reachable from the public internet).
* **Core Data Structures:** Student and tutor profiles mapping microtopic competencies (e.g., `"Physics: Kinematics"`).
* **Realtime/Video:** Daily.co, free tier (10,000 participant-minutes/month, no credit card required) — comfortably covers pilot-scale volume.
* **Shared Whiteboard:** An embedded open-source library (e.g., tldraw or Excalidraw) rather than a custom-built canvas.
* **Text-to-Speech / Speech-to-Text:** Google Cloud TTS/STT — permanent free tier (4M chars/month TTS, 60 min/month STT), used for WhatsApp voice notes.
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
  * **Onboarding Threshold:** A simulation score of 70/100 or higher is the pass gate. Academic grade, test performance, and extracurricular standing are informational fields shown to admins, not folded into the score.
  * **Out of Scope:** Identity verification and background-check vetting are handled by a separate manual/external process, not modeled in this system.
  * **Post-Certification Onboarding:** A certified tutor must complete a one-time availability + capacity form (also editable later in account settings) before entering the Matching Engine's pool.

### 2\. Algorithmic Matching Engine

To prevent first-come, first-served inefficiencies, matching runs on an hourly batch schedule governed by a randomized domain-selection algorithm: the **domain** is the set of tutors available during the student's requested window, with remaining weekly capacity, and certified in the request's exact microtopic (via `tutor_microtopic_competencies`); a tutor is then selected **randomly** from that domain to ensure fairness rather than favoring whoever responds fastest.

  * **Priority Scoring:** Students are assigned an urgency score derived from a multiplier of their current grades and local school board funding deficits (an admin-entered value per region for v1, not an automated external dataset). When multiple pending requests compete for scarce tutor capacity in a batch run, higher-urgency requests are processed first. Tutors are assigned a quality score based on their certification performance — informational only, shown to admins, never used to bias tutor selection.
  * **Time Normalization:** All inputs are converted into a standardized runtime index of absolute minutes based on Central Time (e.g., 1:30 AM–3:30 AM maps to `90-210`). Each request carries exactly one fixed window, not a range or set of candidate windows.
  * **Capacity Constraints:** Tutors define daily and weekly caps on volunteer minutes. The algorithm dynamically filters out any tutor whose current commitments or preferred hours conflict with a student's window.
  * **Session Requests (v1):** Admin-mediated — a coordinator enters a student's request (microtopic, window) directly into the database. WhatsApp-based request intake is a separate, later feature.
  * **Minimum Lead Time:** A request's window must be at least 2 hours out at entry, so a batch cycle has a realistic chance to match it before it arrives.
  * **Unmatched Requests:** A request with an empty domain stays `pending` and is re-evaluated on every subsequent hourly run — no special retry logic needed. Once its window passes unmatched, it flips to `unmatched`/`expired`, visible on the admin dashboard; it's never silently dropped.
  * **Notification (v1):** No automated messaging. A match or an expiration is admin-mediated — the coordinator sees it on the dashboard and reaches out to the student directly. Automating this over WhatsApp would cost real money per message (Meta retired free business-initiated messaging in 2025) and is deferred to the WhatsApp tutoring feature.

### 3\. Real-Time Session Interaction

  * **Session Access:** No student login — a matched session is joined via an unauthenticated, single-use link (shared by the admin coordinator per the Matching Engine's notification policy). The call runs on Daily's prebuilt embeddable UI (a single iframe), not a custom video UI.
  * **AI Teaching Assistant:** Runs background processes during live lessons to create visual assets, render mathematical graphs, and translate terms across language barriers. Visuals are rendered server-side (e.g., via matplotlib/plotly) and inserted onto the whiteboard as a single image asset — the AI does not manipulate the whiteboard's live document/shapes directly.
  * **Shared Workspace:** A collaborative digital whiteboard equipped with AI-powered solution generation.
  * **Live Error Flagging:** The AI identifies technical mistakes or pedagogical missteps in real time by analyzing whiteboard and chat content only (v1 does not transcribe or analyze live audio), caching them for the tutor's post-session feedback loop. Triggered event-driven and debounced (re-checks once activity pauses after an edit/message) rather than on a fixed polling interval, so AI API usage tracks actual session activity instead of idle time.

### 4\. High-Accessibility / Low-Data Offline Learning

To serve the \~40% of urban low-income households and \>60% of Indigenous communities lacking reliable high-speed internet, Bridge AI acts as an asynchronous learning bridge:

  * **WhatsApp-Based Tutoring:** Leverages the Meta WhatsApp Cloud API for extreme low-data environments. Students send photos of problems or text questions directly to the Bridge AI bot. The backend receives the media via webhooks and returns AI-generated voice notes or text explanations entirely within the free 24-hour user-initiated service window, eliminating MMS/SMS telecom fees.
  * **Student Identity:** A student's WhatsApp phone number is their entire identity — there's no student login system anywhere in the product. A message from an unrecognized number auto-creates a minimal student record rather than requiring prior registration.
  * **Low-Data Data Packages:** At the end of an online session, the system compiles highly compressed, downloadable text packages containing fill-in-the-blank summaries, core concept PDFs, and digital flashcards. Claude generates the content as structured JSON; the backend renders it to PDF with WeasyPrint (free, open-source, no external service).

### 5\. Post-Session Evaluation & The "Continue-Learning" Program

The session workflow does not conclude when the video call disconnects:

1.  **Pre-Session Baseline:** A short, tailored AI-generated diagnostic delivered as a web form on the same unauthenticated join-link page, right before the student enters the call — not via WhatsApp, so it doesn't depend on the student having WhatsApp open at that exact moment.
2.  **Student Diagnostic:** The student completes a short, tailored AI-generated exit ticket to evaluate concept retention.
3.  **Tutor Analytics:** The tutor receives an updated score sheet detailing structural strengths, time management optimization, and a Delta Growth metric: the percentage-point difference between the pre-session baseline diagnostic and the post-session exit ticket, scored per microtopic. Surfaced on the tutor's in-app dashboard (same as match notifications).
4.  **Next-Step Logic:** The AI generates an automated recommendation tracking whether the student should move to independent practice, schedule a reinforcing lesson on a sub-topic, or advance to the next academic chapter.


# Project Status
Feature 1 (Reverse-AI Tutor Assessment & Certification) is implemented end-to-end. Auth is currently stubbed via a dev bypass in `deps.py`; real Supabase Auth (magic link, tutor-only) is next, before building the Algorithmic Matching Engine. Real-Time Session Interaction, WhatsApp/Low-Data Learning, and Post-Session Evaluation are designed (see below) but not yet built.

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