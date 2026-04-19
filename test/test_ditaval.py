"""Tests the DitavalFilter object"""
from io import IOBase
import os
import sys
from datetime import datetime
from xmlrpc.client import DateTime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

import pytest
from pydita import loggingutils
from pydita import ditaenv
from pydita.loggingutils import ErrorRecord
from pydita.ditacontext import DitaContext
from pydita.ditaval import DitavalFilter
from pydita.ditaval import DitavalCondition
from pydita import ditautils
from pydita import resolvemap
from pydita.keyspace import KeySpace
from pydita.keyspacemgr import KeyspaceManager
from pydita import ditaval
from pydita import ditavalvisitors
from pydita.ditavalvisitors import ExcelGeneratingDitavalVisitor

from lxml import etree
from lxml.etree import ElementTree
from lxml.etree import Element

# NOTE: You have to import all the fixtures that the fixtures
#       you're using also use. So we need to import resolvedMap
#       even though the test only asks for rootMap and keyspaceMgr
from .fixtures import rootKeySpace, resolvedMap, rootMap, keyspaceMgr, ditaContext, topic01, filteredTopic01, flaggedTopic01

def test_conditions():
    """Test creation of Conditions in a filter"""

    filter: DitavalFilter = DitavalFilter([], debug=False)
    condition: DitavalCondition = filter.addCondition("audience")
    assert condition is not None, f'Expected to get a Condition object'
    assert condition.getName() == "audience", f'Expected condition name "audience", got "{condition.getName()}"'
    condition.setDefaultAction(False)
    assert condition.getDefault() == False, f'Expected default of False", got "{condition.getDefault()}"'
    assert not condition.isIncluded("foo"), f'Expected undefined condition value "foo" to be excluded'
    condition.addValue("foo", True)
    assert condition.isIncluded("foo"), f'Expected undefined condition value "foo" to be included'
    elem:Element = etree.Element("p", {"audience": "foo"})
    assert filter.isIncluded(elem), 'Expected element {etree.tostring(elem, encoding="unicode")} to be included'
    assert DitavalCondition.getActionStr(False) == "exclude", f'Expected "exnclude" for False, got "{DitavalCondition.getActionStr(False)}"'
    assert DitavalCondition.getActionStr(True) == "include", f'Expected "include" for True, got "{DitavalCondition.getActionStr(True)}"'
    elem:Element = etree.Element("p", {"audience": "bar"})
    assert not filter.isIncluded(elem), f'Expected audience="bar" to be excluded.'
    elem:Element = etree.Element("p", {"audience": "foo bar"})
    assert filter.isIncluded(elem), f'Expected audience="foo bar" to be included.'

    condition: DitavalCondition = filter.addCondition("product")
    condition.addValue("prod1", False)

    elem:Element = etree.Element("p", {"audience": "foo bar", "product": "prod1"})
    assert not filter.isIncluded(elem), f'Expected audience="foo bar", product="prod1" to be excluded.'
    assert filter.isExcluded(elem), f'Expected audience="foo bar", product="prod1" to be excluded.'

    elem:Element = etree.Element("p", {"audience": "foo bar", "product": "prod2"})
    assert filter.isIncluded(elem), f'Expected audience="foo bar", product="prod2" to be included.'


