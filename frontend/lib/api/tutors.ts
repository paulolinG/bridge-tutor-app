import { postJson } from "@/lib/api/client";
import type { TutorProfile } from "@/lib/types/tutor";

export function ensureTutorProfile(displayName: string): Promise<TutorProfile> {
  return postJson<TutorProfile>("/tutors", { display_name: displayName });
}
