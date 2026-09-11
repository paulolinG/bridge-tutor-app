"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PlusIcon, XIcon, AlertCircleIcon, CheckCircle2Icon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { PageHeader } from "@/components/layout/PageHeader";
import { getAvailability, updateAvailability } from "@/lib/api/availability";
import type { Availability, AvailabilityWindow } from "@/lib/types/availability";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";

const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
] as const;

const DEFAULT_DAILY_CAP_MINUTES = 120;
const DEFAULT_WEEKLY_CAP_MINUTES = 600;
const MINUTES_PER_HOUR = 60;
const DEFAULT_WINDOW_START_MINUTE = 16 * 60; // 4:00 PM
const DEFAULT_WINDOW_END_MINUTE = 17 * 60; // 5:00 PM

interface WindowRow extends AvailabilityWindow {
  key: string;
}

function minuteOfDayToTime(minute: number): string {
  const hours = Math.floor(minute / MINUTES_PER_HOUR)
    .toString()
    .padStart(2, "0");
  const minutes = (minute % MINUTES_PER_HOUR).toString().padStart(2, "0");
  return `${hours}:${minutes}`;
}

function timeToMinuteOfDay(time: string): number {
  const [hours, minutes] = time.split(":").map(Number);
  return hours * MINUTES_PER_HOUR + minutes;
}

function toWindowRows(windows: AvailabilityWindow[]): WindowRow[] {
  return windows.map((window, index) => ({
    ...window,
    key: `${window.day_of_week}-${index}-${crypto.randomUUID()}`,
  }));
}

function validate(rows: WindowRow[]): string | null {
  for (const row of rows) {
    if (row.start_minute >= row.end_minute) {
      return `${DAYS[row.day_of_week]}: a window's start time must be before its end time.`;
    }
  }
  for (let day = 0; day < DAYS.length; day++) {
    const dayRows = rows
      .filter((row) => row.day_of_week === day)
      .sort((a, b) => a.start_minute - b.start_minute);
    for (let i = 1; i < dayRows.length; i++) {
      if (dayRows[i].start_minute < dayRows[i - 1].end_minute) {
        return `${DAYS[day]}: time windows can't overlap.`;
      }
    }
  }
  return null;
}

