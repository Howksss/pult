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
