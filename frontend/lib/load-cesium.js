// Loads CesiumJS in the browser from /public/cesium.
// Cesium is a very large library that also needs web workers and textures,
// so we serve its official prebuilt files as static assets instead of
// pushing them through the Next.js bundler.

const CESIUM_BASE_URL = '/cesium/'
let loadingPromise = null

export function loadCesium() {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('CesiumJS can only run in the browser'))
  }
  if (window.Cesium) return Promise.resolve(window.Cesium)
  if (loadingPromise) return loadingPromise

  window.CESIUM_BASE_URL = CESIUM_BASE_URL

  loadingPromise = new Promise((resolve, reject) => {
    const stylesheet = document.createElement('link')
    stylesheet.rel = 'stylesheet'
    stylesheet.href = `${CESIUM_BASE_URL}Widgets/widgets.css`
    document.head.appendChild(stylesheet)

    const script = document.createElement('script')
    script.src = `${CESIUM_BASE_URL}Cesium.js`
    script.async = true
    script.onload = () => resolve(window.Cesium)
    script.onerror = () => {
      loadingPromise = null
      reject(new Error('Failed to load CesiumJS'))
    }
    document.head.appendChild(script)
  })

  return loadingPromise
}
