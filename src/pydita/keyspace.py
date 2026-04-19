"""Manages DITA key spaces

Provides the following services:

* Resolves a DITA map tree to a single document instance equivalent to the XSLT resolve-map.xsl library
* Constructs the key spaces defined in a root map
* Provides key lookup based on both context-free key lookup (ignoring reference context) and
    context-aware lookup

"""
import os
import sys
from copy import copy, deepcopy
from typing import Any, Union

from lxml import etree
from lxml.etree import Element
from lxml.etree import ElementTree
from anytree import NodeMixin
from anytree import RenderTree

from pydita import ditautils
from pydita.visitor import Visitor
from pydita.visitor import Visitable

from pydita import xmlutils
from pydita import loggingutils
from pydita.loggingutils import ErrorRecord




class KeyDefinition(NodeMixin, Visitable):
    """Binding of a key name to one more key-defining topic references.

    Serves as the value of the conceptual dictionary of key names to
    resources that is a key space.

    Acts as a node in an anytree tree (child of KeySpace)
    """

    # The tree node label (used by AnyTree rendering)
    label = None

    def __init__(self, keySpace: 'KeySpace', keyName: str, keydefElem: Element=None, parent=None, children=None):
        """Construct a new KeyDefinition instance

        Args:

            keySpace (KeySpace): The key space this definition is part of.

            keyName (str): The key name for the definition.

            keydefElem (Element): The first (or only) key-defining element for the key definition.
        """
        # For tree node:
        self.label = "KeyDef: " + keyName
        self.parent = parent
        if children:
            self.children = children
        # Key definition stuff
        # List, in priority order, of the key-defining elements
        # for this key definition.

        self._keySpace = keySpace
        self.keydefElems = [keydefElem]
        # The key name
        self.keyName = keyName

    def __copy__(self):
        cls = self.__class__
        result = cls.__new__(cls)
        result.__dict__.update(self.__dict__)
        return result

    def __str__(self) -> str:
        return f'[{self.keyName}] Keydef elem count: {len(self.keydefElems)}'

    def accept(self, visitor):
        visitor.visit(self)

    def getKeyName(self) -> str:
        """Get the key name for this key definition

        Returns:

            str: The key name
        """
        return self.keyName

    def setKeyName(self, keyName: str) -> None:
        """Sets the key name

        Args:
            keyName (str): The new key name for the key definition.
        """
        self.keyName = keyName

    def getKeySpace(self) -> 'KeySpace':
        """Get the key space this definition is a direct member of

        Returns:

            KeySpace: The containing key space
        """
        return self._keySpace

    def resolveToResource(self, errors: dict={}, debug:bool=False) -> Union[Element, ElementTree]:
        """Resolve the key definition to a resource.

        Returns:

            Union[Element, ElementTree]: The resource
        """
        if debug:
            print(f'[DEBUG] resolveToResource(): Calling self._keySpace.resolveKeydefToResource()...')
        resource = self._keySpace.resolveKeydefToResource(self,errors=errors, debug=debug)
        if debug:
            print(f'[DEBUG] resolveToResource(): Returning {resource}')
        return resource

    def append(self, keydefElem: Element):
        """Add a new key-definining element to this key definition.

        Elements must be appended in priority order.

        Args:

            keydefElem (Element): The key-defining DITA map element
        """
        self.keydefElems.append(keydefElem)

    def getKeyDefiner(self) -> Element:
        """Get the first key-defining element for the key definition.

        Returns:

            Element: The highest-priority key-defining element for the key.
        """
        return self.keydefElems[0]

    def getKeyDefiners(self) -> list:
        """Get the list of key-defining elements.

        Returns:

            list(Element): List of key-defining elements.
        """
        return self.keydefElems.copy()

    def isStringKey(self) -> bool:
        """Determines if the key definition is a string key, a key with no external resource.

        Returns:

            bool: True if the key has no external resource, otherwise False.
        """
        definer: Element = self.getKeyDefiner()
        return not (definer.get("href") is not None) and not (definer.get("keyref") is not None)

    def isTopicKey(self) -> bool:
        """Determines if the key definition is bound to a topic

        Returns:

            bool: True if the key is directly bound to a topic. Does not recurse through keyrefs.
        """
        definer: Element = self.getKeyDefiner()
        # If there's an @href attribute and the @format is "dita" (the default) then it must be a reference to a topic.
        return (definer.get("href") is not None) and (definer.get("format") is None or definer.get("format") == "dita")

    def prependKeyDefiningElements(self, elems: list) -> None:
        """Adds the specified key-defining elements to the start of the key definers"

        Args:

            elems (list[Element]): The key-defining elements to prepend.
        """
        elemsToAdd = []
        for elem in elems:
            if elem not in self.keydefElems:
                elemsToAdd.append(elem)
        self.keydefElems = elemsToAdd + self.keydefElems

