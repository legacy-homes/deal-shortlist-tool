// ─── API Request Types ────────────────────────────────────────────────────────

export interface FindDealsParams {
  rightmove_url: string;
  price_difference_threshold: number;
  max_properties: number;
  include_featured: boolean;
  tenure: "FREEHOLD" | "LEASEHOLD" | "ANY";
  min_properties_for_median: number;
}

// ─── API Response Types ───────────────────────────────────────────────────────

export interface DealProperty {
  address: string;
  postcode: string;
  property_type: string;
  bedrooms: number;
  asking_price: number;
  median_price: number | null;
  difference: number | null;
  sample_size: number | null;
  link: string;
  floor_area: string | null;
  floor_area_availability: string | null;
  comparables_postcode: string;
  median_search_params: { label: string } | null;
  comparable_properties: ComparableProperty[] | null;
  is_deal: boolean;
}

export interface FindDealsResponse {
  status: string;
  total_processed: number;
  deals_found: number;
  price_difference_threshold: number;
  deals: DealProperty[];
  all_properties: DealProperty[];
}

export interface ComparableProperty {
  id: string;
  address: string;
  postcode: string;
  property_type: string;
  bedrooms: number;
  sold_date: string;
  sold_price: number;
  link: string;
  floor_area: string | null;
  floor_area_availability: string | null;
  search_radius_miles: number;
}

export interface GetMedianPropertiesResponse {
  status: string;
  median_price: number | null;
  property_count: number | null;
  search_params: { label: string } | null;
  properties: ComparableProperty[] | null;
}

// Extends the API response with persisted user qualification state
export interface ComparablesCacheEntry extends GetMedianPropertiesResponse {
  qualifiedIds: string[] | null;  // null = all qualified (default)
  qualifiedMedian: number | null; // recalculated from qualified comparables only
}

// ─── App State Types ──────────────────────────────────────────────────────────

export interface SavedSearch {
  id: string;           // uuid
  label: string;        // user-given name
  searchedAt: string;   // ISO date string
  params: FindDealsParams;
  results: FindDealsResponse;
}

export interface PipelineDeal {
  id: string;           // uuid
  savedSearchId: string;
  savedSearchLabel: string;
  sentAt: string;       // ISO date string
  property: DealProperty;
}
