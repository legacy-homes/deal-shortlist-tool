#!/usr/bin/env python3.11
"""
Median Property Price Calculator - Enhanced Version with Progressive Search
============================================================================

This tool calculates the median sold price for properties with intelligent
progressive search strategy:

1. Start with "This area only" (radius=0) within last 2 years
2. If < 10 properties, expand radius: 0.25 → 0.5 → 1.0 miles
3. If still < 10 properties, expand time: 2 years → 3 years
4. Target: Minimum 10 properties for reliable median calculation

Filters supported:
- Postcode
- Property type (Semi-Detached, Terraced, Detached, Flat, etc.)
- Number of bedrooms
- Tenure (Freehold, Leasehold, or both)

Version: 3.0.0 (Progressive Search)
Author: Manus AI
Date: 2026-02-14

Changes from v2.0:
- Added progressive search strategy (radius + time expansion)
- Added tenure filter (FREEHOLD/LEASEHOLD)
- Added property type filter in URL
- Target minimum 10 properties for reliable median
- Better logging of search progression
"""

import sys
import os
import argparse
import json
import requests
import time
from statistics import median
from datetime import datetime

# Import shared parsing module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from rightmove_parsers import extract_sold_properties_from_html


def format_postcode_for_url(postcode):
    """Format postcode for URL (e.g., 'CV10 0BD' -> 'cv10-0bd')"""
    return postcode.lower().replace(' ', '-')


def normalize_property_type_for_url(property_type):
    """Convert property type to Rightmove URL format"""
    if not property_type:
        return None
    
    normalized = property_type.lower().replace('-', '').replace('_', '').replace(' ', '')
    
    # Map to Rightmove's URL format
    mappings = {
        'semidetached': 'SEMI_DETACHED',
        'semi': 'SEMI_DETACHED',
        'terraced': 'TERRACED',
        'terrace': 'TERRACED',
        'detached': 'DETACHED',
        'flat': 'FLAT',
        'bungalow': 'BUNGALOW'
    }
    
    return mappings.get(normalized, property_type.upper())


def fetch_properties_with_filters(postcode, property_type=None, tenure=None, radius=0, sold_in=2):
    """
    Fetch sold properties with specific filters.
    
    Args:
        postcode: UK postcode
        property_type: Property type (e.g., 'Semi-Detached')
        tenure: 'FREEHOLD', 'LEASEHOLD', or None for both
        radius: Search radius in miles (0 = this area only)
        sold_in: Time period in years (2 or 3)
    
    Returns:
        list: All properties found
    """
    all_properties = []
    seen_property_ids = set()  # Track unique properties to avoid duplicates
    
    # Format postcode for URL
    postcode_url = format_postcode_for_url(postcode)
    
    # Build base URL
    base_url = f"https://www.rightmove.co.uk/house-prices/{postcode_url}.html"
    
    # Add filters
    params = []
    params.append(f"soldIn={sold_in}")
    
    if radius > 0:
        params.append(f"radius={radius}")
    
    if property_type:
        prop_type_url = normalize_property_type_for_url(property_type)
        if prop_type_url:
            params.append(f"propertyType={prop_type_url}")
    
    if tenure and tenure.upper() in ['FREEHOLD', 'LEASEHOLD']:
        params.append(f"tenure={tenure.upper()}")
    
    if params:
        base_url += "?" + "&".join(params)
    
    # Setup session
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    page = 1
    max_pages = 5  # Limit to prevent excessive fetching
    while page <= max_pages:
        # Build URL with page number
        if page == 1:
            url = base_url
        else:
            separator = '&' if '?' in base_url else '?'
            url = f"{base_url}{separator}page={page}"
        
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            html = response.text
            
            # Use shared parser to extract properties
            properties = extract_sold_properties_from_html(html)
            
            # Filter out None values
            valid_properties = [p for p in properties if p is not None]
            
            if not valid_properties:
                break
            
            # Add only new properties (avoid duplicates)
            new_properties = 0
            for prop in valid_properties:
                # Create unique ID from address and sold date
                prop_id = f"{prop.get('address', '')}_{prop.get('sold_date', '')}_{prop.get('sold_price', '')}"
                if prop_id not in seen_property_ids:
                    seen_property_ids.add(prop_id)
                    all_properties.append(prop)
                    new_properties += 1
            
            # Stop if no new properties found (all were duplicates)
            if new_properties == 0:
                break
            
            # Check if there's a next page (simple heuristic)
            if len(valid_properties) < 20:
                break
            
            page += 1
            time.sleep(0.5)  # Be polite to the server
            
        except Exception as e:
            print(f"    Error fetching page {page}: {e}")
            break
    
    return all_properties


