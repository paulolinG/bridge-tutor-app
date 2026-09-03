"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { listMicrotopics, startCertification } from "@/lib/api/certification";

function CenteredCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Tutor certification</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">{children}</CardContent>
      </Card>
    </div>
  );
}

export default function CertificationStartPage() {
  const router = useRouter();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const {
    data: microtopics,
    isPending,
    isError,
  } = useQuery({
    queryKey: ["microtopics"],
    queryFn: listMicrotopics,
  });

  const startMutation = useMutation({
    mutationFn: (microtopicId: string) => startCertification(microtopicId),
    onSuccess: (response) => {
      router.push(`/certification/${response.certification_id}`);
    },
  });

  if (isPending) {
    return (
      <CenteredCard>
        <p className="text-sm">Loading subjects...</p>
      </CenteredCard>
    );
  }

  if (isError) {
    return (
      <CenteredCard>
        <p className="text-sm text-destructive">
          Could not load subjects. Try refreshing the page.
        </p>
      </CenteredCard>
    );
  }

  return (
    <CenteredCard>
      <p className="text-sm text-muted-foreground">
        Pick a subject to start a practice teaching simulation.
      </p>
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
