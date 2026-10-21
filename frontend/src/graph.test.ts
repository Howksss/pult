import { describe, expect, it } from "vitest";
import type { Graph } from "./api";
import { countByStatus, toFlow } from "./graph";

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
  ],
  links: [
    { id: 10, source_block_id: 1, target_block_id: 2, label: "продажи" },
    { id: 11, source_block_id: 1, target_block_id: 3, label: null },
  ],
};

describe("toFlow", () => {
  it("переносит блоки в узлы с позициями", () => {
    const { nodes } = toFlow(graph);
    expect(nodes.map((n) => [n.id, n.position.x, n.position.y])).toEqual([
      ["1", 0, 10],
      ["2", 260, 0],
      ["3", 260, 120],
    ]);
    expect(nodes[1].data.block.status).toBe("fail");
  });

  it("анимирует связь, ведущую в упавший блок", () => {
    const { edges } = toFlow(graph);
    expect(edges.map((e) => [e.source, e.target, e.label, e.animated])).toEqual([
      ["1", "2", "продажи", true],
      ["1", "3", undefined, false],
    ]);
  });
});

describe("countByStatus", () => {
  it("считает блоки по статусам", () => {
    expect(countByStatus(graph)).toEqual({ ok: 1, warn: 0, fail: 1, unknown: 1 });
  });
});
