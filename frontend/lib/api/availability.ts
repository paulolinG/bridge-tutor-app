import { apiFetch, putJson } from "@/lib/api/client";
import type {
  Availability,
  UpdateAvailabilityRequest,
} from "@/lib/types/availability";

export function getAvailability(): Promise<Availability> {
  return apiFetch<Availability>("/tutors/me/availability");
}

export function updateAvailability(
  body: UpdateAvailabilityRequest,
): Promise<Availability> {
  return putJson<Availability>("/tutors/me/availability", body);
}
