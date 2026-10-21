import type { Edge, Node } from "@xyflow/react";
import type { Block, Graph } from "./api";

export type BlockNodeData = { block: Block };
export type BlockNode = Node<BlockNodeData, "block">;

export const KIND_LABELS: Record<Block["kind"], string> = {
  server: "Сервер",
  scheduled_job: "Задание по расписанию",
  bot: "Бот",
  integration: "Интеграция",
  config: "Конфигурация",
  storage: "Хранилище",
};

export function toFlow(graph: Graph): { nodes: BlockNode[]; edges: Edge[] } {
  const nodes: BlockNode[] = graph.blocks.map((block) => ({
    id: String(block.id),
    type: "block",
    position: { x: block.x, y: block.y },
    data: { block },
  }));
  const failing = new Set(graph.blocks.filter((b) => b.status === "fail").map((b) => b.id));
  const edges: Edge[] = graph.links.map((link) => ({
    id: String(link.id),
    source: String(link.source_block_id),
    target: String(link.target_block_id),
    label: link.label ?? undefined,
    animated: failing.has(link.target_block_id),
  }));
  return { nodes, edges };
}

export function countByStatus(graph: Graph): Record<Block["status"], number> {
  const counts = { ok: 0, warn: 0, fail: 0, unknown: 0 };
  for (const block of graph.blocks) {
    counts[block.status] += 1;
  }
  return counts;
}
