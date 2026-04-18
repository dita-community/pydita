"""Error capture and logging utilities beyond built-in logging facilities.
"""

from typing import Union
from datetime import datetime
from copy import copy, deepcopy

# Serverity levels:
INFO: str = "info"
ERROR: str = "error"
FATAL: str = "fatal"
WARN: str = "warning"

class ErrorRecord():
    """Captures the details about an error
    """

    def __init__(self, key: str, err: Exception, severity:str=ERROR,timestamp:datetime=datetime.now()):
        """A single error record

        Args:

            key (str): The key for the record, such as a file name.

            err (Exception): The exception that describes the error being recorded.

            severity (str, optional): The error's severity. Defaults to ERROR.

            timestamp (datetime, optional): The time the error occurred. Defaults to datetime.now().
        """
        self._key = key
        self._err = Exception
        self._severity = severity
        self._timestamp: datetime = timestamp

    def getKey(self) -> str:
        return self._key

    def getException(self) -> Exception:
        return self._err

    def getSeverity(self) -> str:
        return self._severity

class Errors(dict):
    """Maintains a dictionary of named things to ErrorRecord objects.
    """

    def __init__(self):
        super().__init__()

    def logErrorRecord(self, error: ErrorRecord) -> None:
        """Logs an error record.

        Args:

            error (ErrorRecord): The error record to be logged.
        """
        errors: list[ErrorRecord] = self.get(error.getKey())
        if errors is None:
            errors = []
            self[error.getKey()] = errors
        errors.append(error)
        
    def logError(self, key: str, err: Union[str, Exception], severity="error") -> None:
        """Log an error.

        Args:

            key (str): Key to associate with the error, such as filename.

            err (Exception): Message or exception that describes the error being logged.

            severity (str, optional): _description_. Defaults to "error".
        """
        exception: Exception = None
        if isinstance(err, Exception):
            exception = err
        else:
            exception = Exception(err)

        error: ErrorRecord = ErrorRecord(key, exception, severity=severity)
        self.logErrorRecord(error)