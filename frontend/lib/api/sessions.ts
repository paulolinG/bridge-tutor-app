import { apiFetch, patchJson, postJson, putJson } from "@/lib/api/client";
import type { BaselineScore } from "@/lib/types/diagnostic";
import type {
  CallCredentials,
  PostMessageRequest,
  PutWhiteboardRequest,
  SessionMessage,
  UpcomingSession,
  UpdateSessionStatusRequest,
  Whiteboard,
} from "@/lib/types/session";

export function listMySessions(): Promise<UpcomingSession[]> {
  return apiFetch<UpcomingSession[]>("/tutors/me/sessions");
}

export function startTutorCall(sessionId: string): Promise<CallCredentials> {
  return postJson<CallCredentials>(`/tutors/me/sessions/${sessionId}/call`);
}

export function updateSessionStatus(
  sessionId: string,
  body: UpdateSessionStatusRequest,
): Promise<{ status: string }> {
  return patchJson<{ status: string }>(`/tutors/me/sessions/${sessionId}`, body);
}

export function listSessionMessages(sessionId: string): Promise<SessionMessage[]> {
  return apiFetch<SessionMessage[]>(`/tutors/me/sessions/${sessionId}/messages`);
}

export function postSessionMessage(
  sessionId: string,
  body: PostMessageRequest,
): Promise<SessionMessage> {
  return postJson<SessionMessage>(`/tutors/me/sessions/${sessionId}/messages`, body);
}

export function getSessionWhiteboard(sessionId: string): Promise<Whiteboard> {
  return apiFetch<Whiteboard>(`/tutors/me/sessions/${sessionId}/whiteboard`);
}

export function putSessionWhiteboard(
  sessionId: string,
  body: PutWhiteboardRequest,
): Promise<Whiteboard> {
  return putJson<Whiteboard>(`/tutors/me/sessions/${sessionId}/whiteboard`, body);
}

export function getSessionBaselineScore(sessionId: string): Promise<BaselineScore> {
  return apiFetch<BaselineScore>(`/tutors/me/sessions/${sessionId}/baseline-score`);
}
