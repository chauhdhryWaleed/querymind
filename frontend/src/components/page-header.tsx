import * as React from "react";

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="border-b">
      <div className="mx-auto flex w-full max-w-5xl items-start justify-between gap-4 px-4 py-5 sm:px-6">
        <div>
          <h1 className="text-xl font-semibold capitalize tracking-tight">{title}</h1>
          {description && (
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        {action}
      </div>
    </div>
  );
}
