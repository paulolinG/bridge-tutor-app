"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { CenteredCard } from "@/components/layout/CenteredCard";
import { SignOutButton } from "@/components/auth/SignOutButton";
import { listMicrotopics, startCertification } from "@/lib/api/certification";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";

export default function CertificationStartPage() {
  const router = useRouter();
  const { checking } = useRequireAuth();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const {
    data: microtopics,
    isPending,
    isError,
  } = useQuery({
    queryKey: ["microtopics"],
    queryFn: listMicrotopics,
    enabled: !checking,
  });

  const startMutation = useMutation({
    mutationFn: (microtopicId: string) => startCertification(microtopicId),
    onSuccess: (response) => {
      router.push(`/certification/${response.certification_id}`);
    },
  });

  if (checking || isPending) {
    return (
      <CenteredCard title="Tutor certification">
        <p className="text-sm">Loading...</p>
      </CenteredCard>
    );
  }

  if (isError) {
    return (
      <CenteredCard title="Tutor certification">
        <p className="text-sm text-destructive">
          Could not load subjects. Try refreshing the page.
        </p>
      </CenteredCard>
    );
  }

  return (
    <CenteredCard title="Tutor certification">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Pick a subject to start a practice teaching simulation.
        </p>
        <SignOutButton />
      </div>
      <div className="flex flex-col gap-2">
        {microtopics.map((microtopic) => (
          <button
            key={microtopic.id}
            onClick={() => setSelectedId(microtopic.id)}
            className={`rounded-md border px-3 py-2 text-left text-sm ${
              selectedId === microtopic.id
                ? "border-primary bg-primary/10"
                : "border-border"
            }`}
          >
            {microtopic.label}
          </button>
        ))}
      </div>
      <Button
        disabled={!selectedId || startMutation.isPending}
        onClick={() => selectedId && startMutation.mutate(selectedId)}
      >
        {startMutation.isPending ? "Starting..." : "Start assessment"}
      </Button>
      {startMutation.isError && (
        <p className="text-sm text-destructive">
          Could not start the assessment. Try again.
        </p>
      )}
    </CenteredCard>
  );
}
