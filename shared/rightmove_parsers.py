#!/usr/bin/env python3.11
"""
Rightmove Data Parsers - Isolated Parsing Module
=================================================

This module contains ALL Rightmove-specific JSON/HTML parsing logic.
When Rightmove changes their website structure, ONLY this file needs to be updated.

All other modules should use the standardized output from these functions.

Version: 2.0.0
Last Updated: 2026-02-12
Author: Manus AI
"""

import re
import json
from typing import Dict, List, Optional, Any


# ============================================================================
# VERSION TRACKING
# ============================================================================

PARSER_VERSION = "2.0.6"
LAST_VERIFIED_DATE = "2026-02-24"

# Track which Rightmove structure version this parser supports
RIGHTMOVE_STRUCTURE_VERSION = {
    'active_listings': '2026-02',  # __NEXT_DATA__ in script tag
    'sold_listings': '2026-02-24'  # React Router context (supports filtered & unfiltered pages)
}


# ============================================================================
# HELPER FUNCTIONS (Stable - not Rightmove-specific)
# ============================================================================

def extract_postcode(address: str) -> Optional[str]:
    """
    Extract UK postcode from address string.
    
    Pattern: 1-2 letters, 1-2 digits, optional letter, space, digit, 2 letters
    Example: "123 Main St, CV10 0BD" -> "CV10 0BD"
    
    Args:
        address: Full address string
        
    Returns:
        Postcode string or None if not found
    """
    pattern = r'([A-Z]{1,2}\d{1,2}[A-Z]?)\s+(\d[A-Z]{2})'
    match = re.search(pattern, address, re.IGNORECASE)
    if match:
        return f"{match.group(1)} {match.group(2)}".upper()
    return None


def clean_price(price_str: Any) -> Optional[int]:
    """
    Extract integer price from various formats.
    
    Handles: £123,456 | Â£123456 | 123456 | "£123,456"
    
    Args:
        price_str: Price in any format (str, int, or dict)
        
    Returns:
        Integer price or None if invalid
    """
    if isinstance(price_str, int):
        return price_str
    
    if isinstance(price_str, dict):
        # Sometimes price is in dict like {'amount': 123456}
        if 'amount' in price_str:
            return clean_price(price_str['amount'])
        if 'value' in price_str:
            return clean_price(price_str['value'])
        return None
    
    # Convert to string and remove all non-digit characters
    price_clean = re.sub(r'[^\d]', '', str(price_str))
    
    if price_clean:
        try:
            return int(price_clean)
        except ValueError:
            return None
    
    return None


def extract_bedrooms(bedroom_data: Any) -> Optional[int]:
    """
    Extract number of bedrooms from various formats.
    
    Handles: 3 | "3" | "3 bedrooms" | "3 bed"
    
    Args:
        bedroom_data: Bedroom info in any format
        
    Returns:
        Integer bedroom count or None if invalid
    """
    if isinstance(bedroom_data, int):
        return bedroom_data
    
    # Extract number from string
    match = re.search(r'(\d+)', str(bedroom_data))
    if match:
        return int(match.group(1))
    
    return None


# ============================================================================
# ACTIVE LISTINGS PARSERS (Rightmove-specific - may need updates)
# ============================================================================

def extract_json_from_active_listing_html(html: str) -> Optional[Dict]:
    """
    Extract JSON data from Rightmove active listing page HTML.
    
    **RIGHTMOVE-SPECIFIC:** This function depends on Rightmove's HTML structure.
    Current structure (2026-02): JSON in <script type="application/json"> tag
    
    Args:
        html: Full HTML content from Rightmove active listings page
        
    Returns:
        Parsed JSON dict or None if extraction fails
        
    Raises:
        None - returns None on any error
    """
    try:
        # Pattern to find <script type="application/json">...</script>
        pattern = r'<script[^>]*type="application/json"[^>]*>(.*?)</script>'
        matches = re.findall(pattern, html, re.DOTALL)
        
        if not matches:
            return None
        
        # Parse the first match (usually contains __NEXT_DATA__)
        data = json.loads(matches[0])
        return data
        
    except (json.JSONDecodeError, IndexError) as e:
        return None


