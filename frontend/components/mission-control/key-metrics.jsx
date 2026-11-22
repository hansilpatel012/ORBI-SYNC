'use client'

import { motion } from 'framer-motion'

export function KeyMetrics({ metrics }) {
  const items = [
    { label: 'Monitored objects', value: metrics.monitored, tone: 'text-foreground' },
    {
      label: 'Active connections',
      value: metrics.activeConnections,
      suffix: `/${metrics.totalConnections}`,
      tone: 'text-foreground',
    },
    { label: 'Close approaches', value: metrics.closeApproaches, tone: 'text-warning' },
    { label: 'Critical warnings', value: metrics.critical, tone: 'text-critical', pulse: metrics.critical > 0 },
  ]

  return (
    <motion.dl
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.75, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      className="grid grid-cols-2 gap-y-6 border-t border-border pt-6 sm:grid-cols-4 sm:divide-x sm:divide-border"
    >
      {items.map((item) => (
        <div key={item.label} className="flex flex-col gap-2 sm:px-5 sm:first:pl-0">
          <dt className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            {item.pulse && (
              <span className="relative flex size-1.5" aria-hidden="true">
                <span className="absolute inset-0 animate-ping rounded-full bg-critical" />
                <span className="relative size-1.5 rounded-full bg-critical" />
              </span>
            )}
            {item.label}
          </dt>
          <dd className={`font-mono text-4xl font-light tabular-nums tracking-tight ${item.tone}`}>
            {String(item.value).padStart(2, '0')}
            {item.suffix && <span className="text-lg text-muted-foreground">{item.suffix}</span>}
          </dd>
        </div>
      ))}
    </motion.dl>
  )
}
