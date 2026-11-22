// Marks information that comes from the demonstration dataset, not real tracking.
export function SimulatedBadge({ label = 'Simulated data', className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border border-warning/30 bg-warning/10 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-warning ${className}`}
    >
      <span className="size-1.5 rounded-full bg-warning" aria-hidden="true" />
      {label}
    </span>
  )
}