class KeySpace(NodeMixin, Visitable):
    """Manages a single key space of key definitions

    Acts as node in an anytree tree: Tree of key spaces.

    Each key space has its KeyDefinition nodes as child
    nodes in the tree.
    """

    def __init__(self, keyspaceManager, spaceDefiner: Element, *keyScopeNames: str, parent=None, children=None):
        """Construct a new key space

        Args:

            keyspaceManager (KeyspaceManager): The keyspace manager that manages this keyspace.

            spaceDefiner: The element that defines the key space: a map, topicref, or a peer mapref.

            keyScopeNames (str): One or more key scope names
        """
        self.keyspaceManager = keyspaceManager
        # The space definer, either a map, a peer mapref, or
        # a topicref that specifies @keyscope.
        # When the definer is a peer mapref, then key space is
        # "deferred" and will not be constructed until an attempt
        # is made to resolve a key reference against it.
        self.setSpaceDefiner(spaceDefiner)
        # For tree node:
        self.parent = parent
        if children:
            self.children = children

        """The keys scope names assigned to this key space.

        There must be at least one key scope name.

        The root key scope always has the key scope name
        "#annonymous" in addition to any other key scope
        names it might get from the root map element.
        """

        self.keyScopeNames: set[str] = set(item for item in keyScopeNames)

        # Dictionary of key names to key definitions for
        # the key space. The values are lists of key definitions.
        self.keydefsByKeyName = {}

        # Dictionary of key spaces by key scope name.
        # Enables looking up child key spaces by
        # key scope name. There may be multiple key
        # spaces with the same key scope name,
        # So the values are lists.
        self.keyspacesByScopeName = {}
        # The key space is always bound to its definer.
        # Note that the root key space may have multiple
        # definers if it starts as a peer mapref and
        # is subsequently constructed due to a resolution
        # attempt being made against it. In addition,
        # multiple maps may use the same map as a peer,
        # meaning each such map may constribute a peer
        # map ref space definer to the key space.
        # When the referenced map is constructed, that
        # map will be set as the space definer and
        # an entry for it in keyspacesByDefiner will
        # be added.
        self.keyspacesByDefiner = {spaceDefiner : self}
        self.keySpaces: list = []
        # List of peer keyscope definers (map references):
        self.peerKeyscopes: dict[str, Element] = {}

        # The tree node label (used by AnyTree rendering)
        self.label: str = "KeySpace: " + ", ".join(self.keyScopeNames)
        # When True, the key space is known (from a peer map reference)
        # but is not yet constructed. When the key space is constructed
        # it is no longer deferred.
        self._isDeferred = True

    def __str__(self) -> str:
        result = f'{self.__class__.__name__}[{self.__hash__}] ({self.getScopeNames()})'
        return result

    def accept(self, visitor):
        visitor.visit(self)

    def getKeyspaceManager(self):
        """Get the key space manager that manages this key space.

        Returns:
            KeyspaceManager: The key space manager that manages this key space.
        """
        return self.keyspaceManager

    def getChildSpaces(self) -> 'list[KeySpace]':
        """Get the child key spaces in priority order.

        Returns:

            list[KeySpace]: The child key spaces in priority order.
        """
        result = []
        for child in self.children:
            if isinstance(child, KeySpace):
                result += [child]
        return result

    def getKeyspacesByScopeName(self, scopeName: str) -> 'list[KeySpace]':
        """Gets any child key spaces with the specified scope name.

        Args:

            scopeName (str): The scope name to look for.

        Returns:

            list[KeySpace]: List of key spaces that have the specified scope name or None.
        """
        result = self.keyspacesByScopeName.get(scopeName)
        return result

    def getKeySpaceForMapContext(self,
                   mapcontext: Element,
                   errors: dict={},
                   debug: bool=False) -> 'KeySpace':
        """Returns the key space constructed from the specified map context.

        Args:

            mapcontext (Element): DITA map element.

            errors: (dict): Holds any reported errors

            debug (bool): Controls debug logging.

        Returns:

            KeySpace: The keyspace constructed from the nearest space-defining ancestor or self
                      of the map context element.
        """
        spaceDefiner = self.spaceDefiner
        # If mapcontext is not already a space-defining element (has @keyscope),
        # then find nearest ancestor that is a space definer: element with @keyscope
        # or the map's root element.
        if mapcontext.get("keyscope") is None:
            definers: list[Element] = mapcontext.xpath("ancestor-or-self::*[@keyscope][1]")
            if len(definers) > 0:
                spaceDefiner = definers[0]
        else:
            spaceDefiner = mapcontext

        if debug:
            print(f'[DEBUG] getKeySpaceForMapContext(): spaceDefiner: {spaceDefiner}')
        if ditautils.isPeerMapref(spaceDefiner):
            manager = self.getKeyspaceManager()
            result = manager.getKeyspaceByDefiner(spaceDefiner)
        else:
            result = self.keyspacesByDefiner.get(spaceDefiner)
            if result is None:
                for keySpace in self.keySpaces:
                    result = keySpace.keyspacesByDefiner.get(spaceDefiner)
                    if result is not None:
                        break
            if debug:
                print(f'[DEBUG] getKeySpaceForMapContext(): result: {result}')

        return result


    def getKeyDefinitions(self,sortKeys:bool=False) -> list:
        """Get the list of key definitions in this key space

        Args:

            sortKeys (bool): If true, sort the key definitions by key name, ignoring case.

        Returns:

            list[KeyDefinition]: The keydefs, one per key name.
        """
        keys: list = sorted(self.keydefsByKeyName.keys(), key=str.lower) if sortKeys else self.keydefsByKeyName.keys()
        allKeydefs = []
        for keydefs in [self.keydefsByKeyName[key] for key in keys]:
            allKeydefs.extend(keydefs)
        return allKeydefs

    def getScopeNames(self) -> set:
        """Get the scope names associated with the key space.

        Each key space must have at least one scope name.

        Returns:

            set[str]: The scope names
        """
        return self.keyScopeNames.copy()

    def isDeferred(self) -> bool:
        """Determine if the key space is a deferred key space, meaning it is known from a
        peer map reference but has not yet been constructed.

        Returns:
            bool: True if the key space is deferred.
        """
        return self._isDeferred

    def unsetDeferred(self) -> None:
        """Set the keyspace as no longer deferred (meaning it has been constructed).
        """
        self._isDeferred = False

    def addKeyDefinitionElem(self, keydefElem: Element) -> None:
        """Adds key definitions to the key space for single key-defining element.

        Definitions for existing key names are appended to the end of the key
        definition's priority sequence. This means key definitions must be
        added in priority order (i.e., breadth-first traversal of the map
        tree the keys are pulled from)

        Args:

            keydefElem (Element): The key definition element from a DITA map
        """

        keysValue = keydefElem.get("keys")
        keyNames = keysValue.split()

        for keyName in keyNames:
            # keydefs is a list, in priority order of the key definitions associated
            # with the specified name.
            keydefs: list = self.keydefsByKeyName.get(keyName)
            # NOTE: Not including keydefs in the key space tree.
            keydef = KeyDefinition(self, keyName, keydefElem)
            if keydefs is None:
                self.keydefsByKeyName[keyName] = [keydef]
            else:
                keydefs.append(keydef)

    def addKeyDefinition(self, keyDef: KeyDefinition):
        """Add a new KeyDefinition to the key space.

        If there is already a key definition for the
        keydef's key name, the key-defining elements
        from this keydef are prepended to the existing
        list of key-defining elements, making the added
        keydef higher priority.

        Args:

            keyDef (KeyDefinition): The key definition to add.
        """
        keyName = keyDef.getKeyName()
        existingDef = self.resolveKey(keyName, mapcontext=keyDef.getKeyDefiner(), resolvePeerKeys=False)
        if existingDef is not None:
            # Merge the key-defining elements from the
            existingDef.prependKeyDefiningElements(keyDef.getKeyDefiners())
        else:
            self.keydefsByKeyName[keyDef.getKeyName()] = [keyDef]

    def addKeyScopeNames(self, scopeNames: list) -> None:
        """Add names to the space's key scopes

        Args:

            scopeNames (list[str]): List of key scope names.
        """
        # NOTE: The value of scopeNames is a tuple of strings (because of the '*scopeNames' in the method signature)
        #       That is, the value to be specified needs to be a flat sequence of strings, not a list of strings.
        #       So we need to use "*" on scopeNames to unpack the tuple.
        self.keyScopeNames.add(*scopeNames)

    def addPeerMapref(self, mapref: Element) -> None:
        """Add a peer mapref to the key space.

        The mapref serves as the key space definer for the peer key space as managed
        by the KeyspaceManager. So given a peer mapref you can get to the
        key space constructed from the peer map.

        Args:
            mapref (Element): A peer map reference. Must specify @keyscope (and @scope and @href)

        """
        keyscopeValue: str = mapref.get("keyscope")
        if keyscopeValue is None:
            print(f'[ERROR] mapref element does not have a @keyscope attribute. This should not happen')
            return
        scopeValue: str = mapref.get("scope")
        if scopeValue is None or scopeValue != "peer":
            print(f'[ERROR] mapref element does not have a @scope attribute or value is not "peer": scope="{scopeValue}"')
            return
        # Capture the mapping from peer key scope names to peer map references
        scopeNames: list[str] = keyscopeValue.split()
        for scopeName in scopeNames:
            maprefs: list[Element] = self.peerKeyscopes.get(scopeName)
            if maprefs is None:
                self.peerKeyscopes[scopeName] = [mapref]
            else:
                self.peerKeyscopes[scopeName].extend(mapref)

    # NOTE: Have to use a string for the type name when annotating a Class's functions
    #       with its own type. See
    # https://stackoverflow.com/questions/33533148/how-do-i-type-hint-a-method-with-the-type-of-the-enclosing-class
    def appendKeySpace(self, mapcontext: Element = None, *scopeNames: str) -> 'KeySpace':
        """Creates a new key space as a child of this key space.

        Key spaces are in priority order.

        Args:

            scopeNames (list[str]): Scope names for this scope.

            mapcontext (Element): The DITA map element that defines this scope. Omit for root scope

        Returns:

            KeySpace: The new key space
        """
        # NOTE: The value of scopeNames is a tuple of strings (because of the '*scopeNames' in the method signature)
        #       That is, the value to be specified needs to be a flat sequence of strings, not a list of strings.
        #       So we need to use "*" on scopeNames to unpack the tuple.
        keySpace: 'KeySpace' = KeySpace(self.getKeyspaceManager(), mapcontext, *scopeNames, parent=self)
        self.keySpaces.append(keySpace)
        self.keyspacesByDefiner[mapcontext] = keySpace
        for scopeName in scopeNames:
            spaces = self.keyspacesByScopeName.get(scopeName)
            if spaces is None:
                self.keyspacesByScopeName[scopeName] = [keySpace]
            else:
                spaces.append(keySpace)
        return keySpace

    def addKeyDefinitions(self, keyDefs: list) -> None:
        """Adds the key definitions to the key space.

        For existing keys, key-defining elements are prepended.

        Args:

            keyDefs (list[KeyDefinition]): Key definitions to add
        """
        for keyDef in keyDefs:
            self.addKeyDefinition(keyDef)

    def getSpaceDefiner(self) -> Element:
        """Gets the space-defining element for the key space

        Returns:

            Element: The space-defining element
        """
        return self.spaceDefiner

    def setSpaceDefiner(self, elem: Element) -> None:
        """Sets the space-defining element for the key space

        Args:

            elem (Element): The space defining element for this key space.
        """
        self.spaceDefiner = elem

    def hasScopeName(self, keyScopeName: str) -> bool:
        """Determines if the key scope has the specified name

        Args:

            keyScopeName (str): key scope name (token from @keyscope attribute)

        Returns:

            bool: True if the key scope name is one of the scope's names
        """
        return keyScopeName in self.keyScopeNames

    def getKeyspaceForKeyref(self,
                             keyref: str,
                             mapcontext: Element = None,
                             errors: dict={},
                             debug: bool=False
                            ) -> 'KeySpace':
        """Get the key space that a key reference is resolved in in the context of this keyspace.

        Args:
            keyref (str): The key to be resolved.

        Returns:
            KeySpace: The key space the key is resolved in. May be this key space or a peer map's key space.
        """
        # If this key can be resolved in the current keyspace, then that's the keyspace,
        # otherwise, see if it is a peer keyref
        if self.resolveKey(keyref, mapcontext, resolvePeerKeys=False ) is not None:
            return self

        # Didn't resolve, see if it's a peer mapref

        # FIXME: For now assuming only the first dot-separated token
        #        is a candidate scope name, but there could be scope
        #        names that include dots, although that's a bit perverse.
        keySpace: 'KeySpace' = None
        scopeName = keyref.split(".")[0]
        definers: list[Element] = self.peerKeyscopes.get(scopeName)
        if definers is not None:
            for definer in definers:
                keySpace = self.keyspaceManager.getKeyspaceByDefiner(definer)
                if keySpace is None:
                    print(f'[ERROR] Failed to get a keySpace for peer definer: <{definer.name} keyscope="{definer.get("keyscope")} href="{definer.get("href")}"/>')
                else:
                    # FIXME: For now, assume that the first peer scope with the scope name is the right one.
                    #        A more complete solution would actually attempt to resolve the key and then
                    #        return the first keyspace the key resolves in.
                    break
        return keySpace

    def resolveKey(self,
                   keyName: str,
                   mapcontext: Element=None,
                   hopsRemaining: int=3,
                   resolvePeerKeys: bool=True,
                   errors: dict={},
                   debug: bool=False) -> KeyDefinition:
        """Attempt to find a key definition for the specified key name.

        Args:

            keyName (str): The key name to resolve (keyname component of value of
                           @keyref or @conkeyref attribute)

            mapcontext (Element): The map context to resolve the key within.

            hopsRemaining (int): The number of indirect key references that can be resolved. When
                                 set to zero (0), indirect key references cannot be resolved.

        Returns:

            KeyDefinition: The key definition for the key name or None of it not found.
        """
        keySpace: 'KeySpace' = self
        # If no map context is provided, assume the this space's definer is
        # the map context. This could also be a runtime failure but currently it is not.
        if mapcontext is None:
            mapcontext = self.getSpaceDefiner()
        keySpace = self.getKeySpaceForMapContext(mapcontext, errors=errors, debug=debug)
        if keySpace is None:
            loggingutils.recordError(errors, keyName, Exception(f'No key space for map context {mapcontext} resolving key "{keyName}".'))
            keySpace = self
        keyDefs: list = keySpace.keydefsByKeyName.get(keyName)
        if keyDefs is not None:
            keyDef = keyDefs[0]
            definer = keyDef.getKeyDefiner()
            keyref = definer.get("keyref")
            hopsRemaining -= 1
            if keyref is not None and hopsRemaining:
                return self.resolveKey(keyref, mapcontext=definer, resolvePeerKeys=resolvePeerKeys, hopsRemaining=hopsRemaining)
            else:
                return keyDef
        if resolvePeerKeys:
            # If we didn't find a definition for the key, maybe it's a peer mapref.
            # Look at the scope qualifiers, if any, and see if we have peer maprefs
            # for those scopes.
            if "." in keyName:
                # FIXME: For now assuming only the first dot-separated token
                #        is a candidate scope name, but there could be scope
                #        names that include dots, although that's a bit perverse.
                scopeName = keyName.split(".")[0]
                definers: list[Element] = self.peerKeyscopes.get(scopeName)
                if definers is not None:
                    for definer in definers:
                        keySpace = self.keyspaceManager.getKeyspaceByDefiner(definer)
                        if keySpace is None:
                            print(f'[ERROR] Failed to get a keySpace for peer definer: <{definer.name} keyscope="{definer.get("keyscope")} href="{definer.get("href")}"/>')
                            break
                        if (keySpace.isDeferred()):
                            # Construct the key space. Note that this updates the KeySpace
                            # object in place.
                            self.keyspaceManager.constructDeferredKeyspace(keySpace)
                        keyToResolve: str = ".".join(keyName.split(".")[1:])
                        return keySpace.resolveKey(keyToResolve, resolvePeerKeys=False)
        return None

    def resolveKeydefToResource(self,
                                keyDef: KeyDefinition,
                                resolvePeerKeys: bool=False,
                                hopsRemaining: int=3,
                                errors: dict={},
                                debug: bool=False
                                ) -> Element:
        """Resolve a key definition to a resource.

        Resolves any intermediate key references.

        Resource returned will be one of the following:

        * A DITA topic
        * A DITA map
        * The link text from the key definition
        * The topicref itself when the format is not "dita" or "ditamap"
            * Image keydefs
            * External-scope keydefs for non-DITA resources

        Args:

            keyDef (KeyDefinition): The key definition to resolve

            resolvePeerKeys (bool): When True, keys in peer maps are resolved.

            hopsRemaining (int): The number of indirect key references that can be resolved. When
                                 set to zero (0), indirect key references cannot be resolved.

            errors (dict): Holds errors reported during resolution process

            debug (bool): Turns on debugging messages

        Returns:

            Element: The resource element or None if the key cannot be resolved.
        """
        if keyDef is not None:
            definer: Element = keyDef.getKeyDefiner()
            format = definer.get("format", "dita")
            scope = definer.get("scope")
            href = definer.get("href")
            keyref = definer.get("keyref")
            if debug:
                print(f'+ [DEBUG] resolveKeydefToResource(): definer: <{definer.tag} href="{href}">')

            if keyref is not None and hopsRemaining <= 0:
                loggingutils.recordError(errors, keyDef.getKeyName(), Exception(f'Hop count exceeded resolving key {keyref} from topicref {etree.tostring(definer)}.'), operation="KeySpace.resolveKeyToResource()")
                return None
            if keyref is not None and hopsRemaining:
                if debug:
                    print(f'+ [DEBUG] resolveKeydefToResource(): definer has @keyref, resolving through it...>')
                return self.resolveKey(keyref, resolvePeerKeys=resolvePeerKeys, hopsRemaining=(hopsRemaining - 1), mapcontext=definer)
            elif href is not None:
                if debug:
                    print(f'+ [DEBUG] resolveKeydefToResource(): definer has @href, resolving it...')
                if scope in ["peer", "external"]:
                    if debug:
                        print(f'+ [DEBUG] resolveKeydefToResource():   @scope is "peer", returning definer')
                    return definer
                elif format in ["dita", "ditamap"]:
                    if debug:
                        print(f'+ [DEBUG] resolveKeydefToResource():   @format is "{format}", resolving the @href')
                    return xmlutils.resolveUriRef(href, definer, errors=errors, debug=debug)
                else:
                    if debug:
                        print(f'+ [DEBUG] resolveKeydefToResource():   @format is "{format}", returning the definer')
                    return definer
            else: # Must be a string key
                if debug:
                    print(f'+ [DEBUG] resolveKeydefToResource():   no @href and local scope, must be key def, returning definer.')
                keyword: Element = definer.find('topicmeta/keywords/keyword')
                return deepcopy(keyword)

    def resolveKeyToResource(self, keyName: str,
                             mapcontext: Element=None,
                             resolvePeerKeys: bool=False,
                             hopsRemaining: int=3,
                             errors: dict={},
                             debug: bool=False
                             ) -> Element:
        """Resolve a key to the resource ultimately addressed.

        Resolves any intermediate key references.

        Resource returned will be one of the following:

        * A DITA topic
        * A DITA map
        * The link text from the key definition
        * The topicref itself when the format is not "dita" or "ditamap"
            * Image keydefs
            * External-scope keydefs for non-DITA resources

        Args:

            keyName (str): The key to be resolved.

            mapcontext (Element): The map context to resolve the key within. Defaults to root space

            resolvePeerKeys (bool): When True, keys in peer maps are resolved.

            hopsRemaining (int): The number of indirect key references that can be resolved. When
                                 set to zero (0), indirect key references cannot be resolved.

            errors (dict): Holds errors reported during resolution process

            debug (bool): Turns on debugging messages

        Returns:

            Element: The resource element or None if the key cannot be resolved.
        """

        keyDef: KeyDefinition = self.resolveKey(keyName, mapcontext=mapcontext, hopsRemaining=hopsRemaining)
        if debug:
            print(f'+ [DEBUG] resolveKeyToResource(): keyName: "{keyName}", keyDef: {keyDef}')
        return self.resolveKeydefToResource(
            keyDef,
            resolvePeerKeys=resolvePeerKeys,
            hopsRemaining=hopsRemaining,
            errors=errors,
            debug=debug
            )
