"""Unit tests for the keyspace.py library
"""

import os
import sys
import io

from copy import copy

from pydita import keyspace, resolvemap
from pydita.keyspace import KeySpace, KeyDefinition
from pydita.keyspacemgr import KeyspaceManager
from pydita.keyspacevisitors import KeyspaceReportingVisitor
from pydita.keyspacevisitors import ExcelGeneratingKeyspaceVisitor
from lxml import etree
from lxml.etree import Element, ElementTree
from anytree import RenderTree
from pydita import loggingutils
from pydita.loggingutils import ErrorRecord


from .fixtures import rootMap, rootMap02, resolvedMap, keyspaceMgr, rootKeySpace, outdir, recursiveKeydefMap

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def test_keyspace(resolvedMap):
    # Construct a new key space representing the root key space from a map:
    keydefElem = Element("keydef",
                     {
                         "class": "+ map/topicref mapgroup-d/keydef ",
                         "keys": "topic01 second-key-name-topic01",
                         "href": "topics/topic-01.dita",
                         "processing-role": "resource-only",
                         "format": "dita"
                     })
    space = keyspace.KeySpace(KeyspaceManager(), resolvedMap.getroot(), "#annonymous", "bundle-devops")
    assert space.hasScopeName("#annonymous"), "Expected to have scope name #annonymous"
    assert not space.hasScopeName("not-a-scope"), "Expected no scope"
    assert space.hasScopeName("bundle-devops"), "Expected to have scope name bundle-devops"
    space.addKeyDefinitionElem(keydefElem)
    keydef = space.resolveKey("topic01")
    assert keydef is not None, "Expected to get a keydef"
    assert keydef.getKeyName() == "topic01", "Expected to have key name topic01"
    keydef = space.resolveKey("second-key-name-topic01")
    assert keydef is not None, "Expected to get a keydef"
    assert keydef.getKeyName() == "second-key-name-topic01", "Expected to have key name second-key-name-topic01"
    keydefElem = Element("keydef",
                     {
                         "class": "+ map/topicref mapgroup-d/keydef ",
                         "keys": "topic01 third-key-name-topic01",
                         "href": "topics/topic-01.dita",
                         "processing-role": "resource-only",
                         "format": "dita",
                         "product": "tokyo"
                     })
    space.addKeyDefinitionElem(keydefElem)
    keydef = space.resolveKey("third-key-name-topic01")
    assert keydef is not None, "Expected to get a keydef"
    assert keydef.getKeyName() == "third-key-name-topic01", "Expected to have key name third-key-name-topic01"

    # Test KeyDefinition.copy()
    newKeydef = copy(keydef)
    assert newKeydef is not None, "Expectd to get an object"
    print("New keydef:")
    print(newKeydef)

    assert newKeydef is not keydef, "Copy did not create new object"
    assert newKeydef.getKeyName() == keydef.getKeyName()
    assert newKeydef.getKeyDefiner() is keydef.getKeyDefiner(), "Expected same element"

    # Resolve the keydef to a resource. In this case the key definition is not real so it won't resolve:
    errors = {}
    resource = keydef.resolveToResource(errors=errors, debug=True)
    assert len(errors.keys()) > 0, f'Expected to get errors'

    # Now add new key scope:

    subscope1 = space.appendKeySpace(Element("topicref", {"class": "- map/topicref "}), "scope01")
    assert subscope1 is not None, "Expected to get a key space"
    assert isinstance(subscope1, keyspace.KeySpace), "Expected a KeySpace object"
    assert subscope1.parent is space

    # Render the tree:

    print(RenderTree(space).by_attr("label"))

