# Manus Prompt: Fix Rightmove Parsing Issues

## Objective

Automatically detect and fix Rightmove parsing issues when their website structure changes.

## Instructions for Manus

Please perform the following steps to fix broken parsing modules:

### Step 1: Download Current Parser

Download the parsing module from Google Drive:
- Location: `DealFinder/Tools/RightmoveParsingModule/shared/rightmove_parsers.py`
- Download to `/home/ubuntu/rightmove_parsers.py`

### Step 2: Run Tests to Identify Failures

```bash
cd /home/ubuntu/test_suite
python3.11 test_parsing.py --verbose > test_output.txt
```

Analyze which specific tests are failing.

### Step 3: Fetch Fresh HTML from Rightmove

**For Active Listings (if tests failing):**

```bash
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier=REGION%5E904&propertyTypes=semi-detached&sortType=1&index=0" \
  -o /home/ubuntu/fresh_active.html
```

**For Sold Listings (if tests failing):**

```bash
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://www.rightmove.co.uk/house-prices/manchester.html?soldIn=2&radius=1.0" \
  -o /home/ubuntu/fresh_sold.html
```

### Step 4: Analyze Structure Changes

**For Active Listings:**

1. Extract JSON from fresh HTML:
   ```python
   import re, json
   with open('fresh_active.html', 'r') as f:
       html = f.read()
   
   pattern = r'<script[^>]*type="application/json"[^>]*>(.*?)</script>'
   matches = re.findall(pattern, html, re.DOTALL)
   data = json.loads(matches[0])
   
   # Check structure
   print("Top-level keys:", list(data.keys()))
   print("Props keys:", list(data.get('props', {}).keys()))
   print("PageProps keys:", list(data.get('props', {}).get('pageProps', {}).keys()))
   
   # Check property structure
   search_results = data.get('props', {}).get('pageProps', {}).get('searchResults', {})
   if search_results and 'properties' in search_results:
       prop = search_results['properties'][0]
       print("\nFirst property keys:", list(prop.keys()))
       print("Price structure:", prop.get('price'))
       print("Address field:", prop.get('displayAddress'))
       print("Property type field:", prop.get('propertySubType'))
   ```

2. Compare with old structure in test data
3. Document what changed

**For Sold Listings:**

1. Extract JSON from fresh HTML:
   ```python
   import re, json
   with open('fresh_sold.html', 'r') as f:
       html = f.read()
   
   pattern = r'window\.__reactRouterContext\.streamController\.enqueue\(\s*"(.+?)"\s*\)'
   matches = re.findall(pattern, html)
   
   for match in matches:
       json_str = match.encode().decode('unicode_escape')
       data = json.loads(json_str)
       
       # Find properties
       for i, item in enumerate(data):
           if item == 'properties':
               print(f"Found 'properties' at index {i}")
               if i + 1 < len(data):
                   prop_indices = data[i + 1]
                   print(f"Property indices: {prop_indices}")
                   
                   # Get first property
                   if prop_indices and prop_indices[0] < len(data):
                       prop_obj = data[prop_indices[0]]
                       print(f"Property object keys: {list(prop_obj.keys())}")
                       
                       # Try to decode values
                       for key, value in prop_obj.items():
                           if isinstance(value, int) and value < len(data):
                               print(f"  {key} -> {data[value][:50] if isinstance(data[value], str) else data[value]}")
   ```

2. Identify new index mappings
3. Document changes

### Step 5: Update Parser Code

Based on the structure analysis, update `rightmove_parsers.py`:

**For Active Listings:**

Update the `parse_active_property()` function if field names changed:
- Update price extraction if `price.amount` changed
- Update address field if `displayAddress` changed
- Update property type if `propertySubType` changed
- Update any other field mappings

**For Sold Listings:**

Update the `parse_sold_property_from_indexed_array()` function if indices changed:
- Update index mappings (e.g., `_72` -> new index)
- Update transaction indices
- Update price/date indices

### Step 6: Update Test Data

Update test data files with new structure:
- Save fresh property JSON to test data files
- Update expected outputs

### Step 7: Re-run Tests

```bash
cd /home/ubuntu/test_suite
python3.11 test_parsing.py --verbose
```

Verify all tests now pass.

### Step 8: Update Version Info

In `rightmove_parsers.py`, update:

```python
PARSER_VERSION = "2.0.1"  # Increment version
LAST_VERIFIED_DATE = "2026-02-XX"  # Update date

RIGHTMOVE_STRUCTURE_VERSION = {
    'active_listings': '2026-XX',  # Update if changed
    'sold_listings': '2026-XX'      # Update if changed
}
```

### Step 9: Upload Fixed Parser

Upload the updated parser to Google Drive:
- Upload `rightmove_parsers.py` to `DealFinder/Tools/RightmoveParsingModule/shared/`
- Upload updated test data to `DealFinder/Tools/RightmoveParsingModule/test_suite/test_data/`

### Step 10: Report Changes

Provide a detailed report:

1. **What changed:**
   - List specific field names or indices that changed
   - Show before/after comparison

2. **What was fixed:**
   - List functions updated
   - Show code changes made

3. **Test results:**
   - Report pass/fail status after fixes
   - Note any remaining issues

4. **Recommendations:**
   - Suggest testing with real tools
   - Recommend updating documentation if needed

## Example Usage

```
User: "The sold listing parser is broken. Please fix it."

Manus: [Follows steps above]

Manus: "I've fixed the sold listing parser. Here's what changed:

CHANGES DETECTED:
- Property address index changed: '_72' → '_82'
- Property type index changed: '_74' → '_84'  
- Transaction list index changed: '_80' → '_90'
- Sold price index changed: '_83' → '_93'

FIXES APPLIED:
- Updated parse_sold_property_from_indexed_array() with new indices
- Updated test data with fresh HTML sample
- Incremented parser version to 2.0.1

TEST RESULTS:
✓ All 24 tests now passing
✓ Sold listing parser working correctly

The fixed parser has been uploaded to Google Drive. You can now use 
the PropertyDealFinder and MedianPriceCalculator tools normally."
```

## Success Criteria

- All tests passing after fixes
- Parser version incremented
- Test data updated with current structure
- Fixed parser uploaded to Google Drive
- Clear documentation of changes made

## Notes

- This prompt assumes Rightmove made structural changes
- If tests pass, no fixes are needed
- Always test with real Rightmove URLs after fixing
- Keep old parser version as backup
