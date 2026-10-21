import { describe, expect, it } from "vitest";
import type { Graph } from "./api";
import {
  connections,
  countByStatus,
  mergeNodes,
  neighbourhood,
  toEdges,
  toNodes,
  type BlockNode,
} from "./graph";

const graph: Graph = {
  project_id: 1,
  generated_at: "2026-10-21T08:00:00Z",
  blocks: [
    {
      id: 1,
      kind: "scheduled_job",
      name: "Расчёт плана",
      description: null,
      x: 0,
      y: 10,
      status: "ok",
    },
    {
      id: 2,
      kind: "integration",
      name: "POS-система",
      description: null,
      x: 260,
      y: 0,
      status: "fail",
    },
    {
      id: 3,
      kind: "integration",
      name: "Погода API",
      description: null,
      x: 260,
      y: 120,
      status: "unknown",
    },
    {
      id: 4,
      kind: "bot",
      name: "Telegram-бот",
      description: null,
      x: 520,
      y: 120,
      status: "ok",
    },
  ],
  links: [
    { id: 10, source_block_id: 1, target_block_id: 2, label: "продажи" },
    { id: 11, source_block_id: 1, target_block_id: 3, label: null },
    { id: 12, source_block_id: 3, target_block_id: 4, label: "прогноз" },
  ],
};

describe("toNodes", () => {
  it("переносит блоки в узлы с позициями", () => {
    const nodes = toNodes(graph);
    expect(nodes.map((n) => [n.id, n.type, n.position.x, n.position.y])).toEqual([
      ["1", "block", 0, 10],
      ["2", "block", 260, 0],
      ["3", "block", 260, 120],
      ["4", "block", 520, 120],
    ]);
    expect(nodes[1].data.block.status).toBe("fail");
  });
});

describe("mergeNodes", () => {
  const moved = (node: BlockNode, x: number, dragging: boolean): BlockNode => ({
    ...node,
    position: { x, y: node.position.y },
    dragging,
    measured: { width: 248, height: 120 },
  });

  it("берёт позицию с сервера и сохраняет размеры узла", () => {
    const current = toNodes(graph).map((node) => moved(node, 999, false));
    const merged = mergeNodes(current, toNodes(graph));
    expect(merged.map((n) => n.position.x)).toEqual([0, 260, 260, 520]);
    expect(merged[0].measured).toEqual({ width: 248, height: 120 });
  });

  it("не сдвигает блок, который пользователь сейчас тащит", () => {
    const [first, ...rest] = toNodes(graph);
    const merged = mergeNodes([moved(first, 999, true), ...rest], toNodes(graph));
    expect(merged[0].position.x).toBe(999);
    expect(merged[1].position.x).toBe(260);
  });

  it("добавляет новые блоки и убирает удалённые", () => {
    const [first] = toNodes(graph);
    const merged = mergeNodes([first], toNodes({ ...graph, blocks: graph.blocks.slice(1) }));
    expect(merged.map((n) => n.id)).toEqual(["2", "3", "4"]);
  });

  it("обновляет статус блока из нового ответа", () => {
    const current = toNodes(graph);
    const recovered = {
      ...graph,
      blocks: graph.blocks.map((b) => ({ ...b, status: "ok" as const })),
    };
    expect(mergeNodes(current, toNodes(recovered))[1].data.block.status).toBe("ok");
  });
});

describe("toEdges", () => {
  it("помечает связи со сбойным блоком как оборванные", () => {
    const edges = toEdges(graph, null);
    expect(edges.map((e) => [e.source, e.target, e.type, e.data?.label, e.data?.broken])).toEqual([
      ["1", "2", "flow", "продажи", true],
      ["1", "3", "flow", null, false],
      ["3", "4", "flow", "прогноз", false],
    ]);
  });

  it("без выбранного блока ничего не подсвечивает и не приглушает", () => {
    const edges = toEdges(graph, null);
    expect(edges.every((e) => !e.data?.active && !e.data?.dimmed)).toBe(true);
  });

  it("подсвечивает связи выбранного блока и приглушает остальные", () => {
    const edges = toEdges(graph, 3);
    expect(edges.map((e) => [e.id, e.data?.active, e.data?.dimmed])).toEqual([
      ["10", false, true],
      ["11", true, false],
      ["12", true, false],
    ]);
  });
});

describe("neighbourhood", () => {
  it("возвращает выбранный блок и его соседей в обе стороны", () => {
    expect(neighbourhood(graph, 3)).toEqual(new Set([3, 1, 4]));
  });

  it("без выбора возвращает null", () => {
    expect(neighbourhood(graph, null)).toBeNull();
  });
});

describe("connections", () => {
  it("делит связи блока на входящие и исходящие", () => {
    const { incoming, outgoing } = connections(graph, 3);
    expect(incoming.map((c) => [c.block.name, c.link.label])).toEqual([["Расчёт плана", null]]);
    expect(outgoing.map((c) => [c.block.name, c.link.label])).toEqual([
      ["Telegram-бот", "прогноз"],
    ]);
  });

  it("пропускает связи на блоки, которых нет в графе", () => {
    const broken = {
      ...graph,
      links: [{ id: 99, source_block_id: 1, target_block_id: 42, label: null }],
    };
    expect(connections(broken, 1).outgoing).toEqual([]);
  });
});

describe("countByStatus", () => {
  it("считает блоки по статусам", () => {
    expect(countByStatus(graph)).toEqual({ ok: 2, warn: 0, fail: 1, unknown: 1 });
  });
});