def test_keyspaceManager(rootMap: str, resolvedMap: ElementTree, keyspaceMgr: KeyspaceManager):

    emptyManager: KeyspaceManager = KeyspaceManager()
    assert emptyManager.getRootKeyspace() is None, f'Expected None for root keyspace from empty manager constructor.'
    assert emptyManager.getKeyspaceByMapUri("foo") is None, f'Expected to not get a keyspace from empty manager'

    rootSpace = keyspaceMgr.getRootKeyspace()
    assert rootSpace is not None, "Expected to get the root key space"
    # Print the space:
    print("Root space report:")
    print(KeyspaceReportingVisitor().reportKeySpace(rootSpace))
    assert "scope-on-root-map" in rootSpace.getScopeNames(), "Expected 'scope-on-root-map' in scope names of root space."

    # Verify that we can construct a key space from an Element as well as from an ElementTree:

    mapRoot: Element = resolvedMap.getroot()
    ksm = KeyspaceManager(mapRoot)
    assert ksm is not None, f'Expected to get a KeyspaceManager'
    cand  = ksm.getRootKeyspace().getSpaceDefiner()
    assert cand is mapRoot, f'Expected the keyspace definer to be the mapRoot, got {cand}'

    expected: int = 4
    assert len(rootSpace.getChildSpaces()) == expected, f'Expected {expected} child spaces, got {len(rootSpace.getChildSpaces())} '
    # Resolve a key relative to the root key space:
    keydef: KeyDefinition = keyspaceMgr.resolveRootKeyref("key-01")
    assert keydef is not None, "Expected to get a key definition for key-01"
    keydef = keyspaceMgr.resolveRootKeyref("string-01")
    assert keydef is not None, "Expected to get a key definition for string-01"
    resource = keyspaceMgr.getRootKeyspace().resolveKeydefToResource(keydef)
    assert resource is not None, "Expected to get a resource"
    # Resolve a scope-qualified key reference to the scope's own scope:
    keydef = keyspaceMgr.resolveRootKeyref("scope-on-root-map.topic-01")
    assert keydef is not None, "Expected to get a key definition for scope-on-root-map.topic-01"
    # Resolve a scope-qualified key reference
    keydef = keyspaceMgr.resolveRootKeyref("submap01.topic-01")
    assert keydef is not None, "Expected to get a key definition for submap01.topic-01"
    keydef2 = keyspaceMgr.resolveRootKeyref("topic-02")
    assert keydef2 is not keydef, "Expected different keydef for topic-02 resolved from root scope."
    scopes = rootSpace.getKeyspacesByScopeName("submap01")
    assert scopes is not None, "Expected to have at least one 'submap01' scope"
    scope01 = None
    if scopes:
        scope01 = scopes[0]
    assert scope01 is not None, "Expected to have a scope01 key space"
    assert scope01.resolveKey("submap01.topic-01") is keyspaceMgr.resolveRootKeyref("submap01.topic-01"), "Expected same keydef for submap01.topic-01"

    keydef3 = scope01.resolveKey("topic-02")
    # keydef3 will be a different object but it should have the key-defining element from the root scope
    assert keydef2.getKeyDefiner() is keydef3.getKeyDefiner(), "Expected same key defininer for topic-02 keydef in submap01"

    assert rootSpace.resolveKey("submap02.submap01.topic-01") is None, "Should not have entry for key submap02.submap01.topic-01"

    # Check that we get the expected key-definers for overrides and scope-qualified keys:
    definer = rootSpace.resolveKey("topic-01").getKeyDefiner()
    assert definer.get("href") == "topics/topic-01.dita", "Expected root map's topic"
    definer = scope01.resolveKey("topic-01").getKeyDefiner()
    assert definer.get("href") == "topics/topic-01.dita", "Expected root map's topic"
    definer = rootSpace.resolveKey("submap01.topic-01").getKeyDefiner()
    assert definer.get("href") == "topics/sub-01-topic-01.dita", "Expected submap 01's topic"
    assert rootSpace.resolveKey("topic-03") is None, "Did not expect 'topic-03 to be resolvable from root scope."
    definer = rootSpace.resolveKey("submap01.topic-03").getKeyDefiner()
    assert definer.get("href") == "topics/sub-01-topic-03.dita", "Expected submap 01's topic"
    definer = scope01.resolveKey("topic-03").getKeyDefiner()
    assert definer.get("href") == "topics/sub-01-topic-03.dita", "Expected submap 01's topic"

def test_get_scope_by_definer(rootMap, resolvedMap, outdir):
    # Test the ability to get a key scope from scope-defining element
    resolvedMap.write(os.path.join(outdir, "resolved-map.dita"))

    keyspaceMgr: KeyspaceManager = KeyspaceManager(resolvedMap)
    rootSpace: KeySpace = keyspaceMgr.getRootKeyspace()
    assert rootSpace is not None, "Expected to get the root key space"

    # First test that using scope-defining elements works:
    scopeDefiners = resolvedMap.xpath("//*[@keyscope]")
    if len(scopeDefiners):
        for definer in scopeDefiners:
            keySpace: KeySpace = rootSpace.getKeySpaceForMapContext(definer)
            assert keySpace is not None, f'Expected to get a key space for key definer {definer}'
            definerScopes = definer.get("keyscope").split()
            test = False in (scope in keySpace.getScopeNames() for scope in definerScopes)
            assert not test, f'Scope names do not match, expected {keySpace.getScopeNames()}, got {definerScopes}'

    # Now test using non-scope-defining map contexts

    mapcontext = resolvedMap.xpath("//*[@href = 'topics/sub-01-topic-03.dita']")[0]
    keySpace: KeySpace = rootSpace.getKeySpaceForMapContext(mapcontext)
    assert keySpace is not None, "Expected a key space"
    test = False in (scope in ["submap01"] for scope in keySpace.getScopeNames())
    assert not test, f'Scope names do not match, expected {["submap01"]}, got {keySpace.getScopeNames()}'

