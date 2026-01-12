import type { components } from "./api-types";

type S = components["schemas"];

// Generated api-types lag behind backend additions, so a few shapes are augmented by hand.
export type UserOut = S["UserOut"] & {
  name?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  job_role?: string | null;
  company?: string | null;
  country?: string | null;
  use_case?: string | null;
};

export interface SignupValues {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  job_role: string;
  company: string;
  country: string;
  use_case: string;
}

export interface ProfileUpdate {
  first_name?: string | null;
  last_name?: string | null;
  job_role?: string | null;
  company?: string | null;
  country?: string | null;
  use_case?: string | null;
}

export type WorkspaceOut = S["WorkspaceOut"] & {
  default_model?: string | null;
  max_rows?: number | null;
  statement_timeout_ms?: number | null;
};

export type MeResponse = { user: UserOut; workspaces: WorkspaceOut[] };
export type AuthResponse = { user: UserOut; workspace: WorkspaceOut; csrf_token: string };

export interface SessionOut {
  id: string;
  user_agent: string | null;
  ip: string | null;
  created_at: string;
  expires_at: string;
  current: boolean;
}

export interface WorkspacePreferencesUpdate {
  default_model?: string | null;
  max_rows?: number | null;
  statement_timeout_ms?: number | null;
}

export type ConnectionOut = S["ConnectionOut"];
export type ConnectionCreate = S["ConnectionCreate"];
export type ConnectionTestResponse = S["ConnectionTestResponse"];
export type IndexedSchemaOut = S["IndexedSchemaOut"];

export type LlmKeyOut = S["LlmKeyOut"];
export type LlmKeyCreate = S["LlmKeyCreate"];

export type QueryResponse = S["QueryResponse"];
export type VisualizationHint = S["VisualizationHint"];

export type HistoryResponse = S["HistoryResponse"];
export type HistoryItem = S["HistoryItem"] & { answer?: string | null };
export type FavoritesResponse = S["FavoritesResponse"];
export type StatsResponse = S["StatsResponse"];
export type ExamplesResponse = S["ExamplesResponse"];

export type Provider = "anthropic" | "openai" | "gemini";
