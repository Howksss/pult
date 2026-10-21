import { STATUS_PRESENTATION, type BlockStatus } from "../status";

export type { BlockStatus };

export function StatusIcon({ status }: { status: BlockStatus }) {
  return (
    <span className={`status-icon status-icon--${status}`} aria-hidden="true">
      {STATUS_PRESENTATION[status].icon}
    </span>
  );
}

interface StatusBadgeProps {
  status: BlockStatus;
  count?: number;
}

export function StatusBadge({ status, count }: StatusBadgeProps) {
  const { label } = STATUS_PRESENTATION[status];
  const classes = ["status-badge", `status-badge--${status}`];
  if (count === 0) {
    classes.push("status-badge--empty");
  }
  return (
    <span className={classes.join(" ")} title={label}>
      <StatusIcon status={status} />
      <span className="status-badge__label">{label}</span>
      {count !== undefined && <span className="status-badge__count">{count}</span>}
    </span>
  );
}
