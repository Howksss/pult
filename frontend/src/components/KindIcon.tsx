import {
  Bot,
  Clock,
  Database,
  Plug,
  Server,
  SlidersHorizontal,
  type LucideIcon,
} from "lucide-react";
import type { BlockKind } from "../api";

const ICONS: Record<BlockKind, LucideIcon> = {
  server: Server,
  scheduled_job: Clock,
  bot: Bot,
  integration: Plug,
  config: SlidersHorizontal,
  storage: Database,
};

interface KindIconProps {
  kind: BlockKind;
  size?: "sm" | "md";
}

export function KindIcon({ kind, size = "md" }: KindIconProps) {
  const Icon = ICONS[kind];
  return (
    <span className={`kind-icon kind-icon--${kind} kind-icon--${size}`} aria-hidden="true">
      <Icon size={size === "md" ? 18 : 14} strokeWidth={1.8} />
    </span>
  );
}
