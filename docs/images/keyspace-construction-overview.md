# Key Space Construction: Three-Phase Overview

```mermaid
flowchart TD
    IN([resolvedMap + rootKeySpace]) --> P1

    subgraph P1["Phase 1: Structural Population"]
        direction TB
        P1A["constructKeySpace(rootKeySpace, resolvedMap)"]
        P1B["_handleElement — depth-first pre-order walk"]
        P1C["Key space tree built.\nLocal KeyDefinitions appended in traversal order.\nPeer map scopes registered as deferred spaces."]
        P1A --> P1B --> P1C
    end

    P1 --> P2

    subgraph P2["Phase 2: Pull Up (qualified visibility)"]
        direction TB
        P2A["PullUpVisitor — post-order walk"]
        P2B["For each scope name in each space,\ncreate qualified alias: scopeName.keyName"]
        P2C["Aliases propagated upward to ancestor spaces.\nRoot space receives all qualified aliases."]
        P2A --> P2B --> P2C
    end

    P2 --> P3

    subgraph P3["Phase 3: Push Down (inherited visibility)"]
        direction TB
        P3A["PushDownVisitor — pre-order walk"]
        P3B["Add all parent key definitions to each child.\nIncoming definitions prepended (ancestor wins on collision)."]
        P3C["Every descendant space contains\nfull merged view of visible keys."]
        P3A --> P3B --> P3C
    end

    P3 --> DONE(["rootKeySpace.unsetDeferred() — Construction complete"])
```

## Effect of each phase

| Phase | What it builds | Who benefits |
|-------|---------------|--------------|
| 1 — Populate | Local key definitions in each scope | Same-scope resolution |
| 2 — Pull up | Scope-qualified aliases (`child.key`) in ancestor spaces | Ancestor-to-descendant qualified references |
| 3 — Push down | Inherited ancestor definitions in every descendant | Unqualified resolution of ancestor keys from any descendant context |
