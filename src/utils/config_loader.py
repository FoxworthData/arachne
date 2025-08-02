import os
import toml
from typing import Any, Dict

# Default configuration used if no config file is found or if there are errors in reading the config file.
DEFAULT_CONFIG = {
    "log_directory": "logs",
    "sensitivity": "INFO",
    "sensitive_keys": []
}


class ConfigLoader:
    """
    A Singleton class responsible for loading and managing configuration settings.

    - Loads configuration settings from a TOML file (`project_config/config.toml`).
    - Supports environment-specific configurations (`development`, `production`, etc.).
    - Falls back to `DEFAULT_CONFIG` if the configuration file is missing or invalid.

    This class follows the Singleton pattern to ensure that configuration settings
    are loaded only once and shared across the application.

    Attributes:
        _instance (ConfigLoader): The Singleton instance of the ConfigLoader class.
        config_file (str): Path to the configuration file.
        environment (str): The current environment (defaults to "development").
        config (Dict[str, Any]): The loaded configuration settings.
    """

    _instance = None  # Singleton instance

    def __new__(cls, config_file: str = None):
        """
        Implements the Singleton pattern to ensure only one instance of ConfigLoader exists.

        Args:
            config_file (str): Path to the TOML configuration file.

        Returns:
            ConfigLoader: The Singleton instance of ConfigLoader.
        """
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._init(config_file)  # Initialize only once
        return cls._instance

    def _init(self, config_file: str):
        """
        Initializes the ConfigLoader instance, loads configuration settings.

        Args:
            config_file (str): Path to the configuration file.
        """
        self.environment = os.getenv("APP_ENV", "development")
        self.config_file = config_file or os.getenv("CONFIG_FILE", "config.toml")

        if "APP_ENV" not in os.environ:
            print("Warning: APP_ENV not set. Defaulting to 'development'.")

        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:

        if not os.path.exists(self.config_file):
            print(f"Warning: Configuration file not found ({self.config_file}). Using default configuration.")
            return DEFAULT_CONFIG

        try:
            with open(self.config_file, "r") as file:
                config = toml.load(file)

            print("DEBUG: Successfully loaded configuration from config.toml")

            base_config = config.get("default", {})
            env_config = config.get(self.environment, {})

            # ✅ Include ALL top-level sections (e.g., walmart, scrapfly)
            merged_config = {**config, **base_config, **env_config}

            return merged_config
        except Exception as e:
            print(f"Error reading configuration file '{self.config_file}': {e}. Using default configuration.")
            return DEFAULT_CONFIG

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value by key.

        Args:
            key (str): The configuration key to retrieve.
            default (Any): The default value to return if the key is not found.

        Returns:
            Any: The value associated with the key, or the default value if the key is missing.
        """
        return self.config.get(key, default)
