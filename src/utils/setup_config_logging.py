import os
import sys

from src.utils.config_loader import ConfigLoader
from src.utils.logger import LoggerManager


async def async_setup_config_logging(filename:str, config_file_path:str = None):
    return setup_config_logging(filename, config_file_path)


def setup_config_logging(filename:str, config_file_path:str = None):
    # Load configuration **only once**
    try:
        project_config = ConfigLoader(os.getenv("CONFIG_FILE", config_file_path))
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        sys.exit(1)  # 🔴 Exit on failure
    # Set up logger

    # Override with environment variables if they exist
    project_config.config["default"]["log_directory"] = os.getenv("LOG_DIRECTORY", project_config.config["default"]["log_directory"])
    project_config.config["default"]["save_location"] = os.getenv("SAVE_LOCATION", project_config.config["default"]["save_location"])

    project_config.config["development"]["log_directory"] = os.getenv("LOG_DIRECTORY", project_config.config["development"]["log_directory"])
    project_config.config["development"]["save_location"] = os.getenv("SAVE_LOCATION", project_config.config["development"]["save_location"])


    try:
        logger_manager = LoggerManager(project_config)
        logger = logger_manager.get_logger(filename)
    except Exception as e:
        print(f"Failed to initialize logger: {e}")
        sys.exit(1)  # 🔴 Exit on failure
    return logger, logger_manager, project_config
