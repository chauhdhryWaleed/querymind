"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { PageContainer } from "@/components/page-container";
import { ApiError } from "@/lib/api";
import { useMe, useUpdatePreferences } from "@/lib/hooks";

export default function PreferencesPage() {
  return (
    <PageContainer className="max-w-2xl space-y-6">
      <AppearanceCard />
      <QueryDefaultsCard />
    </PageContainer>
  );
}

function AppearanceCard() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Appearance</CardTitle>
        <CardDescription>Choose how QueryMind looks on this device.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between gap-4">
          <Label>Theme</Label>
          {mounted && (
            <NativeSelect
              className="w-40"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </NativeSelect>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function QueryDefaultsCard() {
  const { data: me } = useMe();
  const workspace = me?.workspaces[0];
  const update = useUpdatePreferences(workspace?.id);

  const [model, setModel] = useState("");
  const [maxRows, setMaxRows] = useState("");
  const [timeout, setTimeoutMs] = useState("");

  useEffect(() => {
    if (!workspace) return;
    setModel(workspace.default_model ?? "");
    setMaxRows(workspace.max_rows != null ? String(workspace.max_rows) : "");
    setTimeoutMs(
      workspace.statement_timeout_ms != null ? String(workspace.statement_timeout_ms) : "",
    );
  }, [workspace]);

  function parseOptionalInt(v: string): number | null | undefined {
    if (v.trim() === "") return null; // cleared ⇒ revert to global default
    const n = Number(v);
    return Number.isFinite(n) ? Math.round(n) : undefined;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!workspace) return;
    const rows = parseOptionalInt(maxRows);
    const ms = parseOptionalInt(timeout);
    if (rows === undefined || ms === undefined) {
      return toast.error("Row limit and timeout must be numbers");
    }
    try {
      await update.mutateAsync({
        default_model: model.trim() || null,
        max_rows: rows,
        statement_timeout_ms: ms,
      });
      toast.success("Preferences saved");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save preferences");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Query defaults</CardTitle>
        <CardDescription>
          Applied to every query in this workspace. Leave a field blank to use the
          system default.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="model">Default model override</Label>
            <Input
              id="model"
              value={model}
              placeholder="e.g. claude-sonnet-4-6"
              onChange={(e) => setModel(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Used unless a specific LLM key overrides the model.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="rows">Max result rows</Label>
              <Input
                id="rows"
                inputMode="numeric"
                value={maxRows}
                placeholder="1000"
                onChange={(e) => setMaxRows(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="timeout">Query timeout (ms)</Label>
              <Input
                id="timeout"
                inputMode="numeric"
                value={timeout}
                placeholder="30000"
                onChange={(e) => setTimeoutMs(e.target.value)}
              />
            </div>
          </div>
          <Button type="submit" disabled={update.isPending || !workspace}>
            {update.isPending ? "Saving…" : "Save preferences"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
