import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { BlockChecks, Check } from "../api";
import { ChecksPanel } from "./Checks";

const failedRun = {
  checked_at: "2026-11-17T07:59:50Z",
  status: "fail" as const,
  latency_ms: 3120,
  message: "Код выхода 1: KeyError: 'store_id'",
  error_kind: "exit_code",
  details: {
    exit_code: 1,
    command: "python main_orders.py",
    stderr_tail: "KeyError: 'store_id'",
  },
};

const failing: Check = {
  id: 3,
  title: "Автозаказ отработал",
  name: "Автозаказ отработал",
  method: "exit_code",
  target: "python main_orders.py",
  interval_sec: 60,
  timeout_sec: 10,
  enabled: true,
  config: {},
  status: "fail",
  reason: "Код выхода 1: KeyError: 'store_id'",
  error_kind: "exit_code",
  last: failedRun,
  history: [
    { checked_at: "2026-11-17T07:58:50Z", status: "ok", latency_ms: 2900 },
    { checked_at: "2026-11-17T07:59:50Z", status: "fail", latency_ms: null },
  ],
};

const passing: Check = {
  ...failing,
  id: 4,
  title: "POS отвечает",
  name: "POS отвечает",
  method: "http",
  target: "https://pos.example/api/ping",
  status: "ok",
  reason: null,
  error_kind: null,
  last: {
    ...failedRun,
    status: "ok",
    message: null,
    error_kind: null,
    latency_ms: 180,
    details: null,
  },
  history: [],
};

const silent: Check = {
  ...passing,
  id: 5,
  title: "Сертификат",
  enabled: false,
  last: null,
  status: "unknown",
};

function payload(checks: Check[], blockId = 3): BlockChecks {
  return { block_id: blockId, generated_at: "2026-11-17T08:00:00Z", checks };
}

describe("ChecksPanel", () => {
  it("раскрывает проблемную проверку: причина, подробности, stderr и история", async () => {
    const load = vi.fn().mockResolvedValue(payload([failing, passing]));
    render(<ChecksPanel blockId={3} refreshKey="a" load={load} />);
    expect(await screen.findByText("Код выхода 1: KeyError: 'store_id'")).toBeInTheDocument();
    expect(screen.getByText("Задание · python main_orders.py")).toBeInTheDocument();
    expect(screen.getByText("Код выхода").nextSibling).toHaveTextContent("1");
    expect(screen.getByText("Вывод stderr")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "История: 2 последних результатов" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Автозаказ отработал/ })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(load).toHaveBeenCalledWith(3, expect.any(AbortSignal));
  });

  it("исправную проверку держит свёрнутой и раскрывает по клику", async () => {
    render(
      <ChecksPanel blockId={3} refreshKey="a" load={() => Promise.resolve(payload([passing]))} />,
    );
    const head = await screen.findByRole("button", { name: /POS отвечает/ });
    expect(head).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("180 мс")).toBeInTheDocument();
    fireEvent.click(head);
    expect(head).toHaveAttribute("aria-expanded", "true");
  });

  it("выключенную проверку без результатов помечает", async () => {
    const { container } = render(
      <ChecksPanel blockId={3} refreshKey="a" load={() => Promise.resolve(payload([silent]))} />,
    );
    expect(await screen.findByText("не было")).toBeInTheDocument();
    expect(container.querySelector(".check--off")).not.toBeNull();
  });

  it("сообщает, что проверок нет", async () => {
    render(<ChecksPanel blockId={3} refreshKey="a" load={() => Promise.resolve(payload([]))} />);
    expect(await screen.findByText("Проверок нет: статус блока неизвестен")).toBeInTheDocument();
  });

  it("сообщает об ошибке загрузки", async () => {
    render(
      <ChecksPanel blockId={3} refreshKey="a" load={() => Promise.reject(new Error("API 500"))} />,
    );
    expect(await screen.findByText("Не удалось загрузить проверки")).toBeInTheDocument();
  });

  it("перезапрашивает при обновлении графа и не показывает чужой блок", async () => {
    const load = vi.fn().mockResolvedValue(payload([failing], 3));
    const { rerender } = render(<ChecksPanel blockId={3} refreshKey="a" load={load} />);
    await screen.findByText("Автозаказ отработал");
    rerender(<ChecksPanel blockId={3} refreshKey="b" load={load} />);
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    load.mockReturnValue(new Promise(() => undefined));
    rerender(<ChecksPanel blockId={7} refreshKey="b" load={load} />);
    expect(await screen.findByText("Загружаем проверки…")).toBeInTheDocument();
  });
});
