"""Tests for the xmlutils module
"""



from lxml import etree
from lxml.etree import Element, ElementTree, XMLParser

from ditalib import xmlutils

from .fixtures import resourcesDir, rootMap1Path

def test_getDTDAwareParser(rootMap1Path):
    parser: XMLParser = xmlutils.getDTDAwareParser()
    assert parser is not None, f'Expected to get a parser.'
    parsed: ElementTree = etree.parse(rootMap1Path, parser)
    assert parsed is not None, f'Expected to get a parsed document'
    elem: Element = parsed.getroot()
    assert elem is not None, f'Expected to get a root element'
    assert elem.get("class") is not None, f'Expected to get a @class attribute. Atts are {elem.attrib}'
    
def test_getNoDTDParser(rootMap1Path):
    parser: XMLParser = xmlutils.getNoDTDParser()
    assert parser is not None, f'Expected to get a parser.'
    parsed: ElementTree = etree.parse(rootMap1Path, parser)
    assert parsed is not None, f'Expected to get a parsed document'
    elem: Element = parsed.getroot()
    assert elem is not None, f'Expected to get a root element'
    assert elem.get("class") is None, f'Expected to not get a @class attribute. Atts are {elem.attrib}'
    