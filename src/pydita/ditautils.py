"""Utilities for working with DITA content

Provides functions that understand the DITA-specific rules.

All functions that involve parsing a document take the "errors"
parameter, which is a dictionary into which errors are recorded
(see recordError()) against the full path of the file being
parsed.
"""

from lxml.etree import ParseError
import os
import sys
from collections import namedtuple
from lxml import etree
from lxml.etree import Element
from lxml.etree import ElementTree
from lxml.builder import E

from urllib.parse import urljoin, urlparse

from pydita import xmlutils
from pydita import loggingutils
from pydita.loggingutils import ErrorRecord

# These types can't be imported because it would cause circular imports
# from pydita.keyspace import KeySpace
# from pydita.keyspace import KeyDefinition


def getDirectFilesFromMap(mapDoc: ElementTree, errors: dict={}, debug:bool=False) -> dict:
    """Returns the set of files directly referenced from a map by local-scope references.

    Args:
        mapDoc (ElementTree): The map to process.

        errors (dict): Dictionary to store any errors.

        debug (bool): Controls debug logging

    Returns:
        dict: Dictionary with the following fields, where each field is a set of
        absolute paths.

        topics: Set of topics referenced from the map

        maps: Set of maps referenced from the map

        nondita: Set of non-DITA files (images, etc.)

        errors: Dictionary to put any error messages in. Key is file path, value
                is one or more Exception objects.
    """

    result = {
        "topics": set(),
        "maps": set(),
        "nondita": set()
    }

    # Include the root map:

    result["maps"].add(mapDoc.getroot().base)

    # Get all local-scope references
    refs: list[Element] = mapDoc.xpath("//*[@href][string(@scope) =  '' or @scope = 'local']")
    for ref in refs:
        href = ref.get("href")
        format = ref.get("format")
        path = urlparse(href).path
        absPath = urljoin(ref.base, path)
        if format is None or format == "" or format == "dita":
            result["topics"].add(absPath)
        elif format == "ditamap":
            result["maps"].add(absPath)
        else:
            result["nondita"].add(absPath)

    submaps: list[Element] = mapDoc.xpath("//*[string(@base) = 'submap']")
    for submap in submaps:
        result["maps"].add(submap.base)

    return result

def getConrefTargets(topics: set[str], errors: dict={}, debug:bool=False) -> set[str]:
    """Finds conref target topics in topics.

    Args:
        topics (set[str]): The topics to get conref targets from

        errors (dict): Dictionary to store any errors.

        debug (bool): Controls debug logging

    Returns:

    set of absolute file paths
    """
    result: set[str] = set()

    # Process the topics
    for topic in topics:
        if debug:
            print(f'+ [DEBUG] getConrefTargets(): topic="{topic}"')
        try:
            topicDoc = etree.parse(topic, xmlutils.getNoDTDParser())
        except Exception as err:
            loggingutils.recordError(errors, topic, err, operation="ditautils.getConrefTargets()")
            print(f'- [ERROR] getConrefTargets(): {err} from topic "{topic}": {err}')
            continue
        conrefs: list[Element] = topicDoc.xpath("//*[@conref]")
        if debug:
            print(f'+ [DEBUG] getConrefTargets(): Found {len(conrefs)}"')
        for conref in conrefs:
            ref = conref.get("conref")
            path = urlparse(ref).path
            if path == "" or path is None:
                if debug:
                    print(f'[DEBUG] path from @conref value "{ref}" is empty, ignoring it.')
                continue
            targetPath = urljoin(conref.base, path)
            result.add(targetPath)
    if debug:
        print(f'+ [DEBUG] getConrefTargets(): Returning {result}"')
    return result

