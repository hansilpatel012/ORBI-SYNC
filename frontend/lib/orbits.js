// Simplified orbital mechanics for the demo scenario and Member 1 integration.
// Includes safe fallbacks for missing/undefined orbits or corrupted telemetry.

export const EARTH_RADIUS_KM = 6378.137
export const EARTH_MU = 398600.4418 // km^3 / s^2

const DEG = Math.PI / 180

const DEFAULT_ORBIT = {
  altitudeKm: 550,
  inclinationDeg: 53,
  raanDeg: 0,
  argumentOfLatitudeDeg: 0,
}

export function normalizeOrbit(orbit) {
  if (!orbit || typeof orbit !== 'object') return DEFAULT_ORBIT
  return {
    altitudeKm:
      typeof orbit.altitudeKm === 'number' && Number.isFinite(orbit.altitudeKm) && orbit.altitudeKm > 0
        ? orbit.altitudeKm
        : 550,
    inclinationDeg:
      typeof orbit.inclinationDeg === 'number' && Number.isFinite(orbit.inclinationDeg)
        ? orbit.inclinationDeg
        : 53,
    raanDeg:
      typeof orbit.raanDeg === 'number' && Number.isFinite(orbit.raanDeg)
        ? orbit.raanDeg
        : 0,
    argumentOfLatitudeDeg:
      typeof orbit.argumentOfLatitudeDeg === 'number' && Number.isFinite(orbit.argumentOfLatitudeDeg)
        ? orbit.argumentOfLatitudeDeg
        : 0,
  }
}

export function semiMajorAxisKm(orbit) {
  const norm = normalizeOrbit(orbit)
  return EARTH_RADIUS_KM + norm.altitudeKm
}

export function meanMotionRadPerSec(orbit) {
  const a = semiMajorAxisKm(orbit)
  return Math.sqrt(EARTH_MU / (a * a * a))
}

export function orbitalPeriodSeconds(orbit) {
  return (2 * Math.PI) / meanMotionRadPerSec(orbit)
}

export function circularVelocityKmS(orbit) {
  return Math.sqrt(EARTH_MU / semiMajorAxisKm(orbit))
}

function argumentOfLatitude(orbit, secondsSinceEpoch) {
  const norm = normalizeOrbit(orbit)
  return norm.argumentOfLatitudeDeg * DEG + meanMotionRadPerSec(norm) * (secondsSinceEpoch || 0)
}

// Position (km) in an Earth-centred inertial frame.
function eciFromAngle(orbit, u) {
  const norm = normalizeOrbit(orbit)
  const r = semiMajorAxisKm(norm)
  const i = norm.inclinationDeg * DEG
  const raan = norm.raanDeg * DEG
  const cosU = Math.cos(u)
  const sinU = Math.sin(u)
  const cosO = Math.cos(raan)
  const sinO = Math.sin(raan)
  const cosI = Math.cos(i)
  return {
    x: r * (cosO * cosU - sinO * sinU * cosI),
    y: r * (sinO * cosU + cosO * sinU * cosI),
    z: r * (sinU * Math.sin(i)),
  }
}

export function positionEci(orbit, secondsSinceEpoch) {
  const norm = normalizeOrbit(orbit)
  return eciFromAngle(norm, argumentOfLatitude(norm, secondsSinceEpoch))
}

export function velocityEci(orbit, secondsSinceEpoch) {
  const norm = normalizeOrbit(orbit)
  const u = argumentOfLatitude(norm, secondsSinceEpoch)
  const v = circularVelocityKmS(norm)
  const i = norm.inclinationDeg * DEG
  const raan = norm.raanDeg * DEG
  const cosU = Math.cos(u)
  const sinU = Math.sin(u)
  const cosO = Math.cos(raan)
  const sinO = Math.sin(raan)
  const cosI = Math.cos(i)
  return {
    x: v * (-cosO * sinU - sinO * cosU * cosI),
    y: v * (-sinO * sinU + cosO * sinU * cosI),
    z: v * (cosU * Math.sin(i)),
  }
}

// A full closed ring of points describing the orbit, used to draw the path.
export function orbitRingEci(orbit, segments = 180) {
  if (!orbit) return []
  const norm = normalizeOrbit(orbit)
  const points = []
  for (let k = 0; k <= segments; k++) {
    points.push(eciFromAngle(norm, (k / segments) * 2 * Math.PI))
  }
  return points
}

function distanceKm(a, b) {
  if (!a || !b) return Infinity
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z)
}

