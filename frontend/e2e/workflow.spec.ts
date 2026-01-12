import { test, expect, type Page } from "@playwright/test";

/**
 * End-to-end: signup → connect the demo DB → add an LLM key → ask a question.
 *
 * Prerequisites (the test asserts against a live backend):
 *   - docker compose up (postgres+redis) and the FastAPI backend on :8001
 *   - the `demo` database seeded (it is, by docker/postgres/10-demo-seed.sql)
 *   - an LLM key with quota for the final "ask" assertion; without a valid key
 *     the query still streams the pipeline but the LLM stage will error — the
 *     test tolerates that and asserts the pipeline ran.
 */

const unique = () => `e2e-${Date.now()}-${Math.floor(Math.random() * 1e4)}@example.com`;

async function signup(page: Page, email: string) {
  await page.goto("/signup");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("e2e-password-123");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/app/workbench");
}

test("signup, connect demo DB, add key, ask", async ({ page }) => {
  const email = unique();
  await signup(page, email);

  // Onboarding: prompted to connect a database.
  await expect(page.getByText("Connect a database to get started")).toBeVisible();
  await page.getByRole("link", { name: "Connect a database" }).click();
  await page.waitForURL("**/app/connections/new");

  // Fill the demo connection (reachable from the backend as host=postgres).
  await page.getByLabel("Name").fill("Demo");
  await page.getByLabel("Host").fill("postgres");
  await page.getByLabel("Port").fill("5432");
  await page.getByLabel("Database").fill("demo");
  await page.getByLabel("Username").fill("querymind_reader");
  await page.getByLabel(/Password/).fill("querymind_reader");
  await page.getByRole("button", { name: "Save connection" }).click();
  await page.waitForURL("**/app/connections");
  await expect(page.getByText("Demo")).toBeVisible();

  // Add an LLM key.
  await page.goto("/app/keys");
  await page.getByRole("button", { name: "Add key" }).click();
  await page.getByLabel("API key").fill("sk-ant-e2e-placeholder");
  await page.getByRole("button", { name: "Add key" }).last().click();
  await expect(page.getByText(/anthropic|Anthropic/)).toBeVisible();

  // Workbench: once schema indexing finishes, ask a question.
  await page.goto("/app/workbench");
  const composer = page.getByPlaceholder(/Ask|Select a connection/);
  await expect(composer).toBeVisible();
  // Wait for indexing to settle (status badge leaves "indexing").
  await expect(page.getByText("indexing")).toBeHidden({ timeout: 30_000 });

  await composer.fill("How many customers are there?");
  await page.getByRole("button", { name: "Run" }).click();

  // The live pipeline should at least begin (schema/generate stages render).
  await expect(page.getByText(/Retrieve schema|Generate SQL/)).toBeVisible({ timeout: 20_000 });
});
