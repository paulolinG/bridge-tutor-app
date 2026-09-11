"use client";

import { use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertCircleIcon, ClockIcon } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CenteredCard } from "@/components/layout/CenteredCard";
import { DiagnosticForm } from "@/components/diagnostic/DiagnosticForm";
import { SessionWorkspace } from "@/components/session/SessionWorkspace";
import {
  getJoinDiagnostic,
  getJoinInfo,
  getJoinWhiteboard,
  listJoinMessages,
  postJoinMessage,
  putJoinWhiteboard,
  skipJoinBaseline,
  startStudentCall,
  submitJoinDiagnostic,
} from "@/lib/api/join";
import { ApiError } from "@/lib/api/client";
import type { CallCredentials } from "@/lib/types/session";

const TORONTO_TIME_ZONE = "America/Toronto";

function formatStartTime(startsAt: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: TORONTO_TIME_ZONE,
    weekday: "long",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(startsAt));
}

export default function JoinPage(props: PageProps<"/join/[token]">) {
  const { token } = use(props.params);
  const queryClient = useQueryClient();
  const [credentials, setCredentials] = useState<CallCredentials | null>(null);
  const [entered, setEntered] = useState(false);
  const [justSubmittedExit, setJustSubmittedExit] = useState(false);

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["join", token],
    queryFn: () => getJoinInfo(token),
    retry: false,
  });

  // Polled rather than pushed as well: the tutor's client broadcasts the end
  // of the session, but a student who never entered has no channel open, so
  // the exit ticket has to be able to appear on its own.
  const { data: diagnostic } = useQuery({
    queryKey: ["join-diagnostic", token],
    queryFn: () => getJoinDiagnostic(token),
    enabled: !isError,
    refetchInterval: 30_000,
  });

  const callMutation = useMutation({
    mutationFn: () => startStudentCall(token),
    onSuccess: setCredentials,
  });

  const invalidateDiagnostic = () =>
    queryClient.invalidateQueries({ queryKey: ["join-diagnostic", token] });

  const submitMutation = useMutation({
    mutationFn: (answers: number[]) => {
      const kind = diagnostic?.form?.kind ?? "baseline";
      return submitJoinDiagnostic(token, kind, { answers });
    },
    onSuccess: () => {
      if (diagnostic?.form?.kind === "exit") setJustSubmittedExit(true);
      return invalidateDiagnostic();
    },
  });

  const skipMutation = useMutation({
    mutationFn: () => skipJoinBaseline(token),
    onSuccess: invalidateDiagnostic,
  });

  if (isPending) {
    return (
      <div className="flex flex-1 items-center justify-center p-4 sm:p-8">
        <Skeleton className="h-64 w-full max-w-md" />
      </div>
    );
  }

  if (isError) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <CenteredCard title={notFound ? "Link not found" : "Something went wrong"}>
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertDescription>
            {notFound
              ? "This join link isn't valid. Check the link your coordinator sent you."
              : "Could not load your session. Try refreshing the page."}
          </AlertDescription>
        </Alert>
      </CenteredCard>
    );
  }

  if (justSubmittedExit) {
    // No score: the number is built for the tutor's impact record, and ending
    // a lesson on "2 out of 5" is a discouraging note to finish on.
    return (
      <CenteredCard
        title="All done"
        description="Thanks for working through that — your tutor will see how you did."
      >
        <p className="text-sm text-muted-foreground">
          You can close this page now.
        </p>
      </CenteredCard>
    );
  }

  const form = diagnostic?.form ?? null;

  if (form?.kind === "exit") {
    return (
      <DiagnosticForm
        key="exit"
        form={form}
        submitting={submitMutation.isPending}
        error={submitMutation.isError}
        onSubmit={(answers) => submitMutation.mutate(answers)}
      />
    );
  }

  if (form?.kind === "baseline" && !entered) {
    return (
      <DiagnosticForm
        key="baseline"
        form={form}
        submitting={submitMutation.isPending || skipMutation.isPending}
        error={submitMutation.isError}
        onSubmit={(answers) => submitMutation.mutate(answers)}
        onSkip={() => skipMutation.mutate()}
      />
    );
  }

  if (entered) {
    return (
      <SessionWorkspace
        sessionId={data.id}
        role="student"
        roomUrl={credentials?.room_url ?? null}
        callToken={credentials?.token ?? null}
        callPending={callMutation.isPending}
        callError={callMutation.isError}
        onStartCall={() => callMutation.mutate()}
        onSessionEnded={invalidateDiagnostic}
        listMessages={() => listJoinMessages(token)}
        sendMessage={(content) => postJoinMessage(token, { content })}
        getWhiteboard={() => getJoinWhiteboard(token)}
        putWhiteboard={(snapshot) => putJoinWhiteboard(token, { snapshot })}
      />
    );
  }

  return (
    <CenteredCard
      title={data.microtopic_label}
      description={
        data.join_open ? "Ready when you are." : "Your session hasn't started yet."
      }
    >
      <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <ClockIcon className="size-3.5" />
        {formatStartTime(data.starts_at)}
      </div>
      <Badge variant="secondary" className="w-fit capitalize">
        {data.status}
      </Badge>
      <Button disabled={!data.join_open} onClick={() => setEntered(true)}>
        Enter session
      </Button>
    </CenteredCard>
  );
}
