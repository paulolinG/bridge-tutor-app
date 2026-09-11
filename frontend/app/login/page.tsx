"use client";

import { useState } from "react";
import { MailCheckIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CenteredCard } from "@/components/layout/CenteredCard";
import { supabase } from "@/lib/supabase/client";
import { PENDING_DISPLAY_NAME_KEY } from "@/lib/auth/pendingDisplayName";

type Status = "idle" | "sending" | "sent" | "error";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [status, setStatus] = useState<Status>("idle");

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setStatus("sending");

    window.localStorage.setItem(PENDING_DISPLAY_NAME_KEY, displayName.trim());

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    });

    setStatus(error ? "error" : "sent");
  }

  if (status === "sent") {
    return (
      <CenteredCard title="Check your email">
        <div className="flex flex-col items-center gap-3 text-center">
          <MailCheckIcon className="size-8 text-primary" />
          <p className="text-sm text-muted-foreground">
            We sent a sign-in link to <span className="font-medium text-foreground">{email}</span>.
            Open it on this device to continue.
          </p>
          <Button variant="ghost" size="sm" onClick={() => setStatus("idle")}>
            Use a different email
          </Button>
        </div>
      </CenteredCard>
    );
  }

  return (
    <CenteredCard
      title="Sign in"
      description="Enter your name and email to get a magic sign-in link."
    >
      <form
        onSubmit={(event) => void handleSubmit(event)}
        className="flex flex-col gap-4"
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="displayName">Your name</Label>
          <Input
            id="displayName"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </div>
        <Button type="submit" disabled={status === "sending"}>
          {status === "sending" ? "Sending..." : "Send sign-in link"}
        </Button>
        {status === "error" && (
          <Alert variant="destructive">
            <AlertDescription>
              Could not send the sign-in link. Try again.
            </AlertDescription>
          </Alert>
        )}
      </form>
    </CenteredCard>
  );
}
