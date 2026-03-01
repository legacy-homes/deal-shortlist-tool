# Manus Prompt: Fix Rightmove Parsing Issues

## Objective

Automatically detect and fix Rightmove parsing issues when their website structure changes.
This includes ensuring all fields — including the **property link** — are correctly populated.

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

Analyze which specific tests are failing. Pay particular attention to:
- `extract_sold_properties` — core extraction
- `sold_property_link_populated` — all sold properties must have a non-empty link
- `sold_property_link_format` — links must start with `https://www.rightmove.co.uk/house-prices/details/`
- `sold_property_link_live` — at least one link must return HTTP 200 or 404 from Rightmove

### Step 3: Fetch Fresh HTML from Rightmove

**For Active Listings (if tests failing):**

```bash
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier=REGION%5E904&propertyTypes=semi-detached&sortType=1&index=0" \
  -o /home/ubuntu/fresh_active.html
```

**For Sold Listings (if tests failing):**

Fetch from **multiple radius variants** because Rightmove uses different JSON key indices
depending on the page variant (radius=0, 0.25, 0.5, 1.0 miles all produce different structures):

```bash
# Unfiltered page (radius=1.0)
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://www.rightmove.co.uk/house-prices/manchester.html?soldIn=2&radius=1.0" \
  -o /home/ubuntu/fresh_sold_1mi.html

# Filtered page (radius=0.25) — different key indices
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://www.rightmove.co.uk/house-prices/cv6-6ed.html?soldIn=2&radius=0.25&propertyType=TERRACED&tenure=FREEHOLD" \
  -o /home/ubuntu/fresh_sold_025mi.html
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
       print("Property URL field:", prop.get('propertyUrl'))
   ```

2. Compare with old structure in test data
3. Document what changed

**For Sold Listings — including link field analysis:**

Run this analysis on **both** fresh HTML files (1mi and 0.25mi) to catch key shifts:

```python
import re, json, requests

def analyse_sold_html(html_path):
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
                
                print(f"\nProperty keys: {list(prop_obj.keys())}")
                
                for key, value in prop_obj.items():
                    if isinstance(value, int) and value < len(data):
                        actual = data[value]
                        # IMPORTANT: Look for URL-like strings — this is the link field
                        if isinstance(actual, str) and 'rightmove' in actual.lower():
                            print(f"  *** LINK CANDIDATE: {key} -> {actual[:120]}")
                        elif isinstance(actual, str) and len(actual) > 5:
                            print(f"  {key} -> str: {actual[:60]}")
                        elif isinstance(actual, dict):
                            print(f"  {key} -> dict: {list(actual.keys())[:8]}")
                        elif isinstance(actual, list):
                            print(f"  {key} -> list[{len(actual)}]")
                        else:
                            print(f"  {key} -> {type(actual).__name__}: {actual}")
                break

print("=== 1 mile radius page ===")
analyse_sold_html('/home/ubuntu/fresh_sold_1mi.html')

print("\n=== 0.25 mile radius page ===")
analyse_sold_html('/home/ubuntu/fresh_sold_025mi.html')
```

**Key things to check for the link field:**
- Which key contains a string starting with `https://www.rightmove.co.uk/house-prices/details/`?
- Does the key differ between the 1mi and 0.25mi pages? (It often does)
- Is the current parser using the correct key(s)?

### Step 5: Update Parser Code

Based on the structure analysis, update `rightmove_parsers.py`:

**For Active Listings:**

Update the `parse_active_property()` function if field names changed:
- Update price extraction if `price.amount` changed
- Update address field if `displayAddress` changed
- Update property type if `propertySubType` changed
- Update link field if `propertyUrl` changed

**For Sold Listings:**

