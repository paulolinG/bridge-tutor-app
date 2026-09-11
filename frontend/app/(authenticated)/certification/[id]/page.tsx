"use client";

import { use } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircleIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { ChatInput } from "@/components/chat/ChatInput";
import { RubricScoreCard } from "@/components/certification/RubricScoreCard";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  bypassCertification,
  endCertification,
  getCertificationState,
  sendCertificationMessage,
} from "@/lib/api/certification";
import type { CertificationState } from "@/lib/types/certification";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";

// Local-development affordance. The backend enforces this independently and
// answers 404 unless DEV_ALLOW_CERTIFICATION_BYPASS is set there too, so this
// flag only controls whether the button is worth showing.
const BYPASS_ENABLED =
  process.env.NEXT_PUBLIC_DEV_CERTIFICATION_BYPASS === "true";

export default function CertificationSessionPage(
  props: PageProps<"/certification/[id]">,
) {
  const { id } = use(props.params);
  const { checking } = useRequireAuth();
  const queryClient = useQueryClient();
  const queryKey = ["certification", id];

  const { data: state, isPending } = useQuery({
    queryKey,
    queryFn: () => getCertificationState(id),
    enabled: !checking,
  });

  const sendMutation = useMutation({
    mutationFn: (content: string) => sendCertificationMessage(id, content),
    onSuccess: (response, content) => {
      queryClient.setQueryData<CertificationState>(queryKey, (old) => {
        if (!old) return old;
        const now = new Date().toISOString();
        return {
          ...old,
          transcript: [
            ...old.transcript,
            { role: "tutor", content, created_at: now },
            { role: "student", content: response.reply, created_at: now },
          ],
          tutor_turn_count: response.turn_count,
        };
      });
    },
  });

  const endMutation = useMutation({
    mutationFn: () => endCertification(id),
    onSuccess: (response) => {
      queryClient.setQueryData<CertificationState>(queryKey, (old) =>
        old ? { ...old, status: "completed", score: response.score } : old,
      );
    },
  });

  const bypassMutation = useMutation({
    mutationFn: () => bypassCertification(id),
    onSuccess: (response) => {
      queryClient.setQueryData<CertificationState>(queryKey, (old) =>
        old ? { ...old, status: "completed", score: response.score } : old,
      );
    },
  });

  if (checking || isPending || !state) {
    return (
      <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 p-4 sm:p-8">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-[60vh] w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  const isCompleted = state.status === "completed";

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 p-4 sm:p-8">
      <PageHeader title="Tutor certification" />

      <ChatWindow
        messages={state.transcript}
        pendingReply={sendMutation.isPending}
      />

      {!isCompleted && (
        <>
          <ChatInput
            onSend={async (content) => {
              await sendMutation.mutateAsync(content);
            }}
            disabled={sendMutation.isPending || endMutation.isPending}
          />
          <Button
            variant="outline"
            disabled={
              state.tutor_turn_count < state.min_turns_to_end ||
              sendMutation.isPending ||
              endMutation.isPending
            }
            onClick={() => endMutation.mutate()}
          >
            {endMutation.isPending ? "Scoring..." : "End assessment"}
          </Button>
          {BYPASS_ENABLED && (
            <Button
              variant="destructive"
              disabled={bypassMutation.isPending}
              onClick={() => bypassMutation.mutate()}
            >
              {bypassMutation.isPending
                ? "Skipping..."
                : "Dev: skip assessment and pass"}
            </Button>
          )}
          {state.tutor_turn_count < state.min_turns_to_end && (
            <p className="text-xs text-muted-foreground">
              Respond {state.min_turns_to_end - state.tutor_turn_count} more
              time(s) before ending.
            </p>
          )}
          {(sendMutation.isError || endMutation.isError) && (
            <Alert variant="destructive">
              <AlertCircleIcon />
              <AlertDescription>
                {sendMutation.isError &&
                  (sendMutation.error instanceof Error
                    ? sendMutation.error.message
                    : "Could not send your message. Try again.")}
                {endMutation.isError &&
                  (endMutation.error instanceof Error
                    ? endMutation.error.message
                    : "Could not score the assessment. Try again.")}
              </AlertDescription>
            </Alert>
          )}
        </>
      )}

      {state.score && <RubricScoreCard score={state.score} />}
    </div>
  );
}
