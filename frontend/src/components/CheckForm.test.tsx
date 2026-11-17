import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Check } from "../api";
import { CheckForm } from "./CheckForm";

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

const existing: Check = {
  id: 7,
  title: "POS отвечает",
  name: "POS отвечает",
  method: "http",
  target: "https://pos.example/api/ping",
  interval_sec: 7200,
  timeout_sec: 5,
  enabled: true,
  config: { method: "GET", contains: "items", warn_latency_ms: 1500, expect_status: [200, 204] },
  status: "ok",
  reason: null,
  error_kind: null,
  last: null,
  history: [],
  timeline: [],
  failing_since: null,
};

describe("CheckForm", () => {
  it("собирает HTTP-проверку с настройками", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<CheckForm onSubmit={onSubmit} onCancel={vi.fn()} />);
    fill("Название", " POS отвечает ");
    fill("Адрес", "https://pos.example/api/ping");
    fill("Проверять раз в", "300");
    fill("Таймаут, с", "5");
    fill("Текст в ответе", " items ");
    fill("Порог медленного, мс", "1500");
    fill("Ожидаемые коды", "200, 204 abc");
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit).toHaveBeenCalledWith({
      name: "POS отвечает",
      method: "http",
      target: "https://pos.example/api/ping",
      interval_sec: 300,
      timeout_sec: 5,
      config: { contains: "items", warn_latency_ms: 1500, expect_status: [200, 204] },
    });
  });

  it("для задания нет таймаута и настроек, интервал — ожидание отчёта", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<CheckForm onSubmit={onSubmit} onCancel={vi.fn()} />);
    fill("Тип", "exit_code");
    expect(screen.queryByLabelText("Таймаут, с")).toBeNull();
    expect(screen.getByLabelText("Ждать отчёт раз в")).toBeInTheDocument();
    fill("Команда", "python main_orders.py");
    fill("Ждать отчёт раз в", "86400");
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        name: null,
        method: "exit_code",
        target: "python main_orders.py",
        interval_sec: 86400,
        config: {},
      }),
    );
  });

  it("сертификат: пороги в днях", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<CheckForm onSubmit={onSubmit} onCancel={vi.fn()} />);
    fill("Тип", "tls");
    fill("Хост", "pos.example");
    fill("Предупредить за, дней", "30");
    fill("Сбой за, дней", "");
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    await waitFor(() =>
      expect(onSubmit.mock.calls[0][0].config).toEqual({ warn_days: 30, fail_days: 3 }),
    );
  });

  it("показывает ошибку сервера и даёт исправить", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("адрес во внутренней сети"));
    render(<CheckForm onSubmit={onSubmit} onCancel={vi.fn()} />);
    fill("Адрес", "http://localhost");
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("адрес во внутренней сети");
    expect(screen.getByRole("button", { name: "Сохранить" })).toBeEnabled();
  });

  it("при изменении заполнена текущими значениями и тип не меняется", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<CheckForm initial={existing} onSubmit={onSubmit} onCancel={vi.fn()} />);
    expect(screen.queryByLabelText("Тип")).toBeNull();
    expect(screen.getByLabelText("Адрес")).toHaveValue("https://pos.example/api/ping");
    expect(screen.getByLabelText("Проверять раз в")).toHaveValue("7200");
    expect(screen.getByRole("option", { name: "7200 с" })).toBeInTheDocument();
    expect(screen.getByLabelText("Ожидаемые коды")).toHaveValue("200, 204");
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    await waitFor(() => expect(onSubmit.mock.calls[0][0].config.contains).toBe("items"));
  });

  it("отмена закрывает форму", () => {
    const onCancel = vi.fn();
    render(<CheckForm onSubmit={vi.fn()} onCancel={onCancel} />);
    fireEvent.click(screen.getByRole("button", { name: "Отмена" }));
    expect(onCancel).toHaveBeenCalled();
  });
});
