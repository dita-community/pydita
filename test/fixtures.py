"""Common test fixtures
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

import pytest
from pydita import ditaenv
from pydita import xmlutils
from pydita import ditautils
from pydita import resolvemap
from pydita.keyspacemgr import KeyspaceManager
from pydita.keyspace import KeySpace
from pydita.ditacontext import DitaContext
from pydita.ditaval import DitavalFilter
from lxml import etree
from lxml.etree import ParseError
from lxml.etree import ElementTree
from lxml.etree import Element
from io import IOBase

@pytest.fixture
def resourcesDir() -> str:
    """Gets the resources directory path for test cases.

    Returns:

        str: The resources directory path
    """
    return os.path.join(os.path.dirname(__file__), "resources")

@pytest.fixture
def rootMap1Path(resourcesDir) -> str:
    """The path to root map 1.

    Returns:

        str: path to the root-map-01.ditamap file.
    """
    return os.path.join(resourcesDir, "dita", "root_map_1.ditamap")

@pytest.fixture
def outdir() -> str:
    """Directory to persistently write output files to.

    Defaults to "out" under the user home directory.

    Returns:
        str: Directory to write output to
    """

    outdir = os.path.join(os.environ["HOME"], 'out')
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    return outdir

@pytest.fixture
def rootMap() -> IOBase:
    """File object for the root map.
    """
    rootMap = open(os.path.join(SCRIPT_DIR, "resources/root-map-01.ditamap"), "r")
    assert rootMap is not None, f'Expected to get a map'
    return rootMap

@pytest.fixture
def rootMap02() -> IOBase:
    """File object for root map 2.
    """
    rootMap = open(os.path.join(SCRIPT_DIR, "resources/root-map-02.ditamap"), "r")
    assert rootMap is not None, f'Expected to get a map'
    return rootMap

@pytest.fixture
def resolvedMap(rootMap) -> ElementTree:
    """Resolved map as an ElementTree
    """
    resolvedMap: ElementTree = resolvemap.resolveMap(rootMap)
    return resolvedMap

@pytest.fixture
def keyspaceMgr(resolvedMap: ElementTree) -> KeyspaceManager:
    """Keyspace manager for the resolved map
    """
    keyspaceMgr: KeyspaceManager = KeyspaceManager(resolvedMap)
    return keyspaceMgr

@pytest.fixture
def rootKeySpace(keyspaceMgr: KeyspaceManager) -> KeySpace:
    """The root keyspace constructed from the root map.
    """

    return keyspaceMgr.getRootKeyspace()

@pytest.fixture
def topic01(rootKeySpace: KeySpace) -> Element:
    """Topic `topic-01.dita` from the root map as retrieved from the root keyspace using key "topic-01"

    Args:
        rootKeySpace (KeySpace): _description_

    Returns:
        Element: _description_
    """
    topic01 = rootKeySpace.resolveKeyToResource("topic-01")
    assert topic01 is not None, "fixtures.topic01(): Failed to get topic for key 'topic-01'"
    return topic01

@pytest.fixture
def filteredTopic01() -> Element:
    topicFile = open(os.path.join(SCRIPT_DIR, "resources/topics/filtered-topic-01.dita"), "r")
    doc: ElementTree = etree.parse(topicFile, xmlutils.getNoDTDParser())
    return doc.getroot()

@pytest.fixture
def flaggedTopic01() -> Element:
    topicFile = open(os.path.join(SCRIPT_DIR, "resources/topics/flagged-topic-01.dita"), "r")
    doc: ElementTree = etree.parse(topicFile, xmlutils.getNoDTDParser())
    return doc.getroot()

@pytest.fixture
def ditaContext(keyspaceMgr: KeyspaceManager) -> DitaContext:
    return DitaContext(keyspaceMgr)

@pytest.fixture
def recursiveKeydefMap() -> IOBase:
    mapFile = open(os.path.join(SCRIPT_DIR, "resources/recursive-keydef.ditamap"), "r")
    return mapFile
