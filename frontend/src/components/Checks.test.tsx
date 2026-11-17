import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { defaultChecksApi, type BlockChecks, type Check } from "../api";
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

const day = Array.from({ length: 24 }, (_, hour) => ({
  start: new Date(Date.UTC(2026, 10, 16, 9 + hour)).toISOString(),
  ok: hour < 22 ? 60 : 0,
  warn: 0,
  fail: hour >= 22 ? 60 : 0,
}));
day[3] = { ...day[3], ok: 0 };

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
  timeline: day,
  failing_since: "2026-11-17T06:10:00Z",
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
  failing_since: null,
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
    render(<ChecksPanel blockId={3} refreshKey="a" api={{ ...defaultChecksApi, load: load }} />);
    expect(await screen.findByText("Код выхода 1: KeyError: 'store_id'")).toBeInTheDocument();
    expect(screen.getByText("Задание · python main_orders.py")).toBeInTheDocument();
    expect(screen.getByText("Код выхода").nextSibling).toHaveTextContent("1");
    expect(screen.getByText("Вывод stderr")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Последние сутки по часам: проблемы в 2 из 24 часов" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/^Сбой с \d\d:10, 1 ч 50 мин$/)).toBeInTheDocument();
    expect(screen.getByText("сейчас")).toBeInTheDocument();
    expect(document.querySelectorAll(".timeline__bar--fail")).toHaveLength(2);
    expect(document.querySelectorAll(".timeline__bar--empty")).toHaveLength(1);
    expect(screen.getByRole("button", { name: /Автозаказ отработал/ })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(load).toHaveBeenCalledWith(3, expect.any(AbortSignal));
  });

  it("исправную проверку держит свёрнутой и раскрывает по клику", async () => {
    render(
      <ChecksPanel
        blockId={3}
        refreshKey="a"
        api={{ ...defaultChecksApi, load: () => Promise.resolve(payload([passing])) }}
      />,
    );
    const head = await screen.findByRole("button", { name: /POS отвечает/ });
    expect(head).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("180 мс")).toBeInTheDocument();
    fireEvent.click(head);
    expect(head).toHaveAttribute("aria-expanded", "true");
  });

  it("выключенную проверку без результатов помечает", async () => {
    const { container } = render(
      <ChecksPanel
        blockId={3}
        refreshKey="a"
        api={{ ...defaultChecksApi, load: () => Promise.resolve(payload([silent])) }}
      />,
    );
    expect(await screen.findByText("не было")).toBeInTheDocument();
    expect(container.querySelector(".check--off")).not.toBeNull();
  });

  it("сообщает, что проверок нет", async () => {
    render(
      <ChecksPanel
        blockId={3}
        refreshKey="a"
        api={{ ...defaultChecksApi, load: () => Promise.resolve(payload([])) }}
      />,
    );
    expect(await screen.findByText("Проверок нет: статус блока неизвестен")).toBeInTheDocument();
  });

  it("сообщает об ошибке загрузки", async () => {
    render(
      <ChecksPanel
        blockId={3}
        refreshKey="a"
        api={{ ...defaultChecksApi, load: () => Promise.reject(new Error("API 500")) }}
      />,
    );
    expect(await screen.findByText("Не удалось загрузить проверки")).toBeInTheDocument();
  });

  it("перезапрашивает при обновлении графа и не показывает чужой блок", async () => {
    const load = vi.fn().mockResolvedValue(payload([failing], 3));
    const { rerender } = render(
      <ChecksPanel blockId={3} refreshKey="a" api={{ ...defaultChecksApi, load: load }} />,
    );
    await screen.findByText("Автозаказ отработал");
    rerender(<ChecksPanel blockId={3} refreshKey="b" api={{ ...defaultChecksApi, load: load }} />);
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    load.mockReturnValue(new Promise(() => undefined));
    rerender(<ChecksPanel blockId={7} refreshKey="b" api={{ ...defaultChecksApi, load: load }} />);
    expect(await screen.findByText("Загружаем проверки…")).toBeInTheDocument();
  });
});

describe("действия с проверками", () => {
  function setup(checks: Check[]) {
    const api = {
      load: vi.fn().mockResolvedValue(payload(checks)),
      create: vi.fn().mockResolvedValue(passing),
      update: vi.fn().mockResolvedValue(passing),
      remove: vi.fn().mockResolvedValue(undefined),
      run: vi.fn().mockResolvedValue(passing),
    };
    render(<ChecksPanel blockId={3} refreshKey="a" api={api} />);
    return api;
  }

  it("добавляет проверку и перезагружает список", async () => {
    const api = setup([]);
    fireEvent.click(await screen.findByRole("button", { name: "Добавить проверку" }));
    fireEvent.change(screen.getByLabelText("Адрес"), { target: { value: "https://pos.example" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    await waitFor(() =>
      expect(api.create).toHaveBeenCalledWith(3, expect.objectContaining({ method: "http" })),
    );
    await waitFor(() => expect(api.load).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("form", { name: "Новая проверка" })).toBeNull();
  });

  it("проверяет сейчас, выключает и удаляет с подтверждением", async () => {
    const api = setup([{ ...passing, status: "warn", reason: "Ответ за 2,4 с" }]);
    fireEvent.click(await screen.findByRole("button", { name: "Проверить сейчас" }));
    await waitFor(() => expect(api.run).toHaveBeenCalledWith(4));
    fireEvent.click(screen.getByRole("button", { name: "Выключить" }));
    await waitFor(() => expect(api.update).toHaveBeenCalledWith(4, { enabled: false }));
    fireEvent.click(screen.getByRole("button", { name: "Удалить" }));
    expect(screen.getByText("Удалить вместе с историей?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Отмена" }));
    fireEvent.click(screen.getByRole("button", { name: "Удалить" }));
    fireEvent.click(screen.getByRole("button", { name: "Удалить" }));
    await waitFor(() => expect(api.remove).toHaveBeenCalledWith(4));
  });

  it("показывает ошибку действия", async () => {
    const api = setup([{ ...passing, status: "fail" }]);
    api.run.mockRejectedValue(new Error("API 500"));
    fireEvent.click(await screen.findByRole("button", { name: "Проверить сейчас" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("API 500");
  });

  it("изменяет проверку без смены типа", async () => {
    const api = setup([{ ...passing, status: "fail" }]);
    fireEvent.click(await screen.findByRole("button", { name: "Изменить" }));
    fireEvent.change(screen.getByLabelText("Название"), { target: { value: "POS жив" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    await waitFor(() => expect(api.update).toHaveBeenCalled());
    expect(api.update.mock.calls[0][1]).not.toHaveProperty("method");
    expect(api.update.mock.calls[0][1].name).toBe("POS жив");
  });

  it("закрывает изменение по отмене", async () => {
    setup([{ ...passing, status: "fail" }]);
    fireEvent.click(await screen.findByRole("button", { name: "Изменить" }));
    fireEvent.click(screen.getByRole("button", { name: "Отмена" }));
    expect(screen.getByRole("button", { name: "Изменить" })).toBeInTheDocument();
  });

  it("для задания показывает строку для cron и не предлагает проверить сейчас", async () => {
    setup([failing]);
    expect(await screen.findByText("pult-run 3 python main_orders.py")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Проверить сейчас" })).toBeNull();
  });

  it("включает выключенную проверку", async () => {
    const api = setup([{ ...silent, status: "unknown" }]);
    fireEvent.click(await screen.findByRole("button", { name: "Включить" }));
    await waitFor(() => expect(api.update).toHaveBeenCalledWith(5, { enabled: true }));
  });
});