def getConrefTargetsRecursive(topics: set[str], errors: dict={}, debug:bool=False) -> set[str]:
    """Get the conref targets from a set of topics, recursively.

    Looks for conref targets in the conref targets found in the initial
    set of topics.

    Args:
        topics (set[str]): The topics to look for conrefs in.

        errors (dict): Dictionary to store any errors.

        debug (bool): Controls debug logging

    Returns:
        set[str]: The files that are conref targets.
    """
    if debug:
        filenames: list[str] = list(map(lambda path : os.path.basename(path), topics))
        print(f'+ [DEBUG] getConrefTargetsRecursive(): topics: {filenames}')
    conref_files: set[str] = getConrefTargets(topics, errors=errors)
    if debug:
        filenames: list[str] = list(map(lambda path : os.path.basename(path), conref_files))
        print(f'+ [DEBUG] getConrefTargetsRecursive(): conref_files: {filenames}')
    # Get conref files referenced from first set of conref files
    more_conref_files: set[str] = getConrefTargets(conref_files, errors=errors)
    if debug:
        filenames: list[str] = list(map(lambda path : os.path.basename(path), more_conref_files))
        print(f'+ [DEBUG] getConrefTargetsRecursive(): more_conref_files: {filenames}')
    conref_files.update(more_conref_files)
    if debug:
        filenames: list[str] = list(map(lambda path : os.path.basename(path), conref_files))
        print(f'+ [DEBUG] getConrefTargetsRecursive(): After update, conref_files: {conref_files}')
    # Keep gathering new conref targets until we don't get any more.
    if more_conref_files is not None and len(more_conref_files):
        if debug:
            print(f'+ [DEBUG] getConrefTargetsRecursive(): more_conref_files is not None and not empty.')
        maxloops = 5
        ctr = 0
        more_conref_files = getConrefTargets(more_conref_files, errors=errors, debug=debug)
        if debug:
            filenames: list[str] = list(map(lambda path : os.path.basename(path), more_conref_files))
            print(f'+ [DEBUG] getConrefTargetsRecursive(): [{ctr}] more_conref_files: {more_conref_files}')
            print(f'+ [DEBUG] getConrefTargetsRecursive():         adding {more_conref_files} to {conref_files} (.update())')
        conref_files.update(more_conref_files)
        while ctr <= maxloops:
            more_conref_files = getConrefTargets(more_conref_files)
            if debug:
                filenames: list[str] = list(map(lambda path : os.path.basename(path), more_conref_files))
                print(f'+ [DEBUG] getConrefTargetsRecursive(): [{ctr}] more_conref_files: {more_conref_files}')
            if more_conref_files.issubset(conref_files):
                if debug:
                    print(f'+ [DEBUG] getConrefTargetsRecursive(): [{ctr}] more_conref_files is a subset of conref_files, breaking out of while loop.')
                break
            conref_files.update(more_conref_files)
            ctr += 1
            if ctr >= maxloops:
                print(f'[WARN] Still getting content reference links after going through {maxloops} iterations, not doing more.')
    if debug:
        filenames: list[str] = list(map(lambda path : os.path.basename(path), conref_files))
        print(f'+ [DEBUG] getConrefTargetsRecursive(): Returning: {conref_files}')
    return conref_files

def getReferencedImages(topics: set[str], errors: dict={}) -> set[str]:
    """Finds all direct (@href) image references in the specified topics and returns their absolute paths.

    Args:
        topics (set[str]): The topics to find image references in.

        errors (dict): Dictionary to store any errors.

        debug (bool): Controls debug logging

    Returns:
        set[str]: Set of unique image paths.

        errors (dict): Dictionary to store any errors.

        debug (bool): Controls debug logging
    """
    result: set[str] = set()

    # Process the topics
    for topic in topics:
        try:
            topicDoc = etree.parse(topic, xmlutils.getNoDTDParser())
        except Exception as err:
            loggingutils.recordError(errors, topic, err, operation="ditautils.getReferencedImages()")
            continue
        imageElems: list[Element] = topicDoc.xpath("//image[@href]|//*[contains(@class, ' topic/image ')][@href]")
        for elem in imageElems:
            ref = elem.get("href")
            path = urlparse(ref).path
            targetPath = urljoin(elem.base, path)
            result.add(targetPath)
    return result

