"use client";

import { use } from "react";
import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { ConnectionForm } from "@/components/connections/connection-form";
import { useConnection } from "@/lib/hooks";

export default function EditConnectionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: connection, isLoading } = useConnection(id);

  return (
    <div>
      <PageHeader title="Edit connection" description="Leave the password blank to keep the stored one." />
      {isLoading || !connection ? (
        <div className="p-6">
          <Loader2 className="size-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <ConnectionForm existing={connection} />
      )}
    </div>
  );
}
