import type {
  FindDealsParams,
  FindDealsResponse,
  GetMedianPropertiesResponse,
} from "../types";

// Change this to your local or deployed FastAPI URL
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }

  return res.json() as Promise<T>;
}

/** Call /api/find_deals — may take 1–3 minutes */
export function findDeals(params: FindDealsParams): Promise<FindDealsResponse> {
  return post<FindDealsResponse>("/api/find_deals", params);
}

/** Call /api/get_median_properties for a specific property's comparables */
export function getComparables(
  postcode: string,
  property_type: string,
  bedrooms: number,
  tenure: "FREEHOLD" | "LEASEHOLD" | "ANY" = "FREEHOLD",
  min_properties = 5
): Promise<GetMedianPropertiesResponse> {
  return post<GetMedianPropertiesResponse>("/api/get_median_properties", {
    postcode,
    property_type,
    bedrooms,
    tenure,
    min_properties,
  });
}