def getXrefTargets(topics: set[str], errors: dict={}, debug:bool=False) -> set[str]:
    """Finds all direct (@href) cross references (xref, link) in the specified topics and returns their absolute paths.

    Args:c
        topics (set[str]): The topics to find cross references in.

        errors (dict): Dictionary to store any errors.

        debug (bool): Controls debug logging

    Returns:
        set[str]: Set of unique cross reference targets.
    """
    result: set[str] = set()
    for topic in topics:
        try:
            topicDoc = etree.parse(topic, xmlutils.getNoDTDParser())
        except Exception as err:
            loggingutils.recordError(errors, topic, err, operation="ditautils.getXrefTargets()")
            print(f'- [ERROR] getXrefTargets(): {err} from topic "{topic}": {err}')
            continue
        # FIXME: We are parsing without DTDs, so this can only
        #        look for element type names. In Platform content
        #        we only use <xref> and <link> and  but that could change.
        # Ignore xrefs with product="local-link". These are only needed
        # when publishing to self-hosted web help and are essentially
        # never interesting when determining the dependencies for a map,
        # because we are only interested in bundle-level dependencies.
        # This should really be done with a filter, but this will work
        # for now.
        refs: list[Element] = topicDoc.xpath("//xref[@href][string(@format) = '' or string(@format) = 'dita'][string(@scope = '') or string(@scope) = 'local'][string(@product) != 'local-link']|" +
                                             "//link[@href][string(@format) = '' or string(@format) = 'dita'][string(@scope = '') or string(@scope) = 'local'][string(@product) != 'local-link']")
        for refElem in refs:
            if debug:
                print(f'getXrefTargets(): refElem: {etree.tostring(refElem,pretty_print=True,encoding="unicode")}')
            ref = refElem.get("href")
            path = urlparse(ref).path
            targetPath = urljoin(refElem.base, path)
            result.add(targetPath)
    return result

def resolveStringKeyrefs(
    elem: Element,
    keySpace,
    stringKeyScope: str="var",
    mapcontext: Element=None,
    errors: dict={},
    debug: bool=None):
    """Processes an element recursively and replaces any key references to string keys with the key's value.

    Updates the element in place.

    Args:
        elem (Element): The element to process.

        keySpace (KeySpace): The key space to resolve keys in

        stringKeyScope (str): The key scope used for string keys. If specified, only try to resolve
                              keys in this scope. Defaults to "var"

        mapcontext (Element): The map element to resolve the key relative to. If None, key is resolved in the root key space.

        errors (dict): Dictionary to store any errors.

        debug (bool): Controls debug logging
    """
    if debug:
        print(f'[DEBUG] resolveStringKeyrefs(): keySpace: {keySpace}')
    for node in elem.iter(tag=etree.Element):
        if node.get("keyref"):
            if debug:
                print(f'[DEBUG] resolveStringKeyrefs(): Have keyref element: {etree.tostring(node, method="xml", pretty_print=True, encoding="unicode")}')
            keyName: str = node.get("keyref")
            if stringKeyScope is not None and not keyName.startswith(f'{stringKeyScope}.'):
                if debug:
                    print(f'[DEBUG] resolveStringKeyrefs(): keyName "{keyName}" does not reference scope "{stringKeyScope}"')
                # Not a reference to the string key key scope, so ignore it.
                continue
            keyDef = keySpace.resolveKey(keyName, mapcontext=mapcontext, errors=errors, debug=debug)
            if keyDef is None:
                if debug:
                    print(f'[DEBUG] resolveStringKeyrefs(): No key definition for keyName "{keyName}"')
                # FIXME: Should define a KeyResolutionException in keyspace module
                keyspaceLabel = keySpace.getSpaceDefiner().base
                msg = f'For element {elem.tag} ({elem.base}), key "{keyName}" not resolvable in key space {keyspaceLabel}'
                print(msg)
                loggingutils.recordError(errors, elem.base, Exception(msg), operation="ditautils.resolveStringKeyrefs()")
            elif keyDef.isStringKey():
                if debug:
                    print(f'[DEBUG] resolveStringKeyrefs(): Keydef is a string key, getting the nodes from it')
                newNodes = keySpace.resolveKeydefToResource(keyDef,errors=errors,debug=debug)
                if debug:
                    print(f'+ [DEBUG] resolveStringKeyrefs(): newNodes:')
                    print(newNodes)
                # Replace the keyref node with the new node:
                if newNodes is not None:
                    # Preserve any tail from the node we're about to replace.
                    # Put the tail on the last (or only) item in the newNodes
                    # list we got from the key definition.
                    tail = node.tail
                    # For now assume newNodes is a single element, which it should
                    # normally be.
                    newNodes.tail = tail
                    # Filter out attributes that we never want to have be in document
                    # instances. These are attributes defaulted in the DTD. At a minimum
                    # this is the @class attribute. Others would be attributes where the
                    # the value matches the DTD-defined default.
                    for attName in ["class"]:
                        if attName in newNodes.attrib:
                            newNodes.attrib.pop(attName)
                    parent = node.getparent()
                    if parent is not None:
                        parent.replace(node, newNodes)
                    else:
                        print(f'[DEBUG] resolveStringKeyrefs(): No parent for element {node.tag} with key "{keyName }" ({node.base})')
            else:
                # Not resolvable or not a string key, ignore it
                pass

