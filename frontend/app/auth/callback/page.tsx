"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { LoaderCircleIcon } from "lucide-react";
import type { Session } from "@supabase/supabase-js";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CenteredCard } from "@/components/layout/CenteredCard";
import { supabase } from "@/lib/supabase/client";
import { ensureTutorProfile } from "@/lib/api/tutors";
import { PENDING_DISPLAY_NAME_KEY } from "@/lib/auth/pendingDisplayName";

const SIGN_IN_TIMEOUT_MS = 10_000;

function readRedirectError(): string | null {
  const params = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.slice(1));
  return (
    params.get("error_description") ?? hashParams.get("error_description")
  );
}

export default function AuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(() =>
    typeof window === "undefined" ? null : readRedirectError(),
  );
  const completedRef = useRef(false);

  useEffect(() => {
    if (error) return;

    async function completeSignIn(session: Session) {
      if (completedRef.current) return;
      completedRef.current = true;

      const storedName = window.localStorage.getItem(PENDING_DISPLAY_NAME_KEY);
      window.localStorage.removeItem(PENDING_DISPLAY_NAME_KEY);
      const displayName =
        storedName?.trim() || session.user.email?.split("@")[0] || "Tutor";

      try {
        await ensureTutorProfile(displayName);
        router.replace("/certification");
      } catch {
        setError(
          "Could not finish setting up your account. Try signing in again.",
        );
      }
    }

    const { data: authListener } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (session) void completeSignIn(session);
      },
    );

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) void completeSignIn(session);
    });

    const timeout = window.setTimeout(() => {
      if (!completedRef.current) {
        setError("Sign-in link is invalid or has expired.");
      }
    }, SIGN_IN_TIMEOUT_MS);

    return () => {
      authListener.subscription.unsubscribe();
      window.clearTimeout(timeout);
    };
  }, [router, error]);

  if (error) {
    return (
      <CenteredCard title="Sign-in problem">
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Link href="/login" className="text-center text-sm underline">
          Back to sign in
        </Link>
      </CenteredCard>
    );
  }

  return (
    <CenteredCard title="Signing you in">
      <div className="flex flex-col items-center gap-3 py-4 text-center">
        <LoaderCircleIcon className="size-6 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">
          Just a moment while we finish setting up your account.
        </p>
      </div>
    </CenteredCard>
  );
}
