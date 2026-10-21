import {
  applyNodeChanges,
  Background,
  BackgroundVariant,
  ControlButton,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type NodeChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";
import { fetchGraph, moveBlock, type Graph } from "./api";
import { BlockNode } from "./components/BlockNode";
import { FlowEdge } from "./components/FlowEdge";
import { Icon } from "./components/Icon";
import { Inspector } from "./components/Inspector";
import { TopBar } from "./components/TopBar";
import {
  countByStatus,
  mergeNodes,
  neighbourhood,
  summarize,
  toEdges,
  toNodes,
  type BlockNode as BlockNodeType,
} from "./graph";
import { STATUS_COLORS } from "./status";
import { useTheme } from "./theme";

const PROJECT_ID = Number(new URLSearchParams(window.location.search).get("project") ?? "1");
const REFRESH_MS = 10_000;
const INSPECTOR_WIDTH = 356;
const nodeTypes = { block: BlockNode };
const edgeTypes = { flow: FlowEdge };

function minimapColor(node: BlockNodeType): string {
  return STATUS_COLORS[node.data.block.status];
}

function Board() {
  const [theme, toggleTheme] = useTheme();
  const [graph, setGraph] = useState<Graph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [nodes, setNodes] = useState<BlockNodeType[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { fitView, flowToScreenPosition, getNode, getZoom, setCenter, zoomIn, zoomOut } =
    useReactFlow<BlockNodeType>();

  useEffect(() => {
    const controller = new AbortController();
    const load = () =>
      fetchGraph(PROJECT_ID, controller.signal)
        .then((data) => {
          setGraph(data);
          setNodes((current) => mergeNodes(current, toNodes(data)));
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

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedId(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!notice) {
      return;
    }
    const timer = window.setTimeout(() => setNotice(null), 4000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const onNodesChange = useCallback(
    (changes: NodeChange<BlockNodeType>[]) =>
      setNodes((current) => applyNodeChanges(changes, current)),
    [],
  );

  const onNodeDragStop = useCallback((_: unknown, node: BlockNodeType) => {
    moveBlock(Number(node.id), node.position.x, node.position.y).catch(() =>
      setNotice("Не удалось сохранить положение блока"),
    );
  }, []);

  const focus = useCallback(
    (blockId: number, always: boolean) => {
      setSelectedId(blockId);
      const node = getNode(String(blockId));
      if (!node) {
        return;
      }
      const width = node.measured?.width ?? 0;
      const height = node.measured?.height ?? 0;
      const corner = flowToScreenPosition({ x: node.position.x + width, y: node.position.y });
      if (!always && corner.x < window.innerWidth - INSPECTOR_WIDTH - 24) {
        return;
      }
      const zoom = getZoom();
      void setCenter(
        node.position.x + width / 2 + INSPECTOR_WIDTH / 2 / zoom,
        node.position.y + height / 2,
        { zoom, duration: 450 },
      );
    },
    [flowToScreenPosition, getNode, getZoom, setCenter],
  );

  const near = useMemo(
    () => (graph ? neighbourhood(graph, selectedId) : null),
    [graph, selectedId],
  );
  const shownNodes = useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        selected: Number(node.id) === selectedId,
        className: near && !near.has(Number(node.id)) ? "is-dimmed" : undefined,
      })),
    [nodes, near, selectedId],
  );
  const edges = useMemo(() => (graph ? toEdges(graph, selectedId) : []), [graph, selectedId]);
  const counts = graph ? countByStatus(graph) : null;
  const summary = graph ? summarize(graph) : null;
  const selected = graph?.blocks.find((block) => block.id === selectedId) ?? null;
  const toast = notice ?? (error ? `Не удалось обновить граф: ${error}` : null);

  return (
    <div className="layout">
      <TopBar
        projectId={PROJECT_ID}
        counts={counts}
        summary={summary}
        updatedAt={graph?.generated_at ?? null}
        stale={error !== null}
        theme={theme}
        onToggleTheme={toggleTheme}
        onShowBlock={(blockId) => focus(blockId, true)}
      />
      <main className={selected ? "canvas canvas--inspecting" : "canvas"}>
        {graph ? (
          <ReactFlow
            nodes={shownNodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            colorMode={theme}
            onNodesChange={onNodesChange}
            onNodeDragStop={onNodeDragStop}
            onNodeClick={(_, node) => focus(Number(node.id), false)}
            onPaneClick={() => setSelectedId(null)}
            nodesConnectable={false}
            deleteKeyCode={null}
            fitView
            fitViewOptions={{ padding: 0.18 }}
            minZoom={0.3}
            maxZoom={1.8}
          >
            <Background variant={BackgroundVariant.Dots} gap={22} size={1.4} />
            <Controls showZoom={false} showFitView={false} showInteractive={false}>
              <ControlButton
                onClick={() => zoomIn({ duration: 200 })}
                title="Приблизить"
                aria-label="Приблизить"
              >
                <Icon name="zoomIn" size={16} />
              </ControlButton>
              <ControlButton
                onClick={() => zoomOut({ duration: 200 })}
                title="Отдалить"
                aria-label="Отдалить"
              >
                <Icon name="zoomOut" size={16} />
              </ControlButton>
              <ControlButton
                onClick={() => fitView({ padding: 0.18, duration: 300 })}
                title="Показать всё"
                aria-label="Показать всё"
              >
                <Icon name="fit" size={15} />
              </ControlButton>
            </Controls>
            <MiniMap
              nodeColor={minimapColor}
              nodeBorderRadius={6}
              nodeStrokeWidth={0}
              pannable
              zoomable
            />
          </ReactFlow>
        ) : (
          <div className="canvas__state">
            {error ? (
              "Граф недоступен"
            ) : (
              <>
                <Icon name="loader" className="spin" size={18} />
                Загружаем граф…
              </>
            )}
          </div>
        )}
        {graph && graph.blocks.length === 0 && (
          <div className="canvas__state">В проекте пока нет блоков</div>
        )}
        {toast && (
          <div className="toast" role="status">
            {toast}
          </div>
        )}
        {graph && selected && (
          <Inspector
            graph={graph}
            block={selected}
            onSelect={(blockId) => focus(blockId, true)}
            onClose={() => setSelectedId(null)}
          />
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ReactFlowProvider>
      <Board />
    </ReactFlowProvider>
  );
}
