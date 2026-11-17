import type { Block, ChecksApi, Graph, ScopesApi } from "../api";
import { connections, KIND_LABELS, type Connection } from "../graph";
import { STATUS_PRESENTATION } from "../status";
import { ChecksPanel } from "./Checks";
import { Icon } from "./Icon";
import { KindIcon } from "./KindIcon";
import { ScopesPanel } from "./Scopes";
import { StatusBadge, StatusDot } from "./StatusBadge";

interface ConnectionListProps {
  title: string;
  items: Connection[];
  direction: "in" | "out";
  onSelect: (blockId: number) => void;
}

function ConnectionList({ title, items, direction, onSelect }: ConnectionListProps) {
  return (
    <section className="inspector__section">
      <h3 className="inspector__heading">
        {title}
        <span className="inspector__heading-count">{items.length}</span>
      </h3>
      {items.length === 0 ? (
        <p className="inspector__empty">Связей нет</p>
      ) : (
        <ul className="connection-list">
          {items.map(({ link, block }) => (
            <li key={link.id}>
              <button
                type="button"
                className="connection"
                onClick={() => onSelect(block.id)}
                title={`${block.name}: ${STATUS_PRESENTATION[block.status].label}`}
              >
                <KindIcon kind={block.kind} size="sm" />
                <span className="connection__text">
                  <span className="connection__name">{block.name}</span>
                  {link.label && <span className="connection__label">{link.label}</span>}
                </span>
                <StatusDot status={block.status} />
                <Icon
                  name={direction === "in" ? "arrowLeft" : "arrowRight"}
                  className="connection__arrow"
                  size={15}
                />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

interface InspectorProps {
  graph: Graph;
  block: Block;
  onSelect: (blockId: number) => void;
  onClose: () => void;
  checksApi?: ChecksApi;
  scopesApi?: ScopesApi;
}

export function Inspector({
  graph,
  block,
  onSelect,
  onClose,
  checksApi,
  scopesApi,
}: InspectorProps) {
  const { incoming, outgoing } = connections(graph, block.id);
  return (
    <aside className="inspector" aria-label={`Блок ${block.name}`}>
      <header className="inspector__head">
        <span className="inspector__kind">
          <KindIcon kind={block.kind} />
          {KIND_LABELS[block.kind]}
        </span>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Закрыть">
          <Icon name="close" size={18} />
        </button>
      </header>
      <section className="inspector__summary">
        <h2 className="inspector__name">{block.name}</h2>
        <StatusBadge status={block.status} />
        <p className="inspector__description">{block.description ?? "Без описания"}</p>
      </section>
      <ChecksPanel blockId={block.id} refreshKey={graph.generated_at} api={checksApi} />
      <ConnectionList title="Входящие" items={incoming} direction="in" onSelect={onSelect} />
      <ConnectionList title="Исходящие" items={outgoing} direction="out" onSelect={onSelect} />
      <ScopesPanel blockId={block.id} api={scopesApi} />
      <section className="inspector__agent">
        <h3 className="inspector__heading">Задача агенту</h3>
        <textarea
          className="inspector__prompt"
          placeholder={`Что поправить в блоке «${block.name}»?`}
          rows={3}
          disabled
        />
        <div className="inspector__agent-foot">
          <span className="inspector__scope">
            <Icon name="lock" size={14} />
            Только пути из области агента
          </span>
          <button type="button" className="glass-button" disabled>
            Отправить
          </button>
        </div>
        <p className="inspector__hint">Чат с агентом появится в версии 0.3.0</p>
      </section>
    </aside>
  );
}
