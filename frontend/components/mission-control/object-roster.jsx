'use client'

import { AnimatePresence, motion } from 'framer-motion'
import { Hexagon, Locate, LocateFixed, Rocket, Satellite, TriangleAlert, X } from 'lucide-react'
import { OBJECT_TYPES, RISK_LEVELS, getRiskLevel } from '@/lib/object-types'
import { circularVelocityKmS, orbitalPeriodSeconds, subSatellitePoint } from '@/lib/orbits'
import { formatCoordinate, formatNumber } from '@/lib/format'

const TYPE_ICONS = { active: Satellite, debris: Hexagon, 'rocket-body': Rocket }

export function ObjectRoster({
  objects,
  conjunctions,
  selectedId,
  onSelect,
  visibleTypes,
  onToggleType,
  simTimeMs,
  epochMs,
  followId,
  onToggleFollow,
}) {
  const riskFor = (id) => conjunctions.find((c) => c.objectA === id || c.objectB === id)?.risk

  return (
    <motion.section
      aria-labelledby="roster-heading"
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.6, duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
      className="rounded-lg border border-border bg-space/60 backdrop-blur-xl"
    >
      <header className="flex items-baseline justify-between border-b border-border px-4 py-3.5">
        <h2 id="roster-heading" className="font-mono text-[11px] uppercase tracking-[0.22em]">
          Orbital objects
        </h2>
        <span className="font-mono text-xs tabular-nums text-muted-foreground">
          {String(objects.filter((o) => visibleTypes.includes(o.type)).length).padStart(2, '0')} /{' '}
          {String(objects.length).padStart(2, '0')}
        </span>
      </header>

      <div className="flex flex-wrap gap-1.5 border-b border-border px-4 py-3" role="group" aria-label="Filter by object type">
        {Object.entries(OBJECT_TYPES).map(([type, style]) => {
          const active = visibleTypes.includes(type)
          const count = objects.filter((o) => o.type === type).length
          return (
            <button
              key={type}
              type="button"
              aria-pressed={active}
              onClick={() => onToggleType(type)}
              className={`flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
                active ? 'border-foreground/20 bg-foreground/5 text-foreground' : 'border-border text-muted-foreground/60'
              }`}
            >
              <span className={`size-1.5 rounded-full ${style.bgClass} ${active ? '' : 'opacity-30'}`} aria-hidden="true" />
              {style.shortLabel}
              <span className="font-mono tabular-nums text-muted-foreground">{count}</span>
            </button>
          )
        })}
      </div>

      <ul className="flex flex-col max-h-[420px] overflow-y-auto">
        {objects.map((obj) => {
          const style = OBJECT_TYPES[obj.type]
          const Icon = TYPE_ICONS[obj.type]
          const visible = visibleTypes.includes(obj.type)
          const selected = obj.id === selectedId
          const risk = riskFor(obj.id)
          return (
            <li key={obj.id} className={`border-b border-border last:border-b-0 ${visible ? '' : 'opacity-35'}`}>
              <button
                type="button"
                disabled={!visible}
                onClick={() => onSelect(selected ? null : obj.id)}
                aria-expanded={selected}
                className={`group flex w-full items-center gap-3 px-4 py-3 text-left transition-colors disabled:cursor-not-allowed ${
                  selected ? 'bg-navy/80' : 'hover:bg-foreground/[0.03]'
                }`}
              >
                <span
                  className={`icon-pop flex size-8 shrink-0 items-center justify-center rounded-md border border-border bg-space ${style.textClass} ${
                    selected ? 'icon-pop-on' : ''
                  }`}
                >
                  <Icon className="size-4" aria-hidden="true" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-mono text-sm text-foreground">{obj.name}</span>
                  <span className="block text-xs text-muted-foreground">{style.label}</span>
                </span>
                {risk && (() => {
                  const riskObj = getRiskLevel(risk)
                  return (
                    <TriangleAlert
                      className={`size-3.5 shrink-0 ${riskObj.textClass || 'text-warning'}`}
                      aria-label={`${riskObj.label || 'Warning'} close approach`}
                    />
                  )
                })()}
                <span className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                  {formatNumber(obj.orbit?.altitudeKm || 550)} km
                </span>
              </button>

              <AnimatePresence initial={false}>
                {selected && (
                  <motion.div
                    key="details"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                    className="overflow-hidden"
                  >
                    <ObjectDetails
                      object={obj}
                      simTimeMs={simTimeMs}
                      epochMs={epochMs}
                      following={followId === obj.id}
                      onToggleFollow={() => onToggleFollow(obj.id)}
                      onClose={() => onSelect(null)}
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </li>
          )
        })}
      </ul>
    </motion.section>
  )
}

function ObjectDetails({ object, simTimeMs, epochMs, following, onToggleFollow, onClose }) {
  const orbit = object.orbit || { altitudeKm: 550, inclinationDeg: 53, raanDeg: 0, argumentOfLatitudeDeg: 0 }
  const seconds = (simTimeMs - epochMs) / 1000
  const point = subSatellitePoint(orbit, seconds, new Date(simTimeMs))
  const rows = [
    ['Altitude', `${formatNumber(orbit.altitudeKm, 1)} km`],
    ['Velocity', `${formatNumber(circularVelocityKmS(orbit), 2)} km/s`],
    ['Period', `${formatNumber(orbitalPeriodSeconds(orbit) / 60, 1)} min`],
    ['Inclination', `${formatNumber(orbit.inclinationDeg, 1)}°`],
    ['RAAN', `${formatNumber(orbit.raanDeg, 1)}°`],
    ['Latitude', formatCoordinate(point.latDeg, 'N', 'S')],
    ['Longitude', formatCoordinate(point.lonDeg, 'E', 'W')],
    ['Manoeuvrable', object.manoeuvrable ? 'Yes' : 'No'],
  ]

  return (
    <div className="bg-navy/80 px-4 pb-4">
      <p className="text-xs leading-relaxed text-muted-foreground">
        {object.role} · {object.operator}
      </p>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5 border-t border-border pt-3">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">{label}</dt>
            <dd className="font-mono text-xs tabular-nums text-foreground">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-4 flex items-center gap-2">
        <button
          type="button"
          onClick={onToggleFollow}
          aria-pressed={following}
          className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs transition-colors ${
            following ? 'border-signal/50 bg-signal/10 text-signal' : 'border-border text-foreground hover:border-foreground/25'
          }`}
        >
          {following ? <LocateFixed className="size-3.5" aria-hidden="true" /> : <Locate className="size-3.5" aria-hidden="true" />}
          {following ? 'Following' : 'Follow camera'}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          <X className="size-3.5" aria-hidden="true" />
          Close
        </button>
      </div>
      <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground/70">
        Values from simulated circular-orbit model
      </p>
    </div>
  )
}
