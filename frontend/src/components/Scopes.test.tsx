import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Scope } from "../api";
import { ScopesPanel } from "./Scopes";

const scopes: Scope[] = [
  { id: 1, path_glob: "integrations/pos.py", access: "read" },
  { id: 2, path_glob: "pipeline/**", access: "write" },
];

function setup(list: Scope[] = scopes) {
  const api = {
    load: vi.fn().mockResolvedValue(list),
    create: vi.fn().mockResolvedValue(scopes[0]),
    update: vi.fn().mockResolvedValue(scopes[0]),
    remove: vi.fn().mockResolvedValue(undefined),
  };
  render(<ScopesPanel blockId={3} api={api} />);
  return api;
}

describe("ScopesPanel", () => {
  it("показывает пути с правом", async () => {
    setup();
    expect(await screen.findByText("pipeline/**")).toBeInTheDocument();
    expect(screen.getByLabelText("Право на pipeline/**")).toHaveValue("write");
    expect(screen.getByLabelText("Право на integrations/pos.py")).toHaveValue("read");
  });

  it("добавляет путь и очищает поле", async () => {
    const api = setup([]);
    expect(await screen.findByText("Путей нет: агенту этот блок недоступен")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Путь в репозитории"), { target: { value: " bots/ " } });
    fireEvent.change(screen.getByLabelText("Право"), { target: { value: "write" } });
    fireEvent.click(screen.getByRole("button", { name: "Добавить" }));
    await waitFor(() => expect(api.create).toHaveBeenCalledWith(3, "bots/", "write"));
    await waitFor(() => expect(screen.getByLabelText("Путь в репозитории")).toHaveValue(""));
    expect(api.load).toHaveBeenCalledTimes(2);
  });

  it("пустой путь не отправляет", async () => {
    const api = setup([]);
    await screen.findByText("Путей нет: агенту этот блок недоступен");
    fireEvent.click(screen.getByRole("button", { name: "Добавить" }));
    expect(api.create).not.toHaveBeenCalled();
  });

  it("меняет право и убирает путь", async () => {
    const api = setup();
    fireEvent.change(await screen.findByLabelText("Право на integrations/pos.py"), {
      target: { value: "write" },
    });
    await waitFor(() => expect(api.update).toHaveBeenCalledWith(1, "write"));
    fireEvent.click(screen.getByRole("button", { name: "Убрать pipeline/**" }));
    await waitFor(() => expect(api.remove).toHaveBeenCalledWith(2));
  });

  it("показывает отказ сервера", async () => {
    const api = setup([]);
    api.create.mockRejectedValue(new Error("путь не может выходить за репозиторий"));
    await screen.findByText("Путей нет: агенту этот блок недоступен");
    fireEvent.change(screen.getByLabelText("Путь в репозитории"), { target: { value: "../.ssh" } });
    fireEvent.click(screen.getByRole("button", { name: "Добавить" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("выходить за репозиторий");
  });

  it("сообщает об ошибке загрузки", async () => {
    const api = {
      load: vi.fn().mockRejectedValue(new Error("API 500")),
      create: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
    };
    render(<ScopesPanel blockId={3} api={api} />);
    expect(await screen.findByText("Не удалось загрузить область")).toBeInTheDocument();
  });
});
