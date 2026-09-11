"use client";

import { use, useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertCircleIcon, ChevronDownIcon } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  SESSION_ENDED_EVENT,
  SessionWorkspace,
} from "@/components/session/SessionWorkspace";
import {
  getSessionBaselineScore,
  getSessionWhiteboard,
  listMySessions,
  listSessionMessages,
  postSessionMessage,
  putSessionWhiteboard,
  startTutorCall,
  updateSessionStatus,
} from "@/lib/api/sessions";
import type { CallCredentials, UpdateSessionStatusRequest } from "@/lib/types/session";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";

const STATUS_OPTIONS: { label: string; status: UpdateSessionStatusRequest["status"] }[] = [
  { label: "Completed", status: "completed" },
  { label: "Student didn't show", status: "no_show" },
  { label: "Cancelled", status: "cancelled" },
];

export default function TutorSessionPage(props: PageProps<"/session/[id]">) {
  const { id } = use(props.params);
  const router = useRouter();
  const { checking } = useRequireAuth();
  const [credentials, setCredentials] = useState<CallCredentials | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  // The tutor-facing sessions list already carries this session's details;
  // reuse it rather than adding a single-session GET the backend doesn't have.
  const { data: sessions, isPending } = useQuery({
    queryKey: ["sessions"],
    queryFn: listMySessions,
    enabled: !checking,
  });
  const session = sessions?.find((s) => s.id === id);

  const { data: baseline } = useQuery({
    queryKey: ["session-baseline", id],
    queryFn: () => getSessionBaselineScore(id),
    enabled: !checking,
  });

  // Only ever the number. The two forms share a blueprint, so showing a tutor
  // the baseline items would be showing them the exit ticket.
  const baselineLabel =
    baseline?.score_percent === null || baseline?.score_percent === undefined
      ? null
      : `Baseline ${Math.round(baseline.score_percent)}%`;

  const sendRef = useRef<((event: string, payload: unknown) => void) | null>(null);
  const handleChannelReady = useCallback(
    (send: (event: string, payload: unknown) => void) => {
      sendRef.current = send;
    },
    [],
  );

  const callMutation = useMutation({
    mutationFn: () => startTutorCall(id),
    onSuccess: setCredentials,
  });

  const endMutation = useMutation({
    mutationFn: (status: UpdateSessionStatusRequest["status"]) =>
      updateSessionStatus(id, { status }),
    onSuccess: () => {
      // Flips the student's page to their exit ticket. The backend cannot do
      // this: supabase-py has no broadcast, so it happens from here.
      sendRef.current?.(SESSION_ENDED_EVENT, {});
      router.push("/dashboard");
    },
  });

  if (checking || isPending) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-8">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!session) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-8">
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertDescription>
            Could not find that session. It may not be yours, or the window has closed.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const endSessionMenu = (
    <div className="relative w-fit shrink-0">
      <Button
        variant="outline"
        onClick={() => setMenuOpen((open) => !open)}
        disabled={endMutation.isPending}
      >
        End session
        <ChevronDownIcon />
      </Button>
      {menuOpen && (
        <div className="absolute right-0 z-10 mt-1 flex w-56 flex-col gap-1 rounded-md border bg-popover p-1 shadow-md">
          <p className="px-2 py-1 text-xs text-muted-foreground">
            Sends the student their exit ticket.
          </p>
          {STATUS_OPTIONS.map((option) => (
            <Button
              key={option.status}
              variant="ghost"
              className="justify-start"
              onClick={() => {
                setMenuOpen(false);
                endMutation.mutate(option.status);
              }}
            >
              {option.label}
            </Button>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className="flex flex-1 flex-col">
      <div className="border-b p-4 sm:px-8">
        <PageHeader
          title={session.microtopic_label}
          description={baselineLabel ?? undefined}
          action={endSessionMenu}
        />
      </div>

      {endMutation.isError && (
        <Alert variant="destructive" className="m-4 mb-0 sm:mx-8">
          <AlertCircleIcon />
          <AlertDescription>Could not end the session. Try again.</AlertDescription>
        </Alert>
      )}

      <SessionWorkspace
        sessionId={session.id}
        role="tutor"
        roomUrl={credentials?.room_url ?? null}
        callToken={credentials?.token ?? null}
        callPending={callMutation.isPending}
        callError={callMutation.isError}
        onStartCall={() => callMutation.mutate()}
        onChannelReady={handleChannelReady}
        listMessages={() => listSessionMessages(id)}
        sendMessage={(content) => postSessionMessage(id, { content })}
        getWhiteboard={() => getSessionWhiteboard(id)}
        putWhiteboard={(snapshot) => putSessionWhiteboard(id, { snapshot })}
      />
    </div>
  );
}
