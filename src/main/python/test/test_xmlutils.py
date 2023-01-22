"""Tests for the xmlutils module
"""



from lxml import etree
from lxml.etree import Element, ElementTree, XMLParser

from ditalib import xmlutils


def test_getDTDAwareParser():
    parser: XMLParser = xmlutils.getDTDAwareParser()
    assert parser is not None, f'Expected to get a parser.'