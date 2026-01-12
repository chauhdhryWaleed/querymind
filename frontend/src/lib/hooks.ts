"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { api, setCsrfToken } from "./api";
import type {
  AuthResponse,
  ConnectionCreate,
  ConnectionOut,
  ConnectionTestResponse,
  ExamplesResponse,
  FavoritesResponse,
  HistoryResponse,
  IndexedSchemaOut,
  LlmKeyCreate,
  LlmKeyOut,
  MeResponse,
  ProfileUpdate,
  SessionOut,
  SignupValues,
  StatsResponse,
  UserOut,
  WorkspaceOut,
  WorkspacePreferencesUpdate,
} from "./types";

// ---- auth -------------------------------------------------------------------

export function useMe(options?: Partial<UseQueryOptions<MeResponse>>) {
  return useQuery<MeResponse>({
    queryKey: ["me"],
    queryFn: () => api<MeResponse>("/me"),
    retry: false,
    ...options,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      api<AuthResponse>("/auth/login", { method: "POST", body, noCsrf: true }),
    onSuccess: (data) => {
      setCsrfToken(data.csrf_token);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useRegister() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SignupValues) =>
      api<AuthResponse>("/auth/register", { method: "POST", body, noCsrf: true }),
    onSuccess: (data) => {
      setCsrfToken(data.csrf_token);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api("/auth/logout", { method: "POST" }),
    onSuccess: () => {
      setCsrfToken(null);
      qc.clear();
    },
  });
}

export function useRequestReset() {
  return useMutation({
    mutationFn: (body: { email: string }) =>
      api("/auth/password-reset/request", { method: "POST", body, noCsrf: true }),
  });
}

export function useCompleteReset() {
  return useMutation({
    mutationFn: (body: { token: string; new_password: string }) =>
      api("/auth/password-reset/complete", { method: "POST", body, noCsrf: true }),
  });
}

// ---- account & security -----------------------------------------------------

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfileUpdate) => api<UserOut>("/me", { method: "PATCH", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) =>
      api("/auth/password-change", { method: "POST", body }),
  });
}

export function useResendVerification() {
  return useMutation({
    mutationFn: () => api("/auth/resend-verification", { method: "POST" }),
  });
}

export function useSessions() {
  return useQuery<SessionOut[]>({
    queryKey: ["sessions"],
    queryFn: () => api<SessionOut[]>("/auth/sessions"),
  });
}

export function useRevokeSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(`/auth/sessions/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sessions"] }),
  });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api("/auth/account", { method: "DELETE" }),
    onSuccess: () => {
      setCsrfToken(null);
      qc.clear();
    },
  });
}

export function useUpdateWorkspaceName(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api<WorkspaceOut>(`/workspaces/${workspaceId}`, { method: "PATCH", body: { name } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useUpdatePreferences(workspaceId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: WorkspacePreferencesUpdate) =>
      api<WorkspaceOut>(`/workspaces/${workspaceId}/preferences`, { method: "PATCH", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

// ---- connections ------------------------------------------------------------

export function useConnections() {
  return useQuery<ConnectionOut[]>({
    queryKey: ["connections"],
    queryFn: () => api<ConnectionOut[]>("/connections"),
    // Poll while any connection is indexing so its status flips on its own; otherwise the workbench shows the loader until a manual reload.
    refetchInterval: (query) =>
      query.state.data?.some(
        (c) => c.index_status === "indexing" || c.index_status === "pending",
      )
        ? 2500
        : false,
  });
}

export function useConnection(id: string | undefined) {
  return useQuery<ConnectionOut>({
    queryKey: ["connections", id],
    queryFn: () => api<ConnectionOut>(`/connections/${id}`),
    enabled: !!id,
  });
}

export function useCreateConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ConnectionCreate) =>
      api<ConnectionOut>("/connections", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connections"] }),
  });
}

export function useCreateDemoConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<ConnectionOut>("/connections/demo", { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connections"] }),
  });
}

export function useUpdateConnection(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api<ConnectionOut>(`/connections/${id}`, { method: "PATCH", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connections"] }),
  });
}

export function useDeleteConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(`/connections/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connections"] }),
  });
}

export function useTestConnection() {
  return useMutation({
    mutationFn: (id: string) =>
      api<ConnectionTestResponse>(`/connections/${id}/test`, { method: "POST" }),
  });
}

export function useReloadSchema() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api(`/connections/${id}/reload-schema`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connections"] }),
  });
}

export function useConnectionSchema(id: string | undefined, poll = false) {
  return useQuery<IndexedSchemaOut>({
    queryKey: ["connection-schema", id],
    queryFn: () => api<IndexedSchemaOut>(`/connections/${id}/schema`),
    enabled: !!id,
    refetchInterval: poll ? 2500 : false,
  });
}

// ---- llm keys ---------------------------------------------------------------

export function useLlmKeys() {
  return useQuery<LlmKeyOut[]>({
    queryKey: ["llm-keys"],
    queryFn: () => api<LlmKeyOut[]>("/llm-keys"),
  });
}

export function useCreateLlmKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: LlmKeyCreate) =>
      api<LlmKeyOut>("/llm-keys", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["llm-keys"] }),
  });
}

export function useUpdateLlmKey(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api<LlmKeyOut>(`/llm-keys/${id}`, { method: "PATCH", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["llm-keys"] }),
  });
}

export function useDeleteLlmKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(`/llm-keys/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["llm-keys"] }),
  });
}

// ---- activity ---------------------------------------------------------------

export function useHistory(connectionId?: string) {
  const qs = connectionId ? `?connection_id=${connectionId}` : "";
  return useQuery<HistoryResponse>({
    queryKey: ["history", connectionId ?? null],
    queryFn: () => api<HistoryResponse>(`/history${qs}`),
  });
}

export function useDeleteHistoryItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(`/history/item/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["history"] }),
  });
}

export function useClearHistory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectionId?: string | null) =>
      api(`/history${connectionId ? `?connection_id=${connectionId}` : ""}`, {
        method: "DELETE",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["history"] }),
  });
}

export function useFavorites() {
  return useQuery<FavoritesResponse>({
    queryKey: ["favorites"],
    queryFn: () => api<FavoritesResponse>("/favorites"),
  });
}

export function useStats(windowDays = 30) {
  return useQuery<StatsResponse>({
    queryKey: ["stats", windowDays],
    queryFn: () => api<StatsResponse>(`/stats?window_days=${windowDays}`),
  });
}

export function useExamples() {
  return useQuery<ExamplesResponse>({
    queryKey: ["examples"],
    queryFn: () => api<ExamplesResponse>("/examples"),
    staleTime: Infinity,
  });
}
