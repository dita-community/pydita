# Key Space Construction: Core Data Model

```mermaid
classDiagram
    class KeyspaceManager {
        +keyspaces : set
        +keyspacesByMapUri : dict
        +keyspacesByDefiner : dict
        +rootKeySpace : KeySpace
        +errors : dict
        +getRootKeyspace() KeySpace
        +resolveRootKeyref(keyName) KeyDefinition
        +addDeferredKeyspace(elem) KeySpace
        +constructDeferredKeyspace(keySpace)
        +getKeyspaceByMapUri(mapUri) KeySpace
        +getKeyspaceByDefiner(elem) KeySpace
    }

    class KeySpace {
        +keyScopeNames : list~str~
        +keydefsByKeyName : dict
        +keyspacesByScopeName : dict
        +peerKeyscopes : dict
        +isDeferred : bool
        +addKeyDefinition(keyDef)
        +addKeyDefinitions(keyDefs)
        +addKeyDefinitionElem(elem)
        +appendKeySpace(elem, scopeNames) KeySpace
        +addPeerMapref(elem)
        +resolveKey(keyName) KeyDefinition
        +getKeyDefinitions(sortKeys) list
        +getChildSpaces() list
        +getScopeNames() list
        +getSpaceDefiner() Element
        +setSpaceDefiner(elem)
        +unsetDeferred()
    }

    class KeyDefinition {
        +keyName : str
        +keyDefiners : list~Element~
        +keySpace : KeySpace
        +getKeyName() str
        +setKeyName(name)
        +getKeyDefiner() Element
        +getKeyDefiners() list
        +getKeySpace() KeySpace
        +resolveToResource() Element
        +isStringKey() bool
    }

    class PullUpVisitor {
        +collectedKeyDefsStack : list
        +visitKeySpace(keySpace)
        +visitKeyDefinition(keyDef)
    }

    class PushDownVisitor {
        +visitKeySpace(keySpace)
        +visitKeyDefinition(keyDef)
    }

    KeyspaceManager "1" --> "1" KeySpace : rootKeySpace
    KeyspaceManager "1" --> "0..*" KeySpace : keyspacesByMapUri\nkeyspacesByDefiner
    KeySpace "1" --> "0..*" KeySpace : children\n(anytree NodeMixin)
    KeySpace "1" --> "0..*" KeyDefinition : keydefsByKeyName\n(priority-ordered lists)
    KeyDefinition "1" --> "1" KeySpace : owning keySpace
    PullUpVisitor ..> KeySpace : visits (post-order)
    PushDownVisitor ..> KeySpace : visits (pre-order)
```

## Index relationships in `KeyspaceManager`

```mermaid
flowchart LR
    MapURI["Map URI\n(absolute)"] -->|"keyspacesByMapUri"| KS["KeySpace"]
    DefElem["Defining Element\n(map or peer topicref)"] -->|"keyspacesByDefiner"| KS
    KS -->|"getSpaceDefiner()"| DefElem
```

## Key definition priority list

Each key name maps to an **ordered list** of `KeyDefinition` objects. Index 0 is the highest-priority definition and is the one returned by `resolveKey()`.

```mermaid
flowchart LR
    KN["keyName"] --> KD0["KeyDefinition[0]\nhighest priority"]
    KD0 --> KD1["KeyDefinition[1]"]
    KD1 --> KDN["KeyDefinition[n]\nlowest priority"]
```
