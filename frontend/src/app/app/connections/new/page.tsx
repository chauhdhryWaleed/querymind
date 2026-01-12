import { PageHeader } from "@/components/page-header";
import { ConnectionForm } from "@/components/connections/connection-form";
import { DemoConnectionButton } from "@/components/connections/demo-connection-button";

export default function NewConnectionPage() {
  return (
    <div>
      <PageHeader
        title="New connection"
        description="Credentials are encrypted with a key derived from your password."
        action={<DemoConnectionButton />}
      />
      <ConnectionForm />
    </div>
  );
}