def parse_active_search_results(json_data: Dict) -> Optional[Dict]:
    """
    Extract search results container from active listing JSON.
    
    **RIGHTMOVE-SPECIFIC:** Depends on JSON structure path.
    Current path (2026-02): data['props']['pageProps']['searchResults']
    
    Args:
        json_data: Parsed JSON from extract_json_from_active_listing_html()
        
    Returns:
        Search results dict containing 'properties' and 'pagination' keys
        Returns None if structure not found
    """
    try:
        # Navigate through the JSON structure
        search_results = json_data.get('props', {}).get('pageProps', {}).get('searchResults', {})
        
        if not search_results:
            return None
        
        return search_results
        
    except (AttributeError, TypeError):
        return None


def parse_active_property(prop_data: Dict) -> Optional[Dict]:
    """
    Parse a single active property from Rightmove JSON structure.
    
    **RIGHTMOVE-SPECIFIC:** Field names and structure may change.
    Current structure (2026-02):
    - price: dict with 'amount' key
    - displayAddress: string
    - propertySubType: string
    - bedrooms: int
    - propertyUrl: string
    - featuredProperty: bool
    
    Args:
        prop_data: Single property dict from search results
        
    Returns:
        Standardized property dict with keys:
        {
            'id': str,
            'price': int,
            'address': str,
            'postcode': str,
            'property_type': str,
            'bedrooms': int,
            'link': str,
            'is_featured': bool
        }
        Returns None if required fields are missing
    """
    try:
        # Extract price
        price_data = prop_data.get('price', {})
        price = clean_price(price_data)
        if not price:
            return None
        
        # Extract address
        address = prop_data.get('displayAddress', '').strip()
        if not address:
            return None
        
        # Extract postcode from address
        postcode = extract_postcode(address)
        if not postcode:
            return None
        
        # Extract property type
        property_type = prop_data.get('propertySubType', '').strip()
        if not property_type:
            return None
        
        # Extract bedrooms
        bedrooms = extract_bedrooms(prop_data.get('bedrooms'))
        if bedrooms is None:
            return None
        
        # Extract property URL
        property_url = prop_data.get('propertyUrl', '')
        if property_url and not property_url.startswith('http'):
            property_url = 'https://www.rightmove.co.uk' + property_url
        
        # Check if featured
        is_featured = prop_data.get('featuredProperty', False)
        
        # Get property ID
        prop_id = str(prop_data.get('id', ''))
        
        return {
            'id': prop_id,
            'price': price,
            'address': address,
            'postcode': postcode,
            'property_type': property_type,
            'bedrooms': bedrooms,
            'link': property_url,
            'is_featured': is_featured
        }
        
    except (AttributeError, TypeError, KeyError) as e:
        return None


def extract_active_properties_from_html(html: str, include_featured: bool = False) -> List[Dict]:
    """
    Complete pipeline: Extract all active properties from HTML.
    
    This is a convenience function that combines:
    1. JSON extraction
    2. Search results parsing
    3. Individual property parsing
    
    Args:
        html: Full HTML from Rightmove active listings page
        include_featured: Whether to include featured properties (default: False)
        
    Returns:
        List of standardized property dicts
    """
    # Step 1: Extract JSON from HTML
    json_data = extract_json_from_active_listing_html(html)
    if not json_data:
        return []
    
    # Step 2: Get search results
    search_results = parse_active_search_results(json_data)
    if not search_results:
        return []
    
    # Step 3: Parse individual properties
    properties_list = search_results.get('properties', [])
    parsed_properties = []
    
    for prop_data in properties_list:
        parsed = parse_active_property(prop_data)
        if parsed:
            # Filter featured properties if requested
            if not include_featured and parsed['is_featured']:
                continue
            parsed_properties.append(parsed)
    
    return parsed_properties


