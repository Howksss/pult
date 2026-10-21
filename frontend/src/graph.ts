import type { Edge, Node } from "@xyflow/react";
import type { Block, Graph, Link } from "./api";

export type BlockNodeData = { block: Block };
export type BlockNode = Node<BlockNodeData, "block">;
export type FlowEdgeData = {
  label: string | null;
  broken: boolean;
  active: boolean;
  dimmed: boolean;
};
export type FlowEdge = Edge<FlowEdgeData, "flow">;
export type Connection = { link: Link; block: Block };

export const KIND_LABELS: Record<Block["kind"], string> = {
  server: "Сервер",
  scheduled_job: "Задание по расписанию",
  bot: "Бот",
  integration: "Интеграция",
  config: "Конфигурация",
  storage: "Хранилище",
};

export function toNodes(graph: Graph): BlockNode[] {
  return graph.blocks.map((block) => ({
    id: String(block.id),
    type: "block",
    position: { x: block.x, y: block.y },
    data: { block },
  }));
}

export function mergeNodes(current: BlockNode[], incoming: BlockNode[]): BlockNode[] {
  const byId = new Map(current.map((node) => [node.id, node]));
  return incoming.map((node) => {
    const existing = byId.get(node.id);
    if (!existing) {
      return node;
    }
    const position = existing.dragging ? existing.position : node.position;
    return { ...existing, position, data: node.data };
  });
}

export function neighbourhood(graph: Graph, blockId: number | null): Set<number> | null {
  if (blockId === null) {
    return null;
  }
  const ids = new Set([blockId]);
  for (const link of graph.links) {
    if (link.source_block_id === blockId) {
      ids.add(link.target_block_id);
    }
    if (link.target_block_id === blockId) {
      ids.add(link.source_block_id);
    }
  }
  return ids;
}

export function toEdges(graph: Graph, selectedId: number | null): FlowEdge[] {
  const failing = new Set(graph.blocks.filter((b) => b.status === "fail").map((b) => b.id));
  return graph.links.map((link) => {
    const touchesSelected =
      link.source_block_id === selectedId || link.target_block_id === selectedId;
    return {
      id: String(link.id),
      type: "flow",
      source: String(link.source_block_id),
      target: String(link.target_block_id),
      data: {
        label: link.label,
        broken: failing.has(link.source_block_id) || failing.has(link.target_block_id),
        active: touchesSelected,
        dimmed: selectedId !== null && !touchesSelected,
      },
    };
  });
}

export function connections(
  graph: Graph,
  blockId: number,
): { incoming: Connection[]; outgoing: Connection[] } {
  const blocks = new Map(graph.blocks.map((block) => [block.id, block]));
  const incoming: Connection[] = [];
  const outgoing: Connection[] = [];
  for (const link of graph.links) {
    const source = blocks.get(link.source_block_id);
    const target = blocks.get(link.target_block_id);
    if (link.target_block_id === blockId && source) {
      incoming.push({ link, block: source });
    }
    if (link.source_block_id === blockId && target) {
      outgoing.push({ link, block: target });
    }
  }
  return { incoming, outgoing };
}

export function countByStatus(graph: Graph): Record<Block["status"], number> {
  const counts = { ok: 0, warn: 0, fail: 0, unknown: 0 };
  for (const block of graph.blocks) {
    counts[block.status] += 1;
  }
  return counts;
}

export type Summary = { status: Block["status"]; text: string; blockId: number | null };

function describe(blocks: Block[], one: string, many: string): string {
  if (blocks.length <= 2) {
    return `${one}: ${blocks.map((block) => block.name).join(", ")}`;
  }
  const count = blocks.length;
  const word = count % 10 === 1 && count % 100 !== 11 ? "блоке" : "блоках";
  return `${many} в ${count} ${word}`;
}

export function summarize(graph: Graph): Summary {
  const total = graph.blocks.length;
  if (total === 0) {
    return { status: "unknown", text: "Блоков нет", blockId: null };
  }
  const failed = graph.blocks.filter((block) => block.status === "fail");
  if (failed.length > 0) {
    return { status: "fail", text: describe(failed, "Сбой", "Сбой"), blockId: failed[0].id };
  }
  const warned = graph.blocks.filter((block) => block.status === "warn");
  if (warned.length > 0) {
    return {
      status: "warn",
      text: describe(warned, "Предупреждение", "Предупреждения"),
      blockId: warned[0].id,
    };
  }
  const silent = graph.blocks.filter((block) => block.status === "unknown");
  if (silent.length === total) {
    return { status: "unknown", text: "Нет данных от проверок", blockId: null };
  }
  if (silent.length > 0) {
    return {
      status: "unknown",
      text: `Нет данных: ${silent.length} из ${total}`,
      blockId: silent[0].id,
    };
  }
  return { status: "ok", text: "Всё работает", blockId: null };
}
