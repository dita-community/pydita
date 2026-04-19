"""Manages DITA key spaces

Provides the following services:

* Resolves a DITA map tree to a single document instance equivalent to the XSLT resolve-map.xsl library
* Constructs the key spaces defined in a root map
* Provides key lookup based on both context-free key lookup (ignoring reference context) and
    context-aware lookup

"""
import os
from typing import Union
import sys
from copy import copy
from io import IOBase


from urllib.parse import urljoin, urlparse

from lxml import etree
from lxml.etree import Element
from lxml.etree import ElementTree
from anytree import NodeMixin
from anytree import RenderTree

from pydita import resolvemap

from pydita.visitor import Visitor
from pydita.visitor import Visitable
from pydita.keyspacevisitors import PullUpVisitor
from pydita.keyspacevisitors import PushDownVisitor
from pydita.keyspacevisitors import KeyspaceReportingVisitor

from pydita.keyspace import KeySpace
from pydita.keyspace import KeyDefinition

from pydita import xmlutils
from pydita import loggingutils
from pydita import ditautils

class KeyspaceManager(Visitable):
    """Key space manager

    Manages one or more key spaces.
    """

    def __init__(self, resolvedMap: Union[ElementTree, Element]=None, errors: dict={}, debug: bool = False):
        """Construct a new key space manager, populating the root key space using the specified DITA map.

        Args:

            resolvedMap (ElementTree): A DITA map that has been resolved to reflect the full map tree (`resolvemap.resolveMap()`).

        """
        # Root key spaces managed by this key space manager:
        self.keyspaces: set = set()
        self.errors: dict = errors
        self.debug: bool = debug

        # The key spaces as identified by the absolute URI
        # of the map that defines them. The defining map's
        # URI serves as the global identifier of a key space.
        self.keyspacesByMapUri: dict = {}

        # The same key space may be defined by any number of definers,
        # where all but the root map element may be peer maprefs from
        # other maps.
        self.keyspacesByDefiner: dict = {}

        # Now add the root key space if specified:
        self.rootKeySpace = None
        if resolvedMap is not None:
            if not etree.iselement(resolvedMap):
                resolvedMap = resolvedMap.getroot()

            self.rootKeySpace = KeySpace(self, resolvedMap, "#annonymous")
            self._addKeySpace(self.rootKeySpace)
            constructKeySpace(self.rootKeySpace, resolvedMap)

    def _addKeySpace(self, keySpace: KeySpace):
        self.keyspaces.add(keySpace)
        spaceDefiner: Element = keySpace.getSpaceDefiner()
        mapUri: str = None
        if ditautils.isClass(spaceDefiner, 'map/map'):
            mapUri = spaceDefiner.base
        elif ditautils.isClass(spaceDefiner, 'map/topicref'):
            # Because this method is only called for root or peer
            # key spaces, we should only get here if
            # the spaceDefiner is a peer mapref.
            # We want the map URI of the map the map reference
            # points to. If we don't get that, bail.
            scope: str = spaceDefiner.get("scope")
            if scope is not None and scope == "peer":
                # We should never get here unless this is a
                # peer mapref, but it never hurts to check
                format: str = spaceDefiner.get("format")
                if format is None and spaceDefiner.name == "mapref":
                    format = "ditamap"
                if format != "ditamap":
                    keyscopes: str = spaceDefiner.get("keyscope")
                    loggingutils.recordError(self.errors, f'Peer keyscope {keyscopes}', Exception(f'Peer mapref has format "{format}"'), 'addKeySpace()')
                    return
                else:
                    keyscopes: str = spaceDefiner.get("keyscope")
                    href: str = spaceDefiner.get("href")
                    if href is None or href.strip() == "":
                        loggingutils.recordError(self.errors, f'Peer keyscope {keyscopes}', Exception(f'Peer mapref must specify @href'), 'addKeySpace()')
                        return
                    else:
                        mapUri = urljoin(spaceDefiner.base, href)

        self.keyspacesByDefiner[spaceDefiner] = keySpace
        self.keyspacesByMapUri[mapUri] = keySpace

    def getKeyspaceByMapUri(self, mapUri: str) -> KeySpace:
        """Get the key space for the map with the specified URI, if any.

        Args:
            mapUri (str): The absolute URI of the map to get the key space for.

        Returns:
            KeySpace: The key space for the specified map, if found.
        """
        keySpace: KeySpace = self.keyspacesByMapUri.get(mapUri)
        return keySpace

    def getKeyspaceByDefiner(self, spaceDefiner: Element) -> KeySpace:
        """Get the key space for the space definer.

        Args:
            spaceDefiner (Element): A map element or a peer map reference.

        Returns:
            KeySpace: The key space for the specified definer, if found.
        """
        keySpace: KeySpace = self.keyspacesByDefiner.get(spaceDefiner)
        return keySpace

    def resolveRootKeyref(self, keyName: str, resolvePeerKeys: bool=False, errors: dict={}, debug: bool=False) -> KeyDefinition:
        """Resolves a key name in the context of the root key space

        This is used for resolving fully-qualified key references as
        though the reference was in the root key scope.

        This method avoids the need to provide the map context of
        the original reference.

        Args:

            keyName (str): The key name to resolve.

            errors (dict): Dictionary to store any errors.

            debug (bool): Controls debug logging

        Returns:

            KeyDefinition object that is first in priority order or
            None if key reference is not resolved.
        """

        result = self.rootKeySpace.resolveKey(keyName, resolvePeerKeys=resolvePeerKeys, errors=errors, debug=debug)

        return result

    def getRootKeyspace(self) -> KeySpace:
        """Get the root key space for the key space manager

        Returns:

            KeySpace: The root key space
        """
        return self.rootKeySpace

    def addDeferredKeyspace(self, elem: Element) -> KeySpace:
        """Adds a "deferred" key space represented by a peer map reference to a
        root map.

        The key space is not constructed until an attempt is make to
        resolve a key in the space, at which point the key space is constructed
        in order to then resolve the key reference.

        A peer map reference must have the following attributes:

        @scope: Has the value "peer"
        @keyscope: Must specify at least one scope names
        @href: The URI of the target root map

        Args:
            elem (Element): A peer map reference that represents the key space.

        Returns:
            KeySpace: The deferred key space.
        """
        scope: str = elem.get("scope")
        assert scope == "peer", f'For a peer mapref, the @scope attribute must have the value "peer", got "{scope}"'
        keyscope: str = elem.get("keyscope")
        assert keyscope is not None, f'For a peer mapref, the @keyscope attribute must be specified'
        href: str = elem.get("href")
        assert href is not None, f'For a peer mapref, the @href attribute must be specified'

        # Construct the absolute URL of the target map, but don't try to parse it now--it's not required
        # to exist until a key resolution attempt is made.

        keyscopeNames: list = keyscope.split()
        mapUri: str = urljoin(elem.base, href)
        keySpace: KeySpace = self.getKeyspaceByMapUri(mapUri)
        if keySpace is None:
            # Construct the key space and register it in this key space manager.
            keySpace = KeySpace(self, elem, *keyscopeNames)
            self.keyspacesByDefiner[elem] = keySpace
            self.keyspacesByMapUri[mapUri] = keySpace

        else:
            keySpace.addKeyScopeNames(keyscopeNames)
        return keySpace

    def constructDeferredKeyspace(self, keySpace: KeySpace, errors: dict={}, debug: bool=False) -> None:
        """For a deferred key space, construct the space.

        Args:
            keySpace (KeySpace): The deferred key space to be constructed.
            errors (dict, optional): Error dictionary. Defaults to {}.
            debug (bool, optional): Controls debug logging. Defaults to False.
        """
        if not keySpace.isDeferred():
            print(f'[WARN] constructDeferredKeyspace(): Attempt to construct non-deferred key space: {keySpace.label}')
            return
        # The key space definer should be a map reference with an @href attribute
        definer: Element = keySpace.getSpaceDefiner()
        hrefValue: str = definer.get("href")
        if hrefValue is None:
            print(f'[WARN] constructDeferredKeyspace(): key space definer does not have an @href attribute: {keySpace.label}')
            return
        mapUri: str = urljoin(definer.base, hrefValue)
        if not os.path.exists(mapUri) or not os.access(mapUri, os.R_OK):
            print(f'[WARN] constructDeferredKeyspace(): map URI "{mapUri}" does not exist or cannot be read.')
            return
        mapFile: IOBase = open(mapUri, 'r')
        resolvedMap: ElementTree = resolvemap.resolveMap(mapFile)
        constructKeySpace(keySpace, resolvedMap, errors=errors, debug=debug)


