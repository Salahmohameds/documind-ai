"use client"

import * as React from "react"
import { Progress as ProgressPrimitive } from "radix-ui"

import { motion } from "@/components/motion"
import { SPRING } from "@/lib/motion"
import { cn } from "@/lib/utils"

const MotionIndicator = motion.create(ProgressPrimitive.Indicator)

/**
 * DocuMind adds `indicatorClassName` / `indicatorStyle` because the canvas
 * colours its bars by tone (ok / warn / bad / a series colour), not by a single
 * primary. The track defaults to `--border`, which is what the canvas uses.
 */
function Progress({
  className,
  value,
  indicatorClassName,
  indicatorStyle,
  ...props
}: React.ComponentProps<typeof ProgressPrimitive.Root> & {
  indicatorClassName?: string
  indicatorStyle?: React.CSSProperties
}) {
  return (
    <ProgressPrimitive.Root
      data-slot="progress"
      className={cn(
        "relative flex h-1 w-full items-center overflow-x-hidden rounded-full bg-[var(--border)]",
        className
      )}
      {...props}
    >
      {/* Motion drives the fill so a value that changes mid-flight retargets
          from wherever the bar currently is, rather than restarting. */}
      <MotionIndicator
        data-slot="progress-indicator"
        className={cn("size-full flex-1 bg-primary", indicatorClassName)}
        style={indicatorStyle}
        initial={false}
        animate={{ x: `-${100 - (value || 0)}%` }}
        transition={SPRING.layout}
      />
    </ProgressPrimitive.Root>
  )
}

export { Progress }