def resolveConrefs(
    elem: Element,
    errors: dict={},
    debug: bool=False):
    """Processes an element recursively and replaces any direct conrefs (not conkeyrefs) with the referenced element(s).

    Updates the element in place.

    Args:
        elem (Element): The element to process.

        errors (dict): Dictionary to store any errors.

        debug (bool): Controls debug logging

    Returns:

       Updates the input element in place.
    """
    if len(elem.xpath('//*[@conref]')) == 0:
        if debug:
            print(f'[DEBUG] resolveConrefs(): No conrefs in the input element, nothing to do.')
        return

    if debug:
        print(f'[DEBUG] resolveConrefs(): Starting, input element is {elem.tag}')
    # Get the containing topic. Note that putting the ancestor axis results into parens puts the results
    # in document order, not ancestor axis order, so we use last() to select the nearest ancestor.
    # We have to select on the tag names because we parse the topics without DTDs.
    nodelist: list[Element] = elem.xpath('(./ancestor-or-self::topic|./ancestor-or-self::concept|./ancestor-or-self::task|./ancestor-or-self::reference)[last()]')
    containingTopic: Element = None
    if len(nodelist) > 0:
        containingTopic = nodelist[0]
    else:
        if debug:
            print(f'[DEBUG] resolveConrefs(): No containing topic found.')
        # If there's no containing topic we can't resolve conrefs.
        return

    for node in elem.iter(tag=etree.Element):
        if debug:
            print(f'[DEBUG] resolveConrefs(): Element {node.tag}')
        if node.get("conref"):
            # FIXME: Handle conrefend
            conrefValue: str = node.get("conref")
            if debug:
                print(f'[DEBUG] resolveConrefs(): Have a conref: "{conrefValue}"')
                if containingTopic is None:
                    print(f'[DEBUG] resolveConrefs(): containingTopic is None')
                else:
                    print(f'[DEBUG] resolveConrefs(): containingTopic/@id="{containingTopic.get("id")}"')
            if conrefValue.find("#") < 0:
                print(f'[WARN] resolveConrefs(): @conref value "{conrefValue}" does not contain a fragment identifier, cannot be resolved')
                continue
            fragID: str = conrefValue.split('#')[1]
            topicId, elementId = fragID.split("/")
            resultList: list[Element] = []
            if debug:
                print(f'[DEBUG] resolveConrefs(): topicId="{topicId}", elementId="{elementId}"')
            if (conrefValue.startswith('#')):
                # Conref to an element in the same document.
                if (topicId != "."):
                    # This could find a non-topic element with the same ID as
                    # the topic but in that case this should find the topic first
                    # assuming the topic is the root element or contains the duplicate
                    # ID. Not bothering to check that the result is in fact a topic
                    # at this time.
                    nodelist = elem.xpath(f'(//*[@id = "{topicId}"])[1]')
                    if len(nodelist) > 0:
                        containingTopic = nodelist[0]
                else:
                    # Current topic is the one we got at the start of the function
                    pass
            else:
                if debug:
                    print(f'[DEBUG] resolveConrefs(): Resolving URI ref')
                containingTopic = xmlutils.resolveUriRef(conrefValue, node,errors=errors,debug=debug)

            # We have a containing topic and an element ID, try to find the element:
            resultList = containingTopic.xpath(f'(.//*[@id = "{elementId}"])[1]')

            if debug:
                print(f'[DEBUG] resolveConrefs(): resultList has {len(resultList)} items')
            if len(resultList) > 0:
                # For now assume newNodes is a single element, which it should
                # normally be.
                targetElement: Element = resultList[0]
                if debug:
                    print(f'[DEBUG] resolveConrefs(): Have a target element: {etree.tostring(targetElement, encoding="unicode",pretty_print=True)}')
                    print(f'[DEBUG] resolveConrefs(): targetElement is {targetElement.tag} id="{targetElement.get("id")}"')
                tail = node.tail
                targetElement.tail = tail
                # Now resolve any conrefs in the conref result:
                if debug:
                    print(f'[DEBUG] resolveConrefs(): Applying resolveConrefs to targetElement {etree.tostring(targetElement, encoding="unicode",pretty_print=True)}')
                resolveConrefs(targetElement,errors=errors,debug=debug)
                parent = node.getparent()
                if parent is not None:
                    parent.replace(node, targetElement)
                else:
                    print(f'[DEBUG] resolveConrefs(): No parent for element {node.tag} making conref "{conrefValue }" ({node.base})')




