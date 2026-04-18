"""Implements DitaContext class

"""

from lxml import etree
from lxml.etree import Element

from ditalib.keyspacemgr import KeyspaceManager
from ditalib.keyspace import KeySpace
from ditalib.ditaval import DitavalFilter
from ditalib import loggingutils
from ditalib.loggingutils import ErrorRecord, SEVERITY

class DitaContext:
    """Maintains a number of DITA-specific properties needed to do DITA processing.

    The properties maintained are:

    * Key space: The key space to use for resolving keys
    * Key space manager: Maintains access to multiple key spaces. Needed
    when the processing involves multiple maps.
    * Map context: The current map context (map or topicref element)
    * Errors: Error collection for error reporting
    * DITAVAL filter: Element filter that applies zero or more DITAVALs
    * debug flag: Controls debugging

    The DITAContext object is passed to all methods and functions that
    need a context, which is most of them.

    """


    def __init__(self,
        keySpaceManager: KeyspaceManager,
        keySpace: KeySpace=None,
        mapContext: Element=None,
        ditavalFilter: DitavalFilter=None,
        errors:dict[str, ErrorRecord]={},
        debug:bool=False
        ):
        """Construct a new DITA context

        Args:

            keySpaceManager (KeyspaceManager): The keyspace manager to get key spaces from.
            Should be already initialized with at least one key space.

            keySpace (KeySpace, optional): The main key space to use. Defaults to the key space manager's root key space.

            mapContext (Element, optional): The map context to use for resolving keys and other map-related processing. Defaults to None.

            ditavalFilter (DitavalFilter, optional): DITAVAL filter to apply when processing DITA elements. Defaults to None.

            errors (dict[str, ErrorRecord], optional): Error holder for reporting. Defaults to {}.

            debug (bool, optional): Controls debug logging. Defaults to False.
        """

        self._errors = errors
        self._debug = debug
        self._keyspaceManager = keySpaceManager
        # Use the specified keyspace if provided, otherwise use the
        # manager's root key spaces
        self._keySpace = keySpace or keySpaceManager.getRootKeyspace()
        self._ditavalFilter = ditavalFilter or DitavalFilter(errors=errors,debug=debug)
        self._mapContext = mapContext

    def getKeyspaceManager(self) -> KeyspaceManager:
        return self._keyspaceManager

    def getKeyspace(self) -> KeySpace:
        return self._keySpace

    def getDitavalFilter(self) -> DitavalFilter:
        return self._ditavalFilter

    def getMapContext(self) -> Element:
        return self._mapContext

    def getErrors(self) -> dict[str, ErrorRecord]:
        return self._errors

    def getDebug(self) -> bool:
        return self._debug

    def setDebug(self, debug:bool) -> bool:
        """Turn debugging on or off

        Args:

            debug (bool): Set to True to turn debug logging on

        Returns:

            bool: New debug state
        """
        self._debug = debug
        return self._debug

    def setDitavalFilter(self, filter: DitavalFilter) -> None:
        """Set the DITAVAL filter for the context.

        Args:

            filter (DitavalFilter): The filter to set. Replaces any existing filter.
        """
        if filter is not None:
            self._ditavalFilter = filter
        else:
            # Set a do-nothing filter.
            self._ditavalFilter = DitavalFilter()


    def recordError(self, key: str, error: Exception, operation:str=None, severity:SEVERITY=SEVERITY.ERROR):
        """Record an error for future logging.

        Args:

            key (str): Key to associate the error with

            error (Exception): Exception to be recorded

            operation (str, optional): Operation that produced this error. Defaults to None.

            severity (SEVERITY, optional): Error severity. Defaults to SEVERITY.ERROR.
        """
        loggingutils.recordError(self.getErrors(), key, error, operation=operation, severity=severity)
