"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";

function StatusPage({ status }: { status: string }) {
  return (
    <div className="flex flex-1 items-center justify-center">
      <main className="flex flex-col items-center gap-4 text-center">
        <h1 className="text-2xl font-semibold">Bridge AI</h1>
        <p className="text-sm text-zinc-600">Backend status: {status}</p>
        <Link href="/login" className="text-sm underline">
          Tutor sign in
        </Link>
      </main>
    </div>
  );
}

export default function Home() {
  const { data, isPending, isError } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<{ status: string }>("/health"),
  });

  if (isPending) return <StatusPage status="checking..." />;
  if (isError) return <StatusPage status="unreachable" />;

  return <StatusPage status={data.status} />;
}
