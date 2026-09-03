import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_tutor
from app.core.personas import get_persona_by_key, get_persona_for_microtopic_label
from app.db import certifications as certifications_db
from app.db.microtopics import get_microtopic
from app.models.certification import (
    CertificationStateResponse,
    EndCertificationResponse,
    SendMessageRequest,
    SendMessageResponse,
    StartCertificationRequest,
    StartCertificationResponse,
)
from app.models.message import Message
from app.models.persona import Persona
from app.models.rubric import RubricScore
from app.services.scoring import score_transcript
from app.services.simulation import generate_student_reply

router = APIRouter(prefix="/certifications", tags=["certifications"])

MIN_TURNS_TO_END = 6
MAX_TURNS = 20

AI_UNAVAILABLE_DETAIL = "AI service is temporarily unavailable, please try again"


def _parse_transcript(row: dict[str, Any]) -> list[Message]:
    return [Message.model_validate(m) for m in row["transcript"]]


def _tutor_turn_count(transcript: list[Message]) -> int:
    return sum(1 for message in transcript if message.role == "tutor")


async def _get_owned_certification(certification_id: UUID, tutor_id: UUID) -> dict[str, Any]:
    row = await certifications_db.get_certification(certification_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Certification not found")
    if UUID(row["tutor_id"]) != tutor_id:
        raise HTTPException(status_code=403, detail="Not your certification attempt")
    return row


def _get_persona_for_row_or_500(row: dict[str, Any]) -> Persona:
    persona = get_persona_by_key(row["persona_key"])
    if persona is None:
        raise HTTPException(
            status_code=500, detail="Certification data is inconsistent, contact support"
        )
    return persona


async def _generate_student_reply_or_503(transcript: list[Message], persona: Persona) -> str:
    try:
        return await generate_student_reply(transcript, persona)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=AI_UNAVAILABLE_DETAIL) from exc


async def _score_transcript_or_503(transcript: list[Message], persona: Persona) -> RubricScore:
    try:
        return await score_transcript(transcript, persona)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=AI_UNAVAILABLE_DETAIL) from exc


@router.post("")
async def start_certification(
    body: StartCertificationRequest,
    tutor_id: UUID = Depends(get_current_tutor),
) -> StartCertificationResponse:
    microtopic = await get_microtopic(body.microtopic_id)
    if microtopic is None:
        raise HTTPException(status_code=404, detail="Microtopic not found")

    persona = get_persona_for_microtopic_label(microtopic["label"])
    if persona is None:
        raise HTTPException(
            status_code=404, detail="No certification is available for this subject yet"
        )

    opening_message = await _generate_student_reply_or_503([], persona)

    row = await certifications_db.create_certification(tutor_id, body.microtopic_id, persona.key)
    certification_id = UUID(row["id"])

    transcript = [Message(role="student", content=opening_message)]
    await certifications_db.append_message(certification_id, transcript, expected_version=0)

    return StartCertificationResponse(
        certification_id=certification_id,
        student_facing_blurb=persona.student_facing_blurb,
        opening_message=opening_message,
        min_turns_to_end=MIN_TURNS_TO_END,
        max_turns=MAX_TURNS,
    )


@router.post("/{certification_id}/messages")
async def send_message(
    certification_id: UUID,
    body: SendMessageRequest,
    tutor_id: UUID = Depends(get_current_tutor),
) -> SendMessageResponse:
    row = await _get_owned_certification(certification_id, tutor_id)
    if row["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Certification already completed")

    persona = _get_persona_for_row_or_500(row)
    transcript = _parse_transcript(row)

    if _tutor_turn_count(transcript) >= MAX_TURNS:
        raise HTTPException(
            status_code=400, detail="Maximum turn count reached, end the assessment"
        )

    transcript.append(Message(role="tutor", content=body.content))
    reply = await _generate_student_reply_or_503(transcript, persona)
    transcript.append(Message(role="student", content=reply))

    wrote = await certifications_db.append_message(
        certification_id, transcript, expected_version=row["version"]
    )
    if not wrote:
        raise HTTPException(
            status_code=409,
            detail="This certification was updated by another request, please retry",
        )

    return SendMessageResponse(reply=reply, turn_count=_tutor_turn_count(transcript))


@router.post("/{certification_id}/end")
async def end_certification(
    certification_id: UUID,
    tutor_id: UUID = Depends(get_current_tutor),
) -> EndCertificationResponse:
    row = await _get_owned_certification(certification_id, tutor_id)
    if row["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Certification already completed")

    persona = _get_persona_for_row_or_500(row)
    transcript = _parse_transcript(row)

    if _tutor_turn_count(transcript) < MIN_TURNS_TO_END:
        raise HTTPException(
            status_code=400,
            detail=(
                f"At least {MIN_TURNS_TO_END} exchanges are required before ending the assessment"
            ),
        )

    score = await _score_transcript_or_503(transcript, persona)

    # Credit-granting writes happen before mark_completed flips status to "completed" —
    # if one of these fails, the row is still "in_progress" and /end can be safely retried,
    # instead of the tutor being stuck with a completed-but-uncredited attempt.
    microtopic_id = UUID(row["microtopic_id"])
    if score.passed:
        await asyncio.gather(
            certifications_db.upsert_competency(tutor_id, microtopic_id, certification_id),
            certifications_db.update_tutor_certification_status(tutor_id, "passed"),
        )
    else:
        await certifications_db.update_tutor_certification_status(tutor_id, "failed")

    await certifications_db.mark_completed(certification_id, score)

    return EndCertificationResponse(score=score)


@router.get("/{certification_id}")
async def get_certification_state(
    certification_id: UUID,
    tutor_id: UUID = Depends(get_current_tutor),
) -> CertificationStateResponse:
    row = await _get_owned_certification(certification_id, tutor_id)
    transcript = _parse_transcript(row)

    score = RubricScore.from_row(row) if row["status"] == "completed" else None

    return CertificationStateResponse(
        certification_id=certification_id,
        status=row["status"],
        transcript=transcript,
        tutor_turn_count=_tutor_turn_count(transcript),
        score=score,
        min_turns_to_end=MIN_TURNS_TO_END,
        max_turns=MAX_TURNS,
    )
