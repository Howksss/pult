import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Me, Member } from "../api";
import { NewProject, SignIn } from "./Auth";
import { MembersPanel } from "./Members";
import { TopBar } from "./TopBar";

const me: Me = { id: 1, email: "owner@example.com", full_name: "Владелец", projects: [] };

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

describe("SignIn", () => {
  it("входит по email и паролю", async () => {
    const api = { login: vi.fn().mockResolvedValue(me), register: vi.fn() };
    const onSignedIn = vi.fn();
    render(<SignIn onSignedIn={onSignedIn} api={api} />);
    fill("Email", "owner@example.com");
    fill("Пароль", "secret");
    fireEvent.click(screen.getByRole("button", { name: "Войти" }));
    await waitFor(() => expect(onSignedIn).toHaveBeenCalledWith(me));
    expect(api.login).toHaveBeenCalledWith("owner@example.com", "secret");
  });

  it("переводит ошибку сервера", async () => {
    const api = {
      login: vi.fn().mockRejectedValue(new Error("wrong email or password")),
      register: vi.fn(),
    };
    render(<SignIn onSignedIn={vi.fn()} api={api} />);
    fill("Email", "owner@example.com");
    fill("Пароль", "nope");
    fireEvent.click(screen.getByRole("button", { name: "Войти" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Неверный email или пароль");
  });

  it("регистрирует с именем", async () => {
    const api = { login: vi.fn(), register: vi.fn().mockResolvedValue(me) };
    render(<SignIn onSignedIn={vi.fn()} api={api} />);
    fireEvent.click(screen.getByRole("button", { name: "Нет аккаунта — зарегистрироваться" }));
    expect(screen.getByRole("heading", { name: "Регистрация" })).toBeInTheDocument();
    fill("Имя", "Владелец");
    fill("Email", "owner@example.com");
    fill("Пароль", "long enough password");
    fireEvent.click(screen.getByRole("button", { name: "Зарегистрироваться" }));
    await waitFor(() =>
      expect(api.register).toHaveBeenCalledWith(
        "owner@example.com",
        "long enough password",
        "Владелец",
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Уже есть аккаунт — войти" }));
    expect(screen.getByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });
});

describe("NewProject", () => {
  it("создаёт проект и один раз показывает токен", async () => {
    const created = { id: 5, name: "Пилот", role: "owner" as const, probe_token: "tok-123" };
    const create = vi.fn().mockResolvedValue(created);
    const onCreated = vi.fn();
    render(<NewProject onCreated={onCreated} create={create} />);
    fill("Название", " Пилот ");
    fill("Репозиторий GitHub", "example/pilot");
    fireEvent.click(screen.getByRole("button", { name: "Создать" }));
    expect(await screen.findByText("tok-123")).toBeInTheDocument();
    expect(create).toHaveBeenCalledWith("Пилот", "example/pilot");
    fireEvent.click(screen.getByRole("button", { name: "Открыть проект" }));
    expect(onCreated).toHaveBeenCalledWith(created);
  });

  it("показывает ошибку", async () => {
    render(
      <NewProject onCreated={vi.fn()} create={vi.fn().mockRejectedValue(new Error("API 422"))} />,
    );
    fill("Название", "Пилот");
    fill("Репозиторий GitHub", "example/pilot");
    fireEvent.click(screen.getByRole("button", { name: "Создать" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("API 422");
  });
});

const members: Member[] = [
  { user_id: 1, email: "owner@example.com", full_name: "Владелец", role: "owner" },
  { user_id: 2, email: "client@example.com", full_name: "Управляющий", role: "client" },
];

function membersApi() {
  return {
    list: vi.fn().mockResolvedValue(members),
    add: vi.fn().mockResolvedValue(members[1]),
    update: vi.fn().mockResolvedValue(members[1]),
    remove: vi.fn().mockResolvedValue(undefined),
  };
}

describe("MembersPanel", () => {
  it("владелец добавляет, меняет роль и убирает участника", async () => {
    const api = membersApi();
    render(<MembersPanel projectId={7} myRole="owner" onClose={vi.fn()} api={api} />);
    fireEvent.change(await screen.findByLabelText("Роль client@example.com"), {
      target: { value: "developer" },
    });
    await waitFor(() => expect(api.update).toHaveBeenCalledWith(7, 2, "developer"));
    fireEvent.click(screen.getByRole("button", { name: "Убрать client@example.com" }));
    await waitFor(() => expect(api.remove).toHaveBeenCalledWith(7, 2));
    fill("Email участника", "dev@example.com");
    fill("Роль", "developer");
    fireEvent.click(screen.getByRole("button", { name: "Добавить" }));
    await waitFor(() => expect(api.add).toHaveBeenCalledWith(7, "dev@example.com", "developer"));
  });

  it("переводит отказ сервера", async () => {
    const api = membersApi();
    api.remove.mockRejectedValue(new Error("the project must keep at least one owner"));
    render(<MembersPanel projectId={7} myRole="owner" onClose={vi.fn()} api={api} />);
    fireEvent.click(await screen.findByRole("button", { name: "Убрать owner@example.com" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("хотя бы один владелец");
  });

  it("заказчик только смотрит", async () => {
    const onClose = vi.fn();
    render(<MembersPanel projectId={7} myRole="client" onClose={onClose} api={membersApi()} />);
    expect(await screen.findByText("заказчик")).toBeInTheDocument();
    expect(screen.queryByLabelText("Email участника")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Закрыть" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("сообщает об ошибке загрузки", async () => {
    const api = { ...membersApi(), list: vi.fn().mockRejectedValue(new Error("API 500")) };
    render(<MembersPanel projectId={7} myRole="owner" onClose={vi.fn()} api={api} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось загрузить участников");
  });
});

describe("TopBar с проектами", () => {
  it("переключает проект, открывает участников и выходит", () => {
    const onSwitchProject = vi.fn();
    const onMembers = vi.fn();
    const onLogout = vi.fn();
    render(
      <TopBar
        projectId={1}
        projectName="Пилот"
        counts={null}
        summary={null}
        updatedAt={null}
        stale={false}
        onShowBlock={vi.fn()}
        projects={[
          { id: 1, name: "Пилот", role: "owner" },
          { id: 2, name: "Склад", role: "client" },
        ]}
        userName="Владелец"
        onSwitchProject={onSwitchProject}
        onMembers={onMembers}
        onLogout={onLogout}
      />,
    );
    fill("Проект", "2");
    expect(onSwitchProject).toHaveBeenCalledWith(2);
    fireEvent.click(screen.getByRole("button", { name: "Участники" }));
    fireEvent.click(screen.getByRole("button", { name: "Выйти" }));
    expect(onMembers).toHaveBeenCalled();
    expect(onLogout).toHaveBeenCalled();
  });
});
