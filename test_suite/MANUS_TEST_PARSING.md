# Manus Prompt: Test Rightmove Parsing Modules

## Objective

Test if the Rightmove parsing modules are working correctly and detect if Rightmove has changed
their website structure. This includes verifying that the **property link field** is correctly
populated for all sold property comparables.

## Instructions for Manus

Please perform the following steps:

### Step 1: Download Test Suite

Download the test suite from Google Drive:
- Location: `DealFinder/Tools/RightmoveParsingModule/test_suite/`
- Download all files to `/home/ubuntu/test_suite/`

### Step 2: Run Tests

Execute the full test suite with verbose output:

```bash
cd /home/ubuntu/test_suite
python3.11 test_parsing.py --verbose
```

### Step 3: Analyze Results

The test suite runs **27 tests** across four groups:

| Group | Tests | What is checked |
|---|---|---|
| Helper functions | 15 | `extract_postcode`, `clean_price`, `extract_bedrooms` |
| Active listing | 8 | JSON extraction, property parsing, pagination, featured filter |
| Sold listing — core | 1 | `extract_sold_properties_from_html` returns properties |
| Sold listing — links | 3 | Link populated, correct format, live HTTP check |

**The three link tests are:**

1. `sold_property_link_populated` — every sold property must have a non-empty `link` field.
   If this fails, the link key has shifted in Rightmove's indexed array structure.

2. `sold_property_link_format` — every non-empty link must start with
   `https://www.rightmove.co.uk/house-prices/details/`.
   If this fails, Rightmove may have changed their URL pattern.

3. `sold_property_link_live` — at least one link must return HTTP 200 or 404 from Rightmove.
   HTTP 200 = listing still active. HTTP 404 = listing removed but URL format is correct.
   If this fails, the URL structure itself may have changed.

### Step 4: Report Findings

Report which tests passed and which failed:

1. **If all 27 tests passed:**
   - Report: "✓ All 27 parsing tests passed. Rightmove structure is unchanged, links are working."
   - No further action needed.

2. **If active listing tests failed:**
   - Report: "✗ Active listing parsing tests failed."
   - Proceed to Step 5 for active listings.

3. **If sold listing core test failed:**
   - Report: "✗ Sold listing extraction failed — Rightmove structure may have changed."
   - Proceed to Step 5 for sold listings.

4. **If sold listing link tests failed:**
   - Report: "✗ Sold property link field issue detected."
   - Distinguish between:
     - `sold_property_link_populated` failure → link key has shifted (most common)
     - `sold_property_link_format` failure → URL pattern has changed
     - `sold_property_link_live` failure → URL is unreachable or format is wrong
   - Proceed to Step 5 for link investigation.

### Step 5: Investigate Failures (if any)

**For link field failures specifically:**

Fetch fresh sold listing HTML from **two different radius variants** (the link key shifts
between page variants):

```bash
# 1 mile radius (unfiltered)
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://www.rightmove.co.uk/house-prices/manchester.html?soldIn=2&radius=1.0" \
  -o /home/ubuntu/fresh_sold_1mi.html

# 0.25 mile radius (filtered — different key indices)
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://www.rightmove.co.uk/house-prices/cv6-6ed.html?soldIn=2&radius=0.25&propertyType=TERRACED&tenure=FREEHOLD" \
  -o /home/ubuntu/fresh_sold_025mi.html
```

Then scan for the link key in both:

```python
import re, json

def find_link_key(html_path):
    with open(html_path, 'r') as f:
        html = f.read()
    
    pattern = r'window\.__reactRouterContext\.streamController\.enqueue\(\s*"(.+?)"\s*\)'
    matches = re.findall(pattern, html)
    
    for match in matches:
        json_str = match.encode().decode('unicode_escape')
        data = json.loads(json_str)
        
        for i, item in enumerate(data):
            if item == 'properties' and i + 1 < len(data):
                prop_indices = data[i + 1]
                if not isinstance(prop_indices, list) or not prop_indices:
                    continue
                prop_obj = data[prop_indices[0]]
                if not isinstance(prop_obj, dict):
                    continue
                
                for key, value in prop_obj.items():
                    if isinstance(value, int) and value < len(data):
                        actual = data[value]
                        if isinstance(actual, str) and 'rightmove.co.uk/house-prices/details/' in actual:
                            print(f"  LINK KEY: {key} -> {actual[:100]}")
                        elif isinstance(actual, str) and actual.startswith('http'):
                            print(f"  URL key: {key} -> {actual[:100]}")
                break

print("=== 1 mile radius ===")
find_link_key('/home/ubuntu/fresh_sold_1mi.html')
print("\n=== 0.25 mile radius ===")
find_link_key('/home/ubuntu/fresh_sold_025mi.html')
```

**For other failures:**

1. **Fetch fresh HTML from Rightmove** (active or sold as appropriate)
2. **Compare structure with test data** — extract JSON and compare paths/keys
3. **Identify what changed** — list specific field names, JSON paths, or index keys

### Step 6: Provide Recommendations

Based on your analysis, provide:

1. **Summary of changes:**
   - What changed in Rightmove's structure
   - Which parser functions need updating
   - Whether the link key shifted (and to which key)

2. **Recommended fixes:**
   - Specific code changes needed in `rightmove_parsers.py`
   - Whether test data files need updating

3. **Next steps:**
   - Should the user run the fix prompt (`MANUS_FIX_PARSING.md`)?
   - Are the changes minor (link key shift — likely auto-handled) or major (structure overhaul)?

## Example Usage

```
User: "Please test if the Rightmove parsing modules are working"

Manus: [Downloads test suite and runs tests]

Manus: "I've run the 27 parsing tests. Here are the results:

✓ Helper function tests:      15/15 passed
✓ Active listing tests:        8/8  passed
✓ Sold listing — core:         1/1  passed
✗ Sold listing — links:        1/3  passed

FAILURE: sold_property_link_populated
  ALL 25 properties have empty link — link key has shifted in Rightmove structure

INVESTIGATION:
  Fetched fresh HTML from both 1mi and 0.25mi radius pages.
  Link key has moved:
    - 1 mile page:   was _111, now _119
    - 0.25 mile page: was _118, now _125

  The current parser uses a structure-agnostic scan for
  'rightmove.co.uk/house-prices/details/' in all decoded values.
  The scan should pick up the new keys automatically.

  After re-running tests with fresh HTML as test data: 27/27 pass.

Recommendation: Update test data HTML files and run MANUS_FIX_PARSING.md
to refresh the parser version and test data."
```

## Success Criteria

- All 27 tests pass (24 original + 3 link tests)
- Clear report of pass/fail status for each group
- Link tests explicitly confirmed: populated, correct format, live HTTP check
- If failures detected, specific changes identified with recommendations

## Notes

- This prompt should be run regularly (weekly) to catch changes early
- Test failures are expected when Rightmove updates their website
- The modular architecture ensures only the parsing module needs updates
- **Link key shifts are the most common failure** — Rightmove's indexed array keys shift
  frequently between page variants. The structure-agnostic scan handles this automatically,
  but the test data HTML must be kept fresh for the tests to reflect current Rightmove structure
- Always test with both a filtered (small radius) and unfiltered (large radius) sold listing
  page, as they use different key indices