def constructKeySpace(rootKeySpace: KeySpace, resolvedMap: Union[ElementTree, Element], errors: dict={}, debug: bool=False) -> None:
    """Constructs a key space from a resolved DITA map

    Args:

        rootKeySpace (KeySpace): The key space to construct

        resolvedMap (ElementTree): Resolved map to construct the key space from
    """
    elem: Element = None
    if  etree.iselement(resolvedMap):
        elem = resolvedMap
    else:
        elem = resolvedMap.getroot()

    rootKeySpace.keyspacesByDefiner[elem] = rootKeySpace
    rootKeySpace.setSpaceDefiner(elem)
    _handleElement(rootKeySpace, elem)

    # Step 2: Do the "pull up" of key definitions from descendant spaces to
    #         to ancestor spaces. Enables resolution of scope-qualified
    #         references to keys in descendant scopes from content of ancestor
    #         scope.

    PullUpVisitor().visit(rootKeySpace)

    # Step 3: Do the "push down" of key definitions from ancestor spaces to
    #         descendant spaces. Imposes overrides from ancestor scopes,
    #         makes fully-qualified key definitions for keys in a scope
    #         available from the context of that scope.

    PushDownVisitor().visit(rootKeySpace)

    # Let the keyspace know it's been constructed and is no longer
    # deferred.
    rootKeySpace.unsetDeferred()

