import { useEffect, useState } from "react";
import { fetchChecks, type BlockChecks, type Check, type HistoryPoint } from "../api";
import { excerpt, facts, formatAgo, formatDuration, METHOD_LABELS } from "../checks";
import { STATUS_PRESENTATION } from "../status";
import { StatusDot } from "./StatusBadge";

function History({ points, now }: { points: HistoryPoint[]; now: Date }) {
  if (points.length === 0) {
    return null;
  }
  return (
    <div
      className="check-history"
      role="img"
      aria-label={`История: ${points.length} последних результатов`}
    >
      {points.map((point) => (
        <span
          key={point.checked_at}
          className={`check-history__tick check-history__tick--${point.status}`}
          title={`${STATUS_PRESENTATION[point.status].label}, ${formatAgo(point.checked_at, now)}${
            point.latency_ms === null ? "" : `, ${formatDuration(point.latency_ms)}`
          }`}
        />
      ))}
    </div>
  );
}

export function CheckItem({ check, now }: { check: Check; now: Date }) {
  const [open, setOpen] = useState(check.status !== "ok");
  const details = check.last?.details ?? null;
  const list = facts(details);
  const quote = excerpt(details);
  const latency = check.last?.latency_ms ?? null;
  return (
    <li className={`check check--${check.status}${check.enabled ? "" : " check--off"}`}>
      <button
        type="button"
        className="check__head"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <StatusDot status={check.status} />
        <span className="check__text">
          <span className="check__title">{check.title}</span>
          <span className="check__meta">
            {METHOD_LABELS[check.method]} · {check.target}
          </span>
        </span>
        <span className="check__when">
          {check.last ? formatAgo(check.last.checked_at, now) : "не было"}
          {latency !== null && <span className="check__latency">{formatDuration(latency)}</span>}
        </span>
      </button>
      {open && (
        <div className="check__body">
          {check.reason && <p className="check__reason">{check.reason}</p>}
          {list.length > 0 && (
            <dl className="check__facts">
              {list.map((fact) => (
                <div key={fact.label} className="check__fact">
                  <dt>{fact.label}</dt>
                  <dd>{fact.value}</dd>
                </div>
              ))}
            </dl>
          )}
          {quote && (
            <figure className="check__excerpt">
              <figcaption>{quote.label}</figcaption>
              <pre>{quote.text}</pre>
            </figure>
          )}
          <History points={check.history} now={now} />
        </div>
      )}
    </li>
  );
}

interface ChecksPanelProps {
  blockId: number;
  refreshKey: string;
  load?: (blockId: number, signal: AbortSignal) => Promise<BlockChecks>;
}

export function ChecksPanel({ blockId, refreshKey, load = fetchChecks }: ChecksPanelProps) {
  const [data, setData] = useState<BlockChecks | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setData(null);
    setFailed(false);
  }, [blockId]);

  useEffect(() => {
    const controller = new AbortController();
    load(blockId, controller.signal)
      .then((result) => {
        setData(result);
        setFailed(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setFailed(true);
        }
      });
    return () => controller.abort();
  }, [blockId, refreshKey, load]);

  const checks = data?.block_id === blockId ? data.checks : null;
  const now = new Date(data?.generated_at ?? Date.now());
  return (
    <section className="inspector__section">
      <h3 className="inspector__heading">
        Проверки
        {checks && <span className="inspector__heading-count">{checks.length}</span>}
      </h3>
      {failed && !checks && <p className="inspector__empty">Не удалось загрузить проверки</p>}
      {!failed && !checks && <p className="inspector__empty">Загружаем проверки…</p>}
      {checks && checks.length === 0 && (
        <p className="inspector__empty">Проверок нет: статус блока неизвестен</p>
      )}
      {checks && checks.length > 0 && (
        <ul className="check-list">
          {checks.map((check) => (
            <CheckItem key={check.id} check={check} now={now} />
          ))}
        </ul>
      )}
    </section>
  );
}
