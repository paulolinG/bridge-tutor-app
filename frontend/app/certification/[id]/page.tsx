"use client";

import { use } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { ChatInput } from "@/components/chat/ChatInput";
import { RubricScoreCard } from "@/components/certification/RubricScoreCard";
import { SignOutButton } from "@/components/auth/SignOutButton";
import {
  endCertification,
  getCertificationState,
  sendCertificationMessage,
} from "@/lib/api/certification";
import type { CertificationState } from "@/lib/types/certification";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";

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

  if (checking || isPending || !state) {
    return <div className="p-8 text-sm">Loading...</div>;
  }

  const isCompleted = state.status === "completed";

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Tutor certification</h1>
        <SignOutButton />
      </div>

      <ChatWindow messages={state.transcript} />

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
          {state.tutor_turn_count < state.min_turns_to_end && (
            <p className="text-xs text-muted-foreground">
              Respond {state.min_turns_to_end - state.tutor_turn_count} more
              time(s) before ending.
            </p>
          )}
          {sendMutation.isError && (
            <p className="text-sm text-destructive">
              {sendMutation.error instanceof Error
                ? sendMutation.error.message
                : "Could not send your message. Try again."}
            </p>
          )}
          {endMutation.isError && (
            <p className="text-sm text-destructive">
              {endMutation.error instanceof Error
                ? endMutation.error.message
                : "Could not score the assessment. Try again."}
            </p>
          )}
        </>
      )}

      {state.score && <RubricScoreCard score={state.score} />}
    </div>
  );
}