def _handleElement(keySpace: KeySpace, elem: Element) -> None:
    """Handles a DITA map element for key space construction

    Dispatches the appropriate processing:

    * Keydef: Add a key definition
    * Scope definer: Construct a new key space
    * topicmeta: Skip
    * reltable: Skip
    * Otherwise, handle children.

    Args:

        keySpace (KeySpace): The key space being constructed

        elem (Element): Element to be handled.
    """
    if ditautils.isClass(elem, "map/topicmeta"):
        return
    elif ditautils.isClass(elem, "map/reltable"):
        return
    elif ditautils.isClass(elem, "map/map"):
        keyscopeValue = elem.get("keyscope")
        if keyscopeValue is not None:
            keySpace.addKeyScopeNames(keyscopeValue.split())
        _handleChildren(keySpace, elem)

    elif ditautils.isClass(elem, "map/topicref"):
        keysValue = elem.get("keys")
        keyscopeValue = elem.get("keyscope")
        scopeValue = elem.get("scope")
        if scopeValue in ["peer"]:
            _addPeerMapKeySpace(keySpace, elem)
        elif keyscopeValue is not None:
            _addChildKeySpace(keySpace, elem)
        elif keysValue is not None:
            _addKeyDefinition(keySpace, elem)
        else:
            _handleChildren(keySpace, elem)
    else:
        _handleChildren(keySpace, elem)

def _handleChildren(keySpace: KeySpace, elem: Element) -> None:
    """Process the children of the specified element.

    Args:

        keySpace (KeySpace): The key space being constructed

        elem (Element): The element whose children to process
    """
    for child in elem:
        _handleElement(keySpace, child)

def _addChildKeySpace(keySpace: KeySpace, elem: Element) -> None:
    """Add a child key space to the specified key space.

    Args:

        keySpace (KeySpace): The parent key space

        elem (Element): The scope-defining element
    """
    scopeNames = elem.get("keyscope").split()
    # NOTE: The value of scopeNames is a list of strings but the function takes a variable
    #       number of items for the parameter "scopeNames", so we need to use "*" on scopeNames
    #       to unpack the tuple.
    newKeySpace = keySpace.appendKeySpace(elem, *scopeNames)
    keysValue = elem.get("keys")
    if keysValue is not None:
        _addKeyDefinition(newKeySpace, elem)
    else:
        _handleChildren(newKeySpace, elem)

def _addPeerMapKeySpace(keySpace: KeySpace, elem: Element) -> None:
    """Create a peer map key space item. This functions as an indirection
    to the peer map. The peer map's key space is not constructed at this
    time, but by the KeyspaceManager when a resolution attempt is made,
    if the peer key space is not already present in the KeyspaceManager.

    Args:
        keySpace (KeySpace): This key space
        elem (Element): Peer mapref element
    """
    keySpace.addPeerMapref(elem)
    keyspaceManager: 'KeyspaceManager' = keySpace.getKeyspaceManager()
    keySpace: KeySpace = keyspaceManager.addDeferredKeyspace(elem)

def _addKeyDefinition(keySpace: KeySpace, elem: Element) -> None:
    """Add a key definition to the specified key space

    Args:

        keySpace (KeySpace): The key space to add the key definition to

        elem (Element): The key-defining DITA map element
    """
    keySpace.addKeyDefinitionElem(elem)
    _handleChildren(keySpace, elem)
