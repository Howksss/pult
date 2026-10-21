import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SystemStatus, TopBar } from "./TopBar";

const counts = { ok: 5, warn: 1, fail: 1, unknown: 0 };

describe("SystemStatus", () => {
  it("кнопкой ведёт к проблемному блоку", () => {
    const onShowBlock = vi.fn();
    render(
      <SystemStatus
        summary={{ status: "fail", text: "Сбой: POS-система", blockId: 4 }}
        onShowBlock={onShowBlock}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Сбой: POS-система" }));
    expect(onShowBlock).toHaveBeenCalledWith(4);
  });

  it("без проблемного блока это просто статус", () => {
    render(
      <SystemStatus
        summary={{ status: "ok", text: "Всё работает", blockId: null }}
        onShowBlock={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent("Всё работает");
  });
});

describe("TopBar", () => {
  const props = {
    projectId: 1,
    counts,
    summary: { status: "fail" as const, text: "Сбой: POS-система", blockId: 4 },
    updatedAt: "2026-10-21T08:00:00Z",
    stale: false,
    theme: "dark" as const,
    onToggleTheme: vi.fn(),
    onShowBlock: vi.fn(),
  };

  it("показывает счётчики только ненулевых статусов", () => {
    const { container } = render(<TopBar {...props} />);
    const chips = Array.from(container.querySelectorAll(".health__chips .status-badge"));
    expect(chips.map((chip) => chip.textContent)).toEqual([
      "Сбой1",
      "Предупреждение1",
      "Работает5",
    ]);
    expect(screen.getByRole("img")).toHaveAccessibleName("Работает 5 из 7");
  });

  it("сообщает о потере связи и переключает тему", () => {
    render(<TopBar {...props} stale theme="light" />);
    expect(screen.getByText("Нет связи")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Тёмная тема" }));
    expect(props.onToggleTheme).toHaveBeenCalled();
  });

  it("без данных графа не рисует сводку", () => {
    const { container } = render(
      <TopBar {...props} counts={null} summary={null} updatedAt={null} />,
    );
    expect(container.querySelector(".health")).toBeNull();
    expect(container.querySelector(".live")).toBeNull();
  });
});
