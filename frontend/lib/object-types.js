// Visual identity for each type of orbital object.
// `hex` is used by Cesium (3D scene); `className` values are used by Tailwind.

export const OBJECT_TYPES = {
  active: {
    label: 'Active satellite',
    shortLabel: 'Active',
    hex: '#38d6f0',
    textClass: 'text-obj-active',
    bgClass: 'bg-obj-active',
  },
  debris: {
    label: 'Space debris',
    shortLabel: 'Debris',
    hex: '#c9c1b3',
    textClass: 'text-obj-debris',
    bgClass: 'bg-obj-debris',
  },
  'rocket-body': {
    label: 'Rocket body',
    shortLabel: 'Rocket body',
    hex: '#8f9dff',
    textClass: 'text-obj-rocket',
    bgClass: 'bg-obj-rocket',
  },
}

export const DEFAULT_RISK_LEVEL = {
  label: 'Unknown',
  hex: '#94a3b8',
  textClass: 'text-muted-foreground',
  bgClass: 'bg-muted-foreground',
  severity: 'info',
}

const BASE_RISK_LEVELS = {
  // Canonical frontend risk labels
  critical: {
    label: 'Critical',
    hex: '#f0444a',
    textClass: 'text-critical',
    bgClass: 'bg-critical',
    severity: 'critical',
  },
  warning: {
    label: 'Warning',
    hex: '#f5a524',
    textClass: 'text-warning',
    bgClass: 'bg-warning',
    severity: 'warning',
  },
  monitor: {
    label: 'Monitor',
    hex: '#34d399',
    textClass: 'text-safe',
    bgClass: 'bg-safe',
    severity: 'info',
  },
  // Backend risk levels (LOW, MEDIUM, HIGH, CRITICAL)
  high: {
    label: 'High',
    hex: '#f5a524',
    textClass: 'text-warning',
    bgClass: 'bg-warning',
    severity: 'warning',
  },
  medium: {
    label: 'Medium',
    hex: '#f5a524',
    textClass: 'text-warning',
    bgClass: 'bg-warning',
    severity: 'warning',
  },
  low: {
    label: 'Low',
    hex: '#34d399',
    textClass: 'text-safe',
    bgClass: 'bg-safe',
    severity: 'info',
  },
  unknown: DEFAULT_RISK_LEVEL,
}

/**
 * Normalizes backend risk levels (LOW, MEDIUM, HIGH, CRITICAL)
 * into frontend risk labels (monitor, warning, critical).
 */
export function normalizeRiskLevel(rawRisk) {
  if (!rawRisk || typeof rawRisk !== 'string') return 'monitor'
  const key = rawRisk.trim().toLowerCase()
  switch (key) {
    case 'critical':
      return 'critical'
    case 'high':
    case 'warning':
    case 'medium':
      return 'warning'
    case 'low':
    case 'monitor':
      return 'monitor'
    default:
      return 'monitor'
  }
}

/**
 * Safely resolves risk styling and labels for any risk string.
 * Always returns a valid risk descriptor with label, hex, textClass, and bgClass.
 */
export function getRiskLevel(riskKey) {
  if (!riskKey || typeof riskKey !== 'string') return DEFAULT_RISK_LEVEL
  const key = riskKey.trim().toLowerCase()
  return (
    BASE_RISK_LEVELS[key] ||
    BASE_RISK_LEVELS[normalizeRiskLevel(key)] ||
    DEFAULT_RISK_LEVEL
  )
}

// Proxied RISK_LEVELS ensures safe fallback for direct index access (e.g. RISK_LEVELS[conj.risk])
export const RISK_LEVELS = new Proxy(BASE_RISK_LEVELS, {
  get(target, prop) {
    if (typeof prop === 'string') {
      const lower = prop.trim().toLowerCase()
      if (lower in target) return target[lower]
      const normalized = normalizeRiskLevel(lower)
      if (normalized in target) return target[normalized]
      return DEFAULT_RISK_LEVEL
    }
    return target[prop]
  },
})