function separationAt(objA, objB, t) {
  if (!objA?.orbit || !objB?.orbit) return Infinity
  return distanceKm(positionEci(objA.orbit, t), positionEci(objB.orbit, t))
}

// Golden-section search for the exact minimum separation inside [lo, hi].
function refineMinimum(objA, objB, lo, hi) {
  const ratio = (Math.sqrt(5) - 1) / 2
  let a = lo
  let b = hi
  let c = b - ratio * (b - a)
  let d = a + ratio * (b - a)
  for (let iter = 0; iter < 60; iter++) {
    if (separationAt(objA, objB, c) < separationAt(objA, objB, d)) b = d
    else a = c
    c = b - ratio * (b - a)
    d = a + ratio * (b - a)
  }
  const t = (a + b) / 2
  return { t, missKm: separationAt(objA, objB, t) }
}

export function classifyRisk(missKm, thresholds) {
  if (missKm < thresholds.critical) return 'critical'
  if (missKm < thresholds.warning) return 'warning'
  return 'monitor'
}

// Screens every pair of objects for close approaches inside the time window.
// Each pair is reported once, using its closest encounter.
export function screenConjunctions(objects, epochIso, screening) {
  const epochMs = Date.parse(epochIso)
  const windowSeconds = screening.windowHours * 3600
  const step = screening.coarseStepSeconds
  const results = []

  for (let i = 0; i < objects.length; i++) {
    for (let j = i + 1; j < objects.length; j++) {
      const objA = objects[i]
      const objB = objects[j]
      if (!objA?.orbit || !objB?.orbit) continue

      let best = null
      let encounters = 0
      let prev = separationAt(objA, objB, 0)
      let curr = separationAt(objA, objB, step)

      for (let t = step; t < windowSeconds; t += step) {
        const next = separationAt(objA, objB, t + step)
        const isLocalMinimum = curr <= prev && curr <= next
        if (isLocalMinimum && curr < 400) {
          const refined = refineMinimum(objA, objB, t - step, t + step)
          if (refined.missKm < screening.reportThresholdKm) {
            encounters++
            if (!best || refined.missKm < best.missKm) best = refined
          }
        }
        prev = curr
        curr = next
      }

      if (best) {
        const va = velocityEci(objA.orbit, best.t)
        const vb = velocityEci(objB.orbit, best.t)
        const tcaTag = Math.round(best.t)
        results.push({
          id: `cnj-${objA.id}-${objB.id}-${tcaTag}`,
          objectA: objA.id,
          objectB: objB.id,
          tcaIso: new Date(epochMs + best.t * 1000).toISOString(),
          tcaSecondsFromEpoch: best.t,
          missDistanceKm: best.missKm,
          relativeVelocityKmS: Math.hypot(va.x - vb.x, va.y - vb.y, va.z - vb.z),
          encountersInWindow: encounters,
          risk: classifyRisk(best.missKm, screening.riskThresholdsKm),
          collisionProbability: null,
          source: 'computed-from-simulated-orbits',
        })
      }
    }
  }

  const order = { critical: 0, high: 0, warning: 1, medium: 1, monitor: 2, low: 2 }
  return results.sort(
    (a, b) => (order[a.risk] ?? 3) - (order[b.risk] ?? 3) || a.tcaSecondsFromEpoch - b.tcaSecondsFromEpoch,
  )
}

// Greenwich Mean Sidereal Time (radians) — used to turn inertial positions
// into latitude / longitude for the information panel.
export function gmstRadians(date) {
  const jd = date.getTime() / 86400000 + 2440587.5
  const t = (jd - 2451545.0) / 36525
  let gmstDeg =
    280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t * t - (t * t * t) / 38710000
  gmstDeg = ((gmstDeg % 360) + 360) % 360
  return gmstDeg * DEG
}

export function subSatellitePoint(orbit, secondsSinceEpoch, date) {
  const norm = normalizeOrbit(orbit)
  const p = positionEci(norm, secondsSinceEpoch)
  const r = Math.hypot(p.x, p.y, p.z)
  if (!r || !Number.isFinite(r)) {
    return { latDeg: 0, lonDeg: 0, altitudeKm: 550 }
  }
  const lat = Math.asin(Math.max(-1, Math.min(1, p.z / r))) / DEG
  let lon = (Math.atan2(p.y, p.x) - gmstRadians(date)) / DEG
  lon = ((((lon + 180) % 360) + 360) % 360) - 180
  return { latDeg: lat, lonDeg: lon, altitudeKm: r - EARTH_RADIUS_KM }
}
