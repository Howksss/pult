import {
  type CSSProperties,
  type FocusEvent,
  type KeyboardEvent,
  useCallback,
  useEffect,
  useState,
} from "react";
import {
  defaultChecksApi,
  type BlockChecks,
  type Check,
  type CheckPatch,
  type ChecksApi,
  type TimelineBucket,
} from "../api";
import {
  bucketDetails,
  bucketRange,
  bucketShares,
  bucketStatus,
  clock,
  cronLine,
  excerpt,
  facts,
  formatAgo,
  formatDuration,
  formatSpan,
  METHOD_LABELS,
  PULL_METHODS,
  sinceLabel,
} from "../checks";
import { CheckForm } from "./CheckForm";
import { StatusDot } from "./StatusBadge";

const ROW = 12;
const STEPS: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1 };

function moveFocus(event: KeyboardEvent<HTMLDivElement>) {
  const step = STEPS[event.key];
  if (!step) {
    return;
  }
  const items = [...event.currentTarget.querySelectorAll<HTMLButtonElement>(".timeline__hour")];
  const index = items.indexOf(document.activeElement as HTMLButtonElement);
  items[Math.min(items.length - 1, Math.max(0, index + step))]?.focus();
  event.preventDefault();
}

interface HourProps {
  bucket: TimelineBucket;
  current: boolean;
  active: boolean;
  tabbable: boolean;
  onActivate: () => void;
}

function Hour({ bucket, current, active, tabbable, onActivate }: HourProps) {
  const shares = bucketShares(bucket);
  const style = {
    "--fail-share": `${shares.fail}%`,
    "--warn-share": `${shares.warn}%`,
  } as CSSProperties;
  const classes = ["timeline__hour"];
  if (active) classes.push("timeline__hour--active");
  if (current) classes.push("timeline__hour--current");
  return (
    <button
      type="button"
      className={classes.join(" ")}
      tabIndex={tabbable ? 0 : -1}
      aria-label={`${bucketRange(bucket.start, current)}: ${bucketDetails(bucket)}`}
      onMouseEnter={onActivate}
      onFocus={onActivate}
      onClick={onActivate}
    >
      <span className={`timeline__bar timeline__bar--${bucketStatus(bucket)}`} style={style} />
      <span className="timeline__hour-label">{clock(bucket.start).slice(0, 2)}</span>
    </button>
  );
}

function Timeline({ check, now }: { check: Check; now: Date }) {
  const [active, setActive] = useState<number | null>(null);
  const buckets = check.timeline;
  if (buckets.length === 0) {
    return null;
  }
  const last = buckets.length - 1;
  const problems = buckets.filter((bucket) => bucket.fail + bucket.warn > 0).length;
  const shown = active === null ? null : buckets[active];
  const leave = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setActive(null);
    }
  };
  return (
    <div className="timeline">
      {check.failing_since && (
        <p className="timeline__since">
          {check.status === "warn" ? "Предупреждение" : "Сбой"} с{" "}
          {sinceLabel(check.failing_since, now)},{" "}
          {formatSpan((now.getTime() - new Date(check.failing_since).getTime()) / 1000)}
        </p>
      )}
      <div
        className={`timeline__rows${active === null ? "" : " timeline__rows--focus"}`}
        role="group"
        aria-label={`Последние сутки по часам: проблемы в ${problems} из ${buckets.length} часов`}
        onMouseLeave={() => setActive(null)}
        onBlur={leave}
        onKeyDown={moveFocus}
      >
        {[0, ROW].map((offset) => (
          <div key={offset} className="timeline__row">
            {buckets.slice(offset, offset + ROW).map((bucket, position) => {
              const index = offset + position;
              return (
                <Hour
                  key={bucket.start}
                  bucket={bucket}
                  current={index === last}
                  active={index === active}
                  tabbable={index === (active ?? last)}
                  onActivate={() => setActive(index)}
                />
              );
            })}
          </div>
        ))}
      </div>
      <div className="timeline__readout" aria-live="polite">
        {shown ? (
          <>
            <span className="timeline__range">{bucketRange(shown.start, active === last)}</span>
            <span>{bucketDetails(shown)}</span>
          </>
        ) : (
          <>
            <span className="timeline__legend">
              <span className="timeline__swatch timeline__swatch--fail" />
              сбой
              <span className="timeline__swatch timeline__swatch--warn" />
              предупреждение
              <span className="timeline__swatch timeline__swatch--ok" />
              норма
            </span>
            <span>Деление — час, высота цвета — доля проверок</span>
          </>
        )}
      </div>
    </div>
  );
}

interface CheckItemProps {
  check: Check;
  now: Date;
  api: ChecksApi;
  onChanged: () => void;
}

