"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AlertCircleIcon, CalendarIcon, ClockIcon, CopyIcon, CheckIcon } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/PageHeader";
import { listMySessions } from "@/lib/api/sessions";
import { isJoinOpen } from "@/lib/session/window";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";

const TORONTO_TIME_ZONE = "America/Toronto";

function formatSessionTime(startsAt: string, endsAt: string): string {
  const start = new Date(startsAt);
  const end = new Date(endsAt);
  const dateLabel = new Intl.DateTimeFormat("en-CA", {
    timeZone: TORONTO_TIME_ZONE,
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(start);
  const timeFormatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: TORONTO_TIME_ZONE,
    hour: "numeric",
    minute: "2-digit",
  });
  return `${dateLabel}, ${timeFormatter.format(start)}–${timeFormatter.format(end)}`;
}

function JoinLinkButton({ joinToken }: { joinToken: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    const url = `${window.location.origin}/join/${joinToken}`;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Button variant="outline" size="sm" onClick={() => void handleCopy()}>
      {copied ? <CheckIcon /> : <CopyIcon />}
      {copied ? "Copied" : "Copy join link"}
    </Button>
  );
}

export default function DashboardPage() {
  const { checking } = useRequireAuth();

  const {
    data: sessions,
    isPending,
    isError,
  } = useQuery({
    queryKey: ["sessions"],
    queryFn: listMySessions,
    enabled: !checking,
  });

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-8">
      <PageHeader
        title="Upcoming sessions"
        description="Sessions the Matching Engine has scheduled for you."
      />

      {(checking || isPending) && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      )}

      {!checking && isError && (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertDescription>
            Could not load your sessions. Try refreshing the page.
          </AlertDescription>
        </Alert>
      )}

      {!checking && sessions && sessions.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
            <CalendarIcon className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No sessions scheduled yet. The Matching Engine runs hourly and
              will assign you a session as soon as a request fits
              your availability.
            </p>
          </CardContent>
        </Card>
      )}

      {!checking && sessions && sessions.length > 0 && (
        <div className="flex flex-col gap-3">
          {sessions.map((session) => (
            <Card key={session.id}>
              <CardContent className="flex items-center justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <Badge variant="secondary" className="w-fit">
                    {session.microtopic_label}
                  </Badge>
                  <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                    <ClockIcon className="size-3.5" />
                    {formatSessionTime(session.starts_at, session.ends_at)}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <JoinLinkButton joinToken={session.join_token} />
                  <Button
                    size="sm"
                    disabled={!isJoinOpen(session.starts_at, session.ends_at)}
                    nativeButton={false}
                    render={<Link href={`/session/${session.id}`}>Join</Link>}
                  />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
