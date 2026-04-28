"""Strategy classes for retailer-specific scraping behavior.

Each retailer is implemented as a concrete subclass of RetailerScrapeStrategy
in its own module. The orchestration layer (main.py / run_initializer) holds
a strategy reference and calls uniform methods on it; retailer-specific
knowledge stays inside the strategy.

This is the GoF Strategy pattern: the family of algorithms is "scrape a
retailer", encapsulated per retailer, interchangeable behind the ABC.
"""
