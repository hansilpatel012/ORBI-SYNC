'use client'

import { motion } from 'framer-motion'

const STAGES = [
  { n: '01', title: 'Mission Control', body: 'Shared 3D picture of monitored objects, alerts and system health.', live: true },
  { n: '02', title: 'Orbital Network', body: 'Deep inspection of every object, its orbit and its relationships.' },
  { n: '03', title: 'Conjunction Alerts', body: 'Ranked close approaches with time and distance of closest approach.' },
  { n: '04', title: 'Manoeuvre Planner', body: 'Avoidance options compared by delta-v, fuel and residual risk.' },
  { n: '05', title: 'Before & After', body: 'Animated comparison of original and modified trajectories.' },
]

export function PipelineSection() {
  return (
    <section id="pipeline" aria-labelledby="pipeline-heading" className="border-t border-border px-5 py-24 sm:px-8 lg:px-10">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-80px' }}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="max-w-2xl"
      >
        <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-signal">Coordination pipeline</p>
        <h2 id="pipeline-heading" className="mt-4 text-balance text-3xl font-medium tracking-tight sm:text-5xl">
          From detection to a coordinated decision.
        </h2>
      </motion.div>

      <ol className="mt-16 grid border-t border-border sm:grid-cols-2 lg:grid-cols-5">
        {STAGES.map((stage, i) => (
          <motion.li
            key={stage.n}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.7, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] }}
            className="border-b border-border py-8 pr-6 lg:border-b-0 lg:border-r lg:pl-6 lg:first:pl-0 lg:last:border-r-0"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs text-muted-foreground">{stage.n}</span>
              <span
                className={`font-mono text-[10px] uppercase tracking-[0.16em] ${stage.live ? 'text-safe' : 'text-muted-foreground/70'}`}
              >
                {stage.live ? 'Live in this build' : 'Next stage'}
              </span>
            </div>
            <h3 className="mt-6 text-lg font-medium text-foreground">{stage.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{stage.body}</p>
          </motion.li>
        ))}
      </ol>
    </section>
  )
}