def extract_active_pagination_info(json_data: Dict) -> Dict:
    """
    Extract pagination information from active listing JSON.
    
    **RIGHTMOVE-SPECIFIC:** Pagination structure may change.
    
    Args:
        json_data: Parsed JSON from extract_json_from_active_listing_html()
        
    Returns:
        Dict with keys: 'total', 'current_page', 'results_per_page'
    """
    try:
        search_results = parse_active_search_results(json_data)
        if not search_results:
            return {'total': 0, 'current_page': 1, 'results_per_page': 24}
        
        pagination = search_results.get('pagination', {})
        
        return {
            'total': pagination.get('total', 0),
            'current_page': pagination.get('page', 1),
            'results_per_page': pagination.get('pageSize', 24)
        }
        
    except (AttributeError, TypeError):
        return {'total': 0, 'current_page': 1, 'results_per_page': 24}


# ============================================================================
# SOLD LISTINGS PARSERS (Rightmove-specific - may need updates)
# ============================================================================

def extract_json_from_sold_listing_html(html: str) -> List[Dict]:
    """
    Extract JSON data from Rightmove sold listing page HTML.
    
    **RIGHTMOVE-SPECIFIC:** This function depends on Rightmove's HTML structure.
    Current structure (2026-02): React Router context with enqueue() calls
    
    Args:
        html: Full HTML content from Rightmove sold listings page
        
    Returns:
        List of parsed JSON arrays (React Router context data chunks)
    """
    # Pattern to find React Router context data
    pattern = r'window\.__reactRouterContext\.streamController\.enqueue\(\s*"(.+?)"\s*\)'
    matches = re.findall(pattern, html)
    
    if not matches:
        return []
    
    parsed_chunks = []
    
    for match in matches:
        try:
            # Decode the JSON string (handles unicode escapes)
            json_str = match.encode().decode('unicode_escape')
            data = json.loads(json_str)
            
            if isinstance(data, list):
                parsed_chunks.append(data)
                
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    
    return parsed_chunks


