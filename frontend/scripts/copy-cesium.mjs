// Copies CesiumJS's prebuilt files (library, web workers, textures, star map)
// from node_modules into /public/cesium so the browser can load them.
import { cpSync, existsSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const source = join(root, 'node_modules', 'cesium', 'Build', 'Cesium')
const target = join(root, 'public', 'cesium')
const marker = join(target, '.version')
const version = JSON.parse(readFileSync(join(root, 'node_modules', 'cesium', 'package.json'), 'utf8')).version

if (existsSync(marker) && readFileSync(marker, 'utf8') === version) {
  console.log(`[cesium] assets v${version} already in public/cesium`)
} else {
  cpSync(source, target, { recursive: true })
  writeFileSync(marker, version)
  console.log(`[cesium] copied assets v${version} to public/cesium`)
}
