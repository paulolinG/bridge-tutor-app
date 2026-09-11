import { apiFetch, postJson, putJson } from "@/lib/api/client";
import type {
  CurrentDiagnostic,
  DiagnosticKind,
  SubmitDiagnosticRequest,
  SubmitDiagnosticResponse,
} from "@/lib/types/diagnostic";
import type {
  CallCredentials,
  PostMessageRequest,
  PutWhiteboardRequest,
  SessionInfo,
  SessionMessage,
  Whiteboard,
} from "@/lib/types/session";

export function getJoinInfo(joinToken: string): Promise<SessionInfo> {
  return apiFetch<SessionInfo>(`/join/${joinToken}`);
}

export function startStudentCall(joinToken: string): Promise<CallCredentials> {
  return postJson<CallCredentials>(`/join/${joinToken}/call`);
}

export function listJoinMessages(joinToken: string): Promise<SessionMessage[]> {
  return apiFetch<SessionMessage[]>(`/join/${joinToken}/messages`);
}

export function postJoinMessage(
  joinToken: string,
  body: PostMessageRequest,
): Promise<SessionMessage> {
  return postJson<SessionMessage>(`/join/${joinToken}/messages`, body);
}

export function getJoinWhiteboard(joinToken: string): Promise<Whiteboard> {
  return apiFetch<Whiteboard>(`/join/${joinToken}/whiteboard`);
}

export function putJoinWhiteboard(
  joinToken: string,
  body: PutWhiteboardRequest,
): Promise<Whiteboard> {
  return putJson<Whiteboard>(`/join/${joinToken}/whiteboard`, body);
}

export function getJoinDiagnostic(joinToken: string): Promise<CurrentDiagnostic> {
  return apiFetch<CurrentDiagnostic>(`/join/${joinToken}/diagnostic`);
}

export function submitJoinDiagnostic(
  joinToken: string,
  kind: DiagnosticKind,
  body: SubmitDiagnosticRequest,
): Promise<SubmitDiagnosticResponse> {
  return postJson<SubmitDiagnosticResponse>(
    `/join/${joinToken}/diagnostic/${kind}`,
    body,
  );
}

export function skipJoinBaseline(
  joinToken: string,
): Promise<SubmitDiagnosticResponse> {
  return postJson<SubmitDiagnosticResponse>(
    `/join/${joinToken}/diagnostic/baseline/skip`,
  );
}
