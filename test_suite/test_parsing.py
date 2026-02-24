#!/usr/bin/env python3.11
"""
Rightmove Parsers Test Suite
=============================

This test suite validates that the Rightmove parsing modules are working correctly.
Run this regularly to detect when Rightmove changes their website structure.

Usage:
    python3.11 test_parsing.py
    python3.11 test_parsing.py --verbose
    python3.11 test_parsing.py --test active_only
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'shared'))

from rightmove_parsers import (
    # Active listing functions
    extract_json_from_active_listing_html,
    parse_active_search_results,
    parse_active_property,
    extract_active_properties_from_html,
    extract_active_pagination_info,
    # Sold listing functions
    extract_json_from_sold_listing_html,
    extract_sold_properties_from_html,
    # Helper functions
    extract_postcode,
    clean_price,
    extract_bedrooms,
    # Validation
    validate_active_property,
    validate_sold_property,
    get_parser_info
)


class TestResult:
    """Store test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures = []
    
    def add_pass(self, test_name):
        self.passed += 1
        print(f"  ✓ {test_name}")
    
    def add_fail(self, test_name, error):
        self.failed += 1
        self.failures.append((test_name, error))
        print(f"  ✗ {test_name}: {error}")
    
    def add_skip(self, test_name, reason):
        self.skipped += 1
        print(f"  ⊘ {test_name} (skipped: {reason})")
    
    def print_summary(self):
        total = self.passed + self.failed + self.skipped
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {total}")
        print(f"Passed:      {self.passed} ✓")
        print(f"Failed:      {self.failed} ✗")
        print(f"Skipped:     {self.skipped} ⊘")
        print("=" * 80)
        
        if self.failures:
            print("\nFAILURES:")
            print("-" * 80)
            for test_name, error in self.failures:
                print(f"  {test_name}:")
                print(f"    {error}")
            print("=" * 80)
        
        return self.failed == 0


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

def test_extract_postcode(results, verbose=False):
    """Test postcode extraction from addresses"""
    print("\nTesting: extract_postcode()")
    
    test_cases = [
        ("123 Main St, CV10 0BD", "CV10 0BD"),
        ("15 Himley Street, Dudley, DY1 2BD", "DY1 2BD"),
        ("Flat 5, Building Name, M5 4UB", "M5 4UB"),
        ("Property without postcode", None),
    ]
    
    for address, expected in test_cases:
        result = extract_postcode(address)
        if result == expected:
            results.add_pass(f"extract_postcode('{address[:30]}...')")
        else:
            results.add_fail(
                f"extract_postcode('{address[:30]}...')",
                f"Expected {expected}, got {result}"
            )


def test_clean_price(results, verbose=False):
    """Test price cleaning from various formats"""
    print("\nTesting: clean_price()")
    
    test_cases = [
        (123456, 123456),
        ("£123,456", 123456),
        ("Â£123456", 123456),
        ("123456", 123456),
        ({'amount': 123456}, 123456),
        ({'value': 123456}, 123456),
        ("invalid", None),
    ]
    
    for price_input, expected in test_cases:
        result = clean_price(price_input)
        if result == expected:
            results.add_pass(f"clean_price({repr(price_input)})")
        else:
            results.add_fail(
                f"clean_price({repr(price_input)})",
                f"Expected {expected}, got {result}"
            )


def test_extract_bedrooms(results, verbose=False):
    """Test bedroom extraction from various formats"""
    print("\nTesting: extract_bedrooms()")
    
    test_cases = [
        (3, 3),
        ("3", 3),
        ("3 bedrooms", 3),
        ("3 bed", 3),
        ("invalid", None),
    ]
    
    for bedroom_input, expected in test_cases:
        result = extract_bedrooms(bedroom_input)
        if result == expected:
            results.add_pass(f"extract_bedrooms({repr(bedroom_input)})")
        else:
            results.add_fail(
                f"extract_bedrooms({repr(bedroom_input)})",
                f"Expected {expected}, got {result}"
            )


# ============================================================================
# ACTIVE LISTING TESTS
# ============================================================================

def test_extract_json_from_active_html(results, verbose=False):
    """Test JSON extraction from active listing HTML"""
    print("\nTesting: extract_json_from_active_listing_html()")
    
    # Test with real HTML file
    html_file = Path(__file__).parent / 'test_data/active_listings/2026-02-12_full_page.html'
    
    if not html_file.exists():
        results.add_skip("extract_json_from_active_html", "Test HTML file not found")
        return
    
    with open(html_file, 'r') as f:
        html = f.read()
    
    json_data = extract_json_from_active_listing_html(html)
    
    if json_data is None:
        results.add_fail("extract_json_from_active_html", "Failed to extract JSON from HTML")
        return
    
    if not isinstance(json_data, dict):
        results.add_fail("extract_json_from_active_html", f"Expected dict, got {type(json_data)}")
        return
    
    results.add_pass("extract_json_from_active_html (extraction)")
    
    if verbose:
        print(f"    JSON keys: {list(json_data.keys())}")


