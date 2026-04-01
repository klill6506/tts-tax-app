/**
 * Zip code → city/state lookup using zippopotam.us (free, no API key).
 * Results are cached in-memory so repeat lookups are instant.
 */

interface ZipResult {
  city: string;
  state: string;
}

const cache = new Map<string, ZipResult | null>();

export async function lookupZip(zip: string): Promise<ZipResult | null> {
  if (!/^\d{5}$/.test(zip)) return null;

  if (cache.has(zip)) return cache.get(zip) ?? null;

  try {
    const res = await fetch(`https://api.zippopotam.us/us/${zip}`);
    if (!res.ok) {
      cache.set(zip, null);
      return null;
    }
    const data = await res.json();
    const place = data.places?.[0];
    if (!place) {
      cache.set(zip, null);
      return null;
    }
    const result: ZipResult = {
      city: place["place name"],
      state: place["state abbreviation"],
    };
    cache.set(zip, result);
    return result;
  } catch {
    // Network error — don't cache so it can be retried
    return null;
  }
}