def test_resolveKeyToResource(resolvedMap, rootKeySpace: KeySpace):
    # Test the resolution of key names to the actual resources they ultimately
    # point to.

    # Resolve a topicref to a topic:

    errors: dict = {}
    keyDef: KeyDefinition = rootKeySpace.resolveKey("topic-01")
    assert keyDef is not None, "Expected a keydef for topic-01"
    resource = rootKeySpace.resolveKeyToResource("topic-01", errors=errors)
    assert resource is not None, "Expected a resource for topic-01"
    assert resource.tag == "concept", f'Expected a <concept>, got <{resource.tag}>'
    assert resource.base.endswith("topics/topic-01.dita"), f'Expected base URI to be "topic-01.dita", got "{resource.base}"'

    # Now resolve using keyDef:
    resource = keyDef.resolveToResource(errors=errors, debug=True)
    assert resource is not None, "For resolveToResource(), expected a resource for topic-01"
    assert resource.tag == "concept", f'Expected a <concept>, got <{resource.tag}>'
    assert resource.base.endswith("topics/topic-01.dita"), f'Expected base URI to be "topic-01.dita", got "{resource.base}"'

    # Resolve through an intermediate keyref:
    keyDef: KeyDefinition = rootKeySpace.resolveKey("topic-04")
    assert KeyDefinition is not None, "Expected a keydef for topic-04"
    resource = rootKeySpace.resolveKeyToResource("topic-04")
    assert resource is not None, "Expected a resource for topic-04"
    assert not isinstance(resource, KeyDefinition), f'Expected Element, got {resource.__class__}'
    assert not type(resource) == str, f'Expected Element, got str'
    assert resource.base.endswith("topic-04.dita"), f'Expected base URI to be "topic-04.dita", got "{resource.base}"'

    # Resolve from a subspace
    keyDef: KeyDefinition = rootKeySpace.resolveKey("submap01.topic-02")
    assert keyDef is not None, "Expected a keydef for submap01.topic-02"
    subSpace: KeySpace = rootKeySpace.getKeyspacesByScopeName("submap01")[0]
    assert subSpace is not None, f'Expected a keyspace for scope name "submap01"'
    resource = subSpace.resolveKeyToResource("submap01.topic-02")
    assert resource is not None, "Expected a resource for submap01.topic-02"
    assert not isinstance(resource, KeyDefinition), f'Expected Element, got {resource.__class__}'
    assert not type(resource) == str, f'Expected Element, got str'
    assert resource.base.endswith("/submap01/topics/sub-01-topic-02.dita"), f'Expected base URI to be "/submap01/topics/sub-01-topic-02.dita", got "{resource.base[30:]}"'

    # Resolve using a non-defining map context
    topicrefs = resolvedMap.xpath("//*[@href = 'topics/sub-01-topic-03.dita']")
    assert len(topicrefs), f'Expected to get a topicref to topics/sub-01-topic-03.dita'
    mapcontext = topicrefs[0]
    keyName: str = "submap01.topic-03"
    keyDef: KeyDefinition = rootKeySpace.resolveKey(keyName)
    assert keyDef is not None, f'Expected a keydef for {keyName}'
    resource = rootKeySpace.resolveKeyToResource(keyName, mapcontext=mapcontext)
    assert resource is not None, f'Expected a resource for {keyName}'
    assert not isinstance(resource, KeyDefinition), f'Expected Element, got {resource.__class__}'
    assert not type(resource) == str, f'Expected Element, got str'
    assert resource.base.endswith("submap01/topics/sub-01-topic-03.dita"), f'Expected base URI to be "topic-04.dita", got "{resource.base[40:]}"'

    # Resolve an image keydef to a resource:
    keyName: str = "image-01"
    keyDef: KeyDefinition = rootKeySpace.resolveKey(keyName)
    assert keyDef is not None, f'Expected a keydef for {keyName}'
    resource = rootKeySpace.resolveKeyToResource(keyName, mapcontext=mapcontext)
    assert resource is not None, f'Expected a resource for {keyName}'
    assert resource.tag == "keydef", f'Expected to have a <keydef> element object as a result, got {resource}'