def test_parse_active_search_results(results, verbose=False):
    """Test parsing search results from active listing JSON"""
    print("\nTesting: parse_active_search_results()")
    
    html_file = Path(__file__).parent / 'test_data/active_listings/2026-02-12_full_page.html'
    
    if not html_file.exists():
        results.add_skip("parse_active_search_results", "Test HTML file not found")
        return
    
    with open(html_file, 'r') as f:
        html = f.read()
    
    json_data = extract_json_from_active_listing_html(html)
    if not json_data:
        results.add_skip("parse_active_search_results", "Could not extract JSON")
        return
    
    search_results = parse_active_search_results(json_data)
    
    if search_results is None:
        results.add_fail("parse_active_search_results", "Failed to parse search results")
        return
    
    if 'properties' not in search_results:
        results.add_fail("parse_active_search_results", "No 'properties' key in results")
        return
    
    results.add_pass("parse_active_search_results (structure)")
    
    if verbose:
        print(f"    Found {len(search_results.get('properties', []))} properties")


def test_parse_active_property_standard(results, verbose=False):
    """Test parsing a standard active property"""
    print("\nTesting: parse_active_property() - standard")
    
    json_file = Path(__file__).parent / 'test_data/active_listings/single_property_standard.json'
    
    if not json_file.exists():
        results.add_skip("parse_active_property_standard", "Test JSON file not found")
        return
    
    with open(json_file, 'r') as f:
        prop_data = json.load(f)
    
    parsed = parse_active_property(prop_data)
    
    if parsed is None:
        results.add_fail("parse_active_property_standard", "Failed to parse property")
        return
    
    # Check required fields
    required_fields = ['id', 'price', 'address', 'postcode', 'property_type', 'bedrooms', 'link']
    missing_fields = [f for f in required_fields if f not in parsed or not parsed[f]]
    
    if missing_fields:
        results.add_fail("parse_active_property_standard", f"Missing fields: {missing_fields}")
        return
    
    # Validate types
    if not isinstance(parsed['price'], int):
        results.add_fail("parse_active_property_standard", f"Price should be int, got {type(parsed['price'])}")
        return
    
    if not isinstance(parsed['bedrooms'], int):
        results.add_fail("parse_active_property_standard", f"Bedrooms should be int, got {type(parsed['bedrooms'])}")
        return
    
    results.add_pass("parse_active_property_standard (all fields)")
    
    if verbose:
        print(f"    Parsed: {parsed['address'][:50]}")
        print(f"    Price: £{parsed['price']:,}, Bedrooms: {parsed['bedrooms']}")


def test_parse_active_property_featured(results, verbose=False):
    """Test parsing a featured active property"""
    print("\nTesting: parse_active_property() - featured")
    
    json_file = Path(__file__).parent / 'test_data/active_listings/single_property_featured.json'
    
    if not json_file.exists():
        results.add_skip("parse_active_property_featured", "Test JSON file not found")
        return
    
    with open(json_file, 'r') as f:
        prop_data = json.load(f)
    
    parsed = parse_active_property(prop_data)
    
    if parsed is None:
        results.add_fail("parse_active_property_featured", "Failed to parse featured property")
        return
    
    if not parsed.get('is_featured', False):
        results.add_fail("parse_active_property_featured", "Featured flag not set correctly")
        return
    
    results.add_pass("parse_active_property_featured (featured flag)")


def test_extract_active_properties_full_pipeline(results, verbose=False):
    """Test full pipeline: HTML -> parsed properties"""
    print("\nTesting: extract_active_properties_from_html() - full pipeline")
    
    html_file = Path(__file__).parent / 'test_data/active_listings/2026-02-12_full_page.html'
    
    if not html_file.exists():
        results.add_skip("extract_active_properties_full", "Test HTML file not found")
        return
    
    with open(html_file, 'r') as f:
        html = f.read()
    
    # Test without featured
    properties = extract_active_properties_from_html(html, include_featured=False)
    
    if not properties:
        results.add_fail("extract_active_properties_full", "No properties extracted")
        return
    
    # Validate first property
    if not validate_active_property(properties[0]):
        results.add_fail("extract_active_properties_full", "First property failed validation")
        return
    
    results.add_pass(f"extract_active_properties_full ({len(properties)} properties)")
    
    # Test with featured
    properties_with_featured = extract_active_properties_from_html(html, include_featured=True)
    
    if len(properties_with_featured) <= len(properties):
        results.add_fail("extract_active_properties_full_featured", "Featured filter not working")
    else:
        results.add_pass(f"extract_active_properties_full_featured ({len(properties_with_featured)} total)")
    
    if verbose:
        print(f"    Non-featured: {len(properties)}")
        print(f"    With featured: {len(properties_with_featured)}")
        print(f"    Sample: {properties[0]['address'][:50]}")


