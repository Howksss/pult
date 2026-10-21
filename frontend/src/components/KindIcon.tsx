import type { BlockKind } from "../api";
import { Icon, type IconName } from "./Icon";

const ICONS: Record<BlockKind, IconName> = {
  server: "server",
  scheduled_job: "schedule",
  bot: "bot",
  integration: "integration",
  config: "config",
  storage: "storage",
};

interface KindIconProps {
  kind: BlockKind;
  size?: "sm" | "md";
}

export function KindIcon({ kind, size = "md" }: KindIconProps) {
  return (
    <span className={`kind-icon kind-icon--${kind} kind-icon--${size}`} aria-hidden="true">
      <Icon name={ICONS[kind]} size={size === "md" ? 20 : 15} />
    </span>
  );
}
