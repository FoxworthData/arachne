"""RunConfig: input parameters for a single scrape run.

Holds the inputs the orchestration layer needs to dispatch a scrape:
which retailer, which store, which fetch_type, which query, which
browser persona. All fields are inputs — RunConfig has no mutable state,
no resolved URLs, no harvested cookies. Those live on the strategy.

This is deliberately a small dataclass rather than a service object.
main.py constructs one, hands it to the dispatcher, and that's it.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RunConfig:
    retailer: str
    store_id: str
    fetch_type: str
    query: str
    persona_os_name: str = "Windows"
    persona_browser_name: str = "Chrome"
