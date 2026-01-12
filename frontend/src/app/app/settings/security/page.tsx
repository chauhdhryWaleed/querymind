"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Loader2, Monitor, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/components/page-container";
import { cn } from "@/lib/utils";
import { passwordStrength } from "@/lib/password";
import { ApiError } from "@/lib/api";
import {
  useChangePassword,
  useDeleteAccount,
  useRevokeSession,
  useSessions,
} from "@/lib/hooks";

export default function SecurityPage() {
  return (
    <PageContainer className="max-w-2xl space-y-6">
      <ChangePasswordCard />
      <SessionsCard />
      <DangerZoneCard />
    </PageContainer>
  );
}

function ChangePasswordCard() {
  const change = useChangePassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const strength = passwordStrength(next);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (next.length < 8) return toast.error("New password must be at least 8 characters");
    if (next !== confirm) return toast.error("New passwords do not match");
    try {
      await change.mutateAsync({ current_password: current, new_password: next });
      toast.success("Password changed. Other sessions were signed out.");
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not change password");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Change password</CardTitle>
        <CardDescription>
          Your password also encrypts your saved credentials. Changing it re-encrypts
          them and signs out your other sessions.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="current">Current password</Label>
            <PasswordInput
              id="current"
              autoComplete="current-password"
              required
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="next">New password</Label>
            <PasswordInput
              id="next"
              autoComplete="new-password"
              required
              value={next}
              onChange={(e) => setNext(e.target.value)}
            />
            {next && (
              <div className="space-y-1">
                <div className="flex gap-1">
                  {[0, 1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className={cn(
                        "h-1 flex-1 rounded-full bg-muted transition-colors",
                        i < strength.score &&
                          (strength.score <= 1
                            ? "bg-destructive"
                            : strength.score === 2
                              ? "bg-warning"
                              : "bg-success"),
                      )}
                    />
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">{strength.label}</p>
              </div>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm">Confirm new password</Label>
            <PasswordInput
              id="confirm"
              autoComplete="new-password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={change.isPending}>
            {change.isPending ? "Updating…" : "Update password"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function SessionsCard() {
  const router = useRouter();
  const { data: sessions, isLoading } = useSessions();
  const revoke = useRevokeSession();

  function onRevoke(id: string, current: boolean) {
    revoke.mutate(id, {
      onSuccess: () => {
        if (current) {
          toast.success("Signed out");
          router.replace("/login");
        } else {
          toast.success("Session revoked");
        }
      },
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Active sessions</CardTitle>
        <CardDescription>Devices currently signed in to your account.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading ? (
          [0, 1].map((i) => <Skeleton key={i} className="h-14 w-full" />)
        ) : (
          sessions?.map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between gap-3 rounded-lg border p-3"
            >
              <div className="flex min-w-0 items-center gap-3">
                <Monitor className="size-4 shrink-0 text-muted-foreground" />
                <div className="min-w-0">
                  <p className="flex items-center gap-2 text-sm font-medium">
                    <span className="truncate">{s.user_agent ?? "Unknown device"}</span>
                    {s.current && <Badge variant="success">this device</Badge>}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">
                    {s.ip ?? "unknown IP"} · since {new Date(s.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                disabled={revoke.isPending}
                onClick={() => onRevoke(s.id, s.current)}
              >
                {s.current ? "Sign out" : "Revoke"}
              </Button>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

function DangerZoneCard() {
  const router = useRouter();
  const del = useDeleteAccount();
  const [open, setOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  async function onDelete() {
    try {
      await del.mutateAsync();
      toast.success("Account deleted");
      router.replace("/signup");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete account");
    }
  }

  return (
    <Card className="border-destructive/40">
      <CardHeader>
        <CardTitle className="text-destructive">Danger zone</CardTitle>
        <CardDescription>
          Permanently delete your account, workspace, connections and keys. This cannot
          be undone.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Dialog open={open} onOpenChange={setOpen}>
          <Button variant="destructive" onClick={() => setOpen(true)}>
            <Trash2 className="size-4" /> Delete account
          </Button>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete account?</DialogTitle>
              <DialogDescription>
                This removes everything tied to your account. Type{" "}
                <span className="font-mono font-medium">DELETE</span> to confirm.
              </DialogDescription>
            </DialogHeader>
            <Input
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="DELETE"
            />
            <DialogFooter>
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                disabled={confirmText !== "DELETE" || del.isPending}
                onClick={onDelete}
              >
                {del.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Trash2 className="size-4" />
                )}
                Delete account
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
