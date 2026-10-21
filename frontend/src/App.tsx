import { Background, Controls, ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useMemo, useState } from "react";
import "./App.css";
import { fetchGraph, type Graph } from "./api";
import { BlockNode } from "./components/BlockNode";
import { StatusBadge } from "./components/StatusBadge";
import { countByStatus, KIND_LABELS, toFlow } from "./graph";

const PROJECT_ID = Number(new URLSearchParams(window.location.search).get("project") ?? "1");
const REFRESH_MS = 10_000;
const nodeTypes = { block: BlockNode };

export default function App() {
  const [graph, setGraph] = useState<Graph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const load = () =>
      fetchGraph(PROJECT_ID, controller.signal)
        .then((data) => {
          setGraph(data);
          setError(null);
        })
        .catch((reason: unknown) => {
          if (!controller.signal.aborted) {
            setError(String(reason));
          }
        });
    void load();
    const timer = window.setInterval(() => void load(), REFRESH_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, []);

  const flow = useMemo(() => (graph ? toFlow(graph) : { nodes: [], edges: [] }), [graph]);
  const counts = graph ? countByStatus(graph) : null;
  const selected = graph?.blocks.find((block) => String(block.id) === selectedId) ?? null;

  return (
    <div className="layout">
      <header className="topbar">
        <strong>Pult</strong>
        <span className="topbar__muted">Проект {PROJECT_ID}</span>
        {counts && (
          <span className="topbar__counts">
            <StatusBadge status="fail" /> {counts.fail}
            <StatusBadge status="warn" /> {counts.warn}
            <StatusBadge status="unknown" /> {counts.unknown}
            <StatusBadge status="ok" /> {counts.ok}
          </span>
        )}
        {graph && (
          <span className={error ? "topbar__stale" : "topbar__muted"}>
            {error ? "данные устарели, " : ""}обновлено{" "}
            {new Date(graph.generated_at).toLocaleTimeString("ru-RU")}
          </span>
        )}
      </header>
      {error && <div className="error">Не удалось загрузить граф: {error}</div>}
      <main className="canvas">
        <ReactFlow
          nodes={flow.nodes}
          edges={flow.edges}
          nodeTypes={nodeTypes}
          onNodeClick={(_, node) => setSelectedId(node.id)}
          onPaneClick={() => setSelectedId(null)}
          fitView
        >
          <Background />
          <Controls />
        </ReactFlow>
      </main>
      {selected && (
        <aside className="panel">
          <h2>{selected.name}</h2>
          <p className="topbar__muted">{KIND_LABELS[selected.kind]}</p>
          <StatusBadge status={selected.status} />
          <p>{selected.description ?? "Без описания"}</p>
          <button type="button" disabled title="Чат с агентом появится в следующей итерации">
            Поставить задачу агенту
          </button>
        </aside>
      )}
    </div>
  );
}
