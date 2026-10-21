import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from "@xyflow/react";
import type { FlowEdge as FlowEdgeType } from "../graph";

export function FlowEdge({
  id,
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
  data,
}: EdgeProps<FlowEdgeType>) {
  const [path, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });
  const classes = ["flow-edge"];
  if (data?.broken) {
    classes.push("flow-edge--broken");
  }
  if (data?.active) {
    classes.push("flow-edge--active");
  }
  if (data?.dimmed) {
    classes.push("flow-edge--dimmed");
  }
  const className = classes.join(" ");
  const offset = (Number(id) % 7) * 0.4;
  return (
    <g className={className}>
      <BaseEdge id={id} path={path} />
      {!data?.broken && (
        <circle r={data?.active ? 3.5 : 2.5} className="flow-edge__packet">
          <animateMotion dur="2.8s" begin={`-${offset}s`} repeatCount="indefinite" path={path} />
        </circle>
      )}
      {data?.label && (
        <EdgeLabelRenderer>
          <div
            className={`flow-edge__label ${className}`}
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          >
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </g>
  );
}
