'use client'

import { useCallback, useMemo, useRef, useState } from 'react'
import { OrbitalGlobe } from '@/components/globe/orbital-globe'
import { SiteHeader } from './site-header'
import { HeroIntro } from './hero-intro'
import { KeyMetrics } from './key-metrics'
import { ConjunctionAlerts } from './conjunction-alerts'
import { ObjectRoster } from './object-roster'
import { SimControls } from './sim-controls'
import { SituationOverview } from './situation-overview'
import { PipelineSection } from './pipeline-section'
import { SiteFooter } from './site-footer'
import { OBJECT_TYPES, normalizeRiskLevel } from '@/lib/object-types'

const ALL_TYPES = Object.keys(OBJECT_TYPES)
const INSPECT_LEAD_SECONDS = 120
const INSPECT_SPEED = 10

export function MissionControl({ scenario, status, conjunctions }) {
  const globeRef = useRef(null)
  const { objects, meta } = scenario
  const epochMs = useMemo(() => Date.parse(meta.epoch), [meta.epoch])
  const windowSeconds = status.screening.windowHours * 3600
  const objectsById = useMemo(() => Object.fromEntries(objects.map((o) => [o.id, o])), [objects])

  const [selectedId, setSelectedId] = useState(null)
  const [activeConjunctionId, setActiveConjunctionId] = useState(conjunctions[0]?.id ?? null)
  const [visibleTypes, setVisibleTypes] = useState(ALL_TYPES)
  const [simTimeMs, setSimTimeMs] = useState(epochMs)
  const [playing, setPlaying] = useState(true)
  const [multiplier, setMultiplier] = useState(60)
  const [autoRotate, setAutoRotate] = useState(true)
  const [followId, setFollowId] = useState(null)

  const handleTick = useCallback((timeMs) => setSimTimeMs(timeMs), [])

  const handleSelectObject = useCallback((id) => {
    setSelectedId(id)
    setFollowId(null)
    globeRef.current?.setFollow(null)
  }, [])

  const handleInspectConjunction = useCallback(
    (id) => {
      const conj = conjunctions.find((c) => c.id === id)
      if (!conj) return
      setActiveConjunctionId(id)
      setSelectedId(null)
      setFollowId(null)
      const globe = globeRef.current
      globe?.focusConjunction(id)
      globe?.jumpToSeconds(Math.max(0, conj.tcaSecondsFromEpoch - INSPECT_LEAD_SECONDS))
      globe?.setMultiplier(INSPECT_SPEED)
      globe?.setPlaying(true)
      setMultiplier(INSPECT_SPEED)
      setPlaying(true)
    },
    [conjunctions],
  )

  const toggleType = (type) =>
    setVisibleTypes((current) => (current.includes(type) ? current.filter((t) => t !== type) : [...current, type]))

  const toggleFollow = (id) => {
    const next = followId === id ? null : id
    setFollowId(next)
    globeRef.current?.setFollow(next)
  }

  const controls = {
    playing,
    multiplier,
    autoRotate,
    onTogglePlay: () => {
      globeRef.current?.setPlaying(!playing)
      setPlaying(!playing)
    },
    onMultiplier: (value) => {
      globeRef.current?.setMultiplier(value)
      setMultiplier(value)
    },
    onToggleAutoRotate: () => {
      globeRef.current?.setAutoRotate(!autoRotate)
      setAutoRotate(!autoRotate)
    },
    onResetView: () => {
      setSelectedId(null)
      setFollowId(null)
      globeRef.current?.flyHome()
    },
    onRestart: () => globeRef.current?.jumpToSeconds(0),
  }

  const metrics = {
    monitored: objects.length,
    activeConnections: status.communication.links.filter((l) => l.status === 'online').length,
    totalConnections: status.communication.links.length,
    closeApproaches: conjunctions.length,
    critical: conjunctions.filter((c) => normalizeRiskLevel(c.risk) === 'critical' || c.risk === 'critical').length,
  }

  return (
    <div className="min-h-svh bg-space text-foreground">
      <SiteHeader simTimeMs={simTimeMs} datasetFreshness={status?.datasetFreshness || scenario?.meta?.datasetFreshness} />

      <main>
        <section id="mission-control" aria-label="Mission Control" className="relative isolate">
          <div className="relative z-0 h-[66svh] min-h-[440px] lg:absolute lg:inset-0 lg:h-auto">
            <OrbitalGlobe
              ref={globeRef}
              objects={objects}
              conjunctions={conjunctions}
              epochIso={meta.epoch}
              windowSeconds={windowSeconds}
              selectedId={selectedId}
              activeConjunctionId={activeConjunctionId}
              visibleTypes={visibleTypes}
              onSelectObject={handleSelectObject}
              onSelectConjunction={handleInspectConjunction}
              onTick={handleTick}
            />
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_60%_50%,transparent_40%,rgba(2,4,10,0.75)_100%)]"
            />
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-y-0 left-0 hidden w-[46%] bg-gradient-to-r from-space via-space/50 to-transparent lg:block"
            />
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-space to-transparent"
            />
          </div>

          <div className="pointer-events-none relative z-10 grid gap-10 px-5 pb-10 pt-8 sm:px-8 lg:min-h-svh lg:grid-cols-[minmax(0,1fr)_380px] lg:gap-8 lg:px-10 lg:pb-8 lg:pt-28">
            <div className="flex min-w-0 flex-col justify-between gap-10">
              <HeroIntro />
              <div className="pointer-events-auto flex max-w-2xl flex-col gap-8">
                <KeyMetrics metrics={metrics} />
                <ConjunctionAlerts
                  conjunctions={conjunctions}
                  objectsById={objectsById}
                  activeId={activeConjunctionId}
                  onInspect={handleInspectConjunction}
                  simTimeMs={simTimeMs}
                  epochMs={epochMs}
                />
              </div>
            </div>

            <div className="pointer-events-auto flex min-w-0 flex-col gap-4 lg:justify-between">
              <ObjectRoster
                objects={objects}
                conjunctions={conjunctions}
                selectedId={selectedId}
                onSelect={handleSelectObject}
                visibleTypes={visibleTypes}
                onToggleType={toggleType}
                simTimeMs={simTimeMs}
                epochMs={epochMs}
                followId={followId}
                onToggleFollow={toggleFollow}
              />
              <SimControls {...controls} simTimeMs={simTimeMs} epochMs={epochMs} windowSeconds={windowSeconds} />
            </div>
          </div>
        </section>

        <SituationOverview status={status} conjunctions={conjunctions} objectsById={objectsById} epochMs={epochMs} />
        <PipelineSection />
      </main>

      <SiteFooter meta={meta} />
    </div>
  )
}
