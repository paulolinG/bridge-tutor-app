"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { SignOutButton } from "@/components/auth/SignOutButton";

const NAV_LINKS = [
  { href: "/certification", label: "Certification" },
  { href: "/availability", label: "Availability" },
  { href: "/dashboard", label: "Sessions" },
  { href: "/impact", label: "Impact" },
] as const;

export function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="flex items-center justify-between border-b px-4 py-3 sm:px-6">
      <div className="flex items-center gap-6">
        <Link href="/certification" className="font-heading text-sm font-semibold">
          Bridge AI
        </Link>
        <nav className="hidden items-center gap-1 sm:flex">
          {NAV_LINKS.map((link) => {
            const isActive = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
      <SignOutButton />
    </header>
  );
}
