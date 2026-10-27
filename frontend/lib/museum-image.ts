export const MUSEUM_IIIF_URL = 'https://www.artic.edu/iiif/2/'

export function museumImageSrc(src: string): string {
  return src.startsWith(MUSEUM_IIIF_URL) ? `/museum-image/${src.slice(MUSEUM_IIIF_URL.length)}` : src
}
