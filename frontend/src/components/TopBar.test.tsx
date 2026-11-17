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
    projectName: "Пилот: планирование выпечки",
    counts,
    summary: { status: "fail" as const, text: "Сбой: POS-система", blockId: 4 },
    updatedAt: "2026-10-21T08:00:00Z",
    stale: false,
    onShowBlock: vi.fn(),
  };

  it("логотип со стеклянной буквой читается диктором как Pult", () => {
    const { container } = render(<TopBar {...props} />);
    expect(container.querySelector(".brand")).toHaveTextContent("Pult");
    expect(container.querySelector(".brand__glass")).toHaveAttribute("alt", "");
  });

  it("подписывает проект названием, а без названия номером", () => {
    const { rerender } = render(<TopBar {...props} />);
    expect(screen.getByText("Пилот: планирование выпечки")).toBeInTheDocument();
    rerender(<TopBar {...props} projectName={null} />);
    expect(screen.getByText("Проект 1")).toBeInTheDocument();
  });

  it("рисует по риске на блок, проблемные первыми", () => {
    const { container } = render(<TopBar {...props} />);
    const ticks = Array.from(container.querySelectorAll(".tick"));
    expect(ticks).toHaveLength(7);
    expect(ticks[0]).toHaveClass("tick--fail");
    expect(ticks[1]).toHaveClass("tick--warn");
    expect(ticks[6]).toHaveClass("tick--ok");
    expect(screen.getByRole("img")).toHaveAccessibleName("5 из 7 работают");
  });

  it("согласует глагол с числом", () => {
    render(<TopBar {...props} counts={{ ok: 1, warn: 0, fail: 1, unknown: 0 }} />);
    expect(screen.getByText("1 из 2 работает")).toBeInTheDocument();
  });

  it("сообщает о потере связи", () => {
    const { container } = render(<TopBar {...props} stale />);
    expect(screen.getByText(/Нет связи/)).toBeInTheDocument();
    expect(container.querySelector(".live--stale .live__dot")).not.toBeNull();
  });

  it("без данных графа не рисует сводку", () => {
    const { container } = render(
      <TopBar {...props} counts={null} summary={null} updatedAt={null} />,
    );
    expect(container.querySelector(".health")).toBeNull();
    expect(container.querySelector(".system-status")).toBeNull();
    expect(container.querySelector(".live")).toBeNull();
  });
});
