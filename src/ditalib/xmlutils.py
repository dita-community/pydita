"""Utilities for working with XML using lxml.
"""

import os
from collections import namedtuple
from copy import deepcopy
from lxml import etree
from lxml.etree import Element, _Element
from lxml.etree import ElementTree, _ElementTree
from lxml.etree import XMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import pathname2url

from ditalib import config
from ditalib import loggingutils
from ditalib.loggingutils import ErrorRecord

# XML catalog path is configured lazily when getDTDAwareParser() is first called.
# Set DITA_OT_DIR environment variable (or dita.ot.dir in ~/.build.properties)
# to enable DTD-aware parsing with entity resolution.
_catalogConfigured = False


def _ensureCatalogConfigured() -> None:
    """Configure XML_CATALOG_FILES from the DITA OT path if not already done.

    Called lazily so that tests or callers can set DITA_OT_DIR before parsing.
    """
    global _catalogConfigured
    if _catalogConfigured:
        return
    _catalogConfigured = True

    ditaOtDir = config.getDitaOtPath()
    if ditaOtDir is not None:
        catalogPath = os.path.join(ditaOtDir, "catalog-dita.xml")
        escaped = pathname2url(catalogPath)
        os.environ["XML_CATALOG_FILES"] = escaped
    elif "XML_CATALOG_FILES" not in os.environ:
        import logging as _logging
        _logging.getLogger("ditalib.xmlutils").warning(
            "No DITA OT directory found. DTD-aware parsing will not resolve entities. "
            "Set DITA_OT_DIR or configure ~/.build.properties to fix this."
        )


def getDTDAwareParser(remove_comments: bool=False, remove_pis: bool=False) -> XMLParser:
    """Constructs an lxml parser configured with an XML catalog so DTD parsing will work.

    Args:

        remove_comments (bool): When True, comments are removed from parsed result. Defaults to False.

        remove_pis (bool): When True, processing instructions are removed from parsed result. Defaults to False.

    Returns:

        XMLParser: Parser configured for DTD-aware parsing.
    """
    _ensureCatalogConfigured()
    parser = XMLParser(load_dtd=True, attribute_defaults=True,
                       remove_comments=remove_comments, remove_pis=remove_pis)
    return parser


def getNoDTDParser(remove_comments: bool=True, remove_pis: bool=True) -> XMLParser:
    """Constructs an lxml parser configured with no DTD parsing.

    This parser is appropriate for use with topics. Note that @class
    attributes will not be set in the result documents.

    Args:

        remove_comments (bool): When True, comments are removed from parsed result. Defaults to True.

        remove_pis (bool): When True, processing instructions are removed from parsed result. Defaults to True.

    Returns:

        XMLParser: Parser configured to not do DTD-aware parsing.
    """
    return XMLParser(load_dtd=False, attribute_defaults=False,
                     remove_comments=remove_comments, remove_pis=remove_pis)


def getKeydefLinkTextElems(keyDefinition: Element) -> list:
    """Given a key definition, returns its link text elements.

    Args:

        keyDefinition (Element): The key definition to get the link text from.

    Returns:

        list[Element]: The link text elements
    """
    keywords = keyDefinition.xpath(
        "*[contains(@class, ' map/topicmeta ')]//*[contains(@class, ' topic/keywords ')]"
    )
    return keywords


def getKeydefLinkTextString(keyDef: Element) -> str:
    """Gets the effective string value of a key definition's link text.

    Args:

        keyDef (Element): The key definition to get the text for.

    Returns:

        str: The link text string with space normalized.
    """
    keywords: list = getKeydefLinkTextElems(keyDef)
    if len(keywords) > 0:
        rawText = "".join(keywords[0].itertext())
        return " ".join(rawText.split())
    return ""