def test_extract_active_pagination(results, verbose=False):
    """Test pagination info extraction"""
    print("\nTesting: extract_active_pagination_info()")
    
    html_file = Path(__file__).parent / 'test_data/active_listings/2026-02-12_full_page.html'
    
    if not html_file.exists():
        results.add_skip("extract_active_pagination", "Test HTML file not found")
        return
    
    with open(html_file, 'r') as f:
        html = f.read()
    
    json_data = extract_json_from_active_listing_html(html)
    if not json_data:
        results.add_skip("extract_active_pagination", "Could not extract JSON")
        return
    
    pagination = extract_active_pagination_info(json_data)
    
    if 'total' not in pagination:
        results.add_fail("extract_active_pagination", "No 'total' in pagination info")
        return
    
    results.add_pass("extract_active_pagination (structure)")
    
    if verbose:
        print(f"    Total results: {pagination['total']}")
        print(f"    Results per page: {pagination['results_per_page']}")


# ============================================================================
# SOLD LISTING TESTS
# ============================================================================

def test_extract_sold_properties(results, verbose=False):
    """Test sold property extraction (may fail if structure changed)"""
    print("\nTesting: extract_sold_properties_from_html()")
    
    html_file = Path(__file__).parent / 'test_data/sold_listings/2026-02-13_fresh.html'
    
    if not html_file.exists():
        results.add_skip("extract_sold_properties", "Test HTML file not found")
        return
    
    with open(html_file, 'r') as f:
        html = f.read()
    
    properties = extract_sold_properties_from_html(html)
    
    if not properties:
        # This is expected if Rightmove changed structure
        results.add_fail(
            "extract_sold_properties",
            "No properties extracted - Rightmove structure may have changed"
        )
        return
    
    # Validate first property
    if not validate_sold_property(properties[0]):
        results.add_fail("extract_sold_properties", "First property failed validation")
        return
    
    results.add_pass(f"extract_sold_properties ({len(properties)} properties)")
    
    if verbose:
        print(f"    Sample: {properties[0]['address'][:50]}")
        print(f"    Sold: {properties[0]['sold_date']} for £{properties[0].get('sold_price', 'N/A')}")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests(test_filter=None, verbose=False):
    """Run all tests"""
    results = TestResult()
    
    # Print parser info
    info = get_parser_info()
    print("=" * 80)
    print("RIGHTMOVE PARSERS TEST SUITE")
    print("=" * 80)
    print(f"Parser Version: {info['parser_version']}")
    print(f"Last Verified: {info['last_verified']}")
    print(f"Active Structure: {info['rightmove_structure_versions']['active_listings']}")
    print(f"Sold Structure: {info['rightmove_structure_versions']['sold_listings']}")
    print("=" * 80)
    
    # Define test groups
    helper_tests = [
        test_extract_postcode,
        test_clean_price,
        test_extract_bedrooms,
    ]
    
    active_tests = [
        test_extract_json_from_active_html,
        test_parse_active_search_results,
        test_parse_active_property_standard,
        test_parse_active_property_featured,
        test_extract_active_properties_full_pipeline,
        test_extract_active_pagination,
    ]
    
    sold_tests = [
        test_extract_sold_properties,
    ]
    
    # Run tests based on filter
    if test_filter is None or test_filter == 'helpers':
        print("\n" + "=" * 80)
        print("HELPER FUNCTION TESTS")
        print("=" * 80)
        for test_func in helper_tests:
            test_func(results, verbose)
    
    if test_filter is None or test_filter == 'active':
        print("\n" + "=" * 80)
        print("ACTIVE LISTING TESTS")
        print("=" * 80)
        for test_func in active_tests:
            test_func(results, verbose)
    
    if test_filter is None or test_filter == 'sold':
        print("\n" + "=" * 80)
        print("SOLD LISTING TESTS")
        print("=" * 80)
        for test_func in sold_tests:
            test_func(results, verbose)
    
    # Print summary
    success = results.print_summary()
    
    return 0 if success else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test Rightmove parsing modules')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--test', choices=['helpers', 'active', 'sold'], help='Run specific test group')
    
    args = parser.parse_args()
    
    exit_code = run_all_tests(test_filter=args.test, verbose=args.verbose)
    sys.exit(exit_code)
