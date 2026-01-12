"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { Badge } from "@/components/ui/badge";
import { PageContainer } from "@/components/page-container";
import { ApiError } from "@/lib/api";
import { JOB_ROLES } from "@/lib/profile-options";
import { COUNTRIES } from "@/lib/countries";
import {
  useMe,
  useResendVerification,
  useUpdateProfile,
  useUpdateWorkspaceName,
} from "@/lib/hooks";

export default function AccountPage() {
  const { data: me } = useMe();
  const workspace = me?.workspaces[0];

  return (
    <PageContainer className="max-w-2xl space-y-6">
      <ProfileCard />
      <VerificationCard />
      {workspace && <WorkspaceCard id={workspace.id} initialName={workspace.name} />}
    </PageContainer>
  );
}

function ProfileCard() {
  const { data: me } = useMe();
  const update = useUpdateProfile();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [jobRole, setJobRole] = useState("");
  const [company, setCompany] = useState("");
  const [country, setCountry] = useState("");
  const [useCase, setUseCase] = useState("");

  useEffect(() => {
    const u = me?.user;
    if (!u) return;
    setFirstName(u.first_name ?? "");
    setLastName(u.last_name ?? "");
    setJobRole(u.job_role ?? "");
    setCompany(u.company ?? "");
    setCountry(u.country ?? "");
    setUseCase(u.use_case ?? "");
  }, [me?.user]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await update.mutateAsync({
        first_name: firstName.trim() || null,
        last_name: lastName.trim() || null,
        job_role: jobRole || null,
        company: company.trim() || null,
        country: country || null,
        use_case: useCase.trim() || null,
      });
      toast.success("Profile updated");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not update profile");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile</CardTitle>
        <CardDescription>Signed in as {me?.user.email}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="first">First name</Label>
              <Input id="first" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="last">Last name</Label>
              <Input id="last" value={lastName} onChange={(e) => setLastName(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="role">Job role</Label>
              <NativeSelect id="role" value={jobRole} onChange={(e) => setJobRole(e.target.value)}>
                <option value="" disabled>
                  Select…
                </option>
                {JOB_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="space-y-2">
              <Label htmlFor="country">Country</Label>
              <NativeSelect
                id="country"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
              >
                <option value="" disabled>
                  Select…
                </option>
                {COUNTRIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </NativeSelect>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="company">Company / Organization</Label>
            <Input id="company" value={company} onChange={(e) => setCompany(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="usecase">Use case</Label>
            <Textarea
              id="usecase"
              rows={2}
              value={useCase}
              onChange={(e) => setUseCase(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={update.isPending}>
            Save
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function VerificationCard() {
  const { data: me } = useMe();
  const resend = useResendVerification();
  const verified = me?.user.email_verified;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Email verification</CardTitle>
        <CardDescription>
          {verified
            ? "Your email address is verified."
            : "Verify your email to secure your account."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex items-center justify-between">
        {verified ? (
          <Badge variant="success">verified</Badge>
        ) : (
          <Badge variant="warning">unverified</Badge>
        )}
        {!verified && (
          <Button
            variant="outline"
            disabled={resend.isPending}
            onClick={() =>
              resend.mutate(undefined, {
                onSuccess: () => toast.success("Verification email sent"),
                onError: () => toast.error("Could not send email"),
              })
            }
          >
            {resend.isPending ? "Sending…" : "Resend email"}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function WorkspaceCard({ id, initialName }: { id: string; initialName: string }) {
  const qc = useQueryClient();
  const rename = useUpdateWorkspaceName(id);
  const [name, setName] = useState(initialName);

  useEffect(() => setName(initialName), [initialName]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Workspace</CardTitle>
        <CardDescription>Rename your workspace.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="flex items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim())
              rename.mutate(name.trim(), {
                onSuccess: () => {
                  qc.invalidateQueries({ queryKey: ["me"] });
                  toast.success("Workspace renamed");
                },
              });
          }}
        >
          <div className="flex-1 space-y-2">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <Button type="submit" disabled={rename.isPending}>
            Save
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
