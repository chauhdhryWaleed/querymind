import * as React from "react";
import { cn } from "@/lib/utils";

/** Centered, max-width body wrapper so page content sits in a readable column
 * instead of stretching full-bleed across wide screens. */
export function PageContainer({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("mx-auto w-full max-w-5xl px-4 py-6 sm:px-6", className)}>
      {children}
    </div>
  );
}
