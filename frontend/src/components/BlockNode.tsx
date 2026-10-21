import { Handle, Position, type NodeProps } from "@xyflow/react";
import { KIND_LABELS, type BlockNode as BlockNodeType } from "../graph";
import { KindIcon } from "./KindIcon";
import { StatusBadge } from "./StatusBadge";

export function BlockNode({ data, selected }: NodeProps<BlockNodeType>) {
  const { block } = data;
  const classes = ["block-node", `block-node--${block.status}`];
  if (selected) {
    classes.push("block-node--selected");
  }
  return (
    <div className={classes.join(" ")}>
      <Handle type="target" position={Position.Left} className="block-node__handle" />
      <div className="block-node__head">
        <KindIcon kind={block.kind} />
        <div className="block-node__title">
          <div className="block-node__name">{block.name}</div>
          <div className="block-node__kind">{KIND_LABELS[block.kind]}</div>
        </div>
      </div>
      {block.description && <div className="block-node__description">{block.description}</div>}
      <div className="block-node__foot">
        <StatusBadge status={block.status} />
      </div>
      <Handle type="source" position={Position.Right} className="block-node__handle" />
    </div>
  );
}
