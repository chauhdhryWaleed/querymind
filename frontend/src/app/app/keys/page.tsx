"use client";

import { useState } from "react";
import { toast } from "sonner";
import { KeyRound, Plus, Trash2, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PageHeader } from "@/components/page-header";
import { PageContainer } from "@/components/page-container";
import { EmptyState } from "@/components/empty-state";
import {
  useCreateLlmKey,
  useDeleteLlmKey,
  useLlmKeys,
  useUpdateLlmKey,
} from "@/lib/hooks";
import { ApiError } from "@/lib/api";
import { formatProvider } from "@/lib/format";
import type { Provider } from "@/lib/types";

const PROVIDER_KEY_HINT: Record<Provider, string> = {
  anthropic: "sk-ant-…",
  openai: "sk-…",
  gemini: "AIza…",
};

export default function KeysPage() {
  const { data: keys, isLoading } = useLlmKeys();
  const del = useDeleteLlmKey();
  const [open, setOpen] = useState(false);

  return (
    <div>
      <PageHeader
        title="LLM Keys"
        description="Bring your own key. Stored encrypted; only a hint is ever shown."
        action={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="size-4" /> Add key
              </Button>
            </DialogTrigger>
            <AddKeyDialog onDone={() => setOpen(false)} />
          </Dialog>
        }
      />
      <PageContainer className="space-y-3">
        {isLoading ? (
          [0, 1].map((i) => <Skeleton key={i} className="h-16 w-full" />)
        ) : !keys?.length ? (
          <EmptyState
            icon={KeyRound}
            title="No LLM keys yet"
            description="Add an Anthropic, OpenAI, or Gemini key to run queries."
          />
        ) : (
          <KeyList />
        )}
      </PageContainer>
    </div>
  );
}

function KeyList() {
  const { data: keys = [] } = useLlmKeys();
  const del = useDeleteLlmKey();

  return (
    <>
      {keys.map((k) => (
        <Card key={k.id}>
          <CardContent className="flex items-center justify-between gap-4 py-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium">{formatProvider(k.provider)}</span>
                {k.label && <span className="text-sm text-muted-foreground">· {k.label}</span>}
                {k.is_default && (
                  <Badge variant="success">
                    <Star className="mr-1 size-3" /> default
                  </Badge>
                )}
              </div>
              <p className="mt-0.5 font-mono text-sm text-muted-foreground">
                {k.key_hint}
                {k.model_override ? ` · ${k.model_override}` : ""}
              </p>
            </div>
            <div className="flex items-center gap-1">
              {!k.is_default && <SetDefaultButton id={k.id} />}
              <Button
                variant="ghost"
                size="icon"
                aria-label="Delete"
                onClick={() => {
                  if (confirm("Delete this key?"))
                    del.mutate(k.id, { onSuccess: () => toast.success("Key deleted") });
                }}
              >
                <Trash2 className="size-4 text-destructive" />
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </>
  );
}

function SetDefaultButton({ id }: { id: string }) {
  const update = useUpdateLlmKey(id);
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => update.mutate({ is_default: true }, { onSuccess: () => toast.success("Default updated") })}
    >
      <Star className="size-4" /> Set default
    </Button>
  );
}

function AddKeyDialog({ onDone }: { onDone: () => void }) {
  const create = useCreateLlmKey();
  const [provider, setProvider] = useState<Provider>("anthropic");
  const [apiKey, setApiKey] = useState("");
  const [label, setLabel] = useState("");
  const [model, setModel] = useState("");
  const [isDefault, setIsDefault] = useState(true);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await create.mutateAsync({
        provider,
        api_key: apiKey,
        label: label || null,
        model_override: model || null,
        is_default: isDefault,
      });
      toast.success("Key added");
      onDone();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to add key");
    }
  }

  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Add an LLM key</DialogTitle>
        <DialogDescription>The key is encrypted at rest and never returned.</DialogDescription>
      </DialogHeader>
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label>Provider</Label>
          <Select value={provider} onValueChange={(v) => setProvider(v as Provider)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="anthropic">Anthropic</SelectItem>
              <SelectItem value="openai">OpenAI</SelectItem>
              <SelectItem value="gemini">Gemini</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>API key</Label>
          <Input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            required
            placeholder={PROVIDER_KEY_HINT[provider]}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label>Label (optional)</Label>
            <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Primary" />
          </div>
          <div className="space-y-2">
            <Label>Model override</Label>
            <Input value={model} onChange={(e) => setModel(e.target.value)} placeholder="Default" />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Switch checked={isDefault} onCheckedChange={setIsDefault} id="default" />
          <Label htmlFor="default" className="font-normal">Set as default</Label>
        </div>
        <DialogFooter>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? "Adding…" : "Add key"}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  );
}
