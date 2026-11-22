import { OrbiMark } from './site-header'

export function SiteFooter({ meta }) {
  return (
    <footer className="border-t border-border px-5 py-12 sm:px-8 lg:px-10">
      <div className="flex flex-col gap-8 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-center gap-3">
          <OrbiMark className="size-8" />
          <div>
            <p className="text-sm font-semibold tracking-[0.22em]">ORBI SYNC</p>
            <p className="text-sm text-muted-foreground">Synchronising Intelligence. Securing Orbits.</p>
          </div>
        </div>
        <div className="max-w-xl text-sm leading-relaxed text-muted-foreground">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-warning">Data notice</p>
          <p className="mt-2">
            {meta.notes} Orbits use a {meta.model.toLowerCase()} model. This is not real-time tracking, and collision
            probabilities are not shown because the dataset contains no uncertainty information.
          </p>
        </div>
      </div>
    </footer>
  )
}
