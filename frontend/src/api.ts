import type { BlockStatus } from "./status";

export type BlockKind = "server" | "scheduled_job" | "bot" | "integration" | "config" | "storage";

export interface Block {
  id: number;
  kind: BlockKind;
  name: string;
  description: string | null;
  x: number;
  y: number;
  status: BlockStatus;
}

export interface Link {
  id: number;
  source_block_id: number;
  target_block_id: number;
  label: string | null;
}

export interface Graph {
  project_id: number;
  generated_at: string;
  blocks: Block[];
  links: Link[];
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
