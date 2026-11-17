import { STATUS_PRESENTATION, type BlockStatus } from "../status";

export type { BlockStatus };

export function StatusDot({ status }: { status: BlockStatus }) {
  return <span className={`status-dot status-dot--${status}`} aria-hidden="true" />;
}

export function StatusBadge({ status }: { status: BlockStatus }) {
  const { label, hint } = STATUS_PRESENTATION[status];
  return (
    <span className={`status-badge status-badge--${status}`} title={hint}>
      <StatusDot status={status} />
      <span className="status-badge__label">{label}</span>
    </span>
  );
}
