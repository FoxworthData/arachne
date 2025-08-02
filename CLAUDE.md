# CLAUDE.md - Arachne Web Scraping Prototype Environment

## Project Overview

**Arachne** is a lightweight web scraping prototyping environment designed for rapid experimentation and proof-of-concept development. It serves as the R&D counterpart to the enterprise-grade **Reaper** platform, allowing quick iteration on scraping approaches before full production implementation.

## Purpose & Philosophy

### Core Mission
- **Rapid Prototyping**: Quickly test scraping approaches for new targets
- **Proof of Concept**: Validate data extraction methods with minimal overhead  
- **Research & Development**: Experiment with anti-bot evasion techniques
- **Fast Iteration**: Test selectors, parsing logic, and request patterns

### Relationship to Reaper
Arachne feeds into the **Reaper** enterprise platform following this workflow:
1. **Arachne Phase**: Prototype and validate scraping approach
2. **Reaper Phase**: Implement production solution with enterprise features

## Project Structure

```
arachne/
├── src/                    # Core scraping modules
│   ├── main.py            # Main execution entry point
│   ├── parse.py           # HTML parsing and data extraction
│   ├── project_config/    # Configuration management
│   ├── utils/             # Utility functions and helpers
│   └── scratch/           # Experimental code and tests
├── data/                  # Input data and configuration files
├── requirements.txt       # Python dependencies
└── CLAUDE.md             # This documentation file
```

## Technology Stack

### Core Dependencies
- **Python 3.8+**: Primary development language
- **requests/aiohttp**: HTTP client for web requests
- **BeautifulSoup/lxml**: HTML parsing and element selection
- **pandas**: Data manipulation and CSV output
- **PyYAML**: Configuration file management

### Design Principles
- **Minimal Dependencies**: Keep external requirements lightweight
- **Simple Architecture**: Avoid complex abstractions and patterns
- **File-Based Output**: Direct CSV/JSON output for immediate inspection
- **No Database**: File-based persistence for simplicity
- **Single-Target Focus**: Optimize for one retailer at a time

## Development Guidelines

### Code Style
- **Keep It Simple**: Favor readability over optimization
- **Minimal Abstraction**: Avoid over-engineering for prototypes
- **Direct Approach**: Use straightforward request/parse patterns
- **Quick Debugging**: Add print statements and file outputs liberally

