import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="flex flex-1 items-center justify-center p-4 sm:p-8">
      <main className="flex max-w-md flex-col items-center gap-4 text-center">
        <h1 className="font-heading text-3xl font-semibold tracking-tight">
          Bridge AI
        </h1>
        <p className="text-sm text-muted-foreground">
          Free AI-assisted tutoring for underserved communities, matching
          certified volunteer tutors with students who need help.
        </p>
        <Button
          nativeButton={false}
          render={<Link href="/login">Tutor sign in</Link>}
        />
      </main>
    </div>
  );
}
