/**
 * ZIPs do dataset King County (Seattle e arredores).
 * Nomes em português + centro aproximado para preview de mapa (OSM embed).
 */
export type ZipRegionOption = {
  code: string
  name: string
  lat: number
  lon: number
}

export const KING_COUNTY_ZIP_OPTIONS: ZipRegionOption[] = [
  { code: '98103', name: 'Seattle — Fremont / Green Lake', lat: 47.661, lon: -122.344 },
  { code: '98115', name: 'Seattle — Lake City / NE', lat: 47.685, lon: -122.292 },
  { code: '98052', name: 'Redmond', lat: 47.669, lon: -122.08 },
  { code: '98004', name: 'Bellevue — centro', lat: 47.614, lon: -122.205 },
  { code: '98101', name: 'Seattle — Downtown / Belltown', lat: 47.606, lon: -122.332 },
  { code: '98105', name: 'Seattle — UW / Ravenna', lat: 47.661, lon: -122.302 },
  { code: '98107', name: 'Seattle — Ballard', lat: 47.668, lon: -122.386 },
  { code: '98117', name: 'Seattle — Phinney / Greenwood', lat: 47.691, lon: -122.377 },
  { code: '98199', name: 'Seattle — Magnolia', lat: 47.651, lon: -122.398 },
]

export function getZipOption(code: string): ZipRegionOption | undefined {
  return KING_COUNTY_ZIP_OPTIONS.find((z) => z.code === code)
}

export function getZipRegionName(code: string): string | undefined {
  return getZipOption(code)?.name
}

/** Texto compacto para cards (evita só o número cru). */
export function formatZipWithRegion(code: string): string {
  const name = getZipRegionName(code)
  return name ? `${name} · ZIP ${code}` : `ZIP ${code}`
}

/** Só a região, para subtítulos curtos. */
export function formatZipRegionShort(code: string): string {
  return getZipRegionName(code) ?? `ZIP ${code}`
}

/**
 * iframe OpenStreetMap (sem API key): mapa real embutido na UI.
 * bbox e marker centrados na região do ZIP.
 */
export function zipOsmEmbedUrl(code: string): string | null {
  const z = getZipOption(code)
  if (!z) return null
  const { lat, lon } = z
  const dLon = 0.042
  const dLat = 0.036
  const bbox = `${lon - dLon},${lat - dLat},${lon + dLon},${lat + dLat}`
  const marker = `${lat}%2C${lon}`
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${marker}`
}
