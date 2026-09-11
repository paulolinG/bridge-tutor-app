"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/layout/PageHeader";
import { getMyImpact } from "@/lib/api/impact";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import type { MicrotopicImpact } from "@/lib/types/impact";

const MINUTES_PER_HOUR = 60;
// The widest gain the bar renders at full width. Beyond this the number still
// reads correctly, the bar just saturates.
const DELTA_BAR_MAX = 50;

function formatHours(minutes: number): string {
  const hours = minutes / MINUTES_PER_HOUR;
  return Number.isInteger(hours) ? `${hours}` : hours.toFixed(1);
}

function DeltaRow({ entry }: { entry: MicrotopicImpact }) {
  const measured = entry.average_delta_growth !== null;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-4">
        <p className="text-sm font-medium">{entry.microtopic_label}</p>
        <p className="text-sm tabular-nums">
          {measured ? `+${entry.average_delta_growth!.toFixed(0)} pts` : "Not measured"}
        </p>
      </div>
      {measured && (
        <Progress value={Math.min(entry.average_delta_growth!, DELTA_BAR_MAX)} max={DELTA_BAR_MAX} />
      )}
      {/* The denominator ships with the number, always: an average built from
          one session must never read like one built from fifty. */}
      <p className="text-xs text-muted-foreground">
        Measured in {entry.measured_sessions} of {entry.total_sessions}{" "}
        {entry.total_sessions === 1 ? "session" : "sessions"}
      </p>
    </div>
  );
}

export default function ImpactPage() {
  const { checking } = useRequireAuth();
  const { data, isPending } = useQuery({
    queryKey: ["impact"],
    queryFn: getMyImpact,
    enabled: !checking,
  });

  if (checking || isPending || !data) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-8">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const stats = [
    { label: "Sessions completed", value: `${data.sessions_completed}` },
    { label: "Volunteer hours", value: formatHours(data.volunteer_minutes) },
    { label: "Students helped", value: `${data.students_helped}` },
  ];

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-8">
      <PageHeader
        title="Your impact"
        description="From completed sessions only. Bridge AI records these measurements itself; nothing here is externally verified."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="flex flex-col gap-1">
              <p className="font-heading text-3xl tabular-nums">{stat.value}</p>
              <p className="text-sm text-muted-foreground">{stat.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <h2 className="font-heading text-lg">Average delta growth</h2>
            <p className="text-sm text-muted-foreground">
              How much students gained between the questions they answered
              before and after each session.
            </p>
          </div>

          {data.by_microtopic.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nothing to show yet. Complete a session and this fills in.
            </p>
          ) : (
            data.by_microtopic.map((entry, index) => (
              <div key={entry.microtopic_label} className="flex flex-col gap-4">
                {index > 0 && <Separator />}
                <DeltaRow entry={entry} />
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
