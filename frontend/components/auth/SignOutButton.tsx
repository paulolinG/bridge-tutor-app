"use client";

import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { supabase } from "@/lib/supabase/client";

export function SignOutButton() {
  const router = useRouter();
  const queryClient = useQueryClient();

  async function handleSignOut() {
    await supabase.auth.signOut();
    // Cached queries (certification state, microtopics) are keyed by id but live in a
    // page-level QueryClient singleton — clear them so a different tutor signing in on
    // the same browser never sees a flash of the previous tutor's cached data.
    queryClient.clear();
    router.replace("/login");
  }

  return (
    <Button variant="ghost" size="sm" onClick={() => void handleSignOut()}>
      Sign out
    </Button>
  );
}
