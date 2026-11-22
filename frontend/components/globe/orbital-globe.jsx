'use client'

import { useEffect, useImperativeHandle, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { loadCesium } from '@/lib/load-cesium'
import { orbitRingEci, positionEci, normalizeOrbit } from '@/lib/orbits'
import { OBJECT_TYPES, RISK_LEVELS, getRiskLevel } from '@/lib/object-types'
import { getObjectIcon, getSelectionRing } from '@/lib/satellite-icons'

const SAMPLE_STEP_SECONDS = 60
const TRAIL_SECONDS = 900
const HOME_VIEW = { lon: 20, lat: 18, height: 24_000_000 }
const AUTO_ROTATE_RAD_PER_SEC = -0.02
const IDLE_BEFORE_ROTATE_MS = 6000

export function OrbitalGlobe({
  ref,
  objects,
  conjunctions,
  epochIso,
  windowSeconds,
  selectedId,
  activeConjunctionId,
  visibleTypes,
  onSelectObject,
  onSelectConjunction,
  onTick,
}) {
  const containerRef = useRef(null)
  const creditRef = useRef(null)
  const sceneRef = useRef(null)
  const [status, setStatus] = useState('loading')

  // Values the Cesium render loop reads every frame. Stored in a ref so that
  // changing them does not rebuild the whole 3D scene.
  const live = useRef({
    selectedId,
    activeConjunctionId,
    hoverId: null,
    autoRotate: true,
    flying: false,
    lastInteraction: 0,
  })
  const handlers = useRef({ onSelectObject, onSelectConjunction, onTick })

  useEffect(() => {
    handlers.current = { onSelectObject, onSelectConjunction, onTick }
  }, [onSelectObject, onSelectConjunction, onTick])

  // ---------- Build the 3D scene once per dataset ----------
  useEffect(() => {
    let cancelled = false
    let viewer = null
    const cleanups = []

    loadCesium()
      .then((Cesium) => {
        if (cancelled || !containerRef.current) return

        viewer = new Cesium.Viewer(containerRef.current, {
          baseLayer: false,
          animation: false,
          timeline: false,
          baseLayerPicker: false,
          geocoder: false,
          homeButton: false,
          sceneModePicker: false,
          navigationHelpButton: false,
          fullscreenButton: false,
          infoBox: false,
          selectionIndicator: false,
          scene3DOnly: true,
          shouldAnimate: true,
          creditContainer: creditRef.current,
          msaaSamples: 4,
          // Our own fallback panel handles failures, so hide Cesium's built-in error popup.
          showRenderLoopErrors: false,
          contextOptions: { webgl: { failIfMajorPerformanceCaveat: false, powerPreference: 'high-performance' } },
        })

        const { scene } = viewer
        scene.backgroundColor = Cesium.Color.BLACK
        scene.globe.baseColor = Cesium.Color.fromCssColorString('#06101f')
        scene.globe.enableLighting = true
        scene.globe.dynamicAtmosphereLighting = true
        scene.globe.showGroundAtmosphere = true
        scene.skyAtmosphere.show = true
        scene.screenSpaceCameraController.minimumZoomDistance = 1_500_000
        scene.screenSpaceCameraController.maximumZoomDistance = 80_000_000

        // Imagery: a bundled offline Earth texture first (always works),
        // then high-resolution satellite imagery on top when reachable.
        viewer.imageryLayers.add(
          Cesium.ImageryLayer.fromProviderAsync(
            Cesium.TileMapServiceImageryProvider.fromUrl(Cesium.buildModuleUrl('Assets/Textures/NaturalEarthII')),
          ),
        )
        try {
          const satelliteLayer = Cesium.ImageryLayer.fromProviderAsync(
            Cesium.ArcGisMapServerImageryProvider.fromBasemapType(Cesium.ArcGisBaseMapType.SATELLITE),
          )
          satelliteLayer.saturation = 0.85
          satelliteLayer.brightness = 0.95
          viewer.imageryLayers.add(satelliteLayer)
        } catch (error) {
          console.warn('[orbi] High-resolution imagery unavailable, using offline texture', error)
        }

        // ---------- Simulation clock ----------
        const start = Cesium.JulianDate.fromIso8601(epochIso)
        const stop = Cesium.JulianDate.addSeconds(start, windowSeconds, new Cesium.JulianDate())
        viewer.clock.startTime = start.clone()
        viewer.clock.stopTime = stop.clone()
        viewer.clock.currentTime = start.clone()
        viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP
        viewer.clock.multiplier = 60
        viewer.clock.shouldAnimate = true

        // Converts an inertial position (km) into Cesium's Earth-fixed frame (m).
        const scratchMatrix = new Cesium.Matrix3()
        const scratchVector = new Cesium.Cartesian3()
        const toEarthFixed = (p, time, result = new Cesium.Cartesian3()) => {
          const matrix = Cesium.Transforms.computeTemeToPseudoFixedMatrix(time, scratchMatrix)
          Cesium.Cartesian3.fromElements(p.x * 1000, p.y * 1000, p.z * 1000, scratchVector)
          return Cesium.Matrix3.multiplyByVector(matrix, scratchVector, result)
        }

        const labelFont = `500 11px ${
          getComputedStyle(document.documentElement).getPropertyValue('--font-geist-mono').trim() || 'monospace'
        }`
        const pulse = (speed = 320) => (Math.sin(performance.now() / speed) + 1) / 2
        const inActiveConjunction = (id) => {
          const active = conjunctions.find((c) => c.id === live.current.activeConjunctionId)
          return !!active && (active.objectA === id || active.objectB === id)
        }

        // ---------- Orbital objects ----------
        for (const obj of objects) {
          const style = OBJECT_TYPES[obj.type] || OBJECT_TYPES.active || { hex: '#22c55e' }
          const color = Cesium.Color.fromCssColorString(style.hex)
          const safeOrbit = normalizeOrbit(obj.orbit)

          const position = new Cesium.SampledPositionProperty()
          position.setInterpolationOptions({
            interpolationDegree: 5,
            interpolationAlgorithm: Cesium.LagrangePolynomialApproximation,
          })

          // Handle Member 1 sampled trajectory coordinates and timestamps if available
          let sampledCount = 0
          if (
            obj.trajectory &&
            Array.isArray(obj.trajectory.positions) &&
            Array.isArray(obj.trajectory.timestamps) &&
            obj.trajectory.positions.length > 0
          ) {
            const count = Math.min(obj.trajectory.positions.length, obj.trajectory.timestamps.length)
            for (let idx = 0; idx < count; idx++) {
              const pt = obj.trajectory.positions[idx]
              const ts = obj.trajectory.timestamps[idx]
              try {
                if (
                  Array.isArray(pt) &&
                  pt.length >= 3 &&
                  Number.isFinite(pt[0]) &&
                  Number.isFinite(pt[1]) &&
                  Number.isFinite(pt[2])
                ) {
                  const julian = Cesium.JulianDate.fromIso8601(ts)
                  const fixedPos = toEarthFixed({ x: pt[0], y: pt[1], z: pt[2] }, julian)
                  position.addSample(julian, fixedPos)
                  sampledCount++
                }
              } catch {
                // Ignore any invalid timestamp or point safely
              }
            }
          }

          // Fallback to circular orbit if no valid trajectory coordinates were sampled
          if (sampledCount === 0) {
            for (let t = 0; t <= windowSeconds + SAMPLE_STEP_SECONDS; t += SAMPLE_STEP_SECONDS) {
              const time = Cesium.JulianDate.addSeconds(start, t, new Cesium.JulianDate())
              position.addSample(time, toEarthFixed(positionEci(safeOrbit, t), time))
            }
          }

          // Eased "pop" factor: 0 at rest, 1 when hovered/touched.
          let pop = 0
          const popAmount = () => {
            const s = live.current
            const target = s.hoverId === obj.id ? 1 : 0
            pop += (target - pop) * 0.18
            return pop
          }

          viewer.entities.add({
            id: String(obj.id),
            name: obj.name,
            position,
            billboard: {
              image: getObjectIcon(obj.type, style.hex),
              scale: new Cesium.CallbackProperty(() => {
                const s = live.current
                let scale = s.selectedId === obj.id ? 0.62 : 0.46
                scale += popAmount() * 0.38
                if (inActiveConjunction(obj.id)) scale += pulse() * 0.12
                return scale
              }, false),
            },
            label: {
              text: obj.name,
              font: labelFont,
              fillColor: Cesium.Color.WHITE.withAlpha(0.9),
              showBackground: true,
              backgroundColor: Cesium.Color.fromCssColorString('#02040a').withAlpha(0.6),
              backgroundPadding: new Cesium.Cartesian2(6, 3),
              pixelOffset: new Cesium.Cartesian2(0, -32),
              scale: new Cesium.CallbackProperty(() => 1 + pop * 0.2, false),
            },
            path: {
              leadTime: 0,
              trailTime: TRAIL_SECONDS,
              width: 3,
              resolution: 30,
              material: new Cesium.PolylineGlowMaterialProperty({
                glowPower: 0.3,
                taperPower: 0.5,
                color: color.withAlpha(0.95),
              }),
            },
          })

          // Targeting reticle shown only around the selected object.
          viewer.entities.add({
            id: `${obj.id}::ring`,
            position,
            billboard: {
              image: getSelectionRing(style.hex),
              show: new Cesium.CallbackProperty(() => live.current.selectedId === obj.id, false),
              scale: new Cesium.CallbackProperty(() => 0.7 + pulse(500) * 0.08, false),
            },
          })

          // Full orbit ring. Drawn in inertial space and rotated into the
          // Earth-fixed frame each frame, so it stays a clean closed loop.
          let ringEci = []
          if (
            obj.trajectory &&
            Array.isArray(obj.trajectory.positions) &&
            obj.trajectory.positions.length >= 10
          ) {
            const stride = Math.max(1, Math.floor(obj.trajectory.positions.length / 180))
            ringEci = obj.trajectory.positions
              .filter((_, i) => i % stride === 0 && Array.isArray(_) && _.length >= 3)
              .map((p) => ({ x: p[0], y: p[1], z: p[2] }))
          } else {
            ringEci = orbitRingEci(safeOrbit, 180)
          }

          if (ringEci.length > 0) {
            viewer.entities.add({
              id: `${obj.id}::orbit`,
              polyline: {
                positions: new Cesium.CallbackProperty(
                  (time) => ringEci.map((p) => toEarthFixed(p, time)),
                  false,
                ),
                arcType: Cesium.ArcType.NONE,
                width: new Cesium.CallbackProperty(() => (live.current.selectedId === obj.id ? 3 : 2), false),
                material: new Cesium.PolylineGlowMaterialProperty({
                  glowPower: 0.18,
                  taperPower: 1,
                  color: new Cesium.CallbackProperty(() => {
                    const s = live.current
                    if (s.selectedId === obj.id || inActiveConjunction(obj.id)) return color.withAlpha(0.95)
                    if (s.selectedId) return color.withAlpha(0.16)
                    return color.withAlpha(0.42)
                  }, false),
                }),
              },
            })
          }
        }

        // ---------- Conjunctions (close approaches) ----------
        const tcaPositions = new Map()
        for (const conj of conjunctions) {
          const risk = getRiskLevel(conj.risk)
          const color = Cesium.Color.fromCssColorString(risk.hex || '#f5a524')
          const objA = objects.find(
            (o) =>
              String(o.id) === String(conj.objectA) ||
              String(o.backendId) === String(conj.objectA) ||
              String(o.norad_id) === String(conj.objectA),
          )
          const objB = objects.find(
            (o) =>
              String(o.id) === String(conj.objectB) ||
              String(o.backendId) === String(conj.objectB) ||
              String(o.norad_id) === String(conj.objectB),
          )

          const tcaTime = Cesium.JulianDate.addSeconds(start, conj.tcaSecondsFromEpoch || 0, new Cesium.JulianDate())
          const entityA =
            viewer.entities.getById(String(conj.objectA)) || (objA ? viewer.entities.getById(String(objA.id)) : null)
          const entityB =
            viewer.entities.getById(String(conj.objectB)) || (objB ? viewer.entities.getById(String(objB.id)) : null)

          let tcaPosition = null
          if (entityA && entityA.position) {
            tcaPosition = entityA.position.getValue(tcaTime)
          }
          if (!tcaPosition && objA?.orbit) {
            tcaPosition = toEarthFixed(positionEci(objA.orbit, conj.tcaSecondsFromEpoch || 0), tcaTime)
          }
          if (!tcaPosition && entityB && entityB.position) {
            tcaPosition = entityB.position.getValue(tcaTime)
          }
          if (!tcaPosition && objB?.orbit) {
            tcaPosition = toEarthFixed(positionEci(objB.orbit, conj.tcaSecondsFromEpoch || 0), tcaTime)
          }

          if (tcaPosition) {
            tcaPositions.set(conj.id, tcaPosition)
            const isActive = () => live.current.activeConjunctionId === conj.id

            viewer.entities.add({
              id: `${conj.id}::tca`,
              position: tcaPosition,
              point: {
                pixelSize: new Cesium.CallbackProperty(() => (isActive() ? 9 : 6) + pulse(260) * (isActive() ? 9 : 4), false),
                color: color.withAlpha(0.95),
                outlineColor: color.withAlpha(0.3),
                outlineWidth: 6,
              },
              label: {
                text: 'TCA',
                font: labelFont,
                fillColor: color,
                pixelOffset: new Cesium.Cartesian2(0, 22),
                show: new Cesium.CallbackProperty(isActive, false),
              },
            })
          }

          if (entityA && entityB) {
            const isActive = () => live.current.activeConjunctionId === conj.id
            viewer.entities.add({
              id: `${conj.id}::link`,
              polyline: {
                positions: new Cesium.CallbackProperty((time) => {
                  const a = entityA.position?.getValue(time)
                  const b = entityB.position?.getValue(time)
                  return a && b ? [a, b] : []
                }, false),
                arcType: Cesium.ArcType.NONE,
                width: 1.5,
                show: new Cesium.CallbackProperty(isActive, false),
                material: new Cesium.PolylineDashMaterialProperty({ color: color.withAlpha(0.85), dashLength: 14 }),
              },
            })
          }
        }

        // ---------- Interaction ----------
        const baseId = (entity) => (entity?.id ? String(entity.id).split('::')[0] : null)

        viewer.selectedEntityChanged.addEventListener((entity) => {
          const id = baseId(entity)
          if (id?.startsWith('cnj-')) handlers.current.onSelectConjunction?.(id)
          else handlers.current.onSelectObject?.(id)
        })

        const input = new Cesium.ScreenSpaceEventHandler(scene.canvas)
        const hoverAt = (screenPosition) => {
          const picked = scene.pick(screenPosition)
          const id = Cesium.defined(picked) ? baseId(picked.id) : null
          live.current.hoverId = id && !id.startsWith('cnj-') ? id : null
          scene.canvas.style.cursor = id ? 'pointer' : 'grab'
        }
        input.setInputAction((movement) => hoverAt(movement.endPosition), Cesium.ScreenSpaceEventType.MOUSE_MOVE)
        const markInteraction = () => {
          live.current.lastInteraction = performance.now()
        }
        // Touch screens have no hover, so a tap also triggers the pop effect.
        input.setInputAction((event) => {
          markInteraction()
          hoverAt(event.position)
        }, Cesium.ScreenSpaceEventType.LEFT_DOWN)
        for (const type of [
          Cesium.ScreenSpaceEventType.RIGHT_DOWN,
          Cesium.ScreenSpaceEventType.MIDDLE_DOWN,
          Cesium.ScreenSpaceEventType.WHEEL,
          Cesium.ScreenSpaceEventType.PINCH_START,
        ]) {
          input.setInputAction(markInteraction, type)
        }
        cleanups.push(() => input.destroy())

        // ---------- Per-frame updates ----------
        let lastFrame = performance.now()
        let lastEmit = 0
        const removeTick = viewer.clock.onTick.addEventListener((clock) => {
          const now = performance.now()
          const dt = (now - lastFrame) / 1000
          lastFrame = now
          const s = live.current
          if (
            s.autoRotate &&
            !s.selectedId &&
            !s.flying &&
            !viewer.trackedEntity &&
            now - s.lastInteraction > IDLE_BEFORE_ROTATE_MS
          ) {
            scene.camera.rotate(Cesium.Cartesian3.UNIT_Z, AUTO_ROTATE_RAD_PER_SEC * dt)
          }
          if (now - lastEmit > 250) {
            lastEmit = now
            handlers.current.onTick?.(Cesium.JulianDate.toDate(clock.currentTime).getTime(), clock.shouldAnimate)
          }
        })
        cleanups.push(removeTick)

        // ---------- Opening camera move ----------
        scene.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(HOME_VIEW.lon - 30, HOME_VIEW.lat, 60_000_000),
        })
        live.current.flying = true
        scene.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(HOME_VIEW.lon, HOME_VIEW.lat, HOME_VIEW.height),
          duration: 3.5,
          easingFunction: Cesium.EasingFunction.QUINTIC_IN_OUT,
          complete: () => (live.current.flying = false),
          cancel: () => (live.current.flying = false),
        })

        sceneRef.current = { viewer, Cesium, start, tcaPositions }
        setStatus('ready')
      })
      .catch((error) => {
        console.error('[orbi] Failed to initialise CesiumJS', error)
        if (!cancelled) setStatus('error')
      })

    return () => {
      cancelled = true
      cleanups.forEach((fn) => fn())
      if (viewer && !viewer.isDestroyed()) viewer.destroy()
      sceneRef.current = null
    }
  }, [objects, conjunctions, epochIso, windowSeconds])

  // ---------- Camera helper ----------
  const flyToward = (cartesian, extraDistance, duration = 2.2) => {
    const ctx = sceneRef.current
    if (!ctx || !cartesian) return
    const { viewer, Cesium } = ctx
    const direction = Cesium.Cartesian3.normalize(cartesian, new Cesium.Cartesian3())
    const destination = Cesium.Cartesian3.multiplyByScalar(
      direction,
      Cesium.Cartesian3.magnitude(cartesian) + extraDistance,
      new Cesium.Cartesian3(),
    )
    live.current.flying = true
    viewer.camera.flyTo({
      destination,
      duration,
      easingFunction: Cesium.EasingFunction.CUBIC_IN_OUT,
      complete: () => (live.current.flying = false),
      cancel: () => (live.current.flying = false),
    })
  }

  // ---------- React → Cesium: selection ----------
  useEffect(() => {
    live.current.selectedId = selectedId
    const ctx = sceneRef.current
    if (!ctx) return
    const { viewer } = ctx
    const entity = selectedId ? viewer.entities.getById(selectedId) : undefined
    if (viewer.selectedEntity !== entity) viewer.selectedEntity = entity
    if (!entity && viewer.trackedEntity) viewer.trackedEntity = undefined
    if (entity) flyToward(entity.position.getValue(viewer.clock.currentTime), 8_000_000)
  }, [selectedId, status])

  useEffect(() => {
    live.current.activeConjunctionId = activeConjunctionId
  }, [activeConjunctionId])

  // ---------- React → Cesium: type filters ----------
  useEffect(() => {
    const ctx = sceneRef.current
    if (!ctx) return
    const { viewer } = ctx
    for (const obj of objects) {
      const show = visibleTypes.includes(obj.type)
      for (const suffix of ['', '::ring', '::orbit']) {
        const entity = viewer.entities.getById(`${obj.id}${suffix}`)
        if (entity) entity.show = show
      }
    }
    for (const conj of conjunctions) {
      const objA = objects.find(
        (o) =>
          String(o.id) === String(conj.objectA) ||
          String(o.backendId) === String(conj.objectA) ||
          String(o.norad_id) === String(conj.objectA),
      )
      const objB = objects.find(
        (o) =>
          String(o.id) === String(conj.objectB) ||
          String(o.backendId) === String(conj.objectB) ||
          String(o.norad_id) === String(conj.objectB),
      )
      const typeAVisible = objA ? visibleTypes.includes(objA.type) : true
      const typeBVisible = objB ? visibleTypes.includes(objB.type) : true
      const show = typeAVisible && typeBVisible
      for (const suffix of ['::tca', '::link']) {
        const entity = viewer.entities.getById(`${conj.id}${suffix}`)
        if (entity) entity.show = show
      }
    }
  }, [visibleTypes, objects, conjunctions, status])

  // ---------- Controls exposed to parent components ----------
  useImperativeHandle(
    ref,
    () => ({
      setPlaying(playing) {
        const ctx = sceneRef.current
        if (ctx) ctx.viewer.clock.shouldAnimate = playing
      },
      setMultiplier(multiplier) {
        const ctx = sceneRef.current
        if (ctx) ctx.viewer.clock.multiplier = multiplier
      },
      jumpToSeconds(secondsFromEpoch) {
        const ctx = sceneRef.current
        if (!ctx) return
        const { viewer, Cesium, start } = ctx
        viewer.clock.currentTime = Cesium.JulianDate.addSeconds(start, secondsFromEpoch, new Cesium.JulianDate())
      },
      setAutoRotate(enabled) {
        live.current.autoRotate = enabled
      },
      setFollow(objectId) {
        const ctx = sceneRef.current
        if (!ctx) return
        const { viewer, Cesium } = ctx
        const entity = objectId ? viewer.entities.getById(objectId) : undefined
        if (entity) entity.viewFrom = new Cesium.Cartesian3(-2_500_000, -2_500_000, 1_800_000)
        viewer.trackedEntity = entity
      },
      focusConjunction(conjunctionId) {
        const ctx = sceneRef.current
        if (!ctx) return
        ctx.viewer.trackedEntity = undefined
        flyToward(ctx.tcaPositions.get(conjunctionId), 5_000_000, 2.6)
      },
      flyHome() {
        const ctx = sceneRef.current
        if (!ctx) return
        const { viewer, Cesium } = ctx
        viewer.trackedEntity = undefined
        live.current.flying = true
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(HOME_VIEW.lon, HOME_VIEW.lat, HOME_VIEW.height),
          duration: 2.4,
          easingFunction: Cesium.EasingFunction.CUBIC_IN_OUT,
          complete: () => (live.current.flying = false),
          cancel: () => (live.current.flying = false),
        })
      },
    }),
    [],
  )

  return (
    <div className="orbi-globe relative h-full w-full overflow-hidden bg-space">
      <div
        ref={containerRef}
        className="absolute inset-0"
        role="application"
        aria-label="Interactive 3D Earth showing simulated orbital objects. Drag to rotate, scroll to zoom, click an object to select it."
      />
      <div ref={creditRef} className="orbi-credits pointer-events-auto absolute bottom-2 right-3 z-10 max-w-[60%] text-right" />

      <AnimatePresence>
        {status !== 'ready' && (
          <motion.div
            key="globe-status"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 1.2, ease: 'easeOut' } }}
            className="absolute inset-0 z-20 flex items-center justify-center bg-space"
          >
            {status === 'loading' ? (
              <div className="flex flex-col items-center gap-4">
                <div className="relative size-16">
                  <span className="absolute inset-0 rounded-full border border-signal/20" />
                  <span className="absolute inset-0 animate-spin rounded-full border-t border-signal [animation-duration:1.6s]" />
                </div>
                <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted-foreground">
                  Initialising orbital scene
                </p>
              </div>
            ) : (
              <div className="max-w-sm px-6 text-center">
                <p className="font-mono text-xs uppercase tracking-[0.3em] text-critical">3D view unavailable</p>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  CesiumJS could not start. Make sure WebGL is enabled in your browser and that the Cesium assets were
                  copied to <code className="font-mono text-foreground">public/cesium</code>.
                </p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
