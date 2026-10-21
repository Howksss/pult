import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Graph } from "../api";
import { Inspector } from "./Inspector";

const graph: Graph = {
  project_id: 1,
  generated_at: "2026-10-21T08:00:00Z",
  blocks: [
    { id: 1, kind: "server", name: "VPS", description: null, x: 0, y: 0, status: "ok" },
    {
      id: 2,
      kind: "scheduled_job",
      name: "Расчёт плана",
      description: "Прогон в 08:00",
      x: 300,
      y: 0,
      status: "ok",
    },
    {
      id: 3,
      kind: "integration",
      name: "POS-система",
      description: null,
      x: 600,
      y: 0,
      status: "fail",
    },
  ],
  links: [
    { id: 10, source_block_id: 1, target_block_id: 2, label: "cron 08:00" },
    { id: 11, source_block_id: 2, target_block_id: 3, label: "продажи" },
  ],
};

function renderInspector(blockId: number) {
  const onSelect = vi.fn();
  const onClose = vi.fn();
  const block = graph.blocks.find((b) => b.id === blockId);
  if (!block) {
    throw new Error(`block ${blockId} not found`);
  }
  render(<Inspector graph={graph} block={block} onSelect={onSelect} onClose={onClose} />);
  return { onSelect, onClose };
}

describe("Inspector", () => {
  it("показывает имя, тип, статус и описание блока", () => {
    renderInspector(2);
    const panel = screen.getByRole("complementary", { name: "Блок Расчёт плана" });
    expect(within(panel).getByRole("heading", { name: "Расчёт плана" })).toBeInTheDocument();
    expect(within(panel).getByText("Задание по расписанию")).toBeInTheDocument();
    expect(within(panel).getByText("Прогон в 08:00")).toBeInTheDocument();
    expect(within(panel).getByTitle("Работает")).toBeInTheDocument();
  });

  it("перечисляет входящие и исходящие связи с подписями", () => {
    renderInspector(2);
    expect(screen.getByTitle("VPS: Работает")).toHaveTextContent("cron 08:00");
    expect(screen.getByTitle("POS-система: Сбой")).toHaveTextContent("продажи");
  });

  it("переходит к соседнему блоку по клику", () => {
    const { onSelect } = renderInspector(2);
    fireEvent.click(screen.getByTitle("POS-система: Сбой"));
    expect(onSelect).toHaveBeenCalledWith(3);
  });

  it("закрывается кнопкой", () => {
    const { onClose } = renderInspector(2);
    fireEvent.click(screen.getByRole("button", { name: "Закрыть" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("пишет, что связей нет, и подставляет текст без описания", () => {
    renderInspector(1);
    expect(screen.getByText("Связей нет")).toBeInTheDocument();
    expect(screen.getByText("Без описания")).toBeInTheDocument();
  });

  it("поле задачи агенту выключено до появления чата", () => {
    renderInspector(3);
    expect(screen.getByPlaceholderText("Что поправить в блоке «POS-система»?")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Отправить" })).toBeDisabled();
  });
});
