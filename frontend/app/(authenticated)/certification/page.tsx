"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AlertCircleIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CenteredCard } from "@/components/layout/CenteredCard";
import { listMicrotopics, startCertification } from "@/lib/api/certification";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { cn } from "@/lib/utils";

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
      <CenteredCard
        title="Tutor certification"
        description="Pick a subject to start a practice teaching simulation."
      >
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
        <Skeleton className="h-9 w-full" />
      </CenteredCard>
    );
  }

  if (isError) {
    return (
      <CenteredCard title="Tutor certification">
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertDescription>
            Could not load subjects. Try refreshing the page.
          </AlertDescription>
        </Alert>
      </CenteredCard>
    );
  }

  return (
    <CenteredCard
      title="Tutor certification"
      description="Pick a subject to start a practice teaching simulation."
    >
      {microtopics.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No subjects are available for certification yet.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {microtopics.map((microtopic) => (
            <button
              key={microtopic.id}
              type="button"
              aria-pressed={selectedId === microtopic.id}
              onClick={() => setSelectedId(microtopic.id)}
              className={cn(
                "rounded-md border px-3 py-2 text-left text-sm transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                selectedId === microtopic.id
                  ? "border-primary bg-primary/10"
                  : "border-border hover:bg-muted",
              )}
            >
              {microtopic.label}
            </button>
          ))}
        </div>
      )}
      <Button
        disabled={!selectedId || startMutation.isPending}
        onClick={() => selectedId && startMutation.mutate(selectedId)}
      >
        {startMutation.isPending ? "Starting..." : "Start assessment"}
      </Button>
      {startMutation.isError && (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertDescription>
            Could not start the assessment. Try again.
          </AlertDescription>
        </Alert>
      )}
    </CenteredCard>
  );
}