def test_resolvePeerKeyrefs(rootMap, rootMap02, rootKeySpace: KeySpace):
    # Test the resolution of peer key references.
    # A peer key reference is a reference to a key in a key scope
    # that is bound to a peer map.
    #
    # This requires constructing the key space from the peer map if
    # it is not already present in the key space manager.

    assert rootMap02 is not None, f'Expected to have root map 02 as a fixture'
    keyspaceMgr: KeyspaceManager = rootKeySpace.getKeyspaceManager()
    assert keyspaceMgr is not None, f'Expected to get the keyspace manager from the key space'
    rootMap01: Element = rootKeySpace.getSpaceDefiner()
    assert rootMap01 is not None, f'Expected to get space definer for root map 1'
    nl: list[Element] = rootMap01.xpath('(//topicref[@keys = "topic-11"])[1]')
    assert len(nl) > 0, f'Expected to find topicref for key "topic-11"'
    topicref: Element = nl[0]
    errors: dict = {}
    debug: bool = False
    keyref: str = 'root-02.topic-10'
    keydef: Element = rootKeySpace.resolveKey(keyref, topicref, errors=errors, debug=debug)
    assert keydef is not None, f'Expected to get a keydef for key "{keyref}"'
    resource: Element = rootKeySpace.resolveKeydefToResource(keydef)
    assert resource is not None, f'Expected to get a resource for the keydef for key "{keyref}"'
    expected: str = "topic-10.dita"
    topicFileName: str = os.path.basename(resource.base)
    assert topicFileName == expected, f'Expected resource filename of "{expected}", got "{topicFileName}"'
    # Now see if we can get the keyspace for the target topic given knowledge of the bundle scope:
    targetKeyspace: KeySpace = rootKeySpace.getKeyspaceForKeyref(keyref, errors=errors, debug=debug)
    assert targetKeyspace is not None, f'Expected to get a target keyspace'
    targetDefiner = targetKeyspace.getSpaceDefiner()
    assert targetDefiner.base.endswith('root-map-02.ditamap'), f'Expected to get map "root-map-02.ditamap", got {targetDefiner.base}'

def test_keydef_isStringKey(keyspaceMgr: KeyspaceManager):
    rootSpace = keyspaceMgr.getRootKeyspace()
    keyDef: KeyDefinition = rootSpace.resolveKey("string-01", resolvePeerKeys=False)
    assert keyDef is not None, f'Expected a keydef for key "string-01"'
    assert keyDef.isStringKey(), f'Expected True for isStringKey() for string key'

    keyDef = rootSpace.resolveKey("topic-01")
    assert keyDef is not None, f'Expected a keydef for key "topic-01"'
    assert not keyDef.isStringKey(), f'Expected False for isStringKey() for key for a topic.'

def test_excelGeneratingKeyspaceVisitor(rootKeySpace: KeySpace):

    name = os.path.basename(rootKeySpace.getSpaceDefiner().base).split(".")[0]
    outDir: str = os.path.join(os.environ["HOME"], 'out')
    debug:bool = False
    visitor:ExcelGeneratingKeyspaceVisitor = ExcelGeneratingKeyspaceVisitor(outDir, debug=debug)
    if debug:
        print(f'[DEBUG] Calling accept(visitor) on rootKeySpace...')
    rootKeySpace.accept(visitor)
    if debug:
        print(f'[DEBUG] Done.')

def test_scope_explosion(outdir):
    rootMap = open(os.path.join(SCRIPT_DIR, "resources/keyscope-explosion.ditamap"), "r")
    assert(None != rootMap)
    resolvedMap = resolvemap.resolveMap(rootMap)
    keyspaceMgr = KeyspaceManager(resolvedMap)
    rootSpace = keyspaceMgr.getRootKeyspace()
    assert rootSpace is not None, "Expected to get the root key space"
    reportPath = os.path.join(outdir, "keyscope-explosion-key-space-report.txt")
    reportFile = open(reportPath, 'w')
    print(f'Key space report is in {reportPath}')
    report = KeyspaceReportingVisitor().reportKeySpace(rootSpace)
    reportFile.write(report)
    name = os.path.basename(rootSpace.getSpaceDefiner().base).split(".")[0]
    debug:bool = False
    visitor:ExcelGeneratingKeyspaceVisitor = ExcelGeneratingKeyspaceVisitor(outdir, debug=debug)
    if debug:
        print(f'[DEBUG] Calling accept(visitor) on rootKeySpace...')
    rootSpace.accept(visitor)
    if debug:
        print(f'[DEBUG] Done.')

def test_recursiveKeydef(recursiveKeydefMap):
    """This function will test the ability to process recursive keydefs without failing.

    Args:
        recursiveKeydefMap (Element): ditamap with a recursive key definition.
    """
    errors: dict[str, ErrorRecord] = {}
    resolvedMap: ElementTree = resolvemap.resolveMap(recursiveKeydefMap, errors=errors)
    if len(errors) > 0:
        print(loggingutils.reportErrors(errors))

    keyspaceMgr: KeyspaceManager = KeyspaceManager(resolvedMap)
    rootKeySpace: KeySpace = keyspaceMgr.getRootKeyspace()

    keydef: KeyDefinition = rootKeySpace.resolveKey("good", errors=errors, debug=True)
    assert keydef is not None, "Expected a keydef"

    keydef: KeyDefinition = rootKeySpace.resolveKey("bad", errors=errors, debug=True)
    assert keydef is not None, "Expected a keydef"
