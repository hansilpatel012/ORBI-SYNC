'use client'

import { motion } from 'framer-motion'
import { formatNumber, formatUtc } from '@/lib/format'
import { RISK_LEVELS, getRiskLevel } from '@/lib/object-types'
import { SimulatedBadge } from './simulated-badge'

const reveal = {
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: '-80px' },
  transition: { duration: 0.8, ease: [0.22, 1, 0.36, 1] },
}

const STATUS_STYLES = {
  online: { label: 'Online', dot: 'bg-safe', text: 'text-safe' },
  nominal: { label: 'Nominal', dot: 'bg-safe', text: 'text-safe' },
  standby: { label: 'Standby', dot: 'bg-warning', text: 'text-warning' },
  degraded: { label: 'Degraded', dot: 'bg-warning', text: 'text-warning' },
  offline: { label: 'Offline', dot: 'bg-critical', text: 'text-critical' },
}

const SEVERITY_DOT = {
  info: 'bg-signal',
  monitor: 'bg-signal',
  low: 'bg-signal',
  warning: 'bg-warning',
  medium: 'bg-warning',
  high: 'bg-warning',
  critical: 'bg-critical',
}

export function SituationOverview({ status, conjunctions, objectsById, epochMs }) {
  const rawEvents = [
    ...status.events.map((e) => ({ ...e, timeMs: epochMs + e.offsetMinutes * 60_000 })),
    ...conjunctions.map((c) => {
      const riskObj = getRiskLevel(c.risk)
      const severity =
        c.risk === 'monitor' || c.risk === 'low'
          ? 'info'
          : c.risk === 'critical' || c.risk === 'high' || riskObj.severity === 'critical'
            ? 'critical'
            : 'warning'
      const nameA = c.satellite1Name
        ? `${c.satellite1Name} (${c.objectA})`
        : (objectsById[c.objectA]?.name || c.objectA)
      const nameB = c.satellite2Name
        ? `${c.satellite2Name} (${c.objectB})`
        : (objectsById[c.objectB]?.name || c.objectB)
      return {
        id: `evt-${c.id}`,
        timeMs: epochMs,
        severity,
        title: `${riskObj.label || 'Approach'} close approach detected`,
        detail: `${nameA} × ${nameB} · miss ${formatNumber(c.missDistanceKm, 3)} km`,
      }
    }),
  ]

  const seenEventKeys = new Set()
  const events = rawEvents
    .filter((e) => {
      if (!e || !e.id || seenEventKeys.has(e.id)) return false
      seenEventKeys.add(e.id)
      return true
    })
    .sort((a, b) => b.timeMs - a.timeMs)

  const reliability = status.dataReliability

  return (
    <section id="overview" aria-labelledby="overview-heading" className="relative border-t border-border px-5 py-24 sm:px-8 lg:px-10">
      <motion.div {...reveal} className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-signal">Situation overview</p>
          <h2 id="overview-heading" className="mt-4 text-balance text-3xl font-medium tracking-tight sm:text-5xl">
            One shared picture of every object and every approach.
          </h2>
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          <SimulatedBadge label="Simulated scenario values" />
          {status.datasetFreshness && (
            <div className="inline-flex items-center gap-2 rounded-full border border-signal/30 bg-signal/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-signal">
              <span className="size-1.5 rounded-full bg-signal animate-pulse" aria-hidden="true" />
              <span>
                Dataset: {status.datasetFreshness.status || 'Fresh'} · {status.datasetFreshness.totalSatellites || 200} Sats (SGP4 GCRS)
              </span>
            </div>
          )}
        </div>
      </motion.div>

      <div className="mt-16 grid gap-14 lg:grid-cols-[1.3fr_1fr_1fr] lg:gap-12">
        <motion.div {...reveal}>
          <h3 className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Recent events</h3>
          <ol className="mt-5 border-l border-border">
            {events.map((event) => (
              <li key={event.id} className="relative pb-6 pl-6 last:pb-0">
                <span
                  className={`absolute -left-[4.5px] top-1.5 size-2 rounded-full ring-4 ring-space ${SEVERITY_DOT[event.severity] || 'bg-signal'}`}
                  aria-hidden="true"
                />
                <p className="font-mono text-[11px] tabular-nums text-muted-foreground">
                  {formatUtc(event.timeMs, { withDate: false })} UTC
                </p>
                <p className="mt-1 text-sm text-foreground">{event.title}</p>
                <p className="mt-0.5 text-sm text-muted-foreground">{event.detail}</p>
              </li>
            ))}
          </ol>
        </motion.div>

        <motion.div {...reveal} transition={{ ...reveal.transition, delay: 0.1 }}>
          <h3 className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Communication status</h3>
          <ul className="mt-5 divide-y divide-border border-y border-border">
            {status.communication.links.map((link) => {
              const s = STATUS_STYLES[link.status]
              return (
                <li key={link.id} className="flex items-center justify-between gap-4 py-3.5">
                  <span className="text-sm text-foreground">{link.name}</span>
                  <span className={`flex shrink-0 items-center gap-2 font-mono text-[11px] uppercase tracking-[0.14em] ${s.text}`}>
                    <span className={`size-1.5 rounded-full ${s.dot}`} aria-hidden="true" />
                    {s.label}
                  </span>
                </li>
              )
            })}
          </ul>
        </motion.div>

        <motion.div {...reveal} transition={{ ...reveal.transition, delay: 0.2 }}>
          <h3 className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Data reliability</h3>
          <p className="mt-5 font-mono text-6xl font-light tabular-nums tracking-tight">
            {reliability.scorePercent}
            <span className="text-2xl text-muted-foreground">%</span>
          </p>
          <div className="mt-4 h-1 w-full overflow-hidden rounded-full bg-border">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-electric to-signal"
              initial={{ width: 0 }}
              whileInView={{ width: `${reliability.scorePercent}%` }}
              viewport={{ once: true }}
              transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1], delay: 0.3 }}
            />
          </div>
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{reliability.basis}</p>
          <ul className="mt-6 divide-y divide-border border-y border-border">
            {reliability.sources.map((source) => {
              const s = STATUS_STYLES[source.status]
              return (
                <li key={source.name} className="flex items-center justify-between gap-4 py-3">
                  <span className="text-sm text-foreground">{source.name}</span>
                  <span className={`font-mono text-[11px] uppercase tracking-[0.14em] ${s.text}`}>{s.label}</span>
                </li>
              )
            })}
          </ul>
          {status.datasetFreshness && (
            <div className="mt-4 rounded-md border border-border/70 bg-navy/40 p-3 font-mono text-[11px] text-muted-foreground space-y-1.5">
              <div className="flex items-center justify-between text-foreground">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-signal">Orbital Ephemeris Freshness</span>
                <span className="rounded bg-signal/15 px-1.5 py-0.5 text-[9px] font-medium uppercase text-signal">
                  {status.datasetFreshness.status || 'Active'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Screening Epoch</span>
                <span className="tabular-nums text-foreground/80">
                  {status.datasetFreshness.conjunctionEpoch ? status.datasetFreshness.conjunctionEpoch.slice(0, 19).replace('T', ' ') : '2026-11-21 17:15:38'} UTC
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Propagator & Frame</span>
                <span className="text-foreground/80">SGP4 · GCRS ({status.datasetFreshness.totalSatellites || 200} Satellites)</span>
              </div>
              {status.datasetFreshness.tleSha256 && (
                <div className="flex items-center justify-between">
                  <span>TLE Integrity</span>
                  <span className="font-mono text-[10px] text-foreground/60">
                    SHA-256: {status.datasetFreshness.tleSha256.slice(0, 12)}...
                  </span>
                </div>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </section>
  )
}
