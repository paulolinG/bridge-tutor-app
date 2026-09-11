export interface UpcomingSession {
  id: string;
  microtopic_label: string;
  starts_at: string;
  ends_at: string;
  join_token: string;
}

export type SessionStatus = "scheduled" | "completed" | "no_show" | "cancelled";

export interface SessionInfo {
  id: string;
  microtopic_label: string;
  starts_at: string;
  ends_at: string;
  status: SessionStatus;
  join_open: boolean;
}

export interface CallCredentials {
  room_url: string;
  token: string;
}

export interface UpdateSessionStatusRequest {
  status: "completed" | "no_show" | "cancelled";
}

export type SenderRole = "tutor" | "student";

export interface SessionMessage {
  id: string;
  sender_role: SenderRole;
  content: string;
  created_at: string;
}

export interface PostMessageRequest {
  content: string;
}

// The tldraw document snapshot shape, opaque to the backend — it only
// stores and returns whatever the client last sent.
export type WhiteboardSnapshot = Record<string, unknown>;

export interface Whiteboard {
  snapshot: WhiteboardSnapshot | null;
}

export interface PutWhiteboardRequest {
  snapshot: WhiteboardSnapshot | null;
}
