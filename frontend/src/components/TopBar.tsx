import { Moon, Sun, Waypoints } from "lucide-react";
import type { Summary } from "../graph";
import { STATUS_COLORS, type BlockStatus } from "../status";
import type { Theme } from "../theme";
import { StatusBadge, StatusDot } from "./StatusBadge";

const CHIP_ORDER: BlockStatus[] = ["fail", "warn", "unknown", "ok"];
const BAR_ORDER: BlockStatus[] = ["ok", "unknown", "warn", "fail"];

interface SystemStatusProps {
  summary: Summary;
  onShowBlock: (blockId: number) => void;
}

export function SystemStatus({ summary, onShowBlock }: SystemStatusProps) {
  const { status, text, blockId } = summary;
  const className = `system-status system-status--${status}`;
  const content = (
    <>
      <StatusDot status={status} />
      <span className="system-status__text">{text}</span>
    </>
  );
  if (blockId === null) {
    return (
      <span className={className} role="status">
        {content}
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
      {content}
    </button>
  );
}

interface TopBarProps {
  projectId: number;
  counts: Record<BlockStatus, number> | null;
  summary: Summary | null;
  updatedAt: string | null;
  stale: boolean;
  theme: Theme;
  onToggleTheme: () => void;
  onShowBlock: (blockId: number) => void;
}

export function TopBar({
  projectId,
  counts,
  summary,
  updatedAt,
  stale,
  theme,
  onToggleTheme,
  onShowBlock,
}: TopBarProps) {
  const total = counts ? Object.values(counts).reduce((sum, value) => sum + value, 0) : 0;
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand__mark" aria-hidden="true">
          <Waypoints size={16} strokeWidth={2} />
        </span>
        Pult
      </div>
      <span className="topbar__divider" aria-hidden="true" />
      <span className="topbar__project">Проект {projectId}</span>
      {counts && summary && total > 0 && (
        <div className="health">
          <SystemStatus summary={summary} onShowBlock={onShowBlock} />
          <div
            className="health__bar"
            role="img"
            aria-label={`Работает ${counts.ok} из ${total}`}
            title={`Работает ${counts.ok} из ${total}`}
          >
            {BAR_ORDER.filter((status) => counts[status] > 0).map((status) => (
              <span
                key={status}
                style={{ flexGrow: counts[status], background: STATUS_COLORS[status] }}
              />
            ))}
          </div>
          <div className="health__chips">
            {CHIP_ORDER.filter((status) => counts[status] > 0).map((status) => (
              <StatusBadge key={status} status={status} count={counts[status]} />
            ))}
          </div>
        </div>
      )}
      <span className="topbar__spacer" />
      {updatedAt && (
        <span className={stale ? "live live--stale" : "live"}>
          <span className="live__dot" aria-hidden="true" />
          {stale ? "Нет связи" : "В сети"}
          <span className="live__time">{new Date(updatedAt).toLocaleTimeString("ru-RU")}</span>
        </span>
      )}
      <button
        type="button"
        className="icon-button"
        onClick={onToggleTheme}
        aria-label={theme === "dark" ? "Светлая тема" : "Тёмная тема"}
        title={theme === "dark" ? "Светлая тема" : "Тёмная тема"}
      >
        {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
      </button>
    </header>
  );
}