def parse_sold_property_from_indexed_array(prop_obj: Dict, data_array: List) -> Optional[Dict]:
    """
    Parse a single sold property from Rightmove's indexed array structure.
    
    **RIGHTMOVE-SPECIFIC:** Index mappings may change frequently!
    Current mappings (2026-02-13):
    - _69: Property ID (updated)
    - _73: Address (updated)
    - _75: Property type (updated)
    - _77: Bedrooms (updated)
    - _90, _89, _80: Transactions list (updated)
    - _93, _83, _92, _95: Sold price (in transaction, updated)
    - _95, _85, _93, _94: Sold date (in transaction, updated)
    - _114: Property link (updated)
    
    Args:
        prop_obj: Property object dict with index keys
        data_array: Full data array to resolve indices
        
    Returns:
        Standardized sold property dict with keys:
        {
            'id': str,
            'postcode': str,
            'address': str,
            'property_type': str,
            'bedrooms': int,
            'sold_date': str,
            'sold_price': int,
            'link': str
        }
        Returns None if required fields are missing
    """
    try:
        property_info = {}
        
        # Decode indexed values
        for key, value in prop_obj.items():
            if isinstance(value, int) and value < len(data_array):
                actual_value = data_array[value]
                
                # Map keys to property fields
                # NOTE: These indices may change when Rightmove updates!
                if key == '_69':  # Property ID (updated 2026-02-13)
                    property_info['id'] = actual_value
                elif key == '_73':  # Address (updated 2026-02-13)
                    property_info['address'] = actual_value
                elif key == '_75':  # Property type (updated 2026-02-13)
                    property_info['property_type'] = actual_value
                elif key == '_77':  # Bedrooms (updated 2026-02-13)
                    property_info['bedrooms'] = actual_value
                elif key in ('_81', '_91', '_90', '_89', '_80'):  # Transactions list (updated 2026-02-19, _81 current)
                    # Handle both direct list and indexed list
                    trans_list = actual_value
                    if isinstance(actual_value, int) and actual_value < len(data_array):
                        trans_list = data_array[actual_value]  # Resolve index for filtered pages
                    
                    if isinstance(trans_list, list) and len(trans_list) > 0:
                        # Get first transaction
                        trans_idx = trans_list[0]
                        if trans_idx < len(data_array):
                            trans_obj = data_array[trans_idx]
                            if isinstance(trans_obj, dict):
                                # Decode transaction data
                                for t_key, t_value in trans_obj.items():
                                    if isinstance(t_value, int) and t_value < len(data_array):
                                        t_actual = data_array[t_value]
                                        # Try all known date keys (filtered pages use _96, unfiltered use _95)
                                        if t_key in ('_86', '_96', '_95', '_85'):  # Sold date (updated 2026-02-19, _86 current)
                                            property_info['sold_date'] = t_actual
                                        # Try all known price keys (filtered pages use _94, unfiltered use _93)
                                        elif t_key in ('_84', '_94', '_93', '_83', '_92'):  # Sold price (updated 2026-02-19, _84 current)
                                            property_info['sold_price'] = t_actual
                elif key == '_112':  # Property link (updated 2026-02-24: _112 is direct URL; _114 is map image dict)
                    if isinstance(actual_value, str):
                        property_info['link'] = actual_value
        
        # Validate required fields
        if 'address' not in property_info or 'sold_date' not in property_info:
            return None
        
        # Extract postcode from address
        postcode = extract_postcode(property_info['address'])
        
        # Clean property type
        property_type = property_info.get('property_type', '').replace('_', ' ').title()
        
        # Extract bedrooms
        bedrooms = extract_bedrooms(property_info.get('bedrooms', ''))
        
        # Clean price
        sold_price = clean_price(property_info.get('sold_price', ''))
        
        return {
            'id': str(property_info.get('id', '')),
            'postcode': postcode or '',
            'address': property_info['address'],
            'property_type': property_type,
            'bedrooms': bedrooms,
            'sold_date': property_info['sold_date'],
            'sold_price': sold_price,
            'link': property_info.get('link', '')
        }
        
    except (AttributeError, TypeError, KeyError, IndexError) as e:
        return None


def extract_sold_properties_from_data_chunks(data_chunks: List[List]) -> List[Dict]:
    """
    Extract all sold properties from React Router data chunks.
    
    Args:
        data_chunks: List of data arrays from extract_json_from_sold_listing_html()
        
    Returns:
        List of standardized sold property dicts
    """
    all_properties = []
    
    for data_array in data_chunks:
        # Find the 'properties' key which contains indices to property objects
        for i, item in enumerate(data_array):
            if item == 'properties' and i + 1 < len(data_array):
                property_indices = data_array[i + 1]
                if not isinstance(property_indices, list):
                    continue
                
                # Extract each property using its index
                for prop_idx in property_indices:
                    if prop_idx >= len(data_array):
                        continue
                    
                    prop_obj = data_array[prop_idx]
                    if not isinstance(prop_obj, dict):
                        continue
                    
                    # Parse the property
                    parsed = parse_sold_property_from_indexed_array(prop_obj, data_array)
                    if parsed:
                        all_properties.append(parsed)
                
                break  # Found properties in this chunk
    
    return all_properties


def extract_sold_properties_from_html(html: str) -> List[Dict]:
    """
    Complete pipeline: Extract all sold properties from HTML.
    
    This is a convenience function that combines:
    1. JSON extraction from React Router context
    2. Property parsing from indexed arrays
    
    Args:
        html: Full HTML from Rightmove sold listings page
        
    Returns:
        List of standardized sold property dicts
    """
    # Step 1: Extract JSON chunks from HTML
    data_chunks = extract_json_from_sold_listing_html(html)
    if not data_chunks:
        return []
    
    # Step 2: Parse properties from chunks
    properties = extract_sold_properties_from_data_chunks(data_chunks)
    
    return properties


