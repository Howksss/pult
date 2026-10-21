import { Handle, Position, type NodeProps } from "@xyflow/react";
import { KIND_LABELS, type BlockNode as BlockNodeType } from "../graph";
import { StatusBadge } from "./StatusBadge";

export function BlockNode({ data, selected }: NodeProps<BlockNodeType>) {
  const { block } = data;
  const classes = ["block-node", `block-node--${block.status}`];
  if (selected) {
    classes.push("block-node--selected");
  }
  return (
    <div className={classes.join(" ")}>
      <Handle type="target" position={Position.Left} />
      <div className="block-node__kind">{KIND_LABELS[block.kind]}</div>
      <div className="block-node__name">{block.name}</div>
      <StatusBadge status={block.status} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
