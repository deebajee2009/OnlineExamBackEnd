import inspect
import logging
import os
from threading import Lock

import colorlog


class CustomLogger:
    _instances = {}
    _lock = Lock()  # To ensure thread safety for instance creation

    def __new__(cls, name: str, log_dir: str = "logs"):
        with cls._lock:
            if name not in cls._instances:
                instance = super(CustomLogger, cls).__new__(cls)
                instance._initialized = False
                cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self, name: str, log_dir: str = "logs") -> None:
        if not self._initialized:
            self._initialized = True
            self._logger = logging.getLogger(name)
            self._logger.setLevel(logging.INFO)  # Capture all log levels
            self._log_dir = log_dir
            self.app_module_name = self._get_app_module_name(name)
            self._setup_log_dir()
            self._create_handler()

    def _get_app_module_name(self, name: str) -> str:
        """Extracts the module name or converts '__main__' to a file-based name."""
        if name == "__main__":
            # Use the file name of the script running as '__main__' for the module name
            main_file = inspect.stack()[-1].filename  # Get the main file
            return os.path.splitext(os.path.basename(main_file))[0]
        else:
            # Convert the module path to a suitable name, e.g., 'myapp.mymodule' to 'myapp_mymodule'
            return name.replace(".", "_")

    def _setup_log_dir(self) -> None:
        """Ensure the log directory exists."""
        os.makedirs(self._log_dir, exist_ok=True)

    def _create_handler(self):
        """Create and add file and console handlers for all log levels."""
        caller_file = inspect.stack()[1].filename  # Get the filename of the caller
        base_file_name = os.path.splitext(os.path.basename(caller_file))[0]  # Extract file name without extension

        # Use the app_module_name in the log file name
        log_file_name = f"{self.app_module_name}_{base_file_name}.log"

        # File Handler
        file_handler = logging.FileHandler(f"{self._log_dir}/{log_file_name}")
        file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        self._logger.addHandler(file_handler)

        # Stream Handler for console output with colored logging
        stream_handler = logging.StreamHandler()
        stream_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        )
        stream_handler.setFormatter(stream_formatter)
        self._logger.addHandler(stream_handler)

    def get_logger(self):
        """Get the custom logger."""
        return self._logger
