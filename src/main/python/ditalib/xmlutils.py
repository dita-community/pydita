"""Utilities for working with XML data: parsers, etc.
"""

import os, sys
from lxml import etree
from lxml.etree import Element, ElementTree, XMLParser

import logging

def getDTDAwareParser() -> XMLParser:
    """Gets an XML parser configured for DTD-aware parsing using the
    configured XML entity resolution catalog.

    Returns:

        XMLParser: Parser configured to do DTD-aware parsing.

    """
    