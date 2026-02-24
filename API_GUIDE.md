# DealFinder API — How to Use Guide

**Version:** 1.0.0  
**Base URL:** `https://8000-izl6ja44klap3udj8j0ap-2316f949.us2.manus.computer`  
**Interactive Docs:** `{BASE_URL}/docs`  
**Parser Version:** 2.0.6 (last verified: 2026-02-24)

---

## Overview

The DealFinder API exposes all IntegratedTools_v2 capabilities as REST endpoints. All endpoints share a single `shared/rightmove_parsers.py` module — when the parser is updated via `/api/parser/fix`, all endpoints automatically use the new version.

---

## Endpoints

### `GET /health`
Health check. Returns parser version and server status.

```bash
curl https://{BASE_URL}/health
```

---

### `GET /parser/info`
Returns the current parser version and the Rightmove structure versions it supports.

```bash
curl https://{BASE_URL}/parser/info
```

---

### `POST /api/search_properties`
Search active Rightmove listings for a given location and property type.

**Request body:**
```json
{
  "locationIdentifier": "REGION%5E904",
  "propertyTypes": "semi-detached",
  "sortType": 1,
  "index": 0,
  "maxPrice": 200000,
  "includeFeatured": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `locationIdentifier` | string | Yes | Rightmove location ID (from URL) |
| `propertyTypes` | string | Yes | e.g. `semi-detached`, `terraced`, `detached`, `flat` |
| `sortType` | int | No | 1=Highest price, 2=Lowest price, 6=Newest (default: 1) |
| `index` | int | No | Pagination offset (0, 24, 48, ...) |
| `maxPrice` | int | No | Maximum asking price filter |
| `includeFeatured` | bool | No | Include promoted listings (default: false) |

**Response:**
```json
{
  "status": "success",
  "count": 9,
  "parser_version": "2.0.6",
  "properties": [
    {
      "id": "172435835",
      "price": 65000,
      "address": "286 Greenside Lane, Droylsden...",
      "postcode": "M43 7XX",
      "property_type": "Semi-Detached",
      "bedrooms": 3,
      "link": "https://www.rightmove.co.uk/...",
      "is_featured": false
    }
  ]
}
```

---

### `POST /api/calculate_median`
Calculate the median sold price for a given postcode, property type, and bedroom count.

Uses a progressive search strategy: starts with 'this area only' (last 2 years), then expands radius (0.25 → 0.5 → 1.0 miles) and time (3 years) until `min_properties` is reached.

**Request body:**
```json
{
  "postcode": "M5 4UB",
  "property_type": "Terraced",
  "bedrooms": 2,
  "tenure": "FREEHOLD",
  "min_properties": 10
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `postcode` | string | Yes | UK postcode |
| `property_type` | string | Yes | e.g. `Semi-Detached`, `Terraced`, `Detached`, `Flat` |
| `bedrooms` | int | Yes | Number of bedrooms |
| `tenure` | string | No | `FREEHOLD`, `LEASEHOLD`, or `ANY` (default: `FREEHOLD`) |
| `min_properties` | int | No | Minimum sample size for reliable median (default: 10) |

**Response:**
```json
{
  "status": "success",
  "result": {
    "median_price": 240000,
    "property_count": 9,
    "search_params": {
      "label": "1 mile radius, last 2 years"
    }
  }
}
```

---

### `POST /api/get_median_properties`
Get the **full list of sold properties** used in the median price calculation.

Uses the same progressive search strategy as `/api/calculate_median` but returns the complete list of individual matching sold properties alongside the median price.

**Request body:** (identical to `/api/calculate_median`)
```json
{
  "postcode": "M5 4UB",
  "property_type": "Terraced",
  "bedrooms": 2,
  "tenure": "FREEHOLD",
  "min_properties": 5
}
```

**Response:**
```json
{
  "status": "success",
  "median_price": 240000,
  "property_count": 9,
  "search_params": { "label": "1 mile radius, last 2 years" },
  "properties": [
    {
      "id": "...",
      "address": "6, Prestage Street, Manchester M16 9LH",
      "postcode": "M16 9LH",
      "property_type": "Terraced",
      "bedrooms": 2,
      "sold_date": "21 Nov 2025",
      "sold_price": 260000,
      "link": "https://www.rightmove.co.uk/house-prices/details/..."
    },
    ...
  ]
}
```

---

### `POST /api/find_deals`
Find undervalued properties on a Rightmove search page.

Fetches active listings from the given URL, then for each property calculates the local median sold price and identifies deals where the asking price is significantly below the median.

> **Note:** This endpoint makes multiple Rightmove requests and may take 1–3 minutes depending on the number of properties.

**Request body:**
```json
{
  "rightmove_url": "https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier=REGION%5E904&propertyTypes=semi-detached&sortType=1&index=0",
  "price_difference_threshold": 50000,
  "max_properties": 10,
  "include_featured": false,
  "tenure": "FREEHOLD",
  "min_properties_for_median": 5
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `rightmove_url` | string | Yes | Full Rightmove search URL |
| `price_difference_threshold` | int | No | Min £ below median to qualify as a deal (default: 50000) |
| `max_properties` | int | No | Limit properties to process (default: all on page) |
| `include_featured` | bool | No | Include featured listings (default: false) |
| `tenure` | string | No | `FREEHOLD`, `LEASEHOLD`, or `ANY` |
| `min_properties_for_median` | int | No | Min sample size for median (default: 5) |

**Response:**
```json
{
  "status": "success",
  "total_processed": 9,
  "deals_found": 2,
  "price_difference_threshold": 50000,
  "deals": [...],
  "all_properties": [
    {
      "address": "...",
      "asking_price": 65000,
      "median_price": 130000,
      "difference": 65000,
      "is_deal": true,
      ...
    }
  ]
}
```

---

### `POST /api/parser/fix`
**Trigger the parser fix workflow** (as defined in `MANUS_FIX_PARSING.md`).

This endpoint:
1. Fetches fresh HTML from Rightmove (active + sold listings)
2. Tests the current parser against the fresh HTML
3. Detects any structural changes (e.g. index key shifts)
4. Applies fixes if needed and increments the version
5. Uploads the updated parser to Google Drive (both `RightmoveParsingModule` and `IntegratedTools_v2`)
6. Reloads the parser in memory — all other endpoints immediately use the new version
7. Runs the test suite to verify the fix

> **Note:** Takes 30–60 seconds. No request body needed.

```bash
curl -X POST https://{BASE_URL}/api/parser/fix
```

**Response:**
```json
{
  "status": "success",
  "changes_made": ["Fixed link field: ...", "Updated parser version: 2.0.5 → 2.0.6"],
  "test_results": {
    "result": "PASSED",
    "passed": 23,
    "failed": 1,
    "total": 24
  },
  "parser_info": {
    "parser_version": "2.0.6",
    "last_verified": "2026-02-24"
  },
  "steps": [...]
}
```

---

### `POST /api/parser/test`
Run the parser test suite (as defined in `MANUS_TEST_PARSING.md`).

Executes `test_parsing.py` against stored test data and returns a structured report.

```bash
curl -X POST https://{BASE_URL}/api/parser/test
```

**Response:**
```json
{
  "status": "success",
  "test_result": "FAILED",
  "summary": {
    "passed": 23,
    "failed": 1,
    "skipped": 0,
    "total": 24
  },
  "parser_info": {...},
  "output": "... full test output ..."
}
```

---

## Architecture Notes

- **Single source of truth:** All endpoints import from `shared/rightmove_parsers.py`. When `/api/parser/fix` updates the file and reloads it, every endpoint immediately uses the new parser.
- **CORS enabled:** All origins are allowed — safe to call from any frontend app.
- **Interactive docs:** Visit `{BASE_URL}/docs` for a Swagger UI where you can test all endpoints directly in the browser.

---

## Quick Start (Frontend Integration)

```javascript
const BASE_URL = 'https://8000-izl6ja44klap3udj8j0ap-2316f949.us2.manus.computer';

// Search properties
const res = await fetch(`${BASE_URL}/api/search_properties`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    locationIdentifier: 'REGION%5E904',
    propertyTypes: 'semi-detached',
    sortType: 1,
    index: 0
  })
});
const data = await res.json();
console.log(data.properties);

// Calculate median price
const medianRes = await fetch(`${BASE_URL}/api/calculate_median`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    postcode: 'M5 4UB',
    property_type: 'Terraced',
    bedrooms: 2,
    tenure: 'FREEHOLD'
  })
});
const median = await medianRes.json();
console.log('Median price:', median.result.median_price);
```
