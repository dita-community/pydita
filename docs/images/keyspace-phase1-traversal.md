# Key Space Construction: Phase 1 Element Traversal

The recursive `_handleElement` function drives Phase 1. It performs a depth-first, pre-order walk and dispatches on element type.

```mermaid
flowchart TD
    START(["_handleElement(currentSpace, elem)"]) --> TYPE{"Element class?"}

    TYPE -->|topicmeta or reltable| SKIP["Skip — return"]

    TYPE -->|map| MAPSCOPE{"Has keyscope attr?"}
    MAPSCOPE -->|Yes| ADDSCOPE["Add keyscope tokens\nto currentSpace"]
    ADDSCOPE --> MAPCHILDREN["Walk children\nin currentSpace"]
    MAPSCOPE -->|No| MAPCHILDREN

    TYPE -->|topicref| PEER{"scope = peer?"}

    PEER -->|Yes| PEERMAP["addPeerMapref(currentSpace, elem)\naddDeferredKeyspace(elem)\nRegister deferred KeySpace by map URI.\nDo NOT traverse into peer content."]

    PEER -->|No| HASSCOPE{"Has keyscope attr?"}

    HASSCOPE -->|Yes| CHILDSPACE["_addChildKeySpace\nCreate child KeySpace\nwith keyscope tokens"]
    CHILDSPACE --> CHILDKEYS{"Also has keys attr?"}
    CHILDKEYS -->|Yes| ADDTOCHILD["_addKeyDefinition\nAdd keys to child space.\nWalk children in child space."]
    CHILDKEYS -->|No| WALKCHILD["Walk children\nin child space"]

    HASSCOPE -->|No| HASKEYS{"Has keys attr?"}
    HASKEYS -->|Yes| ADDLOCAL["_addKeyDefinition\nSplit keys into tokens.\nAppend KeyDefinition per token\nto currentSpace.\nWalk children in currentSpace."]
    HASKEYS -->|No| PASSTHRU["Walk children\nin currentSpace"]

    TYPE -->|Other| PASSTHRU
```

## Priority rule

Key definitions are **appended** in traversal order. Earlier-encountered definitions have higher priority (lower list index). Precedence is therefore document order within a given scope.
