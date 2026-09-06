"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
        <p className="text-sm text-muted-foreground">
          We sent a sign-in link to {email}. Open it on this device to
          continue.
        </p>
      </CenteredCard>
    );
  }

  return (
    <CenteredCard title="Sign in">
      <form
        onSubmit={(event) => void handleSubmit(event)}
        className="flex flex-col gap-4"
      >
        <div className="flex flex-col gap-2">
          <label htmlFor="displayName" className="text-sm font-medium">
            Your name
          </label>
          <Input
            id="displayName"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="email" className="text-sm font-medium">
            Email
          </label>
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
          <p className="text-sm text-destructive">
            Could not send the sign-in link. Try again.
          </p>
        )}
      </form>
    </CenteredCard>
  );
}
