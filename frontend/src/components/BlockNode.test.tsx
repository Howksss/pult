import { ReactFlowProvider, type NodeProps } from "@xyflow/react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Block } from "../api";
import type { BlockNode as BlockNodeType } from "../graph";
import { BlockNode } from "./BlockNode";

const block: Block = {
  id: 4,
  kind: "integration",
  name: "POS-система",
  description: "Продажи и остатки",
  x: 0,
  y: 0,
  status: "fail",
  reason: null,
  checks_total: 1,
  checks_problem: 0,
};

function renderNode(overrides: Partial<Block>, selected = false) {
  const props = {
    id: "4",
    type: "block",
    data: { block: { ...block, ...overrides } },
    selected,
  } as unknown as NodeProps<BlockNodeType>;
  return render(
    <ReactFlowProvider>
      <BlockNode {...props} />
    </ReactFlowProvider>,
  );
}

describe("BlockNode", () => {
  it("показывает имя, тип, описание и статус", () => {
    const { container } = renderNode({});
    expect(screen.getByText("POS-система")).toBeInTheDocument();
    expect(screen.getByText("Интеграция")).toBeInTheDocument();
    expect(screen.getByText("Продажи и остатки")).toBeInTheDocument();
    expect(screen.getByTitle("Одна из проверок блока не прошла")).toHaveTextContent("Сбой");
    expect(container.querySelector(".kind-icon--integration")).not.toBeNull();
    expect(container.firstChild).toHaveClass("block-node--fail");
  });

  it("выделяет выбранный блок", () => {
    const { container } = renderNode(
      { status: "ok", reason: null, checks_total: 1, checks_problem: 0 },
      true,
    );
    expect(container.firstChild).toHaveClass("block-node--ok", "block-node--selected");
  });

  it("при проблеме вместо описания показывает причину и долю проблемных проверок", () => {
    const { container } = renderNode({
      reason: "POS отвечает: HTTP 502 Bad Gateway",
      checks_total: 3,
      checks_problem: 1,
    });
    expect(screen.getByText("POS отвечает: HTTP 502 Bad Gateway")).toBeInTheDocument();
    expect(screen.queryByText("Продажи и остатки")).toBeNull();
    expect(screen.getByTitle("Проблемы в 1 из 3 проверок")).toHaveTextContent("1 из 3");
    expect(container.querySelector(".block-node__description")).toBeNull();
  });

  it("у исправного блока описание и число проверок", () => {
    renderNode({ status: "ok", reason: null, checks_total: 2, checks_problem: 0 });
    expect(screen.getByText("Продажи и остатки")).toBeInTheDocument();
    expect(screen.getByTitle("Все 2 проверки проходят")).toHaveTextContent("2 проверки");
  });

  it("не выводит пустое описание", () => {
    const { container } = renderNode({ description: null });
    expect(container.querySelector(".block-node__description")).toBeNull();
  });
});
