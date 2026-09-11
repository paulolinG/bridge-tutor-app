CONCEPT_BLUEPRINT_INSTRUCTIONS = """\
You are designing a short diagnostic for the microtopic "{microtopic_label}".

Name the five core concepts a {grade_level} student must understand to have
mastered this microtopic. Each should be a short noun phrase, specific enough
that a single question could test it. Order them from most foundational to
most advanced.
"""

DIAGNOSTIC_PAIR_INSTRUCTIONS = """\
You are writing a pre-lesson Baseline Diagnostic and a post-lesson Exit Ticket
for a one-hour tutoring session on "{microtopic_label}", for a {grade_level}
student.

The two forms must be parallel: for each of the five concepts below, write one
baseline item and one exit item testing the same concept at the same
difficulty, differing only in their numbers and wording. A student who
understands the concept should find both equally answerable; a student who has
merely memorised the baseline's answer should gain nothing on the exit item.

The five concepts, in order:
{concepts}

Rules for every item:
- Exactly four options, exactly one unambiguously correct.
- The three wrong options must be plausible mistakes a student actually makes —
  a wrong step, a confused definition, a common miscalculation. Never filler,
  never obviously absurd. The quality of these distractors is what makes the
  measurement meaningful.
- Keep the prompt to one or two sentences, in plain language, readable by a
  student whose first language may not be English.
- No option may reference the other options ("both of the above", "none of
  these").
- Vary which position holds the correct option across the ten items.

Calibrate difficulty to the microtopic and grade level only.
"""
