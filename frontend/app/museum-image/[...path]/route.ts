import { MUSEUM_IIIF_URL } from "@/lib";

const IIIF_PATH = /^[0-9a-f-]{36}\/full\/\d{1,4},\/0\/default\.jpg$/;

const ATTEMPT_TIMEOUT_MS = 45_000;
const ATTEMPTS = 3;
const CACHE_LIMIT = 200;

type CachedImage = { body: ArrayBuffer; contentType: string };

const cache = new Map<string, CachedImage>();

function remember(path: string, image: CachedImage) {
  if (cache.size >= CACHE_LIMIT) cache.delete(cache.keys().next().value!);
  cache.set(path, image);
}

async function download(url: string): Promise<CachedImage | null> {
  for (let attempt = 1; attempt <= ATTEMPTS; attempt++) {
    try {
      const response = await fetch(url, {
        headers: { "AIC-User-Agent": "Arremate (teste tecnico de leiloes)" },
        signal: AbortSignal.timeout(ATTEMPT_TIMEOUT_MS),
      });
      if (response.ok) {
        return {
          body: await response.arrayBuffer(),
          contentType: response.headers.get("Content-Type") ?? "image/jpeg",
        };
      }
      if (response.status !== 429 && response.status < 500) return null;
    } catch {}
    if (attempt < ATTEMPTS) await new Promise((resolve) => setTimeout(resolve, 500 * attempt));
  }
  return null;
}

// The museum sends `Cross-Origin-Resource-Policy: same-origin`, so images are served from here.
export async function GET(_request: Request, { params }: RouteContext<"/museum-image/[...path]">) {
  const path = (await params).path.join("/");
  if (!IIIF_PATH.test(path)) return new Response(null, { status: 404 });

  let image = cache.get(path) ?? null;
  if (!image) {
    image = await download(`${MUSEUM_IIIF_URL}${path}`);
    if (!image) return new Response(null, { status: 502 });
    remember(path, image);
  }

  return new Response(image.body, {
    headers: {
      "Content-Type": image.contentType,
      "Cache-Control": "public, max-age=86400, s-maxage=604800, stale-while-revalidate=86400",
    },
  });
}
