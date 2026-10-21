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
    const { container } = renderNode({ status: "ok" }, true);
    expect(container.firstChild).toHaveClass("block-node--ok", "block-node--selected");
  });

  it("не выводит пустое описание", () => {
    const { container } = renderNode({ description: null });
    expect(container.querySelector(".block-node__description")).toBeNull();
  });
});
