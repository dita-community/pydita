"""Tests the DitaContext object"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

import pytest
from pydita import loggingutils
from pydita.loggingutils import ErrorRecord, SEVERITY
from pydita.ditacontext import DitaContext
from pydita.ditaval import DitavalFilter
from pydita import ditautils
from pydita import resolvemap
from pydita.keyspace import KeySpace
from pydita.keyspacemgr import KeyspaceManager

from lxml import etree
from lxml.etree import ElementTree
from lxml.etree import Element

# NOTE: You have to import all the fixtures that the fixtures
#       you're using also use. So we need to import resolvedMap
#       even though the test only asks for rootMap and keyspaceMgr
from .fixtures import resolvedMap, rootMap, keyspaceMgr, ditaContext

def test_ditaContext(rootMap: ElementTree, keyspaceMgr: KeyspaceManager):
    """Basic method tests"""

    context: DitaContext = DitaContext(keyspaceMgr)
    assert context.getKeyspaceManager() is keyspaceMgr, f'Expected same key space manager'
    assert context.getKeyspace() is keyspaceMgr.getRootKeyspace(), f'Expected root key space from key space manager'
    assert context.getDitavalFilter() is not None, f'Expected to get a DitavalFilter'
    assert context.getMapContext() is None, f'Expected no map context, got {context.getMapContext()}'
    assert context.getDebug() == False, f'Expected getDebug() to be False, got {context.getDebug()}'
    errors: dict[str, ErrorRecord] = context.getErrors()
    assert errors is not None, f'Expected to get an errors object'

    # Test setting of key space
    keySpace = keyspaceMgr.getRootKeyspace().getChildSpaces()[0]
    assert keySpace is not None, f'Need a child key space to test with. Expected to get one from the fixture.'
    context: DitaContext = DitaContext(keyspaceMgr, keySpace=keySpace)
    assert context.getKeyspace() is keySpace, f'Expected to get the new key space, got {context.getKeyspace()}'
    assert context.getKeyspace() is not keyspaceMgr.getRootKeyspace(), f'Expected different key spaces'

    # Test DITAVAl filter

    ditavalFilter: DitavalFilter = context.getDitavalFilter()
    assert ditavalFilter is not None, f'Expected to get a DitavalFilter'
    assert ditavalFilter.getErrors() is errors, f'Expected same errors object.'

    # Test setting debug:

    debug:bool = context.setDebug(False)
    assert not debug, f'Expected debug to be false, is {debug}'
    debug = context.setDebug(True)
    assert debug, f'Expected debug to be true, is {debug}'

def test_errorRecording(ditaContext: DitaContext):
    """Test error recording."""

    error: Exception = Exception("Error 1")
    key: str = "Key 1"
    ditaContext.recordError(key, error)

    report: str = loggingutils.reportErrors(ditaContext.getErrors())
    assert report is not None, f'Expected to get a report string'
    assert report.startswith('Have 1 total errors:'), f'Expected "Have 1 total errors:", got "{report}"'

    error: Exception = Exception("Error 2")
    key: str = "Key 2"
    ditaContext.recordError(key, error, "unit test")

    errors = ditaContext.getErrors()
    assert errors.get(key) is not None, f'Expected errors for key "{key}", errors: {errors}'
    assert len(errors.get(key)) == 1, f'Expected to have 1 error, got {len(errors.get(key))}'
    cand: ErrorRecord = errors.get(key)[0]
    assert isinstance(cand, ErrorRecord), f'Expected to get an ErrorRecord'
    assert str(cand) == '[ERROR] "Key 2" unit test: Error 2', f'[ERROR] Expected \'unit test: "Key 2" Error 2\'", got "{str(cand)}"'

    error: Exception = Exception("Error 3")
    ditaContext.recordError(key, error, operation="unit test", severity=SEVERITY.WARN)
    errors = ditaContext.getErrors()
    cand: ErrorRecord = errors.get(key)[1]
    expected: str = f'[WARN] "Key 2" unit test: Error 3'
    assert str(cand) == expected, f'Expected "{expected}", got "{str(cand)}"'
