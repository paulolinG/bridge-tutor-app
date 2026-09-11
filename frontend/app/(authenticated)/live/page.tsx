"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AlertCircleIcon, CalendarIcon, LoaderCircleIcon } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/layout/PageHeader";
import { listMySessions } from "@/lib/api/sessions";
import { findOngoing } from "@/lib/session/window";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";

// A session can begin while this page is open, so it re-checks rather than
// leaving a tutor looking at "No active session" through the first minutes
// of their own lesson.
const ONGOING_POLL_MS = 30_000;

export default function LiveSessionPage() {
  const router = useRouter();
  const { checking } = useRequireAuth();

  const { data: sessions, isPending, isError } = useQuery({
    queryKey: ["sessions"],
    queryFn: listMySessions,
    enabled: !checking,
    refetchInterval: ONGOING_POLL_MS,
  });

  const ongoing = sessions ? findOngoing(sessions) : undefined;

  useEffect(() => {
    if (ongoing) router.replace(`/session/${ongoing.id}`);
  }, [ongoing, router]);

  if (checking || isPending) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-8">
        <PageHeader title="Live session" />
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <LoaderCircleIcon className="size-6 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Checking for an active session...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-8">
        <PageHeader title="Live session" />
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertDescription>
            Could not load your sessions. Try refreshing the page.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (ongoing) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-8">
        <PageHeader title="Live session" />
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <LoaderCircleIcon className="size-6 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">
              Taking you to {ongoing.microtopic_label}...
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-8">
      <PageHeader
        title="Live session"
        description="Jumps straight into a session that is running now."
      />
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
          <CalendarIcon className="size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            No active session. This page will take you straight into your
            session once one starts.
          </p>
          <Button
            variant="outline"
            size="sm"
            nativeButton={false}
            render={<Link href="/dashboard">See upcoming sessions</Link>}
          />
        </CardContent>
      </Card>
    </div>
  );
}
