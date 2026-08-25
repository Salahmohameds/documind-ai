import { Shimmer } from "@/components/motion"
import { cn } from "@/lib/utils"

/**
 * shadcn's Skeleton, rewired to the product's own shimmer so a shadcn
 * placeholder and a hand-placed one look identical.
 */
function Skeleton({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return <Shimmer data-slot="skeleton" className={cn("rounded-md", className)} style={style} />
}

export { Skeleton }
