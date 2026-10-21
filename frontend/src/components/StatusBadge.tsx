export type BlockStatus = "ok" | "warn" | "fail" | "unknown";

const PRESENTATION: Record<BlockStatus, { label: string; icon: string }> = {
  ok: { label: "Работает", icon: "✓" },
  warn: { label: "Предупреждение", icon: "!" },
  fail: { label: "Сбой", icon: "✕" },
  unknown: { label: "Нет данных", icon: "?" },
};

interface StatusBadgeProps {
  status: BlockStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const { label, icon } = PRESENTATION[status];
  return (
    <span className={`status-badge status-badge--${status}`} title={label}>
      <span className="status-badge__icon" aria-hidden="true">
        {icon}
      </span>
      <span className="status-badge__label">{label}</span>
    </span>
  );
}
