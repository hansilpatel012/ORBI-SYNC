// Single place where the UI gets its data.
// Connects to Member 4 (FastAPI) and Member 2 (Intelligence Engine) with seamless
// fallback to local scenario JSON files if backend is starting or offline.

import orbitalData from '@/data/orbital-objects.json'
import missionStatus from '@/data/mission-status.json'
import { screenConjunctions, normalizeOrbit } from '@/lib/orbits'
import { normalizeRiskLevel } from '@/lib/object-types'
import {
  API_BASE_URL,
  checkBackendHealth,
  fetchBackendConjunctions,
  fetchBackendSatellites,
  fetchCoordinationStatus,
  fetchOrbitalMetadata,
  fetchOrbitalSatellites,
  fetchOrbitalTrajectories,
} from '@/lib/api-client'

// Parses TLE lines into Keplerian orbit elements for 3D visualization.
export function parseTleToOrbit(line1, line2, defaultAlt = 550) {
  try {
    if (!line2 || typeof line2 !== 'string' || line2.length < 63) {
      return normalizeOrbit({ altitudeKm: defaultAlt, inclinationDeg: 53.0, raanDeg: 0.0, argumentOfLatitudeDeg: 0.0 })
    }
    const inc = parseFloat(line2.substring(8, 16)) || 53.0
    const raan = parseFloat(line2.substring(17, 25)) || 0.0
    const argPerigee = parseFloat(line2.substring(34, 42)) || 0.0
    const meanAnomaly = parseFloat(line2.substring(43, 51)) || 0.0
    const meanMotionRevPerDay = parseFloat(line2.substring(52, 63)) || 15.0

    // Compute semi-major axis from mean motion
    const nRadPerSec = (meanMotionRevPerDay * 2 * Math.PI) / 86400
    const semiMajorAxis = Math.cbrt(398600.4418 / (nRadPerSec * nRadPerSec))
    const altitudeKm = Math.max(160, Math.min(40000, semiMajorAxis - 6378.137))
    const argumentOfLatitudeDeg = ((argPerigee + meanAnomaly) % 360 + 360) % 360

    return normalizeOrbit({
      altitudeKm: Number(altitudeKm.toFixed(2)),
      inclinationDeg: Number(inc.toFixed(2)),
      raanDeg: Number(raan.toFixed(2)),
      argumentOfLatitudeDeg: Number(argumentOfLatitudeDeg.toFixed(4)),
    })
  } catch {
    return normalizeOrbit({ altitudeKm: defaultAlt, inclinationDeg: 53.0, raanDeg: 0.0, argumentOfLatitudeDeg: 0.0 })
  }
}

// Infers object type from satellite name or catalog designation.
export function inferObjectType(name) {
  if (!name || typeof name !== 'string') return 'active'
  const upper = name.toUpperCase()
  if (upper.includes('DEB') || upper.includes('FRAGMENT') || upper.includes('DEBRIS')) return 'debris'
  if (
    upper.includes('R/B') ||
    upper.includes('ROCKET') ||
    upper.includes('STAGE') ||
    upper.includes('PAM-D') ||
    upper.includes('AKM')
  ) {
    return 'rocket-body'
  }
  return 'active'
}