### File Organization
- **main.py**: Entry point with argument parsing and execution flow
- **parse.py**: Target-specific parsing logic and selectors
- **utils/**: Reusable functions for headers, proxies, file handling
- **scratch/**: Experimental code that may be discarded

### Configuration Management
- **YAML files**: Store target URLs, selectors, and parameters
- **Environment variables**: Handle sensitive data (API keys, proxies)
- **Command-line args**: Override config for quick testing

## Typical Development Workflow

### 1. Target Analysis
```bash
# Analyze target website structure
python src/main.py --target walmart --analyze-only
```

### 2. Selector Development
```python
# In parse.py - iterate on CSS/XPath selectors
def extract_products(html):
    soup = BeautifulSoup(html, 'html.parser')
    products = soup.select('.product-item')  # Test different selectors
    return [parse_product(p) for p in products]
```

### 3. Request Testing
```python
# In main.py - test different request patterns
headers = {
    'User-Agent': 'Mozilla/5.0...',
    'Referer': 'https://www.google.com'
}
response = requests.get(url, headers=headers)
```

### 4. Data Validation
```bash
# Quick CSV output for manual inspection
python src/main.py --target walmart --query "eggs" --output results.csv
```

### 5. Anti-Bot Testing
```python
# Test different evasion techniques
def test_request_patterns():
    # Test 1: Basic request
    # Test 2: With headers
    # Test 3: With delays
    # Test 4: With proxies
```

## Common Patterns

### Request Headers
```python
def get_basic_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
```

### Error Handling
```python
def safe_request(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
    return None
```

### Data Extraction
```python
def extract_with_fallback(element, selectors):
    """Try multiple selectors until one works"""
    for selector in selectors:
        try:
            result = element.select_one(selector)
            if result:
                return result.get_text(strip=True)
        except:
            continue
    return None
```

## Output Formats

### CSV Output
```python
import pandas as pd

def save_to_csv(products, filename):
    df = pd.DataFrame(products)
    df.to_csv(filename, index=False)
    print(f"Saved {len(products)} products to {filename}")
```

### JSON Output
```python
import json

def save_to_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved data to {filename}")
```

## Testing & Validation

### Quick Tests
```bash
# Test single page
python src/main.py --url "https://example.com/search?q=test" --limit 1

# Test pagination
python src/main.py --target walmart --query "bread" --pages 3

# Test with different headers
python src/main.py --target walmart --query "milk" --user-agent firefox
```

### Data Quality Checks
```python
def validate_extracted_data(products):
    required_fields = ['name', 'price', 'url']
    for product in products:
        missing = [f for f in required_fields if not product.get(f)]
        if missing:
            print(f"Missing fields: {missing}")
    return len([p for p in products if all(p.get(f) for f in required_fields)])
```

## Migration to Reaper

### Learnings to Capture
- **Working selectors**: Document CSS/XPath selectors that work
- **Request patterns**: Headers, delays, and evasion techniques
- **Data structure**: Field mappings and parsing logic
- **Pagination**: How to navigate multiple pages
- **Anti-bot measures**: Detection patterns and successful evasions

### Reaper Component Creation
Once Arachne prototyping is complete:
1. Create retailer component in `backend/components/{retailer}/`
2. Implement ForagerComponent with validated selectors
3. Add ResponseAnalyzer with bot detection patterns
4. Create HeaderBuilder with working header patterns
5. Implement Paginator with pagination logic

## Environment Setup

### Installation
```bash
# Clone and setup
git clone <arachne-repo>
cd arachne
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### Configuration
```bash
# Copy example config
cp data/config.example.yaml data/config.yaml

# Edit for your target
vim data/config.yaml
```

### Quick Start
```bash
# Basic scraping test
python src/main.py --target example --query "test" --output results.csv
```

## Best Practices

### Development
- **Start Simple**: Begin with basic requests and build complexity
- **Test Incrementally**: Validate each piece before combining
- **Save Everything**: Output HTML files for offline analysis
- **Document Findings**: Comment unusual patterns or workarounds

### Data Handling
- **Inspect Output**: Always manually check initial results
- **Handle Errors Gracefully**: Expect and plan for failures
- **Validate Extraction**: Cross-check scraped data with website
- **Monitor Changes**: Target sites change - retest regularly

### Performance
- **Add Delays**: Respect rate limits and avoid being blocked
- **Use Sessions**: Reuse connections when possible
- **Cache Responses**: Save HTML for repeated parsing tests
- **Monitor Resources**: Watch memory usage with large datasets

## Advanced Prototyping

### Browser Fingerprinting Research
Arachne now includes advanced browser fingerprinting prototypes that demonstrate sophisticated bot evasion techniques:

- **`src/advanced_fingerprinting_prototype.py`**: Standalone script showing enterprise-grade fingerprinting
- **Session-consistent browser personas**: Maintain consistent User-Agent across requests
- **Modern browser headers**: Chrome Client Hints, Fetch Metadata, device performance simulation
- **Cookie seeding simulation**: Mock system demonstrating cookie enhancement techniques
- **Advanced bot evasion**: Reaper-style sophistication within Arachne's simple architecture

### Documentation
- **`docs/BROWSER_FINGERPRINTING_COMPARISON.md`**: Detailed comparison of Arachne vs Reaper fingerprinting approaches
- **Header analysis**: Complete breakdown of header keys and cookie strategies
- **Migration guidance**: How to evolve from prototype to production-ready solutions

### Usage
```bash
# Run advanced fingerprinting prototype (fixed import paths for CLI execution)
python src/advanced_fingerprinting_prototype.py

# Compare with basic approach
python src/main.py
```

**Note**: Import paths have been fixed to support both module imports and direct command-line execution.

**Success**: Real cookie seeding now working - harvests authentic Walmart cookies (isoLoc, ak_bmsc, etc.) for enhanced bot evasion and successful store-specific targeting.

---

**Remember**: Arachne is for exploration and learning. Once you understand how to scrape a target effectively, migrate the approach to Reaper for production deployment with enterprise features like monitoring, retry logic, and event-driven processing.