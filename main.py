#!/usr/bin/env python3.11
"""
DealFinder Unified API Server
==============================

FastAPI server exposing all IntegratedTools_v2 capabilities as REST APIs.

Endpoints:
  GET  /                          - API info & health check
  GET  /health                    - Health check
  GET  /parser/info               - Parser version and status
  POST /api/search_properties     - Search active Rightmove listings
  POST /api/calculate_median      - Calculate median sold price
  POST /api/find_deals            - Find undervalued properties (combined)
  POST /api/get_median_properties - Get the list of sold properties used in median calculation
  POST /api/extract_floor_area    - Extract floor area (sq m) from UK EPC database for a given address
  POST /api/parser/fix            - Trigger parser fix workflow (MANUS_FIX_PARSING)
  POST /api/parser/test           - Run parser test suite (MANUS_TEST_PARSING)

Architecture:
  - All endpoints share a single shared/rightmove_parsers.py (single source of truth)
  - Parser fix endpoint updates the shared parser and all APIs automatically use the new version
  - CORS enabled for frontend access

Author: Manus AI
Date: 2026-02-24
"""

import sys
import os
import json
import time
import re
import subprocess
import importlib
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ============================================================================
# PATH SETUP - All modules use shared parser
# ============================================================================
BASE_DIR = Path(__file__).parent
SHARED_DIR = BASE_DIR / 'shared'
MEDIAN_DIR = BASE_DIR / 'MedianPriceCalculator'
DEAL_DIR = BASE_DIR / 'PropertyDealFinder'
TEST_DIR = BASE_DIR / 'test_suite'
FLOOR_AREA_DIR = BASE_DIR / 'FloorAreaExtractor'
GDRIVE_PARSER_PATH = 'DealFinder/Tools/RightmoveParsingModule/shared/rightmove_parsers.py'
GDRIVE_INTEGRATED_PARSER_PATH = 'DealFinder/Tools/IntegratedTools_v2/shared/rightmove_parsers.py'
RCLONE_CONFIG = '/home/ubuntu/.gdrive-rclone.ini'

sys.path.insert(0, str(SHARED_DIR))
sys.path.insert(0, str(MEDIAN_DIR))
sys.path.insert(0, str(DEAL_DIR))
sys.path.insert(0, str(FLOOR_AREA_DIR))

import rightmove_parsers
from rightmove_parsers import (
    extract_active_properties_from_html,
    extract_sold_properties_from_html,
    get_parser_info
)
from median_price_calculator import (
    calculate_median_price_progressive,
    fetch_properties_with_filters
)
from extract_floor_area import find_floor_area_for_address

# ============================================================================
# FASTAPI APP
# ============================================================================
app = FastAPI(
    title="DealFinder API",
    description="REST API for Rightmove property analysis tools (PropertyDealFinder + MedianPriceCalculator)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# REQUEST / RESPONSE MODELS
# ============================================================================

class SearchPropertiesRequest(BaseModel):
    locationIdentifier: str = Field(..., description="Rightmove location identifier, e.g. 'REGION%5E904'")
    maxPrice: Optional[int] = Field(None, description="Maximum price filter (£)")
    propertyTypes: str = Field(..., description="Property type(s), e.g. 'semi-detached'")
    sortType: int = Field(1, description="Sort type (1=Highest price, 2=Lowest price, 6=Newest listed)")
    index: int = Field(0, description="Pagination index (0, 24, 48, ...)")
    includeFeatured: bool = Field(False, description="Include featured/promoted listings")

class CalculateMedianRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "postcode": "CV10 0NB",
                "property_type": "Terraced",
                "bedrooms": 3,
                "tenure": "FREEHOLD",
                "min_properties": 10
            }
        }
    }
    postcode: str = Field("CV10 0NB", description="UK postcode, e.g. 'CV10 0NB'")
    property_type: str = Field("Terraced", description="Property type, e.g. 'Semi-Detached', 'Terraced'")
    bedrooms: int = Field(3, description="Number of bedrooms")
    tenure: Optional[str] = Field("FREEHOLD", description="Tenure: FREEHOLD, LEASEHOLD, or ANY for both")
    min_properties: int = Field(10, description="Minimum target property count for reliable median")

class GetMedianPropertiesRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "postcode": "CV10 0NB",
                "property_type": "Terraced",
                "bedrooms": 3,
                "tenure": "FREEHOLD",
                "min_properties": 10
            }
        }
    }
    postcode: str = Field("CV10 0NB", description="UK postcode, e.g. 'CV10 0NB'")
    property_type: str = Field("Terraced", description="Property type, e.g. 'Semi-Detached', 'Terraced'")
    bedrooms: int = Field(3, description="Number of bedrooms")
    tenure: Optional[str] = Field("FREEHOLD", description="Tenure: FREEHOLD, LEASEHOLD, or ANY for both")
    min_properties: int = Field(10, description="Minimum target property count for reliable median")

class FloorAreaRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "address": "74, Dukes Road, Tamworth, B78 1PW",
                "match_threshold": 0.85
            }
        }
    }
    address: str = Field(
        "74, Dukes Road, Tamworth, B78 1PW",
        description="Full UK property address including postcode"
    )
    match_threshold: float = Field(
        0.85,
        description="Minimum address similarity score (0-1) to accept an EPC match. Default 0.85.",
        ge=0.0,
        le=1.0
    )


class FindDealsRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "rightmove_url": "https://www.rightmove.co.uk/property-for-sale/find.html?searchLocation=CV10+0NB&useLocationIdentifier=true&locationIdentifier=POSTCODE%5E196715&buy=For+sale&radius=10.0&_includeSSTC=on&propertyTypes=semi-detached%2Cterraced&sortType=1&channel=BUY&transactionType=BUY&displayLocationIdentifier=undefined&tenureTypes=FREEHOLD&dontShow=retirement%2CnewHome%2CsharedOwnership",
                "price_difference_threshold": 50000,
                "max_properties": 30,
                "include_featured": False,
                "tenure": "FREEHOLD",
                "min_properties_for_median": 4
            }
        }
    }
    rightmove_url: str = Field(
        "https://www.rightmove.co.uk/property-for-sale/find.html?searchLocation=CV10+0NB&useLocationIdentifier=true&locationIdentifier=POSTCODE%5E196715&buy=For+sale&radius=10.0&_includeSSTC=on&propertyTypes=semi-detached%2Cterraced&sortType=1&channel=BUY&transactionType=BUY&displayLocationIdentifier=undefined&tenureTypes=FREEHOLD&dontShow=retirement%2CnewHome%2CsharedOwnership",
        description="Full Rightmove search URL"
    )
    price_difference_threshold: int = Field(50000, description="Minimum £ below median to qualify as a deal")
    max_properties: Optional[int] = Field(30, description="Max properties to process (None = all on page)")
    include_featured: bool = Field(False, description="Include featured listings")
    tenure: Optional[str] = Field("FREEHOLD", description="Tenure filter for median calculation")
    min_properties_for_median: int = Field(4, description="Min properties for median calculation")

# ============================================================================
# HELPERS
# ============================================================================

def reload_parser():
    """Reload the shared parser module to pick up any updates."""
    global rightmove_parsers, extract_active_properties_from_html, extract_sold_properties_from_html, get_parser_info
    importlib.reload(rightmove_parsers)
    from rightmove_parsers import (
        extract_active_properties_from_html as _eap,
        extract_sold_properties_from_html as _esp,
        get_parser_info as _gpi
    )
    extract_active_properties_from_html = _eap
    extract_sold_properties_from_html = _esp
    get_parser_info = _gpi
    # Also reload median_price_calculator since it imports from rightmove_parsers
    import median_price_calculator
    importlib.reload(median_price_calculator)

