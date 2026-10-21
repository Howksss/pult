import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge, type BlockStatus } from "./StatusBadge";

const cases: [BlockStatus, string, string][] = [
  ["ok", "Работает", "✓"],
  ["warn", "Предупреждение", "!"],
  ["fail", "Сбой", "✕"],
  ["unknown", "Нет данных", "?"],
];

describe("StatusBadge", () => {
  it.each(cases)("статус %s подписан текстом и иконкой", (status, label, icon) => {
    const { container } = render(<StatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(container.querySelector(".status-badge__icon")).toHaveTextContent(icon);
    expect(container.firstChild).toHaveClass(`status-badge--${status}`);
  });

  it("иконка скрыта от экранного диктора, подпись остаётся", () => {
    const { container } = render(<StatusBadge status="fail" />);
    expect(container.querySelector(".status-badge__icon")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByTitle("Сбой")).toBeInTheDocument();
  });
});