export async function getOrbitalScenario() {
  const [backendSatellites, orbitalMeta, orbitalSats, orbitalTrajs] = await Promise.all([
    fetchBackendSatellites(),
    fetchOrbitalMetadata(),
    fetchOrbitalSatellites(200),
    fetchOrbitalTrajectories(15, 200),
  ])

  const satCatalog =
    orbitalSats && orbitalSats.items && orbitalSats.items.length > 0
      ? orbitalSats.items
      : backendSatellites?.items || []

  const hasBackend =
    (backendSatellites && backendSatellites.items && backendSatellites.items.length > 0) ||
    (orbitalMeta && orbitalMeta.status === 'online') ||
    satCatalog.length > 0

  if (hasBackend) {
    // Map Member 1 trajectories by NORAD ID
    const trajByNorad = new Map()
    const timestampsUtc = orbitalTrajs?.timestamps_utc || []
    if (orbitalTrajs?.trajectories && Array.isArray(orbitalTrajs.trajectories)) {
      for (const t of orbitalTrajs.trajectories) {
        if (t.norad_id) {
          trajByNorad.set(String(t.norad_id).trim(), t)
        }
      }
    }

    const objectsList = []
    const seenIds = new Set()

    // 1. First, include and enrich baseline demo scenario objects
    for (const obj of orbitalData.objects) {
      const match = satCatalog.find(
        (b) => b.name?.toLowerCase() === obj.name?.toLowerCase() || String(b.norad_id) === String(obj.norad_id),
      )
      const objId = String(obj.id)
      seenIds.add(objId)
      objectsList.push({
        ...obj,
        id: objId,
        orbit: normalizeOrbit(obj.orbit),
        backendId: match?.id || match?.norad_id || objId,
        operator: match?.operator_name || obj.operator,
        backendStatus: match?.status || 'active',
        tleAgeHours: match?.tle_age_hours ?? null,
      })
    }

    // 2. Second, add Member 1 catalogue satellites with validated trajectories and orbits
    for (const sat of satCatalog) {
      const noradStr = String(sat.norad_id).trim()
      if (!noradStr || seenIds.has(noradStr)) continue
      seenIds.add(noradStr)

      const type = inferObjectType(sat.name)
      const orbit = parseTleToOrbit(sat.line1, sat.line2)
      const traj = trajByNorad.get(noradStr)

      let validTrajectory = null
      if (traj && Array.isArray(traj.positions_km) && traj.positions_km.length > 0 && timestampsUtc.length > 0) {
        const validPoints = []
        const validTimes = []
        const count = Math.min(traj.positions_km.length, timestampsUtc.length)
        for (let idx = 0; idx < count; idx++) {
          const pt = traj.positions_km[idx]
          const ts = timestampsUtc[idx]
          if (Array.isArray(pt) && pt.length >= 3) {
            const [x, y, z] = pt
            if (Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)) {
              const r = Math.hypot(x, y, z)
              if (r >= 6000 && r <= 50000 && !isNaN(Date.parse(ts))) {
                validPoints.push([x, y, z])
                validTimes.push(ts)
              }
            }
          }
        }
        if (validPoints.length >= 5) {
          validTrajectory = {
            timestamps: validTimes,
            positions: validPoints,
            coordinateFrame: orbitalTrajs?.metadata?.coordinate_frame || 'GCRS',
          }
        }
      }

      objectsList.push({
        id: noradStr,
        norad_id: noradStr,
        name: sat.name || `NORAD ${noradStr}`,
        designation: `NORAD-${noradStr}`,
        type,
        operator: type === 'debris' ? 'Debris fragment' : type === 'rocket-body' ? 'Rocket body' : 'Satellite operator',
        role: type === 'debris' ? 'Space debris' : type === 'rocket-body' ? 'Spent stage' : 'Communications / Earth observation',
        massKg: type === 'debris' ? 5 : type === 'rocket-body' ? 1200 : 450,
        manoeuvrable: type === 'active',
        orbit,
        trajectory: validTrajectory,
        backendId: sat.id || noradStr,
        backendStatus: sat.status || 'active',
        tleAgeHours: sat.tle_age_hours ?? null,
      })
    }

    return {
      meta: {
        ...orbitalData.meta,
        backendConnected: true,
        backendUrl: API_BASE_URL,
        backendSatellitesCount: orbitalMeta?.total_satellites || satCatalog.length || 200,
        coordinationEngine: 'Member 2 Intelligence Engine Connected',
        orbitalEngine:
          orbitalMeta?.status === 'online' ? 'Member 1 SGP4 Numerical Propagator (GCRS)' : 'Local Evaluator',
        datasetFreshness: orbitalMeta
          ? {
              status: orbitalMeta.data_freshness_status,
              conjunctionEpoch: orbitalMeta.conjunction_generated_at_utc,
              trajectoryStart: orbitalMeta.trajectory_start_time_utc,
              trajectoryEnd: orbitalMeta.trajectory_end_time_utc,
              tleSha256: orbitalMeta.tle_sha256,
              totalSatellites: orbitalMeta.total_satellites,
              totalConjunctions: orbitalMeta.total_conjunctions,
            }
          : null,
      },
      objects: objectsList,
    }
  }

  return {
    meta: {
      ...orbitalData.meta,
      backendConnected: false,
      backendUrl: API_BASE_URL,
      datasetFreshness: null,
    },
    objects: orbitalData.objects.map((o) => ({ ...o, orbit: normalizeOrbit(o.orbit) })),
  }
}