def test_DitavalFilter(resolvedMap: ElementTree, ditaContext: DitaContext):
    """Test DITAVAL filtering."""

    debug: bool = False
    resourceDir: str = os.path.join(os.path.dirname(__file__), 'resources')
    ditavalDir: str = os.path.join(resourceDir, 'ditaval')

    baseDitaval: IOBase = open(os.path.join(ditavalDir, 'base.ditaval'), 'r')
    noviceDitaval: str = os.path.join(ditavalDir, 'include-novice.ditaval')

    filter: DitavalFilter = DitavalFilter([baseDitaval, noviceDitaval], debug=debug)
    ditaContext.setDitavalFilter(filter)

    assert ditaContext.getDitavalFilter() is filter, f'Expected to get same filter back'

    ditavals: list[IOBase] = filter.getDitavals()
    assert len(ditavals) == 2, f'Expected 2 ditaval files, got {len(ditavals)}'

    propCondition: DitavalCondition = filter.getCondition("product")
    assert propCondition is not None, f'Expected to get condition "product"'
    prodValue: bool = propCondition.isIncluded("prod1")
    assert prodValue, f'Expected product="prod1" to be included, got {prodValue}'

    # Now do some filtering

    keySpace: KeySpace = ditaContext.getKeyspace()

    elem: Element = resolvedMap.xpath("//topicref[string(@audience) = 'novice']")[0]
    assert filter.isIncluded(elem), f'Expected element with audience="novice" to be included.'

    elem: Element = resolvedMap.xpath("//topicref[string(@audience) = 'expert']")[0]
    assert not filter.isIncluded(elem), f'Expected element with audience="expert" to be excluded.'
    assert filter.isExcluded(elem), f'Expected element with audience="expert" to be excluded.'

def test_parse_props_value():
    """Test parsing of @props values
    """

    propsValue = "cond1(foo) cond2(bar baz) cond3(fraz) cond1(fred) cond4()"

    result: dict[str, list[str]] = ditaval.parse_props_value(propsValue, debug=False)
    print(f'result={result}')
    assert result is not None, f'Expected to get a result.'
    # The cond4() should not result in an entry because it's equivalent to cond4="" in the XML
    expected: list[str] = ["cond1", "cond2", "cond3"]
    # Should have one entry for each condition name:
    assert all(x in list(result.keys()) for x in expected), f'Expected {expected}, got {list(result.keys())}'
    values: list[str] = result.get("cond1")
    assert values is not None, f'Expected to get some values, result is {result}'
    # The two separate items for cond1 should result in a combined list of values
    expected = ["foo", "fred"]
    assert all(x in expected for x in result.get("cond1")), f'Expected {expected}, got {result.get("cond1")}'
    expected = ["bar", "baz"]
    assert all(x in expected for x in result.get("cond2")), f'Expected {expected}, got {result.get("cond2")}'
    expected = ["fraz"]
    assert all(x in expected for x in result.get("cond3")), f'Expected {expected}, got {result.get("cond3")}'

def test_filter_element_unconditonal_topic(topic01: Element, filteredTopic01: Element):
    """Tests the filtering of complete elements and documents that
       has no conditional elements that might be filtered out.
    """
    # Create a new filter with one excluding condition:
    filter: DitavalFilter = DitavalFilter([], debug=False)
    condition: DitavalCondition = filter.getCondition("otherprops")
    assert condition is not None, "Expected to get condition 'otherprops'"
    condition.addValue("store-future", False)

    # Get the count of elements before applying the filter:
    elemCountBefore: int = topic01.xpath("count(//*)")

    # Now apply filtering, which updates the document in place:
    resultElem: Element = ditaval.filterElement(topic01, filter)
    assert resultElem is not None, "Expected to get result element back"
    assert resultElem is topic01, "Expected to get back the input element"

    elemCountAfter:  int = resultElem.xpath("count(//*)")
    assert elemCountAfter == elemCountBefore, f'Expected no change in element count, count after is {elemCountAfter}'

def test_filter_element_whole_topic(filteredTopic01: Element):
    """Tests what happens when the entire document is filtered out on the root element
    """
    # Create a new filter with one excluding condition:
    filter: DitavalFilter = DitavalFilter([], debug=False)
    condition: DitavalCondition = filter.getCondition("otherprops")
    assert condition is not None, "Expected to get condition 'otherprops'"
    condition.addValue("store-future", False)

    # Now apply filtering, which updates the document in place:
    resultElem: Element = ditaval.filterElement(filteredTopic01, filter)

    assert resultElem is None, "Expected the root element to be complete removed, but it was not"