export default function AvailabilityPage() {
  const { checking } = useRequireAuth();
  const queryClient = useQueryClient();

  const { data, isPending, isError } = useQuery({
    queryKey: ["availability"],
    queryFn: getAvailability,
    enabled: !checking,
  });

  const [rows, setRows] = useState<WindowRow[]>([]);
  const [dailyCapHours, setDailyCapHours] = useState(
    DEFAULT_DAILY_CAP_MINUTES / MINUTES_PER_HOUR,
  );
  const [weeklyCapHours, setWeeklyCapHours] = useState(
    DEFAULT_WEEKLY_CAP_MINUTES / MINUTES_PER_HOUR,
  );
  const [initializedFrom, setInitializedFrom] = useState<Availability | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [justSaved, setJustSaved] = useState(false);

  // Adjust local form state during render when fresh query data arrives, rather
  // than in an effect — this is the one-time seed of an editable form from
  // server data, not a subscription, so it belongs in the render path per
  // https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes
  if (data && data !== initializedFrom) {
    setInitializedFrom(data);
    setRows(toWindowRows(data.windows));
    setDailyCapHours((data.daily_cap_minutes ?? DEFAULT_DAILY_CAP_MINUTES) / MINUTES_PER_HOUR);
    setWeeklyCapHours((data.weekly_cap_minutes ?? DEFAULT_WEEKLY_CAP_MINUTES) / MINUTES_PER_HOUR);
  }

  const saveMutation = useMutation({
    mutationFn: () =>
      updateAvailability({
        windows: rows.map(({ day_of_week, start_minute, end_minute }) => ({
          day_of_week,
          start_minute,
          end_minute,
        })),
        daily_cap_minutes: Math.round(dailyCapHours * MINUTES_PER_HOUR),
        weekly_cap_minutes: Math.round(weeklyCapHours * MINUTES_PER_HOUR),
      }),
    onSuccess: (response) => {
      queryClient.setQueryData<Availability>(["availability"], response);
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 3000);
    },
  });

  function addWindow(day: number) {
    setRows((prev) => [
      ...prev,
      {
        key: crypto.randomUUID(),
        day_of_week: day,
        start_minute: DEFAULT_WINDOW_START_MINUTE,
        end_minute: DEFAULT_WINDOW_END_MINUTE,
      },
    ]);
  }

  function removeWindow(key: string) {
    setRows((prev) => prev.filter((row) => row.key !== key));
  }

  function updateWindow(key: string, field: "start_minute" | "end_minute", time: string) {
    setRows((prev) =>
      prev.map((row) =>
        row.key === key ? { ...row, [field]: timeToMinuteOfDay(time) } : row,
      ),
    );
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const error = validate(rows);
    setValidationError(error);
    if (error) return;
    saveMutation.mutate();
  }

  if (checking || isPending) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-8">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-8">
        <PageHeader title="Availability & capacity" />
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertDescription>
            Could not load your availability. Try refreshing the page.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-8">
      <PageHeader
        title="Availability & capacity"
        description="Set the recurring times you're free to tutor and your weekly volunteer limits. This determines whether you're eligible to be matched with a student."
      />

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Weekly availability</CardTitle>
            <CardDescription>
              Add the recurring windows you are free each week, in your local time.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            {DAYS.map((dayLabel, dayIndex) => {
              const dayRows = rows.filter((row) => row.day_of_week === dayIndex);
              return (
                <div
                  key={dayLabel}
                  className="flex flex-col gap-2 sm:flex-row sm:items-start sm:gap-4"
                >
                  <div className="w-24 shrink-0 pt-1.5 text-sm font-medium">
                    {dayLabel}
                  </div>
                  <div className="flex flex-1 flex-col gap-2">
                    {dayRows.map((row) => (
                      <div key={row.key} className="flex items-center gap-2">
                        <Input
                          type="time"
                          value={minuteOfDayToTime(row.start_minute)}
                          onChange={(event) =>
                            updateWindow(row.key, "start_minute", event.target.value)
                          }
                          className="w-32"
                        />
                        <span className="text-sm text-muted-foreground">to</span>
                        <Input
                          type="time"
                          value={minuteOfDayToTime(row.end_minute)}
                          onChange={(event) =>
                            updateWindow(row.key, "end_minute", event.target.value)
                          }
                          className="w-32"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => removeWindow(row.key)}
                          aria-label="Remove this time window"
                        >
                          <XIcon />
                        </Button>
                      </div>
                    ))}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => addWindow(dayIndex)}
                      className="w-fit"
                    >
                      <PlusIcon /> Add time
                    </Button>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Weekly capacity</CardTitle>
            <CardDescription>
              The most volunteer time you are able to give per day and per week.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 sm:flex-row">
            <div className="flex flex-1 flex-col gap-2">
              <Label htmlFor="dailyCap">Daily cap (hours)</Label>
              <Input
                id="dailyCap"
                type="number"
                min={0.5}
                step={0.5}
                value={dailyCapHours}
                onChange={(event) => setDailyCapHours(Number(event.target.value))}
              />
            </div>
            <div className="flex flex-1 flex-col gap-2">
              <Label htmlFor="weeklyCap">Weekly cap (hours)</Label>
              <Input
                id="weeklyCap"
                type="number"
                min={0.5}
                step={0.5}
                value={weeklyCapHours}
                onChange={(event) => setWeeklyCapHours(Number(event.target.value))}
              />
            </div>
          </CardContent>
        </Card>

        {validationError && (
          <Alert variant="destructive">
            <AlertCircleIcon />
            <AlertDescription>{validationError}</AlertDescription>
          </Alert>
        )}
        {saveMutation.isError && (
          <Alert variant="destructive">
            <AlertCircleIcon />
            <AlertDescription>
              Could not save your availability. Try again.
            </AlertDescription>
          </Alert>
        )}

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={saveMutation.isPending}>
            {saveMutation.isPending ? "Saving..." : "Save availability"}
          </Button>
          {justSaved && (
            <span className="flex items-center gap-1 text-sm text-muted-foreground">
              <CheckCircle2Icon className="size-4 text-primary" /> Saved
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
