const pad = (n) => String(Math.floor(n)).padStart(2, '0')

export function formatUtc(ms, { withDate = true } = {}) {
  const d = new Date(ms)
  const time = `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`
  if (!withDate) return time
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${time}`
}

// "T−01:12:05" before the event, "T+00:03:10" after it.
export function formatCountdown(targetMs, nowMs) {
  const diff = targetMs - nowMs
  const sign = diff >= 0 ? 'T−' : 'T+'
  const s = Math.abs(diff) / 1000
  return `${sign}${pad(s / 3600)}:${pad((s % 3600) / 60)}:${pad(s % 60)}`
}

export function formatNumber(value, digits = 0) {
  return value.toLocaleString('en-GB', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function formatCoordinate(deg, positive, negative) {
  return `${Math.abs(deg).toFixed(2)}° ${deg >= 0 ? positive : negative}`
}
