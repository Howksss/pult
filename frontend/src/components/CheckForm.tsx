import { useState, type FormEvent } from "react";
import type { Check, CheckInput, CheckMethod } from "../api";
import { buildConfig, METHOD_LABELS, PULL_METHODS } from "../checks";

const TARGETS: Record<CheckMethod, { label: string; placeholder: string }> = {
  http: { label: "Адрес", placeholder: "https://pos.example/api/ping" },
  tls: { label: "Хост", placeholder: "pos.example" },
  tcp: { label: "Хост и порт", placeholder: "db.example:5432" },
  exit_code: { label: "Команда", placeholder: "python main_orders.py" },
  heartbeat: { label: "Источник", placeholder: "cron на сервере" },
  log_pattern: { label: "Шаблон в логе", placeholder: "ConfigError" },
};

const INTERVALS: [number, string][] = [
  [60, "1 мин"],
  [300, "5 мин"],
  [900, "15 мин"],
  [3600, "1 ч"],
  [86_400, "1 день"],
];

const METHODS: CheckMethod[] = ["http", "tls", "tcp", "exit_code", "heartbeat", "log_pattern"];

function text(value: unknown): string {
  return value === undefined || value === null ? "" : String(value);
}

interface CheckFormProps {
  initial?: Check;
  onSubmit: (input: CheckInput) => Promise<unknown>;
  onCancel: () => void;
}

export function CheckForm({ initial, onSubmit, onCancel }: CheckFormProps) {
  const config = initial?.config ?? {};
  const [method, setMethod] = useState<CheckMethod>(initial?.method ?? "http");
  const [fields, setFields] = useState<Record<string, string>>({
    name: initial?.name ?? "",
    target: initial?.target ?? "",
    interval_sec: String(initial?.interval_sec ?? 60),
    timeout_sec: String(initial?.timeout_sec ?? 10),
    contains: text(config.contains),
    warn_latency_ms: text(config.warn_latency_ms),
    expect_status: Array.isArray(config.expect_status) ? config.expect_status.join(", ") : "",
    warn_days: text(config.warn_days ?? 14),
    fail_days: text(config.fail_days ?? 3),
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pull = PULL_METHODS.has(method);
  const intervals = INTERVALS.some(([value]) => String(value) === fields.interval_sec)
    ? INTERVALS
    : [...INTERVALS, [Number(fields.interval_sec), `${fields.interval_sec} с`] as [number, string]];

  const set = (key: string) => (event: { target: { value: string } }) =>
    setFields((current) => ({ ...current, [key]: event.target.value }));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const input: CheckInput = {
      name: fields.name.trim() || null,
      method,
      target: fields.target.trim(),
      interval_sec: Number(fields.interval_sec),
      config: buildConfig(method, fields),
    };
    if (pull) {
      input.timeout_sec = Number(fields.timeout_sec);
    }
    onSubmit(input)
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : String(reason)),
      )
      .finally(() => setBusy(false));
  };

  return (
    <form
      className="check-form"
      onSubmit={submit}
      aria-label={initial ? "Изменить проверку" : "Новая проверка"}
    >
      {!initial && (
        <label className="field">
          <span>Тип</span>
          <select value={method} onChange={(event) => setMethod(event.target.value as CheckMethod)}>
            {METHODS.map((value) => (
              <option key={value} value={value}>
                {METHOD_LABELS[value]}
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="field">
        <span>Название</span>
        <input
          value={fields.name}
          onChange={set("name")}
          placeholder="Например, POS отвечает"
          maxLength={120}
        />
      </label>
      <label className="field">
        <span>{TARGETS[method].label}</span>
        <input
          value={fields.target}
          onChange={set("target")}
          placeholder={TARGETS[method].placeholder}
          required
          maxLength={500}
        />
      </label>
      <div className="field-row">
        <label className="field">
          <span>{pull ? "Проверять раз в" : "Ждать отчёт раз в"}</span>
          <select value={fields.interval_sec} onChange={set("interval_sec")}>
            {intervals.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {pull && (
          <label className="field">
            <span>Таймаут, с</span>
            <input
              type="number"
              min={1}
              max={60}
              value={fields.timeout_sec}
              onChange={set("timeout_sec")}
            />
          </label>
        )}
      </div>
      {method === "http" && (
        <>
          <label className="field">
            <span>Текст в ответе</span>
            <input
              value={fields.contains}
              onChange={set("contains")}
              placeholder="Например, items"
            />
          </label>
          <div className="field-row">
            <label className="field">
              <span>Порог медленного, мс</span>
              <input
                type="number"
                min={1}
                max={60000}
                value={fields.warn_latency_ms}
                onChange={set("warn_latency_ms")}
              />
            </label>
            <label className="field">
              <span>Ожидаемые коды</span>
              <input
                value={fields.expect_status}
                onChange={set("expect_status")}
                placeholder="200, 204"
              />
            </label>
          </div>
        </>
      )}
      {method === "tls" && (
        <div className="field-row">
          <label className="field">
            <span>Предупредить за, дней</span>
            <input
              type="number"
              min={1}
              max={365}
              value={fields.warn_days}
              onChange={set("warn_days")}
            />
          </label>
          <label className="field">
            <span>Сбой за, дней</span>
            <input
              type="number"
              min={0}
              max={365}
              value={fields.fail_days}
              onChange={set("fail_days")}
            />
          </label>
        </div>
      )}
      {error && (
        <p className="check-form__error" role="alert">
          {error}
        </p>
      )}
      <div className="check-form__actions">
        <button type="button" className="text-button" onClick={onCancel}>
          Отмена
        </button>
        <button type="submit" className="glass-button glass-button--sm" disabled={busy}>
          {busy ? "Сохраняем…" : "Сохранить"}
        </button>
      </div>
    </form>
  );
}
