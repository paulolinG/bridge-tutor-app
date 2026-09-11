import { apiFetch } from "@/lib/api/client";
import type { TutorImpact } from "@/lib/types/impact";

export function getMyImpact(): Promise<TutorImpact> {
  return apiFetch<TutorImpact>("/tutors/me/impact");
}
