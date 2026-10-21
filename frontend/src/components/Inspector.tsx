import type { Block, Graph } from "../api";
import { connections, KIND_LABELS, type Connection } from "../graph";
import { STATUS_PRESENTATION } from "../status";
import { Icon } from "./Icon";
import { KindIcon } from "./KindIcon";
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
                  size={14}
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
}

export function Inspector({ graph, block, onSelect, onClose }: InspectorProps) {
  const { incoming, outgoing } = connections(graph, block.id);
  return (
    <aside className="inspector" aria-label={`Блок ${block.name}`}>
      <header className="inspector__head">
        <KindIcon kind={block.kind} />
        <div className="inspector__title">
          <h2>{block.name}</h2>
          <span>{KIND_LABELS[block.kind]}</span>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Закрыть">
          <Icon name="close" size={18} />
        </button>
      </header>
      <section className="inspector__section">
        <StatusBadge status={block.status} />
        <p className="inspector__description">{block.description ?? "Без описания"}</p>
      </section>
      <ConnectionList title="Входящие" items={incoming} direction="in" onSelect={onSelect} />
      <ConnectionList title="Исходящие" items={outgoing} direction="out" onSelect={onSelect} />
      <section className="inspector__agent">
        <h3 className="inspector__heading">
          <Icon name="agent" size={15} />
          Задача агенту
        </h3>
        <textarea
          className="inspector__prompt"
          placeholder={`Что поправить в блоке «${block.name}»?`}
          rows={3}
          disabled
        />
        <div className="inspector__agent-foot">
          <span className="inspector__scope">
            <Icon name="lock" size={13} />
            Только файлы этого блока
          </span>
          <button type="button" className="button button--primary" disabled>
            <Icon name="send" size={15} />
            Отправить
          </button>
        </div>
        <p className="inspector__hint">Чат с агентом появится в версии 0.3.0</p>
      </section>
    </aside>
  );
}
