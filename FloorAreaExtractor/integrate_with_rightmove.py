#!/usr/bin/env python3.11
"""
Integration script to add floor area data to Rightmove extraction results
This script can be used as part of the automated workflow
"""

import argparse
import subprocess
import sys
import os

def integrate_floor_area(input_file, output_file=None, sheet_name='SoldProperties'):
    """
    Add floor area data to a Rightmove extraction result file
    
    Args:
        input_file: Path to the input Excel file
        output_file: Path to the output file (optional, defaults to adding _with_floor_area)
        sheet_name: Name of the sheet to process
    """
    if not output_file:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_with_floor_area{ext}"
    
    print(f"Adding floor area data to: {input_file}")
    print(f"Output will be saved to: {output_file}")
    print()
    
    # Call the extract_floor_area script
    cmd = [
        'python3.11',
        'extract_floor_area.py',
        '--input', input_file,
        '--output', output_file,
        '--sheet', sheet_name
    ]
    
    result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
    
    if result.returncode == 0:
        print()
        print("✓ Floor area data added successfully!")
        print(f"✓ Output file: {output_file}")
        return output_file
    else:
        print()
        print("✗ Error adding floor area data")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Add floor area data to Rightmove extraction results'
    )
    parser.add_argument('--input', required=True, help='Input Excel file from Rightmove extraction')
    parser.add_argument('--output', help='Output Excel file (optional)')
    parser.add_argument('--sheet', default='SoldProperties', help='Sheet name')
    
    args = parser.parse_args()
    
    integrate_floor_area(args.input, args.output, args.sheet)

if __name__ == '__main__':
    main()
