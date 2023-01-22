"""Object that maintains DITA-related context for use in DITA-aware
processing of DITA elements.
"""

from lxml import etree
from lxml.etree import Element

from ditalib.logging import Errors

class DitaContext:
    """Provides access to current context needed to do DITA processing.
    """

    def __init__(self):
        self._mapcontext: Element = None
        self._ditavalFilter: DitavalFilter = DitavalFilter()
        self._errors: Errors = Errors()