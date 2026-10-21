import { Moon, Sun, Waypoints } from "lucide-react";
import { STATUS_COLORS, type BlockStatus } from "../status";
import type { Theme } from "../theme";
import { StatusBadge } from "./StatusBadge";

const CHIP_ORDER: BlockStatus[] = ["fail", "warn", "unknown", "ok"];
const BAR_ORDER: BlockStatus[] = ["ok", "unknown", "warn", "fail"];

interface TopBarProps {
  projectId: number;
  counts: Record<BlockStatus, number> | null;
  updatedAt: string | null;
  stale: boolean;
  theme: Theme;
  onToggleTheme: () => void;
}

export function TopBar({ projectId, counts, updatedAt, stale, theme, onToggleTheme }: TopBarProps) {
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
      {counts && total > 0 && (
        <div className="health">
          <div
            className="health__bar"
            role="img"
            aria-label={`В норме ${counts.ok} из ${total}`}
            title={`В норме ${counts.ok} из ${total}`}
          >
            {BAR_ORDER.filter((status) => counts[status] > 0).map((status) => (
              <span
                key={status}
                style={{ flexGrow: counts[status], background: STATUS_COLORS[status] }}
              />
            ))}
          </div>
          <span className="health__ratio">
            {counts.ok}/{total}
          </span>
          <div className="health__chips">
            {CHIP_ORDER.map((status) => (
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
