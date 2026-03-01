# Manus Prompt: Test Rightmove Parsing Modules

## Objective

Test if the Rightmove parsing modules are working correctly and detect if Rightmove has changed their website structure.

## Instructions for Manus

Please perform the following steps:

### Step 1: Download Test Suite

Download the test suite from Google Drive:
- Location: `DealFinder/Tools/RightmoveParsingModule/test_suite/`
- Download all files to `/home/ubuntu/test_suite/`

### Step 2: Run Tests

Execute the test runner:

```bash
cd /home/ubuntu/test_suite
python3.11 test_runner.py --json test_report.json
```

### Step 3: Analyze Results

Check the test results:

```bash
python3.11 test_parsing.py --verbose
```

### Step 4: Report Findings

Report which tests passed and which failed:

1. **If all tests passed:**
   - Report: "✓ All parsing tests passed. Rightmove structure is unchanged."
   - No further action needed.

2. **If active listing tests failed:**
   - Report: "✗ Active listing parsing tests failed."
   - Proceed to Step 5 for active listings.

3. **If sold listing tests failed:**
   - Report: "✗ Sold listing parsing tests failed."
   - Proceed to Step 5 for sold listings.

### Step 5: Investigate Failures (if any)

For each failed test:

1. **Fetch fresh HTML from Rightmove:**
   - Active listings: Fetch from a Rightmove search URL
   - Sold listings: Fetch from a Rightmove house prices URL

2. **Compare structure with test data:**
   - Extract JSON from fresh HTML
   - Compare with test data JSON structure
   - Identify what changed

3. **Document changes:**
   - List the specific field names that changed
   - List the specific JSON paths that changed
   - Note any new structure patterns

### Step 6: Provide Recommendations

Based on your analysis, provide:

1. **Summary of changes:**
   - What changed in Rightmove's structure
   - Which parser functions need updating

2. **Recommended fixes:**
   - Specific code changes needed in `rightmove_parsers.py`
   - Which test data files need updating

3. **Next steps:**
   - Should the user run the fix prompt?
   - Are the changes minor or major?

## Example Usage

```
User: "Please test if the Rightmove parsing modules are working"

Manus: [Downloads test suite and runs tests]

Manus: "I've run the parsing tests. Here are the results:

✓ Helper function tests: 15/15 passed
✓ Active listing tests: 6/6 passed  
✗ Sold listing tests: 0/1 passed

The sold listing parser is failing. I fetched fresh HTML from Rightmove 
and found that they've changed the React Router context structure:

Changes detected:
- Property index keys changed from '_72', '_74' to '_82', '_84'
- Transaction data moved from '_80' to '_90'
- Price field changed from '_83' to '_93'

Recommendation: Use the MANUS_FIX_PARSING.md prompt to automatically 
update the parser with these new mappings."
```

## Success Criteria

- Test suite runs successfully
- Clear report of pass/fail status
- If failures detected, specific changes identified
- Recommendations provided for fixing issues

## Notes

- This prompt should be run regularly (weekly) to catch changes early
- Test failures are expected when Rightmove updates their website
- The modular architecture ensures only the parsing module needs updates
