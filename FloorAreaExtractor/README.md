# EPC Floor Area Extraction Tool

## Overview

This tool extracts total floor area data from the UK Energy Performance Certificate (EPC) database for property addresses and adds the information to Excel spreadsheets.

## What It Does

The tool takes an Excel file containing property addresses and:
1. Searches the UK EPC database for each address
2. Matches the address to available Energy Performance Certificates
3. Extracts the "Total floor area" in square metres
4. Adds two new columns to the spreadsheet:
   - **Total Floor Area (sq m)**: The floor area value or -1 if not available
   - **Floor Area Availability**: "Available" or "NotAvailable"

## Requirements

**Python Version**: 3.11 or higher

**Dependencies**:
```bash
pip3 install beautifulsoup4 openpyxl requests
```

## Usage

### Basic Usage

```bash
python3.11 extract_floor_area.py --input input_file.xlsx --output output_file.xlsx
```

### With Custom Column Names

```bash
python3.11 extract_floor_area.py \
  --input input_file.xlsx \
  --output output_file.xlsx \
  --address-column "Full Address" \
  --floor-area-column "Total Floor Area (sq m)" \
  --availability-column "Floor Area Availability"
```

### With Custom Sheet Name

```bash
python3.11 extract_floor_area.py \
  --input input_file.xlsx \
  --output output_file.xlsx \
  --sheet "SoldProperties"
```

### Test Single Address

```bash
python3.11 extract_floor_area.py --test-address "1, Westfield Close, NUNEATON, CV10 0BD"
```

## Command-Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--input` | Yes* | - | Input Excel file path |
| `--output` | Yes* | - | Output Excel file path |
| `--sheet` | No | SoldProperties | Sheet name to process |
| `--address-column` | No | Full Address | Column containing addresses |
| `--floor-area-column` | No | Total Floor Area (sq m) | Column name for floor area |
| `--availability-column` | No | Floor Area Availability | Column name for availability status |
| `--test-address` | No | - | Test with a single address |

*Not required when using `--test-address`

## Input File Format

The input Excel file should contain a sheet with at least one column containing full property addresses.

**Example**:

| Postal Code | Full Address | Property Type |
|-------------|--------------|---------------|
| CV10 0BD | 1, Westfield Close, NUNEATON, CV10 0BD | Semi Detached |
| CV10 0DE | 29, Queensway, Nuneaton CV10 0DE | Semi Detached |

## Output File Format

The tool adds two new columns to the existing data:

| ... | Full Address | ... | Total Floor Area (sq m) | Floor Area Availability |
|-----|--------------|-----|-------------------------|-------------------------|
| ... | 1, Westfield Close, NUNEATON, CV10 0BD | ... | 119 | Available |
| ... | 29, Queensway, Nuneaton CV10 0DE | ... | 118 | Available |
| ... | 999, Fake Street, London SW1A 1AA | ... | -1 | NotAvailable |

## How It Works

The tool follows this workflow for each address:

1. **Extract Postcode**: Identifies the UK postcode from the address
2. **Search EPC Database**: Queries the government EPC database for that postcode
3. **Match Address**: Uses fuzzy matching to find the exact property
   - Requires exact house number match
   - Uses 85% similarity threshold for the rest of the address
4. **Extract Floor Area**: Retrieves the "Total floor area" from the EPC certificate
5. **Update Spreadsheet**: Adds the floor area and availability status

## Address Matching

The tool uses intelligent address matching:

**House Number Matching**: The house number MUST match exactly (e.g., "29" will only match "29", not "2" or "290")

**Fuzzy Matching**: The rest of the address uses fuzzy matching to handle variations in formatting, such as comma placement, spacing, and capitalization.

**Similarity Threshold**: Addresses must be at least 85% similar to be considered a match.

**Examples of Successful Matches**:
- "1, Westfield Close, NUNEATON, CV10 0BD" ↔ "1 Westfield Close, Nuneaton CV10 0BD"
- "29, Queensway, Nuneaton CV10 0DE" ↔ "29 Queensway, NUNEATON, CV10 0DE"

