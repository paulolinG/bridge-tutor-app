export type DiagnosticKind = "baseline" | "exit";

export interface DiagnosticItem {
  prompt: string;
  options: string[];
}

export interface DiagnosticForm {
  kind: DiagnosticKind;
  items: DiagnosticItem[];
}

export interface CurrentDiagnostic {
  form: DiagnosticForm | null;
}

export interface SubmitDiagnosticRequest {
  answers: number[];
}

export interface SubmitDiagnosticResponse {
  submitted: boolean;
}

export interface BaselineScore {
  score_percent: number | null;
}
