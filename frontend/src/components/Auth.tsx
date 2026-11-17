import { useState, type FormEvent, type ReactNode } from "react";
import { createProject, login, register, type Me, type MemberProject } from "../api";

function message(reason: unknown): string {
  const text = reason instanceof Error ? reason.message : String(reason);
  const known: Record<string, string> = {
    "wrong email or password": "Неверный email или пароль",
    "this email is already registered": "Этот email уже зарегистрирован",
    "registration is closed": "Регистрация закрыта",
  };
  return known[text] ?? text;
}

function Screen({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="auth">
      <div className="auth__card">
        <span className="brand auth__brand">
          <span className="visually-hidden">Pult</span>
          <img
            className="brand__glass"
            src="/glass/p.webp?v=3"
            srcSet="/glass/p@2x.webp?v=3 2x"
            alt=""
            aria-hidden="true"
          />
          <span aria-hidden="true">ult</span>
        </span>
        <h1 className="auth__title">{title}</h1>
        {children}
      </div>
    </div>
  );
}

interface SignInProps {
  onSignedIn: (me: Me) => void;
  api?: { login: typeof login; register: typeof register };
}

export function SignIn({ onSignedIn, api = { login, register } }: SignInProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [fields, setFields] = useState({ email: "", password: "", name: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const signup = mode === "register";
  const set = (key: keyof typeof fields) => (event: { target: { value: string } }) =>
    setFields((current) => ({ ...current, [key]: event.target.value }));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const request = signup
      ? api.register(fields.email, fields.password, fields.name)
      : api.login(fields.email, fields.password);
    request
      .then(onSignedIn)
      .catch((reason: unknown) => setError(message(reason)))
      .finally(() => setBusy(false));
  };

  return (
    <Screen title={signup ? "Регистрация" : "Вход"}>
      <form className="auth__form" onSubmit={submit}>
        {signup && (
          <label className="field">
            <span>Имя</span>
            <input value={fields.name} onChange={set("name")} required maxLength={150} />
          </label>
        )}
        <label className="field">
          <span>Email</span>
          <input
            type="email"
            value={fields.email}
            onChange={set("email")}
            required
            autoComplete="email"
          />
        </label>
        <label className="field">
          <span>Пароль</span>
          <input
            type="password"
            value={fields.password}
            onChange={set("password")}
            required
            minLength={signup ? 10 : 1}
            autoComplete={signup ? "new-password" : "current-password"}
          />
        </label>
        {error && (
          <p className="check-form__error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="glass-button" disabled={busy}>
          {signup ? "Зарегистрироваться" : "Войти"}
        </button>
      </form>
      <button
        type="button"
        className="text-button auth__switch"
        onClick={() => {
          setMode(signup ? "login" : "register");
          setError(null);
        }}
      >
        {signup ? "Уже есть аккаунт — войти" : "Нет аккаунта — зарегистрироваться"}
      </button>
    </Screen>
  );
}

interface NewProjectProps {
  onCreated: (project: MemberProject) => void;
  create?: typeof createProject;
}

export function NewProject({ onCreated, create = createProject }: NewProjectProps) {
  const [name, setName] = useState("");
  const [repo, setRepo] = useState("");
  const [created, setCreated] = useState<(MemberProject & { probe_token: string }) | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (created) {
    return (
      <Screen title="Проект создан">
        <p className="auth__text">
          Токен для отчётов с сервера. Он показывается один раз, сохраните его:
        </p>
        <pre className="auth__token">{created.probe_token}</pre>
        <button type="button" className="glass-button" onClick={() => onCreated(created)}>
          Открыть проект
        </button>
      </Screen>
    );
  }

  return (
    <Screen title="Первый проект">
      <form
        className="auth__form"
        onSubmit={(event) => {
          event.preventDefault();
          setError(null);
          create(name.trim(), repo.trim())
            .then(setCreated)
            .catch((reason: unknown) => setError(message(reason)));
        }}
      >
        <label className="field">
          <span>Название</span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            maxLength={150}
          />
        </label>
        <label className="field">
          <span>Репозиторий GitHub</span>
          <input
            value={repo}
            onChange={(event) => setRepo(event.target.value)}
            placeholder="owner/repo"
            required
            pattern="[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+"
          />
        </label>
        {error && (
          <p className="check-form__error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="glass-button">
          Создать
        </button>
      </form>
    </Screen>
  );
}
