import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler


class SensitiveFilter(logging.Filter):
    """
    A logging filter that redacts sensitive information from log messages.

    This filter applies regular expressions to mask sensitive keys, such as API keys and passwords,
    replacing them with '[REDACTED]'.
    """

    def __init__(self, sensitive_keys):
        """
        Initialize the SensitiveFilter.

        Args:
            sensitive_keys (list): A list of sensitive keys (e.g., ['API_KEY', 'PASSWORD'])
                                   that should be redacted from logs.
        """
        super().__init__()
        self.sensitive_keys = sensitive_keys
        # Create regex patterns to match key-value pairs with colons or equals signs
        self.patterns = [
            re.compile(rf"({key}\s*[:=]\s*)([^,\s]+)", re.IGNORECASE) for key in self.sensitive_keys
        ]

    def filter(self, record):
        """
        Apply filtering to redact sensitive information in log messages.

        Args:
            record (logging.LogRecord): The log record containing the message.

        Returns:
            bool: True if the record should be logged (always True).
        """
        if not isinstance(record.msg, str):
            try:
                record.msg = str(record.msg)
            except Exception:
                return True  # If conversion fails, log as-is

        for pattern in self.patterns:
            record.msg = pattern.sub(r"\1[REDACTED]", record.msg)

        return True


class LoggerManager:
    """
    A Singleton Logger Manager that configures and provides application-wide loggers.

    This manager ensures that loggers are set up with:
    - A rotating file handler for persistent logging.
    - A stream handler for console output.
    - A custom SensitiveFilter to redact sensitive information.
    """
    _instance = None  # Singleton instance

    def __new__(cls, config_loader):
        """
        Implement Singleton pattern: Ensures only one instance of LoggerManager exists.

        Args:
            config_loader (ConfigLoader): The configuration loader for logging settings.

        Returns:
            LoggerManager: The single instance of LoggerManager.
        """
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance._initialize(config_loader)
        return cls._instance

    def _initialize(self, config_loader):
        """
        Initialize the LoggerManager with settings from the configuration loader.

        Args:
            config_loader (ConfigLoader): Provides logging configurations such as log directory and log level.
        """
        self.project_config = config_loader.config
        self.app_environment = os.environ.get("APP_ENV", "development")
        self.instance_id = os.environ.get("CLOUD_RUN_INSTANCE_ID", f"local-{os.getpid()}")
        self.log_level = self.project_config.get(self.app_environment, "default").get("sensitivity", "INFO").upper()
        self.log_directory = self.project_config.get(self.app_environment, "default").get("log_directory", "./logs")

        project_name = config_loader.get("project", None).get("name", None)

        if self.app_environment == "development":
            self.log_directory = os.path.join(self.log_directory, self.app_environment)
            os.makedirs(self.log_directory, exist_ok=True)

        self.log_file = os.path.join(self.log_directory, f"{project_name}_{self.instance_id}.log")


    def get_logger(self, name: str):
        """
        Retrieve a logger with a specified name, ensuring consistent configuration.

        Args:
            name (str): The name of the logger (e.g., module name).

        Returns:
            logging.Logger: A configured logger instance.
        """
        logger = logging.getLogger(name)
        log_level = logging.getLevelName(self.log_level)
        if not isinstance(log_level, int):
            log_level = logging.INFO
        logger.setLevel(log_level)

        if not logger.hasHandlers():
            formatter = logging.Formatter(f"%(asctime)s - {self.instance_id} - %(name)s - %(levelname)s - %(message)s")
            if self.app_environment == "development":
                handler = RotatingFileHandler(self.log_file, maxBytes=1048576, backupCount=3)

                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)
            else:
                handler = logging.StreamHandler(sys.stdout)  # Cloud Run captures stdout logs

            handler.setFormatter(formatter)
            sensitive_keys = self.project_config.get(self.app_environment, "default").get("sensitive_keys", ["API_KEY", "PASSWORD"])
            handler.addFilter(SensitiveFilter(sensitive_keys))
            logger.addHandler(handler)

        return logger
