"""Unit tests for the ditautils.py library
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

import pytest
from ditalib import loggingutils
from ditalib import xmlutils
from ditalib import ditautils
from ditalib import resolvemap
from ditalib.keyspace import KeySpace
from ditalib.keyspacemgr import KeyspaceManager
from ditalib.ditacontext import DitaContext
from ditalib.ditaval import DitavalFilter

from lxml import etree
from lxml.etree import ElementTree
from lxml.etree import Element


from .fixtures import rootMap, resolvedMap, keyspaceMgr, topic01, rootKeySpace, ditaContext


def test_getDirectFilesFromMap(rootMap, resolvedMap):
    debug:bool = True
    errors: dict[str] = {}
    files: dict = ditautils.getDirectFilesFromMap(resolvedMap, errors=errors, debug=debug)
    assert files is not None, f'Expected to get a result'
    assert not False in (key in ["topics", "maps", "nondita"] for key in files.keys()), f'Unexpected dictionary keys: {files.keys()} '
    assert len(errors) == 0, f'Expected no errors, got: {errors}'

    topics: set[str] = files["topics"]
    assert topics is not None, f'Expected topics'
    assert len(topics) == 15, f'Expected 15 topics, found {len(topics)}'
    assert not False in (f.endswith(".dita") for f in topics), f'Expected .dita files, got {topics}'

    nondita: set[str] = files["nondita"]
    assert nondita is not None, f'Expected nondita'
    assert len(nondita) == 1, f'Expected 1 nondita, found {len(nondita)}'
    assert not False in (f.endswith(".png") for f in nondita), f'Expected a .png file.'

    maps: set[str] = files["maps"]
    assert maps is not None, f'Expected maps'
    assert len(maps) == 3, f'Expected 3 maps, found {len(maps)}'
    assert not False in (f.endswith(".ditamap") for f in maps), f'Expected .ditamap files'

def test_getConrefTargets(resolvedMap):
    files: dict = ditautils.getDirectFilesFromMap(resolvedMap)
    conrefTargets: set[str] = ditautils.getConrefTargets(files["topics"])
    print(f'DEBUG: conrefTargets:')
    print(conrefTargets)
    assert conrefTargets is not None, f'Expected to get a conref targets set'
    assert len(conrefTargets) == 2, f'Expected 2 direct conref target, got {len(conrefTargets)}'

def test_getConrefTargetsRecursive(resolvedMap):
    debug:bool = False
    files: dict = ditautils.getDirectFilesFromMap(resolvedMap)
    conrefTargets: set[str] = ditautils.getConrefTargetsRecursive(files["topics"], debug=debug)
    assert conrefTargets is not None, f'Expected to get a conref targets set'
    filenames: list[str] = list(map(lambda path : os.path.basename(path), conrefTargets))
    assert len(conrefTargets) == 5, f'Expected 5 total conref targets, got {len(conrefTargets)} ({filenames})'
    expected: list[str] = ['reuse-02.dita', 'reuse-05.dita', 'reuse-03.dita', 'reuse-04.dita', 'reuse-01.dita']
    assert all(x in expected for x in filenames), f'Expected {expected}, got {filenames}'


def test_getXrefTargets(resolvedMap):
    debug:bool = False
    files: dict = ditautils.getDirectFilesFromMap(resolvedMap,debug=debug)
    xrefs: set[str] = ditautils.getXrefTargets(files["topics"],debug=debug)
    assert xrefs is not None, f'Expected an xrefs set.'
    print(f'xrefs:')
    print(xrefs)
    # NOTE: We should not get the <xref> elements from the XBL in topic-01.dita, which
    #       would give us 5 or more xrefs.
    assert len(xrefs) == 4, f'Expected 4 xrefs, got {len(xrefs)}.'
    basenames = []
    for path in xrefs:
        basenames.append(os.path.basename(path))
    expected: list[str] = ["sub-01-topic-01.dita", "sub-02-topic-01.dita", 'sub-01-topic-03.dita', 'topic-04.dita']
    assert all(x in expected for x in basenames), f'Expected {expected}, got {basenames}'
    assert not all(x in ["sub-01-topic-02.dita"] for x in basenames), f'Expected sub-01-topic-02.dita to not be in targets, got {basenames}'


def test_getReferencedImages(resolvedMap):
    files: dict = ditautils.getDirectFilesFromMap(resolvedMap)
    images: set[str] = ditautils.getReferencedImages(files["topics"])
    assert images is not None, f'Expected an images set.'
    # image-02.png is referenced in two different topics. The set
    # should result in exactly one occurrence of it.
    assert len(images) == 1, f'Expected 1 image, got {len(images)}.'
    assert not False in (f.endswith("image-02.png") for f in images), f'Expected image-02.png file, got {images}'

def test_resolveStringKeyrefs(topic01: Element, rootKeySpace: KeySpace):
    errors = {}
    keySpace: KeySpace = rootKeySpace

    # Test that the tail text of a nested subelement is correctly returned following
    # expansion of a keyref that is followed by literal text.

    topic05: Element = rootKeySpace.resolveKeyToResource("topic-05")
    assert topic05 is not None, "Expected to get a topic for key 'topic-05"

    titleElem = topic05.find('title')
    assert titleElem is not None, f'Expected to get a title element'
    beforeText = etree.tostring(titleElem, method="text", with_tail=False, encoding="unicode")
    assert beforeText is not None, f'Expected to get the title text'
    expected = "Integrations release notes"
    # Strip leading and trailing space to make our check easier.
    beforeText = beforeText.strip()
    assert beforeText == expected, f'Expected text "{expected}", got "{beforeText}"'
    ditautils.resolveStringKeyrefs(titleElem, keySpace, debug=True)
    afterText = etree.tostring(titleElem, method="text", with_tail=False, encoding="unicode")
    assert afterText is not None, f'Expected to get the title text'
    afterText = afterText.strip()
    expected = "Service Bridge Integrations release notes"
    assert afterText == expected, f'Expected text "{expected}", got "{afterText}"'

    # Test string-01 resolution
    titleElem = topic01.find('title')
    assert titleElem is not None, f'Expected to get a title element for topic01'
    errors: dict = {}
    assert len(errors.keys()) == 0, "Got an error from resolveStringKeyrefs()"
    # By default, resolveStringKeyrefs() only resolves references to keys with a "var."
    # scope qualifier, so we expect the reference to "string-01" to fail here:
    expected = "Topic 01"
    titleText = xmlutils.getElementText(titleElem, normalize=True, errors=errors)
    assert len(errors.keys()) == 0, "Got an error from getElementText"
    assert titleText == expected, f'Expected "{expected}", got "{titleText}"'
    # Now do the same check, but passing in None for stringKeyScope:
    ditautils.resolveStringKeyrefs(titleElem, keySpace, stringKeyScope=None, errors=errors)
    expected = "Topic 01 Value of string-01"
    titleText = xmlutils.getElementText(titleElem, normalize=True, errors=errors)
    assert titleText == expected, f'Expected "{expected}", got "{titleText}"'

def test_getElementText(topic01: Element, rootKeySpace: KeySpace):
    """Test the getElementText() function
    """
    titleElem: Element = topic01.find('title')
    debug = True
    assert titleElem is not None, f'Expected to get a title element'
    # Default is normalized text:
    text: str = ditautils.getElementText(titleElem, rootKeySpace, debug=debug)
    assert text is not None, f'Expected to get the title text'
    expected: str = f'Topic 01'
    assert text == expected, f'Expected text "{expected}", got "{text}"'

def test_makeTopichead():
    """Test getTopichead() function.
    """

    topichead: Element = ditautils.makeTopichead("the title")
    assert topichead is not None, f'Expected a topichead element'
    topicmeta: Element = topichead.find('topicmeta')
    assert topicmeta is not None, f'Expected a topicmeta element'
    navtitle: Element = topicmeta.find('navtitle')
    assert navtitle is not None, f'Expected a navtitle element'
    assert navtitle.text == "the title", f'Expected "the title" text, got "{navtitle.text}"'

def test_isClass():
    elem = Element("foo", {"class": "- topic/p my-d/somep "})
    assert ditautils.isClass(elem, "topic/p"), "Expected True for topic/p"
    assert ditautils.isClass(elem, "my-d/somep"), "Expected True for my-d/somep"
    assert not ditautils.isClass(elem, "topc/param"), "Expected False for topic/param"

    elem = Element("foo", {})
    assert not ditautils.isClass(elem, "topc/p"), "Expected False for topic/p"

def test_isPeerMapref():
    # Start with no scope, format, or keyscope
    elem = Element("topicref", {"class": "- map/topicref mapgroup-d/mapref "})
    assert not ditautils.isPeerMapref(elem), f'Expected false for mapref with no scope, format, or keyscope attributes'
    elem.set("scope", "local")
    assert not ditautils.isPeerMapref(elem), f'Expected false for mapref with no scope = "local"'
    elem.set("scope", "peer")
    assert not ditautils.isPeerMapref(elem), f'Expected false for mapref with no format or keyscope'
    elem.set("format", "ditamap")
    assert not ditautils.isPeerMapref(elem), f'Expected false for mapref with no keyscope'
    elem.set("keyscope", "scope-01")
    elem.attrib.pop("format")
    assert not ditautils.isPeerMapref(elem), f'Expected false for mapref with keyscope but no format'
    elem.set("format", "ditamap")
    assert not ditautils.isPeerMapref(elem), f'Expected false for mapref with no href '
    elem.set("href", "some-uri")
    assert ditautils.isPeerMapref(elem), f'Expected true for mapref with all attributes '
    elem.attrib.pop("format")
    assert not ditautils.isPeerMapref(elem), f'Expected false for topicref with no format '
    elem.tag = "mapref"
    assert ditautils.isPeerMapref(elem), f'Expected true for mapref with no format '
    elem.tag = "topicref"
    elem.set("format", "dita")
    assert not ditautils.isPeerMapref(elem), f'Expected false for topicref with format of "dita"'

def test_getTopicrefsToTopics(rootMap, resolvedMap):
    debug:bool = True
    errors: dict[str] = {}
    files: dict = ditautils.getTopicrefsToTopics(resolvedMap, errors=errors, debug=debug)
    assert files is not None, "Expected to get a files list, got None"
    assert len(files) > 0, "Expected to get at least one item in files list, got nothing."
    topicref: Element = files[0]
    href: str = topicref.get('href')
    assert href is not None, "Expected to get an @href value, got None"
    assert href.endswith(".dita"), f'Expected href to end with ".dita", got "{href}"'
