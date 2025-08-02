import json

import csv
from logging import Logger

import fsspec
import gzip
import io
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict

from src.utils.config_loader import ConfigLoader  # ✅ Correct (relative import)


class FileStorage:
    def __init__(
            self,
            retailer: str,
            project_config: ConfigLoader = None,
            logger: Logger = None
    ):
        self.project_config = project_config or ConfigLoader()  # Allow dependency injection for tests
        self.logger = logger
        self.retailer = retailer

        self.app_environment = os.environ.get("APP_ENV", "development")  # Default to 'development'
        self.file_storage_type = self.project_config.get(self.app_environment, "development").get("file_storage", "file")
        self.save_location = self.project_config.get(self.app_environment, "development").get("save_location", None)
        self.parsed_save_location = self.project_config.get(self.app_environment, "development").get("parsed_save_location", None)

        if not self.file_storage_type or not self.save_location:
            raise ValueError("Invalid storage configuration. Please check the environment settings.")

        if self.file_storage_type == "file":
            Path(self.save_location, self.retailer).mkdir(parents=True, exist_ok=True)

        self.logger.info("Initializing FileStorage")

    def save_html(self, filename: str, html: str, fetch_type: str = 'search'):
        """Save HTML content to a file, optionally compressed."""
        full_path = f"{self.save_location}/{self.retailer}/{fetch_type}/{filename}"
        try:
            with fsspec.open(full_path, "wb") as f:
                with gzip.GzipFile(fileobj=f, mode="wb") as gz:
                    gz.write(html.encode("utf-8"))
            self.logger.info(f"Saved HTML: {full_path}")
        except Exception as e:
            self.logger.error(f"Error saving HTML to {full_path}: {e}")

    def get_html_content(self, source_full_path):
        # Read and decompress the gzipped HTML file
        with fsspec.open(source_full_path, 'rb') as f_in:
            with gzip.open(f_in, 'rt', encoding='utf-8') as gz_in:
                html_content = gz_in.read()
        return html_content

    def save_cleaned_csv(self, csv_data, output_gzip_file):
        """ Saves the cleaned product data to a gzipped CSV file. """
        compressed_data = io.BytesIO()

        # Write the CSV data into the compressed buffer
        with gzip.GzipFile(fileobj=compressed_data, mode='wb') as gz_buffer:
            with io.TextIOWrapper(gz_buffer, encoding='utf-8', newline="") as gz_out:
                fieldnames = csv_data[0].keys()
                writer = csv.DictWriter(gz_out, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)

        # Get compressed size
        compressed_size = compressed_data.tell()

        # Write the compressed data to the actual file
        with fsspec.open(output_gzip_file, 'wb') as f_out:
            f_out.write(compressed_data.getvalue())

        return {"filename": output_gzip_file, "size": compressed_size}

    def save_cleaned_json(self, json_data, output_gzip_file):
        """Saves the cleaned product data to a gzipped JSON file."""
        compressed_data = io.BytesIO()

        # Write the JSON data into the compressed buffer
        with gzip.GzipFile(fileobj=compressed_data, mode='wb') as gz_buffer:
            gz_buffer.write(json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8'))

        # Get compressed size
        compressed_size = compressed_data.tell()

        # Write the compressed data to the actual file
        with fsspec.open(output_gzip_file, 'wb') as f_out:
            f_out.write(compressed_data.getvalue())

        return {"filename": output_gzip_file, "size": compressed_size}

    def list_saved_files(self, fetch_type:str = 'search') -> list:
        """Return a list of all files in the retailer's save directory."""
        try:
            target_dir = Path(self.save_location) / self.retailer / fetch_type
            if not target_dir.exists():
                self.logger.warning(f"Directory does not exist: {target_dir}")
                return []
            files = [f.name for f in target_dir.iterdir() if f.is_file()]
            self.logger.info(f"Found {len(files)} files in {target_dir}")
            return files
        except Exception as e:
            self.logger.error(f"Error listing files in {self.save_location}: {e}")
            return []

    # def _save_compressed(self, content: str, filename: str) -> Dict[str, str]:
    #     """
    #     Save HTML content as a Gzip-compressed file using fsspec, either locally or to Google Cloud Storage.
    #
    #     - Automatically detects whether to save locally or to GCS.
    #     - Uses UTF-8 encoding and Gzip compression.
    #     - Logs success or failure.
    #
    #     Args:
    #         content (str): The raw HTML content to be saved.
    #         filename (str): The sanitized filename (without extension).
    #         folder (Optional[str]): The directory or bucket path where the file will be stored. Defaults to "./data".
    #
    #     Returns:
    #         dict: A dictionary containing the file path and size, or an error message.
    #
    #     Example:
    #         >>> self._save_compressed("<html>...</html>", "search_results", "./scraped_data")
    #         # Saves locally: "scraped_data/search_results.html.gzip"
    #
    #         >>> self._save_compressed("<html>...</html>", "search_results", "gs://my-bucket/scraped_data")
    #         # Saves to GCS: "gs://my-bucket/scraped_data/search_results.html.gzip"
    #     """
    #     try:
    #         if self.file_storage_type not in {"file", "gcs"}:
    #             raise ValueError(f"Unsupported storage type: {self.file_storage_type}")
    #
    #         fs = fsspec.filesystem(self.file_storage_type)
    #         file_path = self._get_file_path(filename)
    #
    #         compressed_data = io.BytesIO()
    #         with gzip.GzipFile(fileobj=compressed_data, mode='wb') as gz_file:
    #             gz_file.write(content if isinstance(content, bytes) else content.encode("utf-8"))
    #         compressed_size = compressed_data.tell()
    #
    #         self.logger.info(f"Saving compressed file to: {file_path}")
    #         with fs.open(str(file_path), "wb") as f:
    #             f.write(compressed_data.getvalue())
    #
    #         size_in_bytes = len(content) if isinstance(content, bytes) else len(content.encode("utf-8"))
    #
    #         return {"filename": str(file_path), "size": size_in_bytes, "compressed_size": compressed_size}
    #     except ValueError as ve:
    #         self.logger.error(f"Configuration error: {ve}")
    #         return {"error": str(ve)}
    #     except Exception as e:
    #         self.logger.error(f"Failed to save file: {e}")
    #         return {"error": str(e)}
    #
    # def _get_file_path(self, filename: str) -> str:
    #     if self.file_storage_type == "file":
    #         return str(Path(self.save_location) / self.retailer / f"{filename}.html.gzip")
    #     elif self.file_storage_type == "gcs":
    #         return f"{self.save_location}/{self.retailer}/{filename}.html.gzip"
    #     else:
    #         raise ValueError(f"Unsupported storage type: {self.file_storage_type}")
