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
  median_price: number;
  difference: number;
  sample_size: number;
  link: string;
  comparables_postcode: string; // postcode used to fetch comparables
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
  floor_area?: string; // empty for now, field reserved
}

export interface GetMedianPropertiesResponse {
  status: string;
  median_price: number;
  property_count: number;
  search_params: { label: string };
  properties: ComparableProperty[];
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
