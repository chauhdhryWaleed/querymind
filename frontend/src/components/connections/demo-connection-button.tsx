"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Loader2, Sparkles } from "lucide-react";
import { Button, type ButtonProps } from "@/components/ui/button";
import { useCreateDemoConnection } from "@/lib/hooks";
import { ApiError } from "@/lib/api";

/** One-click button that adds the seeded read-only `demo` database as a
 * connection and navigates to it. Idempotent on the backend. */
export function DemoConnectionButton({
  variant = "outline",
  className,
}: {
  variant?: ButtonProps["variant"];
  className?: string;
}) {
  const router = useRouter();
  const demo = useCreateDemoConnection();

  async function onClick() {
    try {
      await demo.mutateAsync();
      toast.success("Demo database connected - indexing its schema…");
      router.push("/app/connections");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not add the demo database");
    }
  }

  return (
    <Button variant={variant} className={className} disabled={demo.isPending} onClick={onClick}>
      {demo.isPending ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
      Try the demo database
    </Button>
  );
}
