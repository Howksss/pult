import type { CheckMethod } from "./api";

export const METHOD_LABELS: Record<CheckMethod, string> = {
  http: "HTTP",
  tls: "Сертификат",
  tcp: "Порт",
  heartbeat: "Heartbeat",
  exit_code: "Задание",
  log_pattern: "Лог",
};

export function plural(count: number, forms: [string, string, string]): string {
  const tens = count % 100;
  const ones = count % 10;
  if (tens >= 11 && tens <= 14) {
    return forms[2];
  }
  if (ones === 1) {
    return forms[0];
  }
  return ones >= 2 && ones <= 4 ? forms[1] : forms[2];
}

const CHECK_FORMS: [string, string, string] = ["проверка", "проверки", "проверок"];

export function checksCount(problem: number, total: number): { short: string; full: string } {
  if (problem > 0) {
    return { short: `${problem} из ${total}`, full: `Проблемы в ${problem} из ${total} проверок` };
  }
  const all = `${total} ${plural(total, CHECK_FORMS)}`;
  return { short: all, full: `Все ${all} проходят` };
}

export function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)} мс`;
  }
  if (ms < 60_000) {
    return `${(ms / 1000).toFixed(1).replace(".", ",")} с`;
  }
  const minutes = Math.floor(ms / 60_000);
  const rest = Math.round((ms % 60_000) / 1000);
  return rest ? `${minutes} мин ${rest} с` : `${minutes} мин`;
}

export function formatAgo(iso: string, now: Date): string {
  const seconds = Math.max(0, (now.getTime() - new Date(iso).getTime()) / 1000);
  if (seconds < 45) {
    return "только что";
  }
  if (seconds < 3600) {
    return `${Math.max(1, Math.round(seconds / 60))} мин назад`;
  }
  if (seconds < 86_400) {
    return `${Math.floor(seconds / 3600)} ч назад`;
  }
  return new Date(iso).toLocaleDateString("ru-RU");
}

export type Fact = { label: string; value: string };
export type Excerpt = { label: string; text: string };

const EXCERPT_KEYS: Record<string, string> = {
  stderr_tail: "Вывод stderr",
  body_excerpt: "Ответ сервера",
  lines: "Строки лога",
};

const HIDDEN = new Set(["reason", "port", "final_url", ...Object.keys(EXCERPT_KEYS)]);

function text(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value);
}

function date(value: unknown): string {
  const parsed = new Date(text(value));
  return Number.isNaN(parsed.getTime()) ? text(value) : parsed.toLocaleDateString("ru-RU");
}

const KNOWN: [string, string, (details: Record<string, unknown>) => string][] = [
  [
    "status_code",
    "Код ответа",
    (d) => `${text(d.status_code)} ${d.reason ? text(d.reason) : ""}`.trim(),
  ],
  ["exit_code", "Код выхода", (d) => text(d.exit_code)],
  ["url", "Адрес", (d) => (d.final_url ? `${text(d.url)} → ${text(d.final_url)}` : text(d.url))],
  ["host", "Хост", (d) => (d.port ? `${text(d.host)}:${text(d.port)}` : text(d.host))],
  ["command", "Команда", (d) => text(d.command)],
  ["method", "Метод", (d) => text(d.method)],
  ["latency_ms", "Время ответа", (d) => formatDuration(Number(d.latency_ms))],
  ["duration_ms", "Длительность", (d) => formatDuration(Number(d.duration_ms))],
  ["days_left", "Осталось дней", (d) => text(d.days_left)],
  ["not_after", "Действует до", (d) => date(d.not_after)],
  ["issuer", "Кем выдан", (d) => text(d.issuer)],
  ["subject", "Кому выдан", (d) => text(d.subject)],
  ["pattern", "Шаблон", (d) => text(d.pattern)],
  ["content_type", "Тип ответа", (d) => text(d.content_type)],
  ["load_avg", "Нагрузка", (d) => text(d.load_avg)],
  ["error", "Ошибка", (d) => text(d.error)],
];

export function facts(details: Record<string, unknown> | null): Fact[] {
  if (!details) {
    return [];
  }
  const known = new Set(KNOWN.map(([key]) => key));
  const listed = KNOWN.filter(([key]) => details[key] !== undefined && details[key] !== null).map(
    ([, label, format]) => ({ label, value: format(details) }),
  );
  const extra = Object.entries(details)
    .filter(([key, value]) => !known.has(key) && !HIDDEN.has(key) && value !== null)
    .map(([key, value]) => ({ label: key, value: text(value) }));
  return [...listed, ...extra];
}

export function excerpt(details: Record<string, unknown> | null): Excerpt | null {
  if (!details) {
    return null;
  }
  for (const [key, label] of Object.entries(EXCERPT_KEYS)) {
    const value = details[key];
    if (Array.isArray(value) && value.length > 0) {
      return { label, text: value.map(text).join("\n") };
    }
    if (typeof value === "string" && value.trim()) {
      return { label, text: value };
    }
  }
  return null;
}