def resolveConkeyrefs(
    elem: Element,
    keySpace,
    mapcontext: Element=None,
    errors: dict={},
    debug: bool=None):
    """Processes an element recursively and replaces any conkeyrefs with the referenced element(s).

    Updates the element in place.

    Args:
        elem (Element): The element to process.

        keySpace (KeySpace): The key space to resolve keys in

        mapcontext (Element): The map element to resolve the key relative to. If None, key is resolved in the root key space.

        errors (dict): Dictionary to store any errors.

        debug (bool): Controls debug logging

    Returns:

       Updates the input element in place.
    """
    if debug:
        print(f'[DEBUG] resolveConkeyrefs(): keySpace: {keySpace}')
    for node in elem.iter(tag=etree.Element):
        if node.get("conkeyref"):
            # FIXME: Handle conrefend
            conkeyrefValue: str = node.get("conkeyref")
            # A @conkeyref attribute is "{keyname}/{elementID}"
            if "/" in conkeyrefValue:
                keyName, elemId = conkeyrefValue.split("/")
            else:
                # This path is an authoring error but it will naturally fail
                # to resolve when elemId is None.
                keyName = conkeyrefValue
                elemId = None

            keyDef = keySpace.resolveKey(keyName, mapcontext=mapcontext, errors=errors, debug=debug)
            if keyDef is None:
                keyspaceLabel = keySpace.getSpaceDefiner().base
                msg = f'For element {elem.tag} ({elem.base}), key "{keyName}" not resolvable in key space {keyspaceLabel}'
                print(msg)
                loggingutils.recordError(errors, elem.base, Exception(msg), operation="ditautils.resolveStringKeyrefs()")
            elif keyDef.isTopicKey():
                topic: Element = keySpace.resolveKeydefToResource(keyDef,errors=errors,debug=debug)
                if topic is None:
                   # Failed to resolve the keydef to a topic, skip it.
                   continue
                if debug:
                    print(f'+ [DEBUG] resolveConkeyrefs(): topic:')
                    print(topic)
                # Don't consider the topic itself so that a reference to an ID that is the
                # same as the topic ID does not return the topic.
                resultList: list[Element] = topic.xpath(f'/*//*[@id = "{elemId}"][1]')
                # Replace the keyref node with the new node:
                if resultList is not None and len(resultList) > 0:
                    targetElement = resultList[0]
                    # Preserve any tail from the node we're about to replace.
                    # Put the tail on the last (or only) item in the newNodes
                    # list we got from the key definition.
                    tail = node.tail
                    # For now assume newNodes is a single element, which it should
                    # normally be.
                    targetElement.tail = tail
                    parent = node.getparent()
                    if parent is not None:
                        parent.replace(node, targetElement)
                    else:
                        print(f'[DEBUG] resolveStringKeyrefs(): No parent for element {node.tag} with key "{keyName }" ({node.base})')
            else:
                # Not resolvable, ignore it
                pass

