export interface TutorProfile {
  id: string;
  display_name: string;
  email: string;
  certification_status: "not_started" | "in_progress" | "passed" | "failed";
}
