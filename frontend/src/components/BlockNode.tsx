import { Handle, Position, type NodeProps } from "@xyflow/react";
import { checksCount } from "../checks";
import { KIND_LABELS, type BlockNode as BlockNodeType } from "../graph";
import { KindIcon } from "./KindIcon";
import { StatusBadge } from "./StatusBadge";

export function BlockNode({ data, selected }: NodeProps<BlockNodeType>) {
  const { block } = data;
  const problem = block.status !== "ok" && block.reason;
  const count =
    block.checks_total > 1 ? checksCount(block.checks_problem, block.checks_total) : null;
  const classes = ["block-node", `block-node--${block.status}`];
  if (selected) {
    classes.push("block-node--selected");
  }
  return (
    <div className={classes.join(" ")}>
      <Handle type="target" position={Position.Left} className="block-node__handle" />
      <div className="block-node__head">
        <KindIcon kind={block.kind} />
        <span className="block-node__kind">{KIND_LABELS[block.kind]}</span>
      </div>
      <div className="block-node__name">{block.name}</div>
      {problem ? (
        <div className="block-node__reason">{block.reason}</div>
      ) : (
        block.description && <div className="block-node__description">{block.description}</div>
      )}
      <div className="block-node__foot">
        <StatusBadge status={block.status} />
        {count && (
          <span className="block-node__count" title={count.full}>
            {count.short}
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="block-node__handle" />
    </div>
  );
}
