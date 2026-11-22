'use client'

import { motion } from 'framer-motion'

const rise = {
  hidden: { opacity: 0, y: 24 },
  show: (i) => ({ opacity: 1, y: 0, transition: { delay: 0.3 + i * 0.12, duration: 0.9, ease: [0.22, 1, 0.36, 1] } }),
}

export function HeroIntro() {
  return (
    <div className="max-w-xl">
      <motion.p
        variants={rise}
        initial="hidden"
        animate="show"
        custom={0}
        className="flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.28em] text-signal"
      >
        <span className="relative flex size-2" aria-hidden="true">
          <span className="absolute inset-0 animate-ping rounded-full bg-signal/60" />
          <span className="relative size-2 rounded-full bg-signal" />
        </span>
        Mission Control · Space traffic coordination
      </motion.p>

      <motion.h1
        variants={rise}
        initial="hidden"
        animate="show"
        custom={1}
        className="mt-6 text-balance text-5xl font-medium leading-[0.95] tracking-tight sm:text-6xl xl:text-7xl"
      >
        Synchronising Intelligence.
        <span className="block text-foreground/45">Securing Orbits.</span>
      </motion.h1>

      <motion.p
        variants={rise}
        initial="hidden"
        animate="show"
        custom={2}
        className="mt-6 max-w-md text-pretty text-base leading-relaxed text-muted-foreground"
      >
        A cooperative satellite intelligence ecosystem that monitors orbital objects, detects dangerous close approaches
        and supports coordinated collision avoidance between operators.
      </motion.p>
    </div>
  )
}
