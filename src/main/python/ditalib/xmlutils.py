"""Utilities for working with XML data: parsers, etc.
"""

import os, sys
from lxml import etree
from lxml.etree import Element, ElementTree, XMLParser

import logging
from logging import Logger

from ditalib import config

logger: Logger = logging.getLogger("xmlutils")

# Configure the catalog path for DTD-aware parsing:
ditaOtDir = config.getDitaOtPath()
if ditaOtDir is None:
    logger.warn("Failed to get a DITA OT directory from the configuration. Run configure_ditalib.py to correct this.")
else:
    catalogPath = os.path.join(ditaOtDir, "catalog-dita.xml")
    os.environ["XML_CATALOG_FILES"] = catalogPath

# NOTE: Per the XMLParser docs, parsers should not be reused and there's
#       no performance cost to creating new parsers.

def getDTDAwareParser() -> XMLParser:
    """Gets an XML parser configured for DTD-aware parsing using the
    configured XML entity resolution catalog.

    Returns:

        XMLParser: Parser configured to do DTD-aware parsing.

    """
    parser = XMLParser(load_dtd=True, attribute_defaults=True)
    return parser

def getNoDTDParser() -> XMLParser:
    """Get a parser that does not do DTD-aware parsing.

    Returns:

        XMLParser: Parser configured to not do DTD-aware parsing.
    """
    parser = XMLParser(load_dtd=False, attribute_defaults=False)
    return parser
    
