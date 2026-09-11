import { apiFetch, postJson } from "@/lib/api/client";
import type {
  CertificationState,
  EndCertificationResponse,
  Microtopic,
  SendMessageResponse,
  StartCertificationResponse,
} from "@/lib/types/certification";

export function listMicrotopics(): Promise<Microtopic[]> {
  return apiFetch<Microtopic[]>("/microtopics");
}

export function startCertification(
  microtopicId: string,
): Promise<StartCertificationResponse> {
  return postJson<StartCertificationResponse>("/certifications", {
    microtopic_id: microtopicId,
  });
}

export function sendCertificationMessage(
  certificationId: string,
  content: string,
): Promise<SendMessageResponse> {
  return postJson<SendMessageResponse>(
    `/certifications/${certificationId}/messages`,
    { content },
  );
}

export function endCertification(
  certificationId: string,
): Promise<EndCertificationResponse> {
  return postJson<EndCertificationResponse>(
    `/certifications/${certificationId}/end`,
  );
}

export function getCertificationState(
  certificationId: string,
): Promise<CertificationState> {
  return apiFetch<CertificationState>(`/certifications/${certificationId}`);
}

export function bypassCertification(
  certificationId: string,
): Promise<EndCertificationResponse> {
  return postJson<EndCertificationResponse>(
    `/certifications/${certificationId}/bypass`,
  );
}