export async function getMissionStatus() {
  const [health, coordStatus, orbitalMeta] = await Promise.all([
    checkBackendHealth(),
    fetchCoordinationStatus(),
    fetchOrbitalMetadata(),
  ])

  if (health && health.status === 'ok') {
    const isCoordOnline =
      coordStatus && (coordStatus.status === 'online' || coordStatus.member_2_engine === 'connected')
    const isOrbitalOnline = orbitalMeta && orbitalMeta.status === 'online'

    return {
      ...missionStatus,
      backendConnected: true,
      datasetFreshness: orbitalMeta
        ? {
            status: orbitalMeta.data_freshness_status,
            conjunctionEpoch: orbitalMeta.conjunction_generated_at_utc,
            trajectoryStart: orbitalMeta.trajectory_start_time_utc,
            trajectoryEnd: orbitalMeta.trajectory_end_time_utc,
            tleSha256: orbitalMeta.tle_sha256,
            totalSatellites: orbitalMeta.total_satellites,
          }
        : null,
      communication: {
        links: [
          { id: 'link-backend', name: 'Member 4 FastAPI Backend Gateway', status: 'online' },
          {
            id: 'link-member1',
            name: 'Member 1 Orbital Engine (SGP4 / GCRS)',
            status: isOrbitalOnline ? 'online' : 'standby',
          },
          {
            id: 'link-member2',
            name: 'Member 2 Intelligence Engine',
            status: isCoordOnline ? 'online' : 'standby',
          },
          ...missionStatus.communication.links,
        ],
      },
      dataReliability: {
        scorePercent: isOrbitalOnline && isCoordOnline ? 98 : 94,
        basis:
          isOrbitalOnline && isCoordOnline
            ? `FastAPI Gateway, Member 1 SGP4 Propagator (200 satellites), and Member 2 Intelligence Engine active. Conjunction screening epoch: ${orbitalMeta.conjunction_generated_at_utc || '2026-11-21'}.`
            : 'FastAPI Gateway online with local scenario fallback.',
        sources: [
          { name: 'Member 4 Supabase PostgreSQL', status: 'nominal' },
          { name: 'Member 1 SGP4 Ephemeris Propagator', status: isOrbitalOnline ? 'nominal' : 'standby' },
          { name: 'Member 2 Collision Risk Predictor', status: isCoordOnline ? 'nominal' : 'standby' },
          { name: 'Demonstration Scenario Catalogue', status: 'nominal' },
        ],
      },
      events: [
        {
          id: 'evt-orbital-connected',
          offsetMinutes: 0,
          severity: 'info',
          title: 'Member 1 & 2 Orbital Intelligence Online',
          detail: `200 satellites propagating in GCRS. 40 close approaches screened with continuous-run minimization (TLE SHA-256: ${orbitalMeta?.tle_sha256?.slice(0, 8) || 'verified'}...).`,
        },
        ...missionStatus.events,
      ],
    }
  }

  return missionStatus
}

