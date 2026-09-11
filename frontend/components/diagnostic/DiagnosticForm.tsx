"use client";

import { useState } from "react";
import { AlertCircleIcon } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { DiagnosticForm as Form } from "@/lib/types/diagnostic";

export function DiagnosticForm({
  form,
  submitting,
  error,
  onSubmit,
  onSkip,
}: {
  form: Form;
  submitting: boolean;
  error: boolean;
  onSubmit: (answers: number[]) => void;
  onSkip?: () => void;
}) {
  const [answers, setAnswers] = useState<(number | null)[]>(
    form.items.map(() => null),
  );

  const answered = answers.filter((answer) => answer !== null).length;
  const complete = answered === form.items.length;

  function choose(itemIndex: number, optionIndex: number) {
    setAnswers((current) =>
      current.map((answer, index) => (index === itemIndex ? optionIndex : answer)),
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 p-4 sm:p-8">
      <div className="flex flex-col gap-1">
        <h1 className="font-heading text-2xl">
          {form.kind === "baseline" ? "Before we start" : "One last thing"}
        </h1>
        <p className="text-sm text-muted-foreground">
          {form.kind === "baseline"
            ? "Five quick questions, so your tutor knows where to begin. There are no wrong answers here."
            : "Five quick questions to finish up. Your tutor will see how you did."}
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertDescription>
            Could not send your answers. Try again.
          </AlertDescription>
        </Alert>
      )}

      {form.items.map((item, itemIndex) => (
        <div key={itemIndex} className="flex flex-col gap-3">
          {itemIndex > 0 && <Separator />}
          <p className="text-sm font-medium">
            {itemIndex + 1}. {item.prompt}
          </p>
          <div className="flex flex-col gap-2">
            {item.options.map((option, optionIndex) => (
              <button
                key={optionIndex}
                type="button"
                aria-pressed={answers[itemIndex] === optionIndex}
                onClick={() => choose(itemIndex, optionIndex)}
                className={cn(
                  "rounded-md border px-3 py-2 text-left text-sm transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  answers[itemIndex] === optionIndex
                    ? "border-primary bg-primary/10"
                    : "border-border hover:bg-muted",
                )}
              >
                {option}
              </button>
            ))}
          </div>
        </div>
      ))}

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <Button
          disabled={!complete || submitting}
          onClick={() => onSubmit(answers as number[])}
        >
          {submitting ? "Sending..." : "Submit"}
        </Button>
        {/* Always visible, never blocking: gating a scarce tutoring session
            behind a quiz inverts who the diagnostic is meant to serve. */}
        {onSkip && (
          <Button variant="ghost" onClick={onSkip} disabled={submitting}>
            Skip and join now
          </Button>
        )}
        {!complete && (
          <p className="text-xs text-muted-foreground">
            {answered} of {form.items.length} answered
          </p>
        )}
      </div>
    </div>
  );
}
