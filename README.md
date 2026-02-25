# Deal Shortlist Tool

A FastAPI server that exposes Rightmove property analysis tools as REST endpoints — searching active listings, calculating median sold prices, and identifying undervalued properties.

## Running Locally

### 1. Prerequisites

- Python 3.11+

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the server

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at **http://localhost:8000**.

### 4. Explore the API

Interactive Swagger docs: **http://localhost:8000/docs**

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/parser/info` | Parser version and status |
| `POST` | `/api/search_properties` | Search active Rightmove listings |
| `POST` | `/api/calculate_median` | Calculate median sold price for a postcode |
| `POST` | `/api/get_median_properties` | Get the sold properties used in the median calculation |
| `POST` | `/api/find_deals` | Find undervalued properties on a Rightmove search page |
| `POST` | `/api/parser/fix` | Trigger parser fix workflow |
| `POST` | `/api/parser/test` | Run parser test suite |

See [API_GUIDE.md](API_GUIDE.md) for full request/response documentation.

## Project Structure

```
main.py                          # FastAPI app and all route handlers
requirements.txt                 # Python dependencies
shared/
    rightmove_parsers.py         # Shared HTML parsing module (single source of truth)
MedianPriceCalculator/
    median_price_calculator.py   # Median sold price logic
PropertyDealFinder/
    property_deal_finder.py      # Deal-finding logic
test_suite/
    test_parsing.py              # Parser tests
    test_runner.py               # Test runner
```
