import { STATUS_PRESENTATION, type BlockStatus } from "../status";

export type { BlockStatus };

export function StatusDot({ status }: { status: BlockStatus }) {
  return <span className={`status-dot status-dot--${status}`} aria-hidden="true" />;
}

interface StatusBadgeProps {
  status: BlockStatus;
  count?: number;
}

export function StatusBadge({ status, count }: StatusBadgeProps) {
  const { label, hint } = STATUS_PRESENTATION[status];
  const classes = ["status-badge", `status-badge--${status}`];
  if (count === 0) {
    classes.push("status-badge--empty");
  }
  return (
    <span className={classes.join(" ")} title={hint}>
      <StatusDot status={status} />
      <span className="status-badge__label">{label}</span>
      {count !== undefined && <span className="status-badge__count">{count}</span>}
    </span>
  );
}
