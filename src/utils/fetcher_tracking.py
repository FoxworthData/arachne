
import time
from typing import List, Optional


class FetchedFile:
    def __init__(
        self,
        retailer: str,
        store_id: int,
        fetch_type: Optional[str],
        fetch_query: Optional[str],
        url: str,
        filename: Optional[str],
        size: Optional[int],
        page_number: Optional[int],
        fetched_time: float,
        blocked: bool = False,
        success: bool = True,
        message: Optional[str] = None,
        response_status_code: Optional[int] = None,
    ):
        self.retailer = retailer
        self.store_id = store_id
        self.fetch_type = fetch_type
        self.fetch_query = fetch_query
        self.url = url
        self.filename = filename
        self.size = size or 0
        self.page_number = page_number
        self.fetched_time = fetched_time
        self.blocked = blocked
        self.success = success
        self.message = message
        self.response_status_code = response_status_code
        self.retry_of_url = None

    def to_string(self) -> str:
        return (
            f"FetchedFile(\n"
            f"  retailer={self.retailer},\n"
            f"  store_id={self.store_id},\n"
            f"  fetch_type={self.fetch_type},\n"
            f"  fetch_query={self.fetch_query},\n"
            f"  url={self.url},\n"
            f"  filename={self.filename},\n"
            f"  size={self.size},\n"
            f"  page_number={self.page_number},\n"
            f"  fetched_time={self.fetched_time},\n"
            f"  blocked={self.blocked},\n"
            f"  success={self.success},\n"
            f"  message={self.message},\n"
            f"  response_status_code={self.response_status_code}\n"
            f")"
        )

class FetcherSession:
    def __init__(
        self,
        retailer: str,
        store_id: int,
        fetch_type: Optional[str] = None,
        fetch_query: Optional[str] = None,
        url: Optional[str] = None
    ):
        self.fetcher_session_id = None
        self.start_time = time.time()
        self.end_time = None
        self.retailer = retailer
        self.store_id = store_id
        self.fetch_type = fetch_type
        self.fetch_query = fetch_query
        self.url = url
        self.blocked = False
        self.success = True
        self.message = None
        self.fetched_files: List[FetchedFile] = []
        self.fetched_files_saved = 0
        self.fetched_count = 0
        self.needs_retry = []

    def add_fetched_file(self, file: FetchedFile):
        self.fetched_files.append(file)
        self.fetched_count += 1

        if file.filename is not None:
            self.fetched_files_saved += 1

        if not file.success:
            self.success = False
            self.needs_retry.append(file.url)

        if file.blocked:
            self.blocked = True
            self.success = False

    def close(self):
        self.end_time = time.time()

    def to_string(self) -> str:
        duration = (self.end_time or time.time()) - self.start_time
        status = "SUCCESS" if self.success else "FAILURE"
        block_flag = "BLOCKED" if self.blocked else "CLEAR"

        session_info = (
            f"[FetcherSession] Retailer: {self.retailer}, Store: {self.store_id}, "
            f"Type: {self.fetch_type}, Query: {self.fetch_query}, "
            f"Fetched: {self.fetched_count}, Saved: {self.fetched_files_saved}, Status: {status}, {block_flag}, "
            f"Duration: {duration:.2f}s"
        )

        fetched_files_info = ""

        fetched_files_info = "\n".join(
            f"  {file.to_string()}" for file in self.fetched_files if not file.success
        )

        if len(self.needs_retry) > 0:
            fetched_files_info += f"\n  Needs Retry:\n"
            fetched_files_info += "\n".join(f"    {url}" for url in self.needs_retry)

        return f"{session_info}\nFetched Files:\n{fetched_files_info if fetched_files_info else '  (no info to report)'}"