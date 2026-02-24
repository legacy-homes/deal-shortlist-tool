#!/usr/bin/env python3.11
"""
Automated Test Runner for Rightmove Parsers
============================================

This script runs the test suite and generates a detailed report.
Designed to be run regularly to detect Rightmove structure changes.

Usage:
    python3.11 test_runner.py
    python3.11 test_runner.py --json output.json
    python3.11 test_runner.py --quiet
"""

import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add test module to path
sys.path.insert(0, str(Path(__file__).parent))

from test_parsing import run_all_tests, get_parser_info


def run_tests_with_report(output_file=None, quiet=False):
    """
    Run tests and generate detailed report
    
    Args:
        output_file: Optional JSON file to save report
        quiet: If True, suppress verbose output
    
    Returns:
        Exit code (0 = all passed, 1 = some failed)
    """
    # Capture test output
    if quiet:
        # Redirect stdout to suppress output
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
    
    # Run tests
    exit_code = run_all_tests(test_filter=None, verbose=not quiet)
    
    if quiet:
        # Restore stdout
        sys.stdout = old_stdout
    
    # Generate report
    report = {
        'timestamp': datetime.now().isoformat(),
        'parser_info': get_parser_info(),
        'test_result': 'PASSED' if exit_code == 0 else 'FAILED',
        'exit_code': exit_code,
        'notes': []
    }
    
    # Add notes about known issues
    if exit_code != 0:
        report['notes'].append(
            "Some tests failed. This may indicate Rightmove has changed their website structure."
        )
        report['notes'].append(
            "Run 'python3.11 test_parsing.py --verbose' to see detailed failure information."
        )
        report['notes'].append(
            "Use the Manus prompt 'MANUS_FIX_PARSING.md' to automatically fix parsing issues."
        )
    
    # Save report if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n✓ Report saved to: {output_file}")
    
    # Print summary
    if not quiet:
        print("\n" + "=" * 80)
        print("TEST RUNNER SUMMARY")
        print("=" * 80)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Result: {report['test_result']}")
        print(f"Parser Version: {report['parser_info']['parser_version']}")
        print("=" * 80)
        
        if report['notes']:
            print("\nNOTES:")
            for note in report['notes']:
                print(f"  • {note}")
            print("=" * 80)
    
    return exit_code


def main():
    parser = argparse.ArgumentParser(
        description='Run Rightmove parser tests and generate report'
    )
    parser.add_argument(
        '--json', '-j',
        metavar='FILE',
        help='Save JSON report to file'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress verbose output'
    )
    
    args = parser.parse_args()
    
    exit_code = run_tests_with_report(
        output_file=args.json,
        quiet=args.quiet
    )
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
