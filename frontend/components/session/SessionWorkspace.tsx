"use client";

import { useEffect } from "react";
import dynamic from "next/dynamic";
import { AlertCircleIcon } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SessionStage } from "@/components/session/SessionStage";
import { SessionChat } from "@/components/session/SessionChat";
import { useSessionChannel } from "@/components/session/useSessionChannel";
import { useIsDesktop } from "@/components/session/useIsDesktop";
import type {
  SenderRole,
  SessionMessage,
  Whiteboard,
  WhiteboardSnapshot,
} from "@/lib/types/session";

export const SESSION_ENDED_EVENT = "session-ended";

// tldraw is a heavy package, and this platform exists for people on bad
// connections — keep it out of every bundle except the session pages.
const SessionWhiteboard = dynamic(
  () => import("@/components/session/SessionWhiteboard").then((mod) => mod.SessionWhiteboard),
  { ssr: false, loading: () => <Skeleton className="flex-1 rounded-lg" /> },
);

export function SessionWorkspace({
  sessionId,
  role,
  roomUrl,
  callToken,
  callPending,
  callError,
  onStartCall,
  onSessionEnded,
  onChannelReady,
  listMessages,
  sendMessage,
  getWhiteboard,
  putWhiteboard,
}: {
  sessionId: string;
  role: SenderRole;
  roomUrl: string | null;
  callToken: string | null;
  callPending: boolean;
  callError: boolean;
  onStartCall: () => void;
  onSessionEnded?: () => void;
  onChannelReady?: (send: (event: string, payload: unknown) => void) => void;
  listMessages: () => Promise<SessionMessage[]>;
  sendMessage: (content: string) => Promise<SessionMessage>;
  getWhiteboard: () => Promise<Whiteboard>;
  putWhiteboard: (snapshot: WhiteboardSnapshot | null) => Promise<Whiteboard>;
}) {
  const { send, on } = useSessionChannel(sessionId);
  const isDesktop = useIsDesktop();

  // The tutor's client announces the end of the session: supabase-py cannot
  // broadcast, so the backend has no way to push this itself.
  useEffect(() => {
    if (!onSessionEnded) return;
    return on(SESSION_ENDED_EVENT, onSessionEnded);
  }, [on, onSessionEnded]);

  // Hands the broadcaster up to the page, whose "End session" control lives
  // outside this component but needs to announce on this session's channel.
  useEffect(() => {
    onChannelReady?.(send);
  }, [send, onChannelReady]);

  const videoPane =
    roomUrl && callToken ? (
      <SessionStage roomUrl={roomUrl} token={callToken} />
    ) : (
      <div className="flex aspect-video w-full flex-col items-center justify-center gap-3 rounded-lg border bg-muted p-4">
        {callError && (
          <Alert variant="destructive" className="w-fit">
            <AlertCircleIcon />
            <AlertDescription>Could not connect to the call. Try again.</AlertDescription>
          </Alert>
        )}
        <Button onClick={onStartCall} disabled={callPending}>
          {callPending ? "Connecting..." : "Join call"}
        </Button>
      </div>
    );

  const chatPane = (
    <SessionChat
      role={role}
      listMessages={listMessages}
      sendMessage={sendMessage}
      send={send}
      on={on}
    />
  );

  const whiteboardPane = (
    <SessionWhiteboard
      getWhiteboard={getWhiteboard}
      putWhiteboard={putWhiteboard}
      send={send}
      on={on}
    />
  );

  if (isDesktop) {
    return (
      <div className="flex flex-1 gap-4 p-4 sm:p-8">
        <div className="flex flex-1 flex-col">{whiteboardPane}</div>
        <div className="flex w-80 shrink-0 flex-col gap-4">
          {videoPane}
          {chatPane}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col p-4">
      <Tabs defaultValue="board" className="flex flex-1 flex-col">
        <TabsList className="w-full">
          <TabsTrigger value="board">Board</TabsTrigger>
          <TabsTrigger value="video">Video</TabsTrigger>
          <TabsTrigger value="chat">Chat</TabsTrigger>
        </TabsList>
        <TabsContent value="board" className="flex flex-1 flex-col" keepMounted>
          {whiteboardPane}
        </TabsContent>
        <TabsContent value="video" className="flex flex-1 flex-col" keepMounted>
          {videoPane}
        </TabsContent>
        <TabsContent value="chat" className="flex flex-1 flex-col" keepMounted>
          {chatPane}
        </TabsContent>
      </Tabs>
    </div>
  );
}