Update the `parse_sold_property_from_indexed_array()` function:
- Update index mappings (e.g., `_72` → new index)
- Update transaction indices
- Update price/date indices
- **Update link extraction** — the current approach scans all decoded values for any string
  containing `rightmove.co.uk/house-prices/details/`, which is structure-agnostic. If links
  are still missing after this, check whether the URL pattern itself has changed on Rightmove.

  The link extraction block should look like:
  ```python
  elif isinstance(actual_value, str) and 'rightmove.co.uk/house-prices/details/' in actual_value:
      # Link key shifts between page variants (_111, _112, _118 observed).
      # Match any key whose value is the house-prices/details URL (structure-agnostic).
      property_info['link'] = actual_value
  ```

  If Rightmove has changed the URL pattern (e.g., from `/house-prices/details/` to something else),
  update the substring match accordingly.

### Step 6: Update Test Data

Update test data files with new structure:
- Save fresh sold listing HTML to `test_data/sold_listings/2026-02-13_fresh.html`
  (overwrite with the latest HTML so link tests use current data)
- Save fresh active listing HTML to `test_data/active_listings/2026-02-12_full_page.html`
- Update expected outputs if needed

### Step 7: Re-run Tests

```bash
cd /home/ubuntu/test_suite
python3.11 test_parsing.py --verbose
```

Verify all tests now pass, including the three link tests:
- `sold_property_link_populated` ✓
- `sold_property_link_format` ✓
- `sold_property_link_live` ✓

### Step 8: Update Version Info

In `rightmove_parsers.py`, update:

```python
PARSER_VERSION = "2.0.X"  # Increment version
LAST_VERIFIED_DATE = "2026-XX-XX"  # Update to today's date

RIGHTMOVE_STRUCTURE_VERSION = {
    'active_listings': '2026-XX',   # Update if changed
    'sold_listings': '2026-XX-XX'   # Update if changed
}
```

### Step 9: Upload Fixed Parser

Upload the updated parser to Google Drive:
- Upload `rightmove_parsers.py` to `DealFinder/Tools/RightmoveParsingModule/shared/`
- Upload `rightmove_parsers.py` to `DealFinder/Tools/IntegratedTools_v2/shared/`
- Upload updated test data to `DealFinder/Tools/RightmoveParsingModule/test_suite/test_data/`
- Commit all changes to GitHub: `legacy-homes/deal-shortlist-tool`

### Step 10: Report Changes

Provide a detailed report:

1. **What changed:**
   - List specific field names or indices that changed
   - Show before/after comparison
   - Note whether the link key shifted (and which key it moved to)

2. **What was fixed:**
   - List functions updated
   - Show code changes made

3. **Test results:**
   - Report pass/fail status after fixes (all 27 tests should pass)
   - Specifically confirm the three link tests pass

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
- Link URL key shifted: '_111' → '_118' on filtered pages
  (structure-agnostic scan still works; no code change needed)

FIXES APPLIED:
- Updated parse_sold_property_from_indexed_array() with new indices
- Updated test data with fresh HTML sample (both 1mi and 0.25mi variants)
- Incremented parser version to 2.0.X

TEST RESULTS (27/27):
✓ extract_sold_properties (25 properties)
✓ sold_property_link_populated (25/25 links present)
✓ sold_property_link_format (25 links match expected pattern)
✓ sold_property_link_live (HTTP 200 confirmed)
✓ All other 23 tests passing

The fixed parser has been uploaded to Google Drive and committed to GitHub."
```

## Success Criteria

- All 27 tests passing after fixes (24 original + 3 new link tests)
- Parser version incremented
- Test data updated with current structure (both radius variants for sold listings)
- Fixed parser uploaded to Google Drive (both `RightmoveParsingModule/shared/` and `IntegratedTools_v2/shared/`)
- Fixed parser committed to GitHub (`legacy-homes/deal-shortlist-tool`)
- Clear documentation of changes made

## Notes

- This prompt assumes Rightmove made structural changes
- If all 27 tests pass, no fixes are needed
- Always test with real Rightmove URLs after fixing
- Keep old parser version as backup
- The link key in sold listings shifts between page variants — always test with **both** a
  filtered (small radius) and unfiltered (large radius) page to catch all variants
- The current link extraction is structure-agnostic (scans for the URL pattern), so minor
  key shifts should be handled automatically; only update if the URL pattern itself changes
