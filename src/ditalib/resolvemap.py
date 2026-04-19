# Resolves DITA maps to single documents

from io import IOBase
import os
from typing import Union
from copy import deepcopy
from lxml import etree
from lxml.etree import Element
from lxml.etree import ElementTree
from lxml.etree import XMLParser
from lxml.etree import ParseError
from urllib.parse import urljoin

from ditalib import xmlutils
from ditalib import loggingutils
from ditalib.loggingutils import ErrorRecord

from ditalib.ditaval import DitavalFilter

SUBMAP_TOPICGROUP_ELEM = Element("topicgroup",
                                {
                                    "class": "+ map/topicref mapgroup-d/topicgroup ",
                                    "base": "submap"
                                })

NS_DITAARCH = "http://dita.oasis-open.org/architecture/2005/"

def resolveMap(
    rootmap: Union[IOBase,ElementTree,str],
    ditavalFilter=DitavalFilter(),
    errors={},
    debug:bool=False) -> ElementTree:
    """Resolves a tree of DITA maps to a single XML document. Returns an ElementTree object.

    Args:

        rootmap (file|ElementTree|str): The root DITA map document to resolve. Can be specified as
                                        a file-like object (IOBase), an Element or ElementTree, or
                                        a string that is the path to the map.

        ditavalFilter (DitavalFilter): Filter to use when resolving the map. Resolved map will only reflect
                                       elements filtered in. Default is a null filter.

        errors (dict): Holds any reported errors

        debug (bool): Controls debug logging.
    """

    mapFile = None
    parsedMap = None
    if debug:
        print(f'[DEBUG] resolveMap(): rootmap parameter: {rootmap}')
    if isinstance(rootmap, IOBase):
        if debug:
            print(f'[DEBUG] resolveMap(): rootmap is a file, setting it to mapFile')
        mapFile = rootmap
    elif rootmap.__class__.__name__.startswith("_Element"):
        if debug:
            print(f'[DEBUG] resolveMap(): rootmap is an Element or ElementTree, setting it to parsedMap')
        parsedMap = rootmap
    elif isinstance(rootmap, str):
        if debug:
            print(f'[DEBUG] resolveMap(): rootmap is a str, treating it as a path to a file.')
        mapFile = open(rootmap, "r")
    else:
        raise Exception(f'Value {rootmap} for rootmap parameter of resolveMap() is not a recognized type.')

    if parsedMap is None:
        if debug:
            print(f'[DEBUG] resolveMap(): ditamap not yet parsed; parsing {mapFile.name}"')
        parser = xmlutils.getDTDAwareParser()
        # FIXME: Probably need some error checking and reporting here to catch parsing errors
        #        in a useful way.
        try:
            parsedMap = etree.parse(mapFile, parser)
        except ParseError as err:
            loggingutils.recordError(errors, mapFile.name, err, operation="resolveMap()")

    if parsedMap is None:
        raise Exception(f'Failed to parse the input map', rootmap)

    rootElem = parsedMap.getroot()
    resolvedRoot = Element(rootElem.tag, rootElem.attrib)
    resolvedRoot.base = rootElem.base
    resolvedMap = ElementTree(resolvedRoot)
    for child in rootElem:
        copyElement(child, resolvedRoot, ditavalFilter, errors=errors)
    return resolvedMap

def copyElement(elem: Element, parent: Element, ditavalFilter: DitavalFilter, errors: dict[str, ErrorRecord]={}):
    """Copy an element, resolving any map references

    Args:

        elem (Element): The input root map element

        parent (Element): The parent to add the copy to

        ditavalFilter (DitavalFilter): The filter to apply to elements as they are copied.

        errors: (dict): Holds any reported errors

    """

    # If element is filtered out, don't do anything with it.
    if ditavalFilter.isExcluded(elem):
        return

    scope = elem.get("scope", "local")
    if elem.get("format") == "ditamap" and scope == "local":
        resolveSubmap(elem, parent, ditavalFilter, errors=errors)
    elif elem.tag is etree.Comment or elem.tag is etree.ProcessingInstruction:
        parent.append(deepcopy(elem))
    else:
        # Make a shallow copy of the element:
        newElem = xmlutils.copyElement(elem, errors=errors)
        parent.append(newElem)
        for child in elem:
            copyElement(child, newElem, ditavalFilter, errors=errors)