def test_filter_elementree(filteredTopic01: Element):
    """Tests filtering using the ElementTree (document node) as input,
    rather than the root element of the document.
    """
    # This should get us the ElementTree from the root element of the doc:
    doc = filteredTopic01.getroottree()
    assert doc is not None, "Expected to have an ElementTree from getroottree()"

    filter: DitavalFilter = DitavalFilter([], debug=False)
    condition: DitavalCondition = filter.getCondition("otherprops")
    assert condition is not None, "Expected to get condition 'otherprops'"
    condition.addValue("store-future", False)

    # Now apply filtering, which updates the document in place:
    resultElem: Element = ditaval.filterElement(doc, filter)

    assert resultElem is None, "Expected the root element to be complete removed, but it was not"

def test_filter_element_subelements(filteredTopic01: Element):
    """Test filtering of individual elements.
    """
    # Create a new filter with one excluding condition:
    filter: DitavalFilter = DitavalFilter([], debug=False)
    condition: DitavalCondition = filter.getCondition("otherprops")
    assert condition is not None, "Expected to get condition 'otherprops'"
    # Explicitly include store-future so we retain the root element, but filter out store-2023-08
    condition.addValue("store-future", True)
    condition.addValue("store-2023-08", False)

    # Get the count of elements before applying the filter:
    elemCountBefore: int = filteredTopic01.xpath("count(//*)")
    cand: list[Element] = filteredTopic01.xpath("//*[@id = 'step-store-2023-08']")
    assert len(cand) == 1, "Expected find element with id 'step-store-2023-08'"

    # Now apply filtering, which updates the document in place:
    resultElem: Element = ditaval.filterElement(filteredTopic01, filter)

    assert resultElem is not None, "Expected to get the input element back"
    elemCountAfter: int = filteredTopic01.xpath("count(//*)")
    assert elemCountAfter < elemCountBefore, f'Expected count after to be less than before, before: {elemCountBefore}, after: {elemCountAfter}'

    cand = filteredTopic01.xpath("//*[@id = 'step-store-2023-08']")
    assert len(cand) == 0, "Expected to not find step filtered out for store-2023-08"
    condition = filter.addCondition("product")
    condition.addValue("utah", False)

    cand = filteredTopic01.xpath("//*[@id = 'step-utah-sandiego']")
    assert len(cand) == 1, "Expected find element with id 'step-utah-sandiego'"

    # This is a subtle one. The @product value is "utah sandiego". The value
    # "sandiego" is not explicitly filtered out so it's filtered in by default.
    # So even though "utah" is excluded the element should not be.
    resultElem = ditaval.filterElement(filteredTopic01, filter)
    cand = filteredTopic01.xpath("//*[@id = 'step-utah-sandiego']")
    assert len(cand) == 1, "Expected to still find element with id 'step-utah-sandiego'"

    # Now we also exclude "sandiego", so the element should be filtered out.
    condition.addValue("sandiego", False)
    resultElem = ditaval.filterElement(filteredTopic01, filter)
    cand = filteredTopic01.xpath("//*[@id = 'step-utah-sandiego']")
    assert len(cand) == 0, "Expected to not find element with id 'step-utah-sandiego'"

def test_filter_flagged_element(flaggedTopic01: Element):
    debug: bool = False
    resourceDir: str = os.path.join(os.path.dirname(__file__), 'resources')
    ditavalDir: str = os.path.join(resourceDir, 'ditaval')

    baseDitaval: IOBase = open(os.path.join(ditavalDir, 'base.ditaval'), 'r')
    noviceDitaval: str = os.path.join(ditavalDir, 'include-novice.ditaval')

    filter: DitavalFilter = DitavalFilter([baseDitaval, noviceDitaval], debug=debug)

    resultElem: Element = ditaval.filterElement(flaggedTopic01, filter)
    assert resultElem is not None, "Expected to get result element back"
