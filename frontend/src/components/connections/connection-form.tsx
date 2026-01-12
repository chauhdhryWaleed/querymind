"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { useCreateConnection, useUpdateConnection } from "@/lib/hooks";
import { ApiError } from "@/lib/api";
import type { ConnectionOut } from "@/lib/types";

const RO_ROLE_SNIPPET = `-- Recommended: a dedicated read-only role
CREATE ROLE t2s_reader WITH LOGIN PASSWORD '••••••';
GRANT CONNECT ON DATABASE your_db TO t2s_reader;
GRANT USAGE ON SCHEMA public TO t2s_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO t2s_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO t2s_reader;`;

export function ConnectionForm({ existing }: { existing?: ConnectionOut }) {
  const router = useRouter();
  const create = useCreateConnection();
  const update = useUpdateConnection(existing?.id ?? "");
  const editing = !!existing;

  const [form, setForm] = useState({
    name: existing?.name ?? "",
    dialect: existing?.dialect ?? "postgres",
    host: existing?.host ?? "",
    port: existing?.port ?? 5432,
    database: existing?.database ?? "",
    username: existing?.username ?? "",
    password: "",
    ssl_mode: existing?.ssl_mode ?? "",
    read_only: existing?.read_only ?? true,
  });

  function set<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (editing) {
        const patch: Record<string, unknown> = {
          name: form.name,
          host: form.host,
          port: form.port,
          database: form.database,
          username: form.username,
          ssl_mode: form.ssl_mode || null,
          read_only: form.read_only,
        };
        if (form.password) patch.password = form.password; // omit ⇒ keep existing
        await update.mutateAsync(patch);
        toast.success("Connection updated");
      } else {
        await create.mutateAsync({
          name: form.name,
          dialect: "postgres",
          host: form.host,
          port: form.port,
          database: form.database,
          username: form.username,
          password: form.password,
          ssl_mode: form.ssl_mode || null,
          read_only: form.read_only,
        });
        toast.success("Connection saved - indexing schema in the background");
      }
      router.push("/app/connections");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to save");
    }
  }

  const pending = create.isPending || update.isPending;

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-2xl space-y-6 p-6">
      <Card>
        <CardContent className="grid gap-4 pt-6 sm:grid-cols-2">
          <Field label="Name" className="sm:col-span-2">
            <Input value={form.name} onChange={(e) => set("name", e.target.value)} required placeholder="Production DB" />
          </Field>
          <Field label="Dialect">
            <NativeSelect value={form.dialect} onChange={(e) => set("dialect", e.target.value)}>
              <option value="postgres">PostgreSQL</option>
              <option value="mysql" disabled>
                MySQL (Phase 2)
              </option>
            </NativeSelect>
          </Field>
          <Field label="SSL mode">
            <NativeSelect
              value={form.ssl_mode || "disable"}
              onChange={(e) => set("ssl_mode", e.target.value === "disable" ? "" : e.target.value)}
            >
              <option value="disable">disable</option>
              <option value="require">require</option>
              <option value="verify-full">verify-full</option>
            </NativeSelect>
          </Field>
          <Field label="Host">
            <Input value={form.host} onChange={(e) => set("host", e.target.value)} required placeholder="db.example.com" />
          </Field>
          <Field label="Port">
            <Input type="number" value={form.port} onChange={(e) => set("port", Number(e.target.value))} required />
          </Field>
          <Field label="Database">
            <Input value={form.database} onChange={(e) => set("database", e.target.value)} required />
          </Field>
          <Field label="Username">
            <Input value={form.username} onChange={(e) => set("username", e.target.value)} required />
          </Field>
          <Field label={editing ? "Password (leave blank to keep)" : "Password"} className="sm:col-span-2">
            <Input type="password" value={form.password} onChange={(e) => set("password", e.target.value)} placeholder={editing ? "••••••••" : ""} required={!editing} />
          </Field>
          <div className="flex items-center gap-3 sm:col-span-2">
            <Switch checked={form.read_only} onCheckedChange={(v) => set("read_only", v)} id="ro" />
            <Label htmlFor="ro" className="font-normal">
              Read-only connection (recommended - enforced at the session level)
            </Label>
          </div>
        </CardContent>
      </Card>

      <details className="rounded-lg border bg-muted/30 p-4 text-sm">
        <summary className="cursor-pointer font-medium">
          Create a read-only role (recommended)
        </summary>
        <pre className="mt-3 overflow-x-auto rounded-md bg-background p-3 text-xs font-mono">
          {RO_ROLE_SNIPPET}
        </pre>
      </details>

      <div className="flex gap-2">
        <Button type="submit" disabled={pending}>
          {pending ? "Saving…" : editing ? "Save changes" : "Save connection"}
        </Button>
        <Button type="button" variant="outline" onClick={() => router.back()}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

function Field({
  label,
  className,
  children,
}: {
  label: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={"space-y-2 " + (className ?? "")}>
      <Label>{label}</Label>
      {children}
    </div>
  );
}
