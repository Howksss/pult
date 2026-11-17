import type { BlockStatus } from "./status";

export type BlockKind = "server" | "scheduled_job" | "bot" | "integration" | "config" | "storage";
export type CheckMethod = "heartbeat" | "http" | "log_pattern" | "exit_code" | "tls" | "tcp";
export type CheckStatus = "ok" | "warn" | "fail";

export interface Block {
  id: number;
  kind: BlockKind;
  name: string;
  description: string | null;
  x: number;
  y: number;
  status: BlockStatus;
  reason: string | null;
  checks_total: number;
  checks_problem: number;
}

export interface Link {
  id: number;
  source_block_id: number;
  target_block_id: number;
  label: string | null;
}

export interface Graph {
  project_id: number;
  project_name: string;
  generated_at: string;
  blocks: Block[];
  links: Link[];
}

export interface CheckResult {
  checked_at: string;
  status: CheckStatus;
  latency_ms: number | null;
  message: string | null;
  error_kind: string | null;
  details: Record<string, unknown> | null;
}

export interface HistoryPoint {
  checked_at: string;
  status: CheckStatus;
  latency_ms: number | null;
}

export interface Check {
  id: number;
  title: string;
  name: string | null;
  method: CheckMethod;
  target: string;
  interval_sec: number;
  timeout_sec: number;
  enabled: boolean;
  config: Record<string, unknown>;
  status: BlockStatus;
  reason: string | null;
  error_kind: string | null;
  last: CheckResult | null;
  history: HistoryPoint[];
}

export interface BlockChecks {
  block_id: number;
  generated_at: string;
  checks: Check[];
}

export async function fetchChecks(blockId: number, signal?: AbortSignal): Promise<BlockChecks> {
  const response = await fetch(`/api/v1/blocks/${blockId}/checks`, { signal });
  if (!response.ok) {
    throw new Error(`API ${response.status}`);
  }
  return (await response.json()) as BlockChecks;
}

export interface CheckInput {
  name?: string | null;
  method: CheckMethod;
  target: string;
  interval_sec?: number;
  timeout_sec?: number;
  enabled?: boolean;
  config?: Record<string, unknown>;
}

export type CheckPatch = Partial<Omit<CheckInput, "method">>;

async function problemText(response: Response): Promise<string> {
  try {
    const problem = (await response.json()) as {
      detail?: string;
      errors?: { message?: string }[];
    };
    const text = problem.errors?.[0]?.message ?? problem.detail ?? `API ${response.status}`;
    return text.replace(/^Value error, /, "");
  } catch {
    return `API ${response.status}`;
  }
}

async function send<T>(method: string, url: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await problemText(response));
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export function createCheck(blockId: number, input: CheckInput): Promise<Check> {
  return send<Check>("POST", `/api/v1/blocks/${blockId}/checks`, input);
}

export function updateCheck(checkId: number, patch: CheckPatch): Promise<Check> {
  return send<Check>("PATCH", `/api/v1/checks/${checkId}`, patch);
}

export async function deleteCheck(checkId: number): Promise<void> {
  await send<unknown>("DELETE", `/api/v1/checks/${checkId}`);
}

export function runCheck(checkId: number): Promise<Check> {
  return send<Check>("POST", `/api/v1/checks/${checkId}/run`);
}

export async function fetchGraph(projectId: number, signal?: AbortSignal): Promise<Graph> {
  const response = await fetch(`/api/v1/projects/${projectId}/graph`, { signal });
  if (!response.ok) {
    throw new Error(`API ${response.status}`);
  }
  return (await response.json()) as Graph;
}

export async function moveBlock(blockId: number, x: number, y: number): Promise<void> {
  const response = await fetch(`/api/v1/blocks/${blockId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ x: Math.round(x), y: Math.round(y) }),
  });
  if (!response.ok) {
    throw new Error(`API ${response.status}`);
  }
}

export interface ChecksApi {
  load: (blockId: number, signal: AbortSignal) => Promise<BlockChecks>;
  create: (blockId: number, input: CheckInput) => Promise<Check>;
  update: (checkId: number, patch: CheckPatch) => Promise<Check>;
  remove: (checkId: number) => Promise<void>;
  run: (checkId: number) => Promise<Check>;
}

export const defaultChecksApi: ChecksApi = {
  load: fetchChecks,
  create: createCheck,
  update: updateCheck,
  remove: deleteCheck,
  run: runCheck,
};

export type ScopeAccess = "read" | "write";

export interface Scope {
  id: number;
  path_glob: string;
  access: ScopeAccess;
}

export async function fetchScopes(blockId: number, signal?: AbortSignal): Promise<Scope[]> {
  const response = await fetch(`/api/v1/blocks/${blockId}/scopes`, { signal });
  if (!response.ok) {
    throw new Error(await problemText(response));
  }
  return (await response.json()) as Scope[];
}

export function createScope(
  blockId: number,
  pathGlob: string,
  access: ScopeAccess,
): Promise<Scope> {
  return send<Scope>("POST", `/api/v1/blocks/${blockId}/scopes`, { path_glob: pathGlob, access });
}

export function updateScope(scopeId: number, access: ScopeAccess): Promise<Scope> {
  return send<Scope>("PATCH", `/api/v1/scopes/${scopeId}`, { access });
}

export async function deleteScope(scopeId: number): Promise<void> {
  await send<unknown>("DELETE", `/api/v1/scopes/${scopeId}`);
}

export interface ScopesApi {
  load: (blockId: number, signal: AbortSignal) => Promise<Scope[]>;
  create: (blockId: number, pathGlob: string, access: ScopeAccess) => Promise<Scope>;
  update: (scopeId: number, access: ScopeAccess) => Promise<Scope>;
  remove: (scopeId: number) => Promise<void>;
}

export const defaultScopesApi: ScopesApi = {
  load: fetchScopes,
  create: createScope,
  update: updateScope,
  remove: deleteScope,
};
