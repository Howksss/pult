export type BlockStatus = "ok" | "warn" | "fail" | "unknown";

export const STATUS_PRESENTATION: Record<BlockStatus, { label: string; icon: string }> = {
  ok: { label: "Работает", icon: "✓" },
  warn: { label: "Предупреждение", icon: "!" },
  fail: { label: "Сбой", icon: "✕" },
  unknown: { label: "Нет данных", icon: "?" },
};

export const STATUS_COLORS: Record<BlockStatus, string> = {
  ok: "#22c55e",
  warn: "#f59e0b",
  fail: "#ef4444",
  unknown: "#8b93a7",
};
