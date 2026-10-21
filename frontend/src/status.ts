export type BlockStatus = "ok" | "warn" | "fail" | "unknown";

export const STATUS_PRESENTATION: Record<BlockStatus, { label: string; hint: string }> = {
  ok: { label: "Работает", hint: "Все проверки блока прошли" },
  warn: { label: "Предупреждение", hint: "Одна из проверок блока прошла с предупреждением" },
  fail: { label: "Сбой", hint: "Одна из проверок блока не прошла" },
  unknown: {
    label: "Нет данных",
    hint: "Свежих проверок нет: probe не подключён или давно не присылал результаты",
  },
};

export const STATUS_COLORS: Record<BlockStatus, string> = {
  ok: "#22c55e",
  warn: "#f59e0b",
  fail: "#ef4444",
  unknown: "#8b93a7",
};
