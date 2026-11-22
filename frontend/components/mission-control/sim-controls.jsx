'use client'

import { motion } from 'framer-motion'
import { Pause, Play, RotateCw, Scan, SkipBack } from 'lucide-react'
import { formatUtc } from '@/lib/format'

const SPEEDS = [1, 10, 60, 300]

export function SimControls({
  playing,
  multiplier,
  autoRotate,
  onTogglePlay,
  onMultiplier,
  onToggleAutoRotate,
  onResetView,
  onRestart,
  simTimeMs,
  epochMs,
  windowSeconds,
}) {
  const progress = Math.min(1, Math.max(0, (simTimeMs - epochMs) / (windowSeconds * 1000)))

  return (
    <motion.section
      aria-label="Simulation clock"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 1, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      className="rounded-lg border border-border bg-space/60 p-4 backdrop-blur-xl"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Simulation clock</p>
          <p className="mt-1 font-mono text-sm tabular-nums text-foreground">{formatUtc(simTimeMs)} UTC</p>
        </div>
        <div className="flex items-center gap-1">
          <IconButton label="Restart scenario" onClick={onRestart}>
            <SkipBack className="size-4" />
          </IconButton>
          <IconButton label={playing ? 'Pause simulation' : 'Play simulation'} onClick={onTogglePlay} emphasis>
            {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
          </IconButton>
        </div>
      </div>

      <div
        className="mt-3 h-px w-full bg-border"
        role="progressbar"
        aria-label="Position in 24-hour scenario window"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(progress * 100)}
      >
        <div className="h-px bg-signal" style={{ width: `${progress * 100}%` }} />
      </div>

      <div className="mt-3 flex items-center justify-between gap-3">
        <div className="flex rounded-md border border-border p-0.5" role="group" aria-label="Simulation speed">
          {SPEEDS.map((speed) => (
            <button
              key={speed}
              type="button"
              aria-pressed={multiplier === speed}
              onClick={() => onMultiplier(speed)}
              className={`rounded px-2.5 py-1 font-mono text-[11px] tabular-nums transition-colors ${
                multiplier === speed ? 'bg-foreground text-space' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {speed}×
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          <IconButton label={autoRotate ? 'Disable auto-rotate' : 'Enable auto-rotate'} onClick={onToggleAutoRotate} active={autoRotate}>
            <RotateCw className="size-4" />
          </IconButton>
          <IconButton label="Reset camera view" onClick={onResetView}>
            <Scan className="size-4" />
          </IconButton>
        </div>
      </div>
    </motion.section>
  )
}

function IconButton({ label, onClick, children, emphasis = false, active = false }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      aria-pressed={active || undefined}
      className={`icon-pop flex size-8 items-center justify-center rounded-md border transition-colors ${
        emphasis
          ? 'border-signal/40 bg-signal/10 text-signal hover:bg-signal/20'
          : active
            ? 'border-foreground/20 bg-foreground/5 text-foreground'
            : 'border-border text-muted-foreground hover:text-foreground'
      }`}
    >
      {children}
    </button>
  )
}