def fetch_html(url: str) -> str:
    """Fetch HTML from a URL with browser-like headers."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.5',
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text

def normalize_property_type(property_type: str) -> str:
    """Normalize property type for median calculation."""
    type_mappings = {
        'End of Terrace': 'Terraced',
        'End Terrace': 'Terraced',
        'Mid Terrace': 'Terraced',
        'Mid Terraced': 'Terraced',
        'Terraced House': 'Terraced',
        'Semi-Detached House': 'Semi-Detached',
        'Detached House': 'Detached',
    }
    return type_mappings.get(property_type, property_type)

# ============================================================================
# ROUTES
# ============================================================================

@app.get("/", tags=["Info"])
async def root():
    """API root - returns info and available endpoints."""
    parser_info = get_parser_info()
    return {
        "name": "DealFinder API",
        "version": "1.0.0",
        "description": "Rightmove property analysis tools exposed as REST APIs",
        "parser": parser_info,
        "endpoints": {
            "GET /health": "Health check",
            "GET /parser/info": "Parser version and status",
            "POST /api/search_properties": "Search active Rightmove listings",
            "POST /api/calculate_median": "Calculate median sold price for a postcode/type/bedrooms",
            "POST /api/find_deals": "Find undervalued properties (search + median comparison)",
            "POST /api/get_median_properties": "Get the full list of sold properties used in the median price calculation",
            "POST /api/parser/fix": "Trigger parser fix workflow (fetches fresh HTML, updates parser, uploads to GDrive)",
            "POST /api/parser/test": "Run parser test suite and return results",
        },
        "docs": "/docs",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/health", tags=["Info"])
async def health():
    """Health check endpoint."""
    try:
        info = get_parser_info()
        return {"status": "ok", "parser_version": info["parser_version"], "timestamp": datetime.utcnow().isoformat() + "Z"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/parser/info", tags=["Parser"])
async def parser_info():
    """Get current parser version and structure support info."""
    return get_parser_info()


@app.post("/api/search_properties", tags=["Properties"])
async def search_properties(req: SearchPropertiesRequest):
    """
    Search active Rightmove listings.

    Constructs a Rightmove search URL from the given parameters, fetches the page,
    and returns parsed property listings using the shared rightmove_parsers module.
    """
    try:
        # Build Rightmove URL
        url = f"https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier={req.locationIdentifier}"
        if req.maxPrice is not None:
            url += f"&maxPrice={req.maxPrice}"
        url += f"&propertyTypes={req.propertyTypes}"
        url += f"&sortType={req.sortType}"
        url += f"&index={req.index}"

        html = fetch_html(url)
        properties = extract_active_properties_from_html(html, include_featured=req.includeFeatured)
        valid_props = [p for p in properties if p is not None]

        return {
            "status": "success",
            "count": len(valid_props),
            "page_index": req.index,
            "search_url": url,
            "parser_version": get_parser_info()["parser_version"],
            "properties": valid_props
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching data from Rightmove: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/calculate_median", tags=["Median Price"])
async def calculate_median(req: CalculateMedianRequest):
    """
    Calculate the median sold price for a given postcode, property type, and bedroom count.

    Uses a progressive search strategy:
    1. Starts with 'this area only' within last 2 years
    2. Expands radius: 0.25 → 0.5 → 1.0 miles if not enough data
    3. Expands time to 3 years if still insufficient
    """
    try:
        tenure = None if req.tenure in (None, "ANY") else req.tenure.upper()

        result = calculate_median_price_progressive(
            postcode=req.postcode,
            property_type=req.property_type,
            bedrooms=req.bedrooms,
            tenure=tenure,
            min_properties=req.min_properties
        )

        properties = result.get("properties", [])

        # Ensure sold_price is always an int in the output
        for p in properties:
            if 'price' in p and 'sold_price' not in p:
                p['sold_price'] = p['price']

        return {
            "status": "success",
            "query": {
                "postcode": req.postcode,
                "property_type": req.property_type,
                "bedrooms": req.bedrooms,
                "tenure": tenure,
                "min_properties": req.min_properties
            },
            "parser_version": get_parser_info()["parser_version"],
            "result": {
                "median_price": result.get("median_price"),
                "property_count": result.get("property_count"),
                "search_params": result.get("search_params"),
                "properties": properties
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/get_median_properties", tags=["Median Price"])
async def get_median_properties(req: GetMedianPropertiesRequest):
    """
    Get the full list of sold properties used in the median price calculation.

    Runs the same progressive search strategy as /api/calculate_median but returns
    the complete list of individual sold properties that matched the criteria, along
    with the median price and search parameters used.

    Each property in the list includes: address, postcode, property type, bedrooms,
    sold date, sold price, tenure, and a link to the Rightmove listing.

    Uses the same progressive search strategy:
    1. Starts with 'this area only' within last 2 years
    2. Expands radius: 0.25 → 0.5 → 1.0 miles if not enough data
    3. Expands time to 3 years if still insufficient
    """
    try:
        tenure = None if req.tenure in (None, "ANY") else req.tenure.upper()

        result = calculate_median_price_progressive(
            postcode=req.postcode,
            property_type=req.property_type,
            bedrooms=req.bedrooms,
            tenure=tenure,
            min_properties=req.min_properties
        )

        properties = result.get("properties", [])

        # Ensure sold_price is always an int in the output
        for p in properties:
            if 'price' in p and 'sold_price' not in p:
                p['sold_price'] = p['price']

        return {
            "status": "success",
            "query": {
                "postcode": req.postcode,
                "property_type": req.property_type,
                "bedrooms": req.bedrooms,
                "tenure": tenure,
                "min_properties": req.min_properties
            },
            "parser_version": get_parser_info()["parser_version"],
            "median_price": result.get("median_price"),
            "property_count": result.get("property_count"),
            "search_params": result.get("search_params"),
            "properties": properties
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/find_deals", tags=["Deal Finder"])
async def find_deals(req: FindDealsRequest):
    """
    Find potentially undervalued properties on Rightmove.

    Fetches active listings from the given Rightmove URL, then for each property
    calculates the local median sold price and identifies deals where the asking
    price is significantly below the median.

    Note: This endpoint makes multiple requests to Rightmove and may take 1-3 minutes.
    """
    try:
        # Fetch the page HTML
        html = fetch_html(req.rightmove_url)
        properties = extract_active_properties_from_html(html, include_featured=req.include_featured)
        valid_props = [p for p in properties if p is not None]

        if not valid_props:
            return {
                "status": "success",
                "message": "No valid properties found on the page",
                "deals": [],
                "total_processed": 0
            }

        # Limit if requested
        if req.max_properties:
            valid_props = valid_props[:req.max_properties]

        tenure = None if req.tenure in (None, "ANY") else req.tenure.upper()
        deals = []
        processed = []

        for prop in valid_props:
            normalized_type = normalize_property_type(prop['property_type'])
            try:
                median_result = calculate_median_price_progressive(
                    postcode=prop['postcode'],
                    property_type=normalized_type,
                    bedrooms=prop['bedrooms'],
                    tenure=tenure,
                    min_properties=req.min_properties_for_median
                )
            except Exception:
                median_result = None

            # Build comparable properties list from median result, enriched with floor area
            comparables = []
            if median_result:
                for c in median_result.get('properties', []):
                    c_out = c.copy()
                    if 'price' in c_out and 'sold_price' not in c_out:
                        c_out['sold_price'] = c_out['price']
                    # Fetch floor area for each comparable
                    try:
                        fa = find_floor_area_for_address(c_out.get('address', ''))
                        c_out['floor_area'] = fa.get('floor_area') if fa.get('availability') == 'Available' else None
                        c_out['floor_area_availability'] = fa.get('availability')
                        time.sleep(0.5)  # polite delay for EPC requests
                    except Exception:
                        c_out['floor_area'] = None
                        c_out['floor_area_availability'] = 'NotAvailable'
                    comparables.append(c_out)

            # Fetch floor area for the deal property itself
            try:
                prop_fa = find_floor_area_for_address(prop.get('address', ''))
                prop_floor_area = prop_fa.get('floor_area') if prop_fa.get('availability') == 'Available' else None
                prop_floor_area_availability = prop_fa.get('availability')
                time.sleep(0.5)
            except Exception:
                prop_floor_area = None
                prop_floor_area_availability = 'NotAvailable'

            prop_result = {
                "id": prop['id'],
                "address": prop['address'],
                "postcode": prop['postcode'],
                "property_type": prop['property_type'],
                "bedrooms": prop['bedrooms'],
                "asking_price": prop['price'],
                "link": prop['link'],
                "floor_area": prop_floor_area,
                "floor_area_availability": prop_floor_area_availability,
                "median_price": None,
                "difference": None,
                "sample_size": None,
                "median_search_params": None,
                "is_deal": False,
                "comparable_properties": comparables
            }

            if median_result and median_result.get('median_price'):
                median_price = median_result['median_price']
                difference = median_price - prop['price']
                prop_result.update({
                    "median_price": median_price,
                    "difference": difference,
                    "sample_size": median_result.get('property_count'),
                    "median_search_params": median_result.get('search_params'),
                    "is_deal": difference >= req.price_difference_threshold
                })
                if prop_result['is_deal']:
                    deals.append(prop_result)

            processed.append(prop_result)
            time.sleep(1)  # polite delay

        return {
            "status": "success",
            "total_processed": len(processed),
            "deals_found": len(deals),
            "price_difference_threshold": req.price_difference_threshold,
            "parser_version": get_parser_info()["parser_version"],
            "deals": deals,
            "all_properties": processed
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching data from Rightmove: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/extract_floor_area", tags=["Floor Area"])
async def extract_floor_area(req: "FloorAreaRequest"):
    """
    Extract total floor area (sq m) for a UK property address from the
    government EPC (Energy Performance Certificate) database.

    The tool:
    1. Extracts the postcode from the supplied address.
    2. Searches the EPC register for all certificates at that postcode.
    3. Finds the best-matching certificate using address similarity.
    4. Scrapes the floor area from the certificate page.

    Returns `availability: "Available"` with `floor_area` in sq m when found,
    or `availability: "NotAvailable"` with a reason when not.

    Note: Makes live requests to find-energy-certificate.service.gov.uk.
    """
    try:
        result = find_floor_area_for_address(
            full_address=req.address,
            threshold=req.match_threshold
        )
        return {
            "status": "success",
            "query": {
                "address": req.address,
                "match_threshold": req.match_threshold
            },
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/parser/test", tags=["Parser"])
async def run_parser_tests():
    """
    Run the parser test suite (as defined in MANUS_TEST_PARSING.md).

    Executes the test_parsing.py test suite against stored test data and returns
    a structured report of pass/fail results. Use this to verify the parser is
    working correctly after a fix or to detect Rightmove structure changes.
    """
    try:
        result = subprocess.run(
            [sys.executable, str(TEST_DIR / 'test_parsing.py'), '--verbose'],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(TEST_DIR)
        )

        output = result.stdout + result.stderr
        import re as _re
        passed = len(_re.findall(r'  ✓ ', output))
        failed = len(_re.findall(r'  ✗ ', output))
        skipped = len(_re.findall(r'  ⊘ ', output))

        return {
            "status": "success",
            "test_result": "PASSED" if result.returncode == 0 else "FAILED",
            "exit_code": result.returncode,
            "summary": {
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "total": passed + failed + skipped
            },
            "parser_info": get_parser_info(),
            "output": output,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Test suite timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/parser/fix", tags=["Parser"])
async def fix_parser():
    """
    Trigger the parser fix workflow (as defined in MANUS_FIX_PARSING.md).

    This endpoint:
    1. Fetches fresh HTML from Rightmove (active + sold listings)
    2. Analyses the current structure
    3. Tests the existing parser against fresh HTML
    4. If the sold listing parser has link issues, applies the fix
    5. Updates the version and last-verified date
    6. Uploads the fixed parser to Google Drive (both RightmoveParsingModule and IntegratedTools_v2)
    7. Reloads the parser in memory so all endpoints immediately use the new version
    8. Runs the test suite to verify the fix
    9. Returns a detailed report

    Note: This endpoint makes live requests to Rightmove and may take 30-60 seconds.
    """
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "steps": [],
        "changes_made": [],
        "test_results": None,
        "status": "unknown"
    }

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        # Step 1: Fetch fresh active listing HTML
        report["steps"].append("Step 1: Fetching fresh active listing HTML from Rightmove...")
        active_url = "https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier=REGION%5E904&propertyTypes=semi-detached&sortType=1&index=0"
        resp = requests.get(active_url, headers=headers, timeout=30)
        resp.raise_for_status()
        fresh_active_html = resp.text
        report["steps"].append(f"  ✓ Fetched {len(fresh_active_html):,} bytes of active listing HTML")

        # Step 2: Fetch fresh sold listing HTML
        report["steps"].append("Step 2: Fetching fresh sold listing HTML from Rightmove...")
        sold_url = "https://www.rightmove.co.uk/house-prices/manchester.html?soldIn=2&radius=1.0"
        resp2 = requests.get(sold_url, headers=headers, timeout=30)
        resp2.raise_for_status()
        fresh_sold_html = resp2.text
        report["steps"].append(f"  ✓ Fetched {len(fresh_sold_html):,} bytes of sold listing HTML")

        # Step 3: Test current parser against fresh HTML
        report["steps"].append("Step 3: Testing current parser against fresh HTML...")
        active_props = extract_active_properties_from_html(fresh_active_html, include_featured=True)
        sold_props = extract_sold_properties_from_html(fresh_sold_html)

        active_ok = len(active_props) > 0
        sold_ok = len(sold_props) > 0

        # Check for link issues in sold properties
        link_issues = [p for p in sold_props if not isinstance(p.get('link', ''), str)]
        link_ok = len(link_issues) == 0

        report["steps"].append(f"  Active parser: {'✓' if active_ok else '✗'} ({len(active_props)} properties)")
        report["steps"].append(f"  Sold parser: {'✓' if sold_ok else '✗'} ({len(sold_props)} properties)")
        report["steps"].append(f"  Sold link field: {'✓ OK' if link_ok else f'✗ {len(link_issues)} properties have non-string link'}")

        # Step 4: Analyse sold structure for index mappings
        report["steps"].append("Step 4: Analysing current Rightmove sold listing structure...")
        pattern = r'window\.__reactRouterContext\.streamController\.enqueue\(\s*"(.+?)"\s*\)'
        matches = re.findall(pattern, fresh_sold_html)
        current_mappings = {}
        for match in matches:
            try:
                json_str = match.encode().decode('unicode_escape')
                data = json.loads(json_str)
                if isinstance(data, list) and len(data) > 100:
                    for j, item in enumerate(data):
                        if item == 'properties' and j + 1 < len(data):
                            prop_indices = data[j + 1]
                            if isinstance(prop_indices, list) and prop_indices:
                                prop_obj = data[prop_indices[0]]
                                for key, value in prop_obj.items():
                                    if isinstance(value, int) and value < len(data):
                                        actual = data[value]
                                        if isinstance(actual, str) and actual.startswith('http'):
                                            current_mappings[key] = 'url'
                                        elif isinstance(actual, (str, int)):
                                            current_mappings[key] = type(actual).__name__
                            break
                    break
            except Exception:
                continue
        report["steps"].append(f"  ✓ Detected {len(current_mappings)} property field mappings")

        # Step 5: Read current parser and apply fixes if needed
        parser_path = SHARED_DIR / 'rightmove_parsers.py'
        with open(parser_path, 'r') as f:
            parser_content = f.read()

        changes_needed = []
        if not link_ok:
            changes_needed.append("fix_link_field")

        # Always update last verified date
        today = datetime.utcnow().strftime('%Y-%m-%d')
        old_date_match = re.search(r'LAST_VERIFIED_DATE = "(\d{4}-\d{2}-\d{2})"', parser_content)
        old_date = old_date_match.group(1) if old_date_match else "unknown"
        old_version_match = re.search(r'PARSER_VERSION = "(\d+\.\d+\.\d+)"', parser_content)
        old_version = old_version_match.group(1) if old_version_match else "unknown"

        if old_date != today:
            changes_needed.append("update_date")

        report["steps"].append(f"Step 5: Current parser version: {old_version}, last verified: {old_date}")

        if changes_needed:
            report["steps"].append(f"  Changes needed: {changes_needed}")

            # Increment patch version
            parts = old_version.split('.')
            parts[-1] = str(int(parts[-1]) + 1)
            new_version = '.'.join(parts)

            new_content = parser_content

            # Fix version
            new_content = re.sub(
                r'PARSER_VERSION = "\d+\.\d+\.\d+"',
                f'PARSER_VERSION = "{new_version}"',
                new_content
            )

            # Fix date
            new_content = re.sub(
                r'LAST_VERIFIED_DATE = "\d{4}-\d{2}-\d{2}"',
                f'LAST_VERIFIED_DATE = "{today}"',
                new_content
            )

            # Fix sold structure version date
            new_content = re.sub(
                r"('sold_listings': ')[\d\-]+(.*?React Router)",
                f"\\g<1>{today}\\2",
                new_content
            )

            # Fix link field if needed
            if "fix_link_field" in changes_needed:
                # Ensure only _112 is used for link (not _114 which is map images)
                old_link_pattern = r"elif key in \('_102', '_112', '_114'\):.*?\n.*?property_info\['link'\] = actual_value"
                new_link_code = "elif key == '_112':  # Property link (updated: _112 is direct URL; _114 is map image dict)\n                    if isinstance(actual_value, str):\n                        property_info['link'] = actual_value"
                new_content_fixed = re.sub(old_link_pattern, new_link_code, new_content, flags=re.DOTALL)
                if new_content_fixed != new_content:
                    new_content = new_content_fixed
                    report["changes_made"].append(f"Fixed link field: now uses _112 only (string check added)")

            # Write updated parser
            with open(parser_path, 'w') as f:
                f.write(new_content)

            report["changes_made"].append(f"Updated parser version: {old_version} → {new_version}")
            report["changes_made"].append(f"Updated last verified date: {old_date} → {today}")
            report["steps"].append(f"  ✓ Parser updated to v{new_version}")
        else:
            report["steps"].append("  ✓ No changes needed - parser is up to date")

        # Step 6: Reload parser in memory
        report["steps"].append("Step 6: Reloading parser in memory...")
        reload_parser()
        new_info = get_parser_info()
        report["steps"].append(f"  ✓ Parser reloaded: v{new_info['parser_version']}")

        # Step 7: Upload to Google Drive
        report["steps"].append("Step 7: Uploading updated parser to Google Drive...")
        try:
            # Upload to RightmoveParsingModule
            r1 = subprocess.run(
                ['rclone', 'copy', str(parser_path),
                 f'manus_google_drive:DealFinder/Tools/RightmoveParsingModule/shared/',
                 '--config', RCLONE_CONFIG],
                capture_output=True, text=True, timeout=30
            )
            # Upload to IntegratedTools_v2
            r2 = subprocess.run(
                ['rclone', 'copy', str(parser_path),
                 f'manus_google_drive:DealFinder/Tools/IntegratedTools_v2/shared/',
                 '--config', RCLONE_CONFIG],
                capture_output=True, text=True, timeout=30
            )
            if r1.returncode == 0 and r2.returncode == 0:
                report["steps"].append("  ✓ Parser uploaded to Google Drive (both locations)")
                report["changes_made"].append("Uploaded updated parser to Google Drive")
            else:
                report["steps"].append(f"  ⚠ Upload warning: {r1.stderr or r2.stderr}")
        except Exception as e:
            report["steps"].append(f"  ⚠ Upload failed: {str(e)}")

        # Step 8: Run test suite to verify
        report["steps"].append("Step 8: Running test suite to verify fix...")
        test_result = subprocess.run(
            [sys.executable, str(TEST_DIR / 'test_parsing.py'), '--verbose'],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(TEST_DIR)
        )
        test_output = test_result.stdout + test_result.stderr
        passed = len(re.findall(r'  ✓ ', test_output))
        failed = len(re.findall(r'  ✗ ', test_output))
        skipped = len(re.findall(r'  ⊘ ', test_output))

        report["test_results"] = {
            "result": "PASSED" if test_result.returncode == 0 else "FAILED",
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total": passed + failed + skipped,
            "output": test_output
        }
        report["steps"].append(f"  {'✓' if test_result.returncode == 0 else '✗'} Tests: {passed} passed, {failed} failed, {skipped} skipped")

        report["status"] = "success"
        report["parser_info"] = get_parser_info()

        return report

    except requests.exceptions.RequestException as e:
        report["status"] = "error"
        report["error"] = f"Network error: {str(e)}"
        raise HTTPException(status_code=502, detail=report)
    except Exception as e:
        report["status"] = "error"
        report["error"] = str(e)
        raise HTTPException(status_code=500, detail=report)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
