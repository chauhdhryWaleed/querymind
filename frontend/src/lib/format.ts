/** Display formatting for dynamic values.
 *
 * Static UI labels are Title-Cased by a global `capitalize` class, but dynamic
 * values (provider ids, model names, statuses coming from the API) are raw
 * lowercase strings. Rendering them through these helpers keeps casing coherent
 * with the rest of the interface - and gets proper-noun casing right, which a
 * blunt CSS `capitalize` cannot ("openai" → "OpenAI", not "Openai").
 */

/** Canonical, correctly-cased display names for the supported LLM providers. */
const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  gemini: "Gemini",
};

/** Human label for an LLM provider id. Falls back to title-casing the unknown. */
export function formatProvider(provider: string | null | undefined): string {
  if (!provider) return "N/A";
  return PROVIDER_LABELS[provider.toLowerCase()] ?? titleCase(provider);
}

/** Human label for a connection's index status. */
const STATUS_LABELS: Record<string, string> = {
  ready: "Ready",
  indexing: "Indexing",
  pending: "Pending",
  failed: "Failed",
};

export function formatStatus(status: string | null | undefined): string {
  if (!status) return "N/A";
  return STATUS_LABELS[status.toLowerCase()] ?? titleCase(status);
}

/** Title-case a snake/kebab/space separated identifier: "read_only" → "Read Only". */
export function titleCase(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .trim()
    .split(/\s+/)
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}