export function CheckItem({ check, now, api, onChanged }: CheckItemProps) {
  const [open, setOpen] = useState(check.status !== "ok");
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const details = check.last?.details ?? null;
  const list = facts(details);
  const quote = excerpt(details);
  const latency = check.last?.latency_ms ?? null;
  const pull = PULL_METHODS.has(check.method);

  const act = (label: string, action: () => Promise<unknown>) => {
    setBusy(label);
    setError(null);
    action()
      .then(onChanged)
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : String(reason)),
      )
      .finally(() => setBusy(null));
  };

  if (editing) {
    return (
      <li className="check">
        <CheckForm
          initial={check}
          onCancel={() => setEditing(false)}
          onSubmit={(input) => {
            const patch: CheckPatch = {
              name: input.name,
              target: input.target,
              interval_sec: input.interval_sec,
              timeout_sec: input.timeout_sec,
              config: input.config,
            };
            return api.update(check.id, patch).then(() => {
              setEditing(false);
              onChanged();
            });
          }}
        />
      </li>
    );
  }

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
          <Timeline check={check} now={now} />
          {!pull && (
            <figure className="check__excerpt">
              <figcaption>Строка для cron на сервере</figcaption>
              <pre>{cronLine(check)}</pre>
            </figure>
          )}
          {error && (
            <p className="check-form__error" role="alert">
              {error}
            </p>
          )}
          <div className="check__actions">
            {confirming ? (
              <>
                <span className="check__confirm">Удалить вместе с историей?</span>
                <button
                  type="button"
                  className="text-button text-button--danger"
                  disabled={busy !== null}
                  onClick={() => act("remove", () => api.remove(check.id))}
                >
                  Удалить
                </button>
                <button type="button" className="text-button" onClick={() => setConfirming(false)}>
                  Отмена
                </button>
              </>
            ) : (
              <>
                {pull && check.enabled && (
                  <button
                    type="button"
                    className="text-button"
                    disabled={busy !== null}
                    onClick={() => act("run", () => api.run(check.id))}
                  >
                    {busy === "run" ? "Проверяем…" : "Проверить сейчас"}
                  </button>
                )}
                <button type="button" className="text-button" onClick={() => setEditing(true)}>
                  Изменить
                </button>
                <button
                  type="button"
                  className="text-button"
                  disabled={busy !== null}
                  onClick={() =>
                    act("toggle", () => api.update(check.id, { enabled: !check.enabled }))
                  }
                >
                  {check.enabled ? "Выключить" : "Включить"}
                </button>
                <button type="button" className="text-button" onClick={() => setConfirming(true)}>
                  Удалить
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </li>
  );
}

interface ChecksPanelProps {
  blockId: number;
  refreshKey: string;
  api?: ChecksApi;
}

export function ChecksPanel({ blockId, refreshKey, api = defaultChecksApi }: ChecksPanelProps) {
  const [data, setData] = useState<BlockChecks | null>(null);
  const [failed, setFailed] = useState(false);
  const [adding, setAdding] = useState(false);
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((value) => value + 1), []);

  useEffect(() => {
    setData(null);
    setFailed(false);
    setAdding(false);
  }, [blockId]);

  useEffect(() => {
    const controller = new AbortController();
    api
      .load(blockId, controller.signal)
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
  }, [blockId, refreshKey, api, version]);

  const checks = data?.block_id === blockId ? data.checks : null;
  const now = new Date(data?.generated_at ?? Date.now());
  return (
    <section className="inspector__section">
      <div className="inspector__section-head">
        <h3 className="inspector__heading">
          Проверки
          {checks && <span className="inspector__heading-count">{checks.length}</span>}
        </h3>
        {!adding && (
          <button type="button" className="text-button" onClick={() => setAdding(true)}>
            Добавить проверку
          </button>
        )}
      </div>
      {adding && (
        <CheckForm
          onCancel={() => setAdding(false)}
          onSubmit={(input) =>
            api.create(blockId, input).then(() => {
              setAdding(false);
              reload();
            })
          }
        />
      )}
      {failed && !checks && <p className="inspector__empty">Не удалось загрузить проверки</p>}
      {!failed && !checks && <p className="inspector__empty">Загружаем проверки…</p>}
      {checks && checks.length === 0 && !adding && (
        <p className="inspector__empty">Проверок нет: статус блока неизвестен</p>
      )}
      {checks && checks.length > 0 && (
        <ul className="check-list">
          {checks.map((check) => (
            <CheckItem key={check.id} check={check} now={now} api={api} onChanged={reload} />
          ))}
        </ul>
      )}
    </section>
  );
}