## Data Availability

The tool sets `Floor Area Availability` to **"NotAvailable"** and floor area to **-1** in these cases:

- No postcode found in the address
- No EPCs exist for the postcode
- No matching address found in the EPC database
- Address match similarity is below 85%
- Floor area information is missing from the EPC certificate

## Performance

**Processing Speed**: Approximately 2-3 seconds per address (includes 2-second delay between requests to be polite to the server)

**Example**: 100 addresses would take approximately 3-5 minutes

## Error Handling

The tool handles various error scenarios gracefully:

- **Network Errors**: Logs error and continues with next address
- **Missing Data**: Sets floor area to -1 and availability to "NotAvailable"
- **Invalid Addresses**: Attempts to extract postcode; if fails, marks as NotAvailable
- **Expired EPCs**: Still extracts floor area if available

## Examples

### Example 1: Process Property Data

```bash
python3.11 extract_floor_area.py \
  --input rightmove_properties.xlsx \
  --output rightmove_properties_with_floor_area.xlsx
```

### Example 2: Test Before Processing

```bash
# Test a single address first
python3.11 extract_floor_area.py --test-address "29, Queensway, Nuneaton CV10 0DE"

# If successful, process the full file
python3.11 extract_floor_area.py \
  --input properties.xlsx \
  --output properties_with_floor_area.xlsx
```

### Example 3: Custom Sheet and Columns

```bash
python3.11 extract_floor_area.py \
  --input data.xlsx \
  --output data_with_floor_area.xlsx \
  --sheet "PropertyData" \
  --address-column "Address" \
  --floor-area-column "Floor Area" \
  --availability-column "Data Available"
```

## Integration with Existing Workflows

### With Rightmove Property Extraction

After extracting property data from Rightmove:

```bash
# Step 1: Extract property data
python3.11 extract_rightmove_data.py --postcodes "CV10 0BD" --output-excel properties.xlsx

# Step 2: Add floor area data
python3.11 extract_floor_area.py --input properties.xlsx --output properties_with_floor_area.xlsx
```

### With Batch Processing

```bash
# Process multiple postcodes and add floor areas
python3.11 batch_process_postcodes.py --input-json postcodes.json

# Then add floor areas to each result file
for file in exact_avg_data_*.xlsx; do
    python3.11 extract_floor_area.py --input "$file" --output "${file%.xlsx}_with_floor_area.xlsx"
done
```

## Troubleshooting

### Issue: "No postcode found in address"

**Solution**: Ensure addresses include UK postcodes in standard format (e.g., "CV10 0BD")

### Issue: "No EPCs found for postcode"

**Possible Reasons**:
- The postcode has no registered EPCs
- The property is new and hasn't been assessed yet
- The postcode is incorrect

### Issue: "No matching address found"

**Possible Reasons**:
- The exact address doesn't have an EPC certificate
- The address format differs significantly from the EPC database
- Try checking the EPC website manually to verify

### Issue: Low Match Rate

**Solutions**:
- Verify address formatting is consistent
- Check if properties are newly built (may not have EPCs yet)
- Consider that not all properties have EPCs (especially older properties)

## Data Source

This tool uses the official UK Government Energy Performance Certificate database:
- Website: https://find-energy-certificate.service.gov.uk/
- Data: HM Land Registry and Department for Energy Security and Net Zero

## Limitations

- Only works for properties in England, Wales, and Northern Ireland
- Requires properties to have an Energy Performance Certificate
- Depends on the availability and accuracy of the EPC database
- Rate limited to 2-3 seconds per request to avoid overloading the server

## Notes

- The tool automatically adds a 2-second delay between requests to be respectful to the government server
- Floor areas are in square metres as per UK EPC standard
- Some properties may have multiple EPCs; the tool uses the most recent valid one
- Expired EPCs are still used if they contain floor area information

## Version

**Version**: 1.0  
**Date**: February 2026  
**Status**: Production Ready
