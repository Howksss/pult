import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge, type BlockStatus } from "./StatusBadge";

const cases: [BlockStatus, string][] = [
  ["ok", "Работает"],
  ["warn", "Предупреждение"],
  ["fail", "Сбой"],
  ["unknown", "Нет данных"],
];

describe("StatusBadge", () => {
  it.each(cases)("статус %s подписан словом и цветной точкой", (status, label) => {
    const { container } = render(<StatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(container.querySelector(".status-dot")).toHaveClass(`status-dot--${status}`);
    expect(container.querySelector(".status-dot")).toBeEmptyDOMElement();
    expect(container.firstChild).toHaveClass(`status-badge--${status}`);
  });

  it("точка скрыта от экранного диктора, подпись остаётся", () => {
    const { container } = render(<StatusBadge status="fail" />);
    expect(container.querySelector(".status-dot")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByText("Сбой")).toBeVisible();
  });

  it("подсказка объясняет, что значит «Нет данных»", () => {
    render(<StatusBadge status="unknown" />);
    expect(screen.getByTitle(/probe не подключён/)).toHaveTextContent("Нет данных");
  });

  it("показывает счётчик и приглушает нулевой", () => {
    const { container, rerender } = render(<StatusBadge status="warn" count={2} />);
    expect(container.querySelector(".status-badge__count")).toHaveTextContent("2");
    expect(container.firstChild).not.toHaveClass("status-badge--empty");
    rerender(<StatusBadge status="warn" count={0} />);
    expect(container.firstChild).toHaveClass("status-badge--empty");
  });

  it("без счётчика не выводит число", () => {
    const { container } = render(<StatusBadge status="ok" />);
    expect(container.querySelector(".status-badge__count")).toBeNull();
  });
});
