"""Utility functions and classes for error capture and logging.
"""

from aenum import Enum, OrderedEnum

class SEVERITY(OrderedEnum):

    __order__ = 'OTHER DEBUG INFO ERROR WARN FATAL'

    OTHER: str = 0, "OTHER"
    DEBUG: str = 1, "DEBUG"
    INFO: str =  2, "INFO"
    ERROR: str = 3, "ERROR"
    WARN: str =  4, "WARN"
    FATAL: str = 5, "FATAL"


class ErrorRecord:
    """Record of a single error.
    """

    def __init__(self, err: Exception, operation: str=None, severity:'SEVERITY'=None, key: str=None, traceBack: str=None):
        """Construct a new error record.

        Args:
            err (Exception): The exception being recorded

            operation (str, optional): The operation that resulted in the exception. Defaults to None.

            severity (SEVERITY, optional): The severity of the error. Defaults to SEVERITY.ERROR.

            key (str, optional): The key this error record is associated with.

            traceBack (str, optional): The Python stack trace for the error.
        """
        if severity is None:
            severity = SEVERITY.ERROR
        self.err = err
        self.operation = operation
        self.severity: SEVERITY = severity
        self.key = key
        self.traceBack = traceBack

    def __str__(self) -> str:
        result = str(self.err)
        if self.operation is not None:
            result = f'{self.operation}: {result}'
        if self.key is not None:
            result = f'"{self.key}" {result}'
        if self.severity is not None:
            result = f'[{self.severity.name}] {result}'
        return result

    def getError(self) -> Exception:
        return self.err

    def getOperation(self) -> str:
        return self.operation

    def getSeverity(self) -> 'SEVERITY':
        return self.severity

    def getKey(self) -> str:
        return self.key

    def getTraceBack(self) -> str:
        return self.traceBack

def recordError(errors: dict,
                key: str,
                err: Exception,
                operation: str=None,
                severity:'SEVERITY'=None,
                traceBack: str=None):
    """Records an exception against some distinguishing key (i.e., file name, key name, etc.).

    Args:
        errors (dict[str, ErrorRecord]): Dictionary to record the error in. Values are lists
        of ErrorRecord objects.

        key (str): The key to associate the error with.

        err (Exception): The exception to be recorded

        operation (str): The name of the operation that resulted in the error, i.e., the function
                   the exception was caught in. Defaults to None.

        severity (SEVERITY): The severity of the exception. Defaults to SEVERITY.ERROR.

        traceBack (str): The formatted traceback, i.e., as created by traceback.format_exc()
    """
    if severity is None:
        severity = SEVERITY.ERROR
    if errors is not None:
        value = errors.get(key)
        if value is None:
            value = []
            errors[key] = value
        value.append(ErrorRecord(err, operation, severity=severity, key=key, traceBack=traceBack))

def reportErrors(errors: dict, showTraceBack: bool=False) -> str:
    """Produce a string report of the errors found.

    Args:

        errors (dict[str]): The dictionary of ErrorReport objects to report

        showTraceBack (bool): When true, also report any traceback for an error.

    Returns:

        str: A multi-line report
    """
    errorsBySeverity: dict = {}
    for errs in errors.values():
        for err in errs:
            severity: SEVERITY = err.getSeverity()
            if severity is None:
                severity = SEVERITY.OTHER
            severityErrors: list = errorsBySeverity.get(severity)
            if severityErrors is None:
                severityErrors = []
                errorsBySeverity[severity] = severityErrors
            severityErrors.append(err)

    totalCount = sum(len(v) for v in errors.values())
    result = f'Have {totalCount} total errors:\n'
    for severity in errorsBySeverity.keys():
        severityErrors: list = errorsBySeverity.get(severity)
        for error in severityErrors:
            result += f'{str(error)}\n'
            if showTraceBack and error.getTraceBack() is not None:
                result += error.getTraceBack() + "\n"
    return result

class Logger():
    """Base class for loggers.
    """

    def __init__(self, logging_level: 'SEVERITY'=None):
        if logging_level is None:
            logging_level = SEVERITY.INFO
        self.logging_level = logging_level

    def get_logging_level(self) -> 'SEVERITY':
        return self.logging_level

    def set_logging_level(self, severity:'SEVERITY'):
        self.logging_level: SEVERITY = severity

    def debug(self, message):
        self._log_message(message, SEVERITY.DEBUG)

    def info(self, message):
        self._log_message(message, SEVERITY.INFO)

    def warn(self, message):
        self._log_message(message, SEVERITY.WARN)

    def error(self, message):
        self._log_message(message, SEVERITY.ERROR)

    def fatal(self, message):
        self._log_message(message, SEVERITY.FATAL)

    def print(self, message, severity: 'SEVERITY'=None):
        """Print the message exactly as provided. Intended primarily to echo messages
        from other processors that already include severity level in the message text.

        Args:
            message: Message to print
            severity (SEVERITY): The message severity. Defaults to SEVERITY.INFO.
        """
        pass

    def _log_message(self, message, severity:'SEVERITY'):
        """Log the message to the logging target (console, etc.)

        Logger implementations must override this method.

        Args:
            message: Message to be logged
            severity (SEVERITY): Message severity
        """
        pass


class ConsoleLogger(Logger):
    """Logs to the console.
    """

    def __init__(self, logging_level:'SEVERITY'=None):
        super().__init__(logging_level=logging_level)

    def print(self, message, severity: 'SEVERITY'=None):
        print(message)

    def _log_message(self, message, severity:'SEVERITY'):
        if severity >= self.get_logging_level():
            msg: str = f'[{severity.name}] {message}'
            print(msg)
