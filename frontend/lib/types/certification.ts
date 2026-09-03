export interface Microtopic {
  id: string;
  subject: string;
  topic: string;
  label: string;
}

export type MessageRole = "tutor" | "student";

export interface ChatMessage {
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface StartCertificationResponse {
  certification_id: string;
  student_facing_blurb: string;
  opening_message: string;
  min_turns_to_end: number;
  max_turns: number;
}

export interface SendMessageResponse {
  reply: string;
  turn_count: number;
}

export interface RubricScore {
  subject_knowledge: number;
  subject_knowledge_rationale: string;
  instructional_quality: number;
  instructional_quality_rationale: string;
  pedagogical_adaptability: number;
  pedagogical_adaptability_rationale: string;
  organization: number;
  organization_rationale: string;
  total_score: number;
  passed: boolean;
}

export interface EndCertificationResponse {
  score: RubricScore;
}

export interface CertificationState {
  certification_id: string;
  status: "in_progress" | "completed";
  transcript: ChatMessage[];
  tutor_turn_count: number;
  score: RubricScore | null;
  min_turns_to_end: number;
  max_turns: number;
}
