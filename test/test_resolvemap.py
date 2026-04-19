"""Unit tests for the resolvemap.py library
"""

from io import IOBase
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

from lxml import etree
from lxml.etree import Element
from lxml.etree import ElementTree

from pydita import resolvemap
from pydita import xmlutils
from pydita import loggingutils

from .fixtures import rootMap

def test_resolve_map(rootMap: IOBase):
    resolvedMap = resolvemap.resolveMap(rootMap)
    assert resolvedMap is not None, f'Expected to get a resolved map from rootMap'
    print("resolvedMap")
    # This assert fails even though resolvedMap is clearly and ElementTree instance
    # assert(isinstance(resolvedMap, type(ElementTree)))
    mapElem = resolvedMap.getroot()
    assert mapElem is not None, "Expected a root element"
    assert mapElem.tag == "map", f'Expected a map element, got {mapElem.tag}'
    assert mapElem.get("class") is not None, "Expected an @class attribute"
    assert mapElem.get("class").find(" map/map "), f'Expected map/map in @class value, got {mapElem.get("class")}'
    mapTitle = mapElem.xpath("./*[contains(@class, ' topic/title ')]")
    mapTitleElem = None
    if mapTitle is not None:
        mapTitleElem = mapTitle[0]
    assert mapTitleElem is not None, "Expected a map title"
    assert mapTitleElem.text == "Root Map 01", "Expected map title text"
    submap = mapElem.xpath(".//*[contains(@base, 'submap')][1]")
    submapElem = None
    if submap is not None:
        submapElem = submap[0]

    assert submapElem is not None, "Expected submap element in the resolved map"
    assert submapElem.get("keyscope"), "Expected a keyscope attribute"
    # Verify that the second submap has topicmeta
    submap = mapElem.xpath(".//*[contains(@base, 'submap')][2]")
    submapElem = None
    if submap is not None:
        submapElem = submap[0]
    assert submapElem is not None, "Expected submap element in the resolved map for 2nd submap"
    list = submapElem.xpath("./*[contains(@class, ' map/topicmeta ')]")
    topicmeta = list[0] if list else None
    assert topicmeta is not None, "Expected a topicmeta element in the 2nd submap"
    child = topicmeta.getchildren()[0]
    assert child.tag == "keywords", f'Expected a keywords element, got {child.tag}'


def test_resolve_map_different_rootmap_types(rootMap: IOBase):
    """Test the ability to pass different kinds of things as the root map
    """
    debug: bool = False

    # Pass in a file:
    if debug:
        print(f'** Pass in a file {rootMap}')
    errors: dict[str] = {}
    resolvedMap = resolvemap.resolveMap(rootMap, errors=errors, debug=debug)
    print(loggingutils.reportErrors(errors))
    assert resolvedMap is not None, f'Expected to get a resolved map from rootMap element'
    mapElem = resolvedMap.getroot()
    assert mapElem.tag == "map", f'Expected a map element, got {mapElem.tag}'

    # Pass in a path to a map:
    if debug:
        print(f'** Pass in a path {rootMap.name}')
    errors: dict[str] = {}
    resolvedMap = resolvemap.resolveMap(rootMap.name, errors=errors, debug=debug)
    if debug:
        print(loggingutils.reportErrors(errors))
    assert resolvedMap is not None, f'Expected to get a resolved map from path to root map file'
    mapElem = resolvedMap.getroot()
    assert mapElem.tag == "map", f'Expected a map element, got {mapElem.tag}'

    # Pass in a parsed map
    if debug:
        print(f'** Pass in parsed map')
    parsedMap: ElementTree = etree.parse(rootMap.name)
    print(f'** Pass in parsed map {parsedMap}')
    errors: dict[str] = {}
    resolvedMap = resolvemap.resolveMap(parsedMap, errors=errors, debug=True)
    print(loggingutils.reportErrors(errors))
    assert resolvedMap is not None, f'Expected to get a resolved map from path to parsed root map'
    mapElem = resolvedMap.getroot()
    assert mapElem.tag == "map", f'Expected a map element, got {mapElem.tag}'

    # Pass in something that won't work
    debug = True
    if debug:
        print(f'** Pass in a dictionary')
    try:
        errors: dict[str] = {}
        resolvedMap = resolvemap.resolveMap(errors, errors=errors, debug=True)
    except Exception as err:
        if debug:
            print(f'Got expected exception from bad input to resolvemap():')
            print(err)