def getElementText(elem: Element, keySpace, stringKeyScope: str="var", normalize:bool=True, errors:dict={}, debug:bool=False) -> str:
    """Gets the text of an element with any string keys resolved.

    Args:
        elem (Element): The element to get the text of.

        keySpace (KeySpace): The key space to use when resolving key references.

        stringKeyScope (str): The key scope used for string keys. If specified, only try to resolve
                              keys in this scope. Defaults to "var"

        normalize (bool, optional): Normalize the resulting string. Defaults to True.

        errors (dict): Dictionary to store any errors.

        debug (bool): Controls debug logging

    Returns:
        str: The string content of the element with keyrefs resolved. If normalize is True, whitespace is normalized.
    """
    resolveStringKeyrefs(elem, keySpace, stringKeyScope=stringKeyScope, errors=errors,debug=debug)
    result = xmlutils.getElementText(elem, normalize=normalize, errors=errors, debug=debug)
    return result

def makeTopichead(title: str) -> Element:
    """Make a new <topichead> element with the specified title.

    Args:

        title (str): Topichead title.

    Returns:

        Element: New <topichead> element.
    """
    topichead: Element = E.topichead(
		{ "processing-role": "resource-only"
		},
		E.topicmeta(
            # Any attributes go here:
			{ },
			E.navtitle(
				title,
                # Any attributes go here:
				{ },
			)
		)
	)

    return topichead

def isClass(elem: Element, classToken: str) -> bool:
    """Determine if the specified element is of the specified DITA class.

    Returns True if the element is of the specified DITA class.

    Args:

        elemElement (Element): The element to check. Should have a @class attribute

        classToken (str): Token from @class value to look for

    Returns:

        boolean: True if the element is of the specified DITA class.
    """

    classValue = elem.get("class")
    if classValue is not None:
        return classToken in classValue.split()
    # FIXME: Use statically-generate tagname-to-class mapping as used
    #        in XQuery.
    return False

def isPeerMapref(elem: Element) -> bool:
    """Determines if the specified element is a peer map reference.

    Args:
        elem (Element): Candidate element

    Returns:
        bool: True if the element has a scope of "peer", a @keyscope attribute, a format of "ditamap", and an @href attribute.
    """
    scope: str = elem.get("scope")
    if scope != "peer":
        return False
    if elem.get("keyscope") is None:
        return False
    if elem.get("href") is None:
        return False
    format: str = elem.get("format")
    return format == "ditamap" or elem.tag == "mapref"

def getTopicrefsToTopics(map: Element, errors: dict[str, ErrorRecord]={}, debug:bool=False) -> list[Element]:
    """From a DITA map, gets the topicrefs that point to topics.

    Does not check that the topicrefs can be resolved.

    Args:
        map (Element): The map to get the topicrefs from. Must have been parsed with a DTD-aware parser


        errors (dict): Dictionary to store any errors.

        debug (bool): Controls debug logging

    Returns:
        list[Element]: List, possibly empty, of topicref elements
    """
    topicrefs: list[Element] = map.xpath("//*[contains(@class, ' map/topicref ')][@href][not(@format) or @format = 'dita']")
    return topicrefs