def normalize_property_type(property_type):
    """Normalize property type for comparison"""
    if not property_type:
        return ''
    
    # Remove hyphens, underscores, and spaces, then lowercase
    normalized = property_type.lower().replace('-', '').replace('_', '').replace(' ', '')
    
    # Map all variations to a canonical form
    mappings = {
        'semidetached': 'semidetached',
        'semi': 'semidetached',
        'terraced': 'terraced',
        'terrace': 'terraced',
        'detached': 'detached',
        'flat': 'flat',
        'bungalow': 'bungalow'
    }
    
    return mappings.get(normalized, normalized)


def _parse_sold_date(sold_date_str):
    """Parse a sold date string into a datetime. Returns None if unparseable."""
    if not sold_date_str:
        return None
    for fmt in ('%d %b %Y', '%d %B %Y', '%b %Y', '%B %Y'):
        try:
            return datetime.strptime(sold_date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _compute_relevance_score(radius_miles, sold_in_years, sold_date_str):
    """
    Compute a relevance score (0-100) for a comparable property.

    Scoring rationale:
    - A comparable sold yesterday within the same postcode area (radius=0)
      is maximally relevant (100).
    - Relevance decreases linearly with search radius (max penalty 40 pts
      across 0 → 1 mile) and with age (max penalty 40 pts across 0 → 3 years).
    - An additional 20 pts are awarded for being within the tightest time
      window (sold_in_years == 2), reflecting the preference for recent data.

    Formula:
        radius_penalty  = min(radius_miles / 1.0, 1.0) * 40
        age_penalty     = min(actual_age_years / sold_in_years, 1.0) * 40
        recency_bonus   = 20 if sold_in_years == 2 else 0
        score           = 100 - radius_penalty - age_penalty + recency_bonus
        (clamped to [0, 100])
    """
    # Radius penalty: 0 miles → 0 pts, 1 mile → 40 pts
    radius_penalty = min(radius_miles / 1.0, 1.0) * 40

    # Age penalty based on actual sold date vs the window used
    sold_dt = _parse_sold_date(sold_date_str)
    if sold_dt:
        age_years = (datetime.now() - sold_dt).days / 365.25
        # Normalise against the window that was used to fetch this comparable
        age_penalty = min(age_years / max(sold_in_years, 1), 1.0) * 40
    else:
        # Unknown date — assume worst case within the window
        age_penalty = 40

    # Recency bonus: data fetched within the tighter 2-year window is preferred
    recency_bonus = 20 if sold_in_years <= 2 else 0

    score = 100 - radius_penalty - age_penalty + recency_bonus
    return round(max(0.0, min(100.0, score)), 1)


def filter_and_calculate_median(all_properties, property_type, bedrooms, search_params=None):
    """
    Filter properties by type and bedrooms, then calculate median.

    Args:
        all_properties: Raw list of properties from Rightmove.
        property_type:  Target property type string.
        bedrooms:       Target bedroom count.
        search_params:  The attempt dict used to fetch these properties
                        (keys: radius, sold_in, label).  When supplied, each
                        matching comparable is tagged with:
                          - search_radius_miles
                          - sold_within_years
                          - relevance_score

    Returns:
        dict: {
            'median_price': int or None,
            'property_count': int,
            'properties': list of matching properties
        }
    """
    target_type = normalize_property_type(property_type)
    matching_properties = []

    import re

    radius_miles = search_params['radius'] if search_params else 0
    sold_in_years = search_params['sold_in'] if search_params else 2

    for prop in all_properties:
        prop_type = normalize_property_type(prop.get('property_type', ''))

        # Handle bedrooms
        prop_bedrooms_value = prop.get('bedrooms')
        if prop_bedrooms_value is None:
            continue

        if isinstance(prop_bedrooms_value, int):
            prop_bedrooms = prop_bedrooms_value
        else:
            match = re.search(r'(\d+)', str(prop_bedrooms_value))
            if match:
                prop_bedrooms = int(match.group(1))
            else:
                continue

        # Extract price
        sold_price = prop.get('sold_price')
        if sold_price is None:
            continue

        if isinstance(sold_price, int):
            price = sold_price
        else:
            price_clean = re.sub(r'[^\d]', '', str(sold_price))
            if price_clean:
                try:
                    price = int(price_clean)
                except:
                    continue
            else:
                continue

        # Match type and bedrooms
        if prop_type == target_type and prop_bedrooms == bedrooms:
            prop_copy = prop.copy()
            prop_copy['price'] = price
            prop_copy['sold_price'] = price
            # Tag with search context
            prop_copy['search_radius_miles'] = radius_miles
            prop_copy['sold_within_years'] = sold_in_years
            prop_copy['relevance_score'] = _compute_relevance_score(
                radius_miles, sold_in_years, prop.get('sold_date', '')
            )
            matching_properties.append(prop_copy)

    # Calculate median
    if matching_properties:
        prices = [prop['price'] for prop in matching_properties]
        median_price = int(median(prices))
    else:
        median_price = None

    return {
        'median_price': median_price,
        'property_count': len(matching_properties),
        'properties': matching_properties
    }


def calculate_median_price_progressive(postcode, property_type, bedrooms, tenure='FREEHOLD', min_properties=10):
    """
    Calculate median with progressive search strategy.
    
    Strategy:
    1. Start with radius=0 (this area only), soldIn=2 years
    2. If < min_properties, try radius: 0.25 → 0.5 → 1.0 miles
    3. If still < min_properties, expand time to 3 years with same radius progression
    
    Args:
        postcode: UK postcode
        property_type: Property type (e.g., 'Semi-Detached')
        bedrooms: Number of bedrooms
        tenure: 'FREEHOLD', 'LEASEHOLD', or None for both
        min_properties: Minimum target count (default: 10)
    
    Returns:
        dict: {
            'median_price': int or None,
            'property_count': int,
            'properties': list,
            'search_params': dict of final search parameters used
        }
    """
    print(f"\n{'='*80}")
    print(f"PROGRESSIVE SEARCH FOR MEDIAN PRICE")
    print(f"{'='*80}")
    print(f"Target: {postcode} | {bedrooms} bed {property_type} | {tenure or 'Any tenure'}")
    print(f"Goal: Find at least {min_properties} matching properties\n")
    
    # Define search progression
    search_attempts = [
        # Phase 1: Within 2 years, expanding radius
        {'radius': 0, 'sold_in': 2, 'label': 'This area only, last 2 years'},
        {'radius': 0.25, 'sold_in': 2, 'label': 'Quarter mile radius, last 2 years'},
        {'radius': 0.5, 'sold_in': 2, 'label': 'Half mile radius, last 2 years'},
        {'radius': 1.0, 'sold_in': 2, 'label': '1 mile radius, last 2 years'},
        
        # Phase 2: Within 3 years, expanding radius
        {'radius': 0, 'sold_in': 3, 'label': 'This area only, last 3 years'},
        {'radius': 0.25, 'sold_in': 3, 'label': 'Quarter mile radius, last 3 years'},
        {'radius': 0.5, 'sold_in': 3, 'label': 'Half mile radius, last 3 years'},
        {'radius': 1.0, 'sold_in': 3, 'label': '1 mile radius, last 3 years'},
    ]
    
    best_result = None
    
    for attempt in search_attempts:
        print(f"Trying: {attempt['label']}...")
        
        # Fetch properties with current parameters
        all_properties = fetch_properties_with_filters(
            postcode=postcode,
            property_type=property_type,
            tenure=tenure,
            radius=attempt['radius'],
            sold_in=attempt['sold_in']
        )
        
        print(f"  → Fetched {len(all_properties)} total properties from Rightmove")
        
        # Filter and calculate median (pass attempt so comparables are tagged)
        result = filter_and_calculate_median(all_properties, property_type, bedrooms, search_params=attempt)
        result['search_params'] = attempt.copy()
        
        print(f"  → Found {result['property_count']} matching properties ({bedrooms} bed {property_type})")
        
        # Update best result
        if result['property_count'] > 0:
            best_result = result
            
            # Check if we've met the target
            if result['property_count'] >= min_properties:
                print(f"  ✓ SUCCESS: Found {result['property_count']} properties (target: {min_properties})")
                print(f"  ✓ Median Price: £{result['median_price']:,}\n")
                break
            else:
                print(f"  ⚠ Only {result['property_count']} properties (target: {min_properties}), expanding search...\n")
        else:
            print(f"  ✗ No matching properties, expanding search...\n")
    
    # Return best result found
    if best_result:
        print(f"{'='*80}")
        print(f"FINAL RESULT")
        print(f"{'='*80}")
        print(f"Search params: {best_result['search_params']['label']}")
        print(f"Properties found: {best_result['property_count']}")
        print(f"Median price: £{best_result['median_price']:,}")
        print(f"{'='*80}\n")
    else:
        print(f"{'='*80}")
        print(f"NO MATCHING PROPERTIES FOUND")
        print(f"{'='*80}\n")
        best_result = {
            'median_price': None,
            'property_count': 0,
            'properties': [],
            'search_params': {'label': 'No results'}
        }
    
    return best_result


def format_price(price):
    """Format price with commas and pound sign"""
    if price is None:
        return 'N/A'
    return f'£{price:,}'


def main():
    parser = argparse.ArgumentParser(
        description='Calculate median sold price with progressive search (v3.0.0)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate median for 3-bed semi-detached freehold
  %(prog)s --postcode "M8 4ND" --type "Semi-Detached" --bedrooms 3 --tenure FREEHOLD
  
  # With custom minimum property count
  %(prog)s --postcode "M8 4ND" --type "Semi-Detached" --bedrooms 3 --min-properties 15
  
  # Save detailed results to JSON
  %(prog)s --postcode "M8 4ND" --type "Semi-Detached" --bedrooms 3 --output results.json

Progressive Search Strategy:
  1. Starts with "This area only" (radius=0) within last 2 years
  2. If < 10 properties, expands radius: 0.25 → 0.5 → 1.0 miles
  3. If still < 10 properties, expands time to 3 years
  4. Returns best result found
        """
    )
    
    parser.add_argument('--postcode', required=True, help='UK postcode (e.g., "M8 4ND")')
    parser.add_argument('--type', '--property-type', dest='property_type', required=True,
                        help='Property type (e.g., "Semi-Detached", "Terraced")')
    parser.add_argument('--bedrooms', type=int, required=True, help='Number of bedrooms')
    parser.add_argument('--tenure', choices=['FREEHOLD', 'LEASEHOLD', 'ANY'], default='FREEHOLD',
                        help='Tenure type (default: FREEHOLD)')
    parser.add_argument('--min-properties', type=int, default=10,
                        help='Minimum target property count (default: 10)')
    parser.add_argument('--output', '-o', help='Output JSON file for detailed results')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed property list')
    
    args = parser.parse_args()
    
    # Convert tenure
    tenure = None if args.tenure == 'ANY' else args.tenure
    
    # Calculate median price with progressive search
    result = calculate_median_price_progressive(
        postcode=args.postcode,
        property_type=args.property_type,
        bedrooms=args.bedrooms,
        tenure=tenure,
        min_properties=args.min_properties
    )
    
    # Show detailed list if verbose
    if args.verbose and result['properties']:
        print("\nMatching Properties:")
        print("-" * 80)
        for i, prop in enumerate(result['properties'], 1):
            print(f"{i}. {prop.get('address', 'N/A')}")
            print(f"   Price: {format_price(prop['price'])} | Sold: {prop.get('sold_date', 'N/A')}")
        print("=" * 80)
    
    # Save to JSON if requested
    if args.output:
        output_data = {
            'query': {
                'postcode': args.postcode,
                'property_type': args.property_type,
                'bedrooms': args.bedrooms,
                'tenure': tenure,
                'min_properties': args.min_properties,
                'timestamp': datetime.now().isoformat()
            },
            'results': {
                'median_price': result['median_price'],
                'property_count': result['property_count'],
                'search_params': result['search_params'],
                'properties': result['properties']
            }
        }
        
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n✓ Detailed results saved to: {args.output}")
    
    # Return appropriate exit code
    sys.exit(0 if result['median_price'] is not None else 1)


if __name__ == '__main__':
    main()
