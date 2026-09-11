export interface MicrotopicImpact {
  microtopic_label: string;
  average_delta_growth: number | null;
  measured_sessions: number;
  total_sessions: number;
}

export interface TutorImpact {
  sessions_completed: number;
  volunteer_minutes: number;
  students_helped: number;
  by_microtopic: MicrotopicImpact[];
}