def extract_sold_pagination_info(html: str) -> Dict:
    """
    Extract pagination information from sold listing HTML.
    
    **RIGHTMOVE-SPECIFIC:** Looks for "X results" text in HTML.
    
    Args:
        html: Full HTML from Rightmove sold listings page
        
    Returns:
        Dict with keys: 'total_results', 'has_next_page'
    """
    # Look for "X results" in the HTML
    results_match = re.search(r'(\d+)\s+results', html)
    total_results = int(results_match.group(1)) if results_match else 0
    
    # Check for next page indicators
    has_next_page = bool(
        re.search(r'pageNumber=\d+', html) or
        re.search(r'Page \d+', html)
    )
    
    return {
        'total_results': total_results,
        'has_next_page': has_next_page
    }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_parser_info() -> Dict:
    """
    Get information about this parser module.
    
    Returns:
        Dict with version, last verified date, and structure versions
    """
    return {
        'parser_version': PARSER_VERSION,
        'last_verified': LAST_VERIFIED_DATE,
        'rightmove_structure_versions': RIGHTMOVE_STRUCTURE_VERSION
    }


def validate_active_property(prop: Dict) -> bool:
    """
    Validate that a property dict has all required fields.
    
    Args:
        prop: Property dict to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['id', 'price', 'address', 'postcode', 'property_type', 'bedrooms', 'link']
    return all(field in prop and prop[field] for field in required_fields)


def validate_sold_property(prop: Dict) -> bool:
    """
    Validate that a sold property dict has all required fields.
    
    Args:
        prop: Sold property dict to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['address', 'sold_date']
    return all(field in prop and prop[field] for field in required_fields)


# ============================================================================
# TESTING SUPPORT
# ============================================================================

def test_parser_with_html(html: str, page_type: str) -> Dict:
    """
    Test parser with HTML content and return diagnostic information.
    
    Useful for debugging when Rightmove changes structure.
    
    Args:
        html: HTML content to test
        page_type: 'active' or 'sold'
        
    Returns:
        Dict with test results and diagnostic info
    """
    result = {
        'page_type': page_type,
        'parser_version': PARSER_VERSION,
        'success': False,
        'properties_found': 0,
        'errors': []
    }
    
    try:
        if page_type == 'active':
            properties = extract_active_properties_from_html(html, include_featured=True)
            result['properties_found'] = len(properties)
            result['success'] = len(properties) > 0
            result['sample_property'] = properties[0] if properties else None
            
        elif page_type == 'sold':
            properties = extract_sold_properties_from_html(html)
            result['properties_found'] = len(properties)
            result['success'] = len(properties) > 0
            result['sample_property'] = properties[0] if properties else None
            
        else:
            result['errors'].append(f"Invalid page_type: {page_type}")
            
    except Exception as e:
        result['errors'].append(str(e))
    
    return result


if __name__ == '__main__':
    # Print parser information
    info = get_parser_info()
    print("=" * 80)
    print("RIGHTMOVE PARSERS MODULE")
    print("=" * 80)
    print(f"Version: {info['parser_version']}")
    print(f"Last Verified: {info['last_verified']}")
    print(f"Active Listings Structure: {info['rightmove_structure_versions']['active_listings']}")
    print(f"Sold Listings Structure: {info['rightmove_structure_versions']['sold_listings']}")
    print("=" * 80)
    print("\nThis module contains isolated Rightmove parsing logic.")
    print("When Rightmove changes their structure, only update this file.")
    print("\nUse test_parsing.py to verify parsers are working correctly.")
    print("=" * 80)