def resolveUriRef(uri: str, context: Element, useDTDs: bool=False,
                  errors: dict=None, debug: bool=True) -> Element:
    """Resolve the specified URI string relative to the base URI of the context element.

    Must be a URI that is expected to resolve to an element.

    Args:

        uri (str): URI to be resolved to an element. May be relative or absolute.

        context (Element): Element to resolve URI relative to (i.e., topicref, xref, etc.)

        useDTDs (bool): When True, use a DTD-aware parser. Otherwise use the no-DTD parser.

        errors (dict): Dictionary to record errors in.

        debug (bool): Control debug logging.

    Returns:

        Element: The element the URI resolves to or None if the URI cannot be resolved.
    """
    absUri = urljoin(context.base, uri)
    uriParts = urlparse(absUri)
    path = uriParts.path
    fragid = uriParts.fragment
    if debug:
        print(f'[DEBUG] resolveUriRef(): uri=   "{uri}"')
        print(f'[DEBUG] resolveUriRef(): absUri="{absUri}"')
        print(f'[DEBUG] resolveUriRef(): path=  "{path}"')
        print(f'[DEBUG] resolveUriRef(): fragid="{fragid}"')

    parser = getDTDAwareParser() if useDTDs else getNoDTDParser()
    try:
        if debug:
            print(f'[DEBUG] resolveUriRef(): Using {"DTD parser" if useDTDs else "no DTD parser"}')
        doc: ElementTree = etree.parse(path, parser)
    except Exception as err:
        if errors is not None:
            loggingutils.recordError(errors, uri, err, operation="xmlutils.resolveUriRef()")
        if errors is None or debug:
            print(f'[ERROR] resolveUriRef(): Exception resolving "{uri}" to an element: {err}')
        return None

    docRoot: Element = doc.getroot()
    if fragid is None or fragid.strip() == "":
        return docRoot
    else:
        tokens: list = fragid.split("/")
        topicID = tokens[0]
        candidates: list = docRoot.xpath(f'(//*[@id = "{topicID}"])[1]')
        if len(candidates):
            targetTopic: Element = candidates[0]
            if debug:
                print(f'[DEBUG] resolveUriRef(): Found topic with ID "{topicID}", returning it.')
            return targetTopic
        else:
            if debug:
                print(f'[DEBUG] resolveUriRef(): No topic with ID "{topicID}", returning None.')
            return None


def copyElement(elem: Element, errors: dict={}) -> Element:
    """Shallow copy an element and its text (but not its child elements).

    Args:

        elem (Element): The element to copy

    Returns:

        Element: The shallow copy of the element.
    """
    tagName = elem.tag
    attDict = elem.attrib
    newElem = Element(tagName, attDict)
    newElem.text = elem.text
    newElem.tail = elem.tail
    return newElem


def deepCopyElement(elem: Element, errors: dict={}) -> _Element:
    """Deep copy an element and its descendants.

    Args:

        elem (Element): The element to copy

    Returns:

        _Element: The deep copy of the element and all its descendants.
                  Does not copy any tail text of the input element.
    """
    newElem: _Element = deepcopy(elem)
    newElem.tail = None
    return newElem


def getElementText(elem: Element, normalize: bool=True, errors: dict={}, debug: bool=False) -> str:
    """Gets the text of an element.

    Args:

        elem (Element): The element to get the text of.

        normalize (bool, optional): Normalize the resulting string. Defaults to True.

        errors (dict): Dictionary to store any errors.

        debug (bool): Controls debug logging.

    Returns:

        str: The string content of the element. If normalize is True, whitespace is normalized.
    """
    result = etree.tostring(elem, with_tail=False, encoding="unicode", method="text")
    if debug:
        print(f'+ [DEBUG] getElementText(): initial string="{result}"')
    if normalize:
        result = " ".join(result.split()).strip()
        if debug:
            print(f'+ [DEBUG] getElementText(): normalize is True, result="{result}"')
    if debug:
        print(f'+ [DEBUG] getElementText(): returning="{result}"')
    return result


def removeElement(elem: Element) -> None:
    """Remove an element from its parent, preserving any tail it might have.

    Args:
        elem (Element): The element to remove
    """
    parent = elem.getparent()
    if elem.tail and elem.tail.strip():
        prev = elem.getprevious()
        if prev is not None:
            prev.tail = (prev.tail or '') + elem.tail
        else:
            parent.text = (parent.text or '') + elem.tail
    parent.remove(elem)
