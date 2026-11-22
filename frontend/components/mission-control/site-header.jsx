import { formatUtc } from '@/lib/format'
import { SimulatedBadge } from './simulated-badge'

const NAV = [
  { href: '#mission-control', label: 'Mission Control' },
  { href: '#overview', label: 'Situation' },
  { href: '#pipeline', label: 'Pipeline' },
]

export function OrbiMark({ className = 'size-7' }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true" fill="none">
      <circle cx="16" cy="16" r="6" className="fill-signal/15 stroke-signal" strokeWidth="1.5" />
      <ellipse cx="16" cy="16" rx="14" ry="5.5" transform="rotate(-28 16 16)" className="stroke-foreground/70" strokeWidth="1.2" />
      <circle cx="27.6" cy="9.8" r="1.9" className="fill-signal" />
    </svg>
  )
}

export function SiteHeader({ simTimeMs, datasetFreshness }) {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-border/60 bg-space/55 backdrop-blur-xl">
      <div className="flex h-14 items-center justify-between gap-6 px-5 sm:px-8 lg:px-10">
        <a href="#mission-control" className="flex items-center gap-2.5" aria-label="ORBI SYNC home">
          <OrbiMark />
          <span className="text-sm font-semibold tracking-[0.22em]">ORBI SYNC</span>
        </a>

        <nav aria-label="Primary" className="hidden md:block">
          <ul className="flex items-center gap-8">
            {NAV.map((item, index) => (
              <li key={item.href}>
                <a
                  href={item.href}
                  className={`text-xs uppercase tracking-[0.18em] transition-colors hover:text-foreground ${
                    index === 0 ? 'text-foreground' : 'text-muted-foreground'
                  }`}
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="flex items-center gap-4">
          {datasetFreshness && (
            <span className="hidden xl:inline-flex items-center gap-1.5 rounded-full border border-signal/30 bg-signal/10 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-signal">
              <span className="size-1.5 rounded-full bg-signal" aria-hidden="true" />
              SGP4 GCRS: {datasetFreshness.status || 'Active'}
            </span>
          )}
          <div className="hidden text-right sm:block">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Scenario time · UTC</p>
            <p className="font-mono text-xs tabular-nums text-foreground">{formatUtc(simTimeMs)}</p>
          </div>
          <SimulatedBadge />
        </div>
      </div>
    </header>
  )
}
