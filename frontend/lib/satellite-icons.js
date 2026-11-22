// Draws a distinct marker for each object type on a <canvas>.
// Cesium uses the resulting image as a "billboard" that always faces the camera.

const SIZE = 96
const cache = new Map()

function glow(ctx, color) {
  const g = ctx.createRadialGradient(SIZE / 2, SIZE / 2, 0, SIZE / 2, SIZE / 2, SIZE / 2)
  g.addColorStop(0, `${color}55`)
  g.addColorStop(0.35, `${color}22`)
  g.addColorStop(1, `${color}00`)
  ctx.fillStyle = g
  ctx.fillRect(0, 0, SIZE, SIZE)
}

function drawActiveSatellite(ctx, color) {
  const c = SIZE / 2
  ctx.save()
  ctx.translate(c, c)
  ctx.rotate(-Math.PI / 8)
  ctx.strokeStyle = color
  ctx.fillStyle = `${color}33`
  ctx.lineWidth = 2
  // Solar panels
  for (const side of [-1, 1]) {
    const x = side === -1 ? -34 : 12
    ctx.fillRect(x, -7, 22, 14)
    ctx.strokeRect(x, -7, 22, 14)
    ctx.beginPath()
    for (let k = 1; k < 4; k++) {
      ctx.moveTo(x + (22 / 4) * k, -7)
      ctx.lineTo(x + (22 / 4) * k, 7)
    }
    ctx.stroke()
  }
  // Booms
  ctx.beginPath()
  ctx.moveTo(-12, 0)
  ctx.lineTo(-8, 0)
  ctx.moveTo(8, 0)
  ctx.lineTo(12, 0)
  ctx.stroke()
  // Bus
  ctx.fillStyle = color
  ctx.fillRect(-8, -9, 16, 18)
  // Antenna
  ctx.beginPath()
  ctx.moveTo(0, -9)
  ctx.lineTo(0, -16)
  ctx.stroke()
  ctx.beginPath()
  ctx.arc(0, -17, 2.5, 0, Math.PI * 2)
  ctx.fill()
  ctx.restore()
}

function drawRocketBody(ctx, color) {
  const c = SIZE / 2
  ctx.save()
  ctx.translate(c, c)
  ctx.rotate(Math.PI / 4)
  ctx.strokeStyle = color
  ctx.lineWidth = 2
  ctx.fillStyle = `${color}44`
  ctx.beginPath()
  ctx.roundRect(-8, -22, 16, 36, 4)
  ctx.fill()
  ctx.stroke()
  // Bands
  ctx.beginPath()
  ctx.moveTo(-8, -10)
  ctx.lineTo(8, -10)
  ctx.moveTo(-8, 2)
  ctx.lineTo(8, 2)
  ctx.stroke()
  // Nozzle
  ctx.fillStyle = color
  ctx.beginPath()
  ctx.moveTo(-5, 14)
  ctx.lineTo(5, 14)
  ctx.lineTo(8, 22)
  ctx.lineTo(-8, 22)
  ctx.closePath()
  ctx.fill()
  ctx.restore()
}

function drawDebris(ctx, color) {
  const c = SIZE / 2
  ctx.save()
  ctx.translate(c, c)
  ctx.strokeStyle = color
  ctx.lineWidth = 2
  ctx.fillStyle = `${color}55`
  ctx.beginPath()
  const shard = [
    [-13, -6],
    [-4, -15],
    [9, -11],
    [14, 1],
    [6, 13],
    [-6, 9],
    [-15, 6],
  ]
  shard.forEach(([x, y], k) => (k === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)))
  ctx.closePath()
  ctx.fill()
  ctx.stroke()
  // Small fragments
  ctx.fillStyle = color
  for (const [x, y, r] of [
    [20, -14, 2.2],
    [-20, 15, 1.8],
    [18, 16, 1.5],
  ]) {
    ctx.beginPath()
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.restore()
}

export function getObjectIcon(type, color) {
  const key = `${type}-${color}`
  if (cache.has(key)) return cache.get(key)

  const canvas = document.createElement('canvas')
  canvas.width = SIZE
  canvas.height = SIZE
  const ctx = canvas.getContext('2d')
  glow(ctx, color)
  if (type === 'active') drawActiveSatellite(ctx, color)
  else if (type === 'rocket-body') drawRocketBody(ctx, color)
  else drawDebris(ctx, color)

  const url = canvas.toDataURL('image/png')
  cache.set(key, url)
  return url
}

export function getSelectionRing(color) {
  const key = `ring-${color}`
  if (cache.has(key)) return cache.get(key)
  const canvas = document.createElement('canvas')
  canvas.width = SIZE
  canvas.height = SIZE
  const ctx = canvas.getContext('2d')
  ctx.strokeStyle = color
  ctx.lineWidth = 2
  const c = SIZE / 2
  // Four corner brackets — a "targeting" reticle.
  const r = 40
  const len = 12
  for (const [sx, sy] of [
    [-1, -1],
    [1, -1],
    [1, 1],
    [-1, 1],
  ]) {
    ctx.beginPath()
    ctx.moveTo(c + sx * r, c + sy * (r - len))
    ctx.lineTo(c + sx * r, c + sy * r)
    ctx.lineTo(c + sx * (r - len), c + sy * r)
    ctx.stroke()
  }
  const url = canvas.toDataURL('image/png')
  cache.set(key, url)
  return url
}