def resolveSubmap(elem: Element, parent: Element, ditavalFilter:DitavalFilter, errors: dict={}, debug:bool=False):
    """Resolve a map reference to its submap, creating a new topicgroup element

    The topicgroup captures the details of the original map element.

    Args:

        elem (Element): Source element. Must be a map reference (format="ditamap")

        parent (Element): The parent to add the resolved submap to

        ditavalFilter (DitavalFilter): The filter to apply to elements as they are copied.

        errors (dict): Holds any reported errors

        debug (bool): Controls debug logging
    """

    href = elem.get("href")
    # Get any keyscopes specified on the map reference
    keyscopeValue: str = elem.get("keyscope")
    keyscopes: set[str] = set() if keyscopeValue is None else set(keyscopeValue.split(" "))
    baseUri = elem.base
    mapUri = urljoin(baseUri, href)
    if debug:
        print(f'[DEBUG] resolveSubmap(): mapUri: {mapUri}')

    parser = xmlutils.getDTDAwareParser()
    try:
        submapDoc = etree.parse(mapUri, parser)
    except ParseError as err:
        if debug:
            print(f'[DEBUG] Exception parsing submap "{mapUri}": {err}')
        # loggingutils.recordError(errors, mapUri, err, operation="resolveSubmap()")
        raise err

    submap = submapDoc.getroot()
    keyscopeValue = submap.get("keyscope")
    if keyscopeValue is not None:
        keyscopes.update(keyscopeValue.split(" "))
    topicGroup = Element(SUBMAP_TOPICGROUP_ELEM.tag, SUBMAP_TOPICGROUP_ELEM.attrib)
    parent.append(topicGroup)
    parent = topicGroup
    # Set the topicgroup elements xml:base to that of the submap so that
    # relative references will resolve without having to be rewritten.
    parent.base = mapUri
    if submap.get("base"):
        newBaseAtt = parent.get("base") + " " + submap.get("base")
        parent.set("base", newBaseAtt)
    # Remember the mapref's class
    parent.set("orig-class", elem.get("class"))
    # Copy all the relevant attributes from the map element to the submap
    # topicgroup:
    MAP_ATTS_TO_IGNORE = ["class", "base", "href", "domains", "keyscope"
                      "{http://dita.oasis-open.org/architecture/2005/}DITAArchVersion"]
    MAPREF_ATTS_TO_IGNORE = MAP_ATTS_TO_IGNORE
    MAPREF_ATTS_TO_IGNORE.append("format")
    # Get the attributes from the referenced map
    for key in submap.attrib.keys():
        if key not in MAP_ATTS_TO_IGNORE:
            attVal = submap.get(key)
            parent.set(key, attVal)
    # Get the attributes from the map reference
    for key in elem.attrib.keys():
        if key not in MAPREF_ATTS_TO_IGNORE:
            attVal = elem.get(key)
            parent.set(key, attVal)
    if len(keyscopes) > 0:
        parent.attrib["keyscope"] = " ".join(keyscopes)
    # Capture the original @href attribute:
    topicGroup.set('orig-href', href)

    # Make map title contents the navtitle for topicgroup (won't be rendered in output):
    titleElem = submap.xpath("*[contains(@class, ' topic/title ')]")
    newTopicmeta = None
    newNavtitle = None
    # Construct a new navtitle if there is a title:
    if len(titleElem):
        title = titleElem[0]
        newNavtitle = etree.SubElement(parent, "navtitle", attrib={"class": "- topic/navtitle "})
        newNavtitle.text = title.text
        for child in title:
            newNavtitle.append(deepcopy(child))
    # See if there is an existing topicmeta element in the submap:
    nodelist = submap.xpath("*[contains(@class, ' map/topicmeta ')]")
    topicMeta = nodelist[0] if nodelist else None
    # Possible conditions are:
    # 1. topicmeta in submap and no title
    # 2. topicmeta in submap and title
    # 3. no topicmeta in submap and title
    # 4. no topicmeta in submap and no title
    if topicMeta is None and newNavtitle is None:
        # No topicmeta and no title, so nothing to do.
        if debug:
            print(f'[DEBUG] resolveSubmap(): No topicmeta and no title.')
        return
    # If we have a new navtitle or we have topicmeta, create a new topicmeta element.
    if topicMeta is not None or newNavtitle is not None:
        newTopicmeta = etree.SubElement(parent, "topicmeta", attrib={"class": "- map/topicmeta "})
    # If we have a new navtitle, add it to the new topicmeta element:
    if newNavtitle is not None:
        newTopicmeta.append(newNavtitle)
    if newNavtitle is None:
        if debug:
            print(f'[DEBUG] resolveSubmap(): No title for submap.')

    # If we have existing topicmeta, copy it to the new topicmeta:
    if topicMeta is not None:
        for child in topicMeta:
            newTopicmeta.append(deepcopy(child))
    # Handle any topicrefs or reltables (should be only thing that can occur following
    # the map's topicmeta):
    for child in submap.xpath("*[contains(@class, ' map/topicref ')] | *[contains(@class, ' map/reltable ')]"):
        copyElement(child, parent, ditavalFilter, errors=errors)