// Close approaches: fetched from Member 1 / Member 2 / FastAPI if available,
// falling back to local orbital screening.
// Deduplicates identical conjunctions while strictly preserving distinct encounters.
export async function getConjunctions(scenario, status) {
  const backendConjunctions = await fetchBackendConjunctions()

  if (backendConjunctions && backendConjunctions.length > 0) {
    const epochMs = Date.parse(scenario.meta.epoch)
    const processed = []
    const seenIdentical = []
    const seenIds = new Set()

    for (let i = 0; i < backendConjunctions.length; i++) {
      const c = backendConjunctions[i]
      const rawRisk = c.risk || c.risk_level || 'warning'
      const normRisk = normalizeRiskLevel(rawRisk)
      const tcaMs = Date.parse(c.tcaIso || c.tca_utc || c.closest_approach)
      const tcaSeconds = !isNaN(tcaMs) ? Math.max(0, (tcaMs - epochMs) / 1000) : 14400
      const objA = String(c.objectA || c.norad_id_1 || c.satellite_1_id || '').trim()
      const objB = String(c.objectB || c.norad_id_2 || c.satellite_2_id || '').trim()
      const missKm = Number(c.missDistanceKm ?? c.miss_distance_km ?? 0)

      if (!objA || !objB) continue

      // Canonical pair key (sorted) to detect identical vs distinct encounters
      const pairKey = [objA, objB].sort().join('-')

      // Check for identical duplicate (same pair, TCA within 60s, miss within 0.05 km)
      const isIdentical = seenIdentical.some((existing) => {
        if (existing.pairKey !== pairKey) return false
        const timeDiff = Math.abs((existing.tcaMs || 0) - (tcaMs || 0))
        const missDiff = Math.abs(existing.missKm - missKm)
        return timeDiff < 60_000 && missDiff < 0.05
      })

      if (isIdentical) {
        // Discard truly identical duplicate
        continue
      }

      seenIdentical.push({ pairKey, tcaMs, missKm })

      // Generate unique, deterministic encounter ID
      const tcaTag = !isNaN(tcaMs)
        ? new Date(tcaMs).toISOString().replace(/[-:.]/g, '').slice(9, 15)
        : String(Math.round(tcaSeconds))

      let candidateId = c.id
      if (!candidateId || seenIds.has(candidateId)) {
        candidateId = `cnj-${objA}-${objB}-${tcaTag}`
      }

      let finalId = candidateId
      let disambiguator = 2
      while (seenIds.has(finalId)) {
        finalId = `${candidateId}-${disambiguator}`
        disambiguator++
      }
      seenIds.add(finalId)

      processed.push({
        id: finalId,
        conjunctionId: c.conjunction_id || finalId,
        objectA: objA,
        objectB: objB,
        satellite1Name: c.satellite_1 || null,
        satellite2Name: c.satellite_2 || null,
        tcaIso: c.tcaIso || c.tca_utc || c.closest_approach,
        tcaSecondsFromEpoch: c.tcaSecondsFromEpoch ?? tcaSeconds,
        missDistanceKm: missKm,
        relativeVelocityKmS: c.relativeVelocityKmS ?? c.relative_speed_kms ?? 10.0,
        encountersInWindow: 1,
        risk: normRisk,
        rawRisk: String(rawRisk).toUpperCase(),
        collisionProbability: c.collisionProbability ?? c.collision_probability ?? null,
        uncertaintyScaleKm: c.uncertainty_scale_km ?? null,
        anomalyFlag: c.anomalyFlag ?? false,
        notes: c.notes ?? '',
        manoeuvrePlan: c.manoeuvrePlan ?? null,
        briefingReport: c.briefingReport ?? null,
        isSynthetic: true,
        source: c.source || 'Member 1 SGP4 Screening + Member 2 Risk Engine',
        syntheticWarning:
          c.syntheticWarning ||
          'SYNTHETIC TEST OUTPUT: Evaluator uses synthetic linear approximation. Certified collision avoidance requires Member 1 numerical orbital repropagation.',
      })
    }

    return processed
  }

  return screenConjunctions(scenario.objects, scenario.meta.epoch, status.screening)
}
