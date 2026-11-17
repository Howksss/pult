import type { MemberProject } from "../api";
import type { Summary } from "../graph";
import type { BlockStatus } from "../status";
import { Icon } from "./Icon";
import { StatusDot } from "./StatusBadge";

const TICK_ORDER: BlockStatus[] = ["fail", "warn", "unknown", "ok"];

function working(ok: number, total: number): string {
  const verb = ok % 10 === 1 && ok % 100 !== 11 ? "работает" : "работают";
  return `${ok} из ${total} ${verb}`;
}

interface SystemStatusProps {
  summary: Summary;
  onShowBlock: (blockId: number) => void;
}

export function SystemStatus({ summary, onShowBlock }: SystemStatusProps) {
  const { status, text, blockId } = summary;
  const className = `system-status system-status--${status}`;
  if (blockId === null) {
    return (
      <span className={className} role="status">
        <StatusDot status={status} />
        <span className="system-status__text">{text}</span>
      </span>
    );
  }
  return (
    <button
      type="button"
      className={className}
      onClick={() => onShowBlock(blockId)}
      title="Показать блок"
    >
      <StatusDot status={status} />
      <span className="system-status__text">{text}</span>
      <Icon name="arrowRight" size={15} className="system-status__arrow" />
    </button>
  );
}

interface TopBarProps {
  projectId: number;
  projectName: string | null;
  counts: Record<BlockStatus, number> | null;
  summary: Summary | null;
  updatedAt: string | null;
  stale: boolean;
  onShowBlock: (blockId: number) => void;
  projects?: MemberProject[];
  userName?: string;
  onSwitchProject?: (projectId: number) => void;
  onMembers?: () => void;
  onLogout?: () => void;
}

export function TopBar({
  projectId,
  projectName,
  counts,
  summary,
  updatedAt,
  stale,
  onShowBlock,
  projects = [],
  userName,
  onSwitchProject,
  onMembers,
  onLogout,
}: TopBarProps) {
  const total = counts ? Object.values(counts).reduce((sum, value) => sum + value, 0) : 0;
  const ticks = counts
    ? TICK_ORDER.flatMap((status) => Array.from({ length: counts[status] }, () => status))
    : [];
  return (
    <header className="topbar">
      <span className="brand">
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
      {projects.length > 1 && onSwitchProject ? (
        <select
          className="topbar__switch"
          value={projectId}
          aria-label="Проект"
          onChange={(event) => onSwitchProject(Number(event.target.value))}
        >
          {projects.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      ) : (
        <span className="topbar__project">{projectName ?? `Проект ${projectId}`}</span>
      )}
      {counts && summary && total > 0 && (
        <SystemStatus summary={summary} onShowBlock={onShowBlock} />
      )}
      <span className="topbar__spacer" />
      {counts && total > 0 && (
        <div className="health">
          <div className="health__ticks" role="img" aria-label={working(counts.ok, total)}>
            {ticks.map((status, index) => (
              <span key={index} className={`tick tick--${status}`} />
            ))}
          </div>
          <span className="health__count">{working(counts.ok, total)}</span>
        </div>
      )}
      {updatedAt && (
        <span className={stale ? "live live--stale" : "live"}>
          {stale && <span className="live__dot" aria-hidden="true" />}
          {stale ? "Нет связи, данные от" : "Обновлено"}
          <span className="live__time">{new Date(updatedAt).toLocaleTimeString("ru-RU")}</span>
        </span>
      )}
      {onMembers && (
        <button type="button" className="text-button" onClick={onMembers}>
          Участники
        </button>
      )}
      {onLogout && (
        <button type="button" className="text-button" onClick={onLogout} title={userName}>
          Выйти
        </button>
      )}
    </header>
  );
}
