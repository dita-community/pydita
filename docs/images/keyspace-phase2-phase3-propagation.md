# Key Space Construction: Phase 2 Pull-Up and Phase 3 Push-Down

## Phase 2 — Pull Up (`PullUpVisitor`)

Pull-up makes descendant keys visible to ancestors via scope-qualified aliases. The visitor uses a stack of collector lists to gather aliases as it ascends the tree.

```mermaid
flowchart TD
    START(["PullUpVisitor.visitKeySpace(keySpace)"]) --> HASCHILDREN{Has\nchildren?}

    HASCHILDREN -->|Yes| PUSH["Push new collector list\nonto collectedKeyDefsStack"]
    PUSH --> VISITKIDS["Visit each child space\n(recursive — post-order)"]
    VISITKIDS --> POP["Pop collector list\n(aliases gathered from descendants)"]
    POP --> ADDCOLLECTED["Add collected keydefs\nto currentSpace\n(addKeyDefinition)"]
    HASCHILDREN -->|No| ADDCOLLECTED

    ADDCOLLECTED --> QUALIFY["For each keyDef in currentSpace:\n  for each scopeName (skip #annonymous):\n    copy keyDef\n    rename: scopeName.originalKeyName\n    append to parent collector (stack top)"]

    QUALIFY --> ISROOT{Is\nroot space?}
    ISROOT -->|Yes| ADDTOROOT["Add all qualified aliases\nfrom collector to root space"]
    ISROOT -->|No| DONE(["Return — parent will\ncollect from stack top"])
    ADDTOROOT --> DONE
```

**Effect:** After pull-up, an ancestor space can resolve `subscope.key` even though `key` was defined in a descendant scope.

---

## Phase 3 — Push Down (`PushDownVisitor`)

Push-down makes ancestor keys available unqualified in every descendant scope, and enforces ancestor-wins precedence for duplicate key names.

```mermaid
flowchart TD
    START(["PushDownVisitor.visitKeySpace(keySpace)"]) --> EACHCHILD["For each child in keySpace.getChildSpaces():\n  child.addKeyDefinitions(keySpace.getKeyDefinitions())"]

    EACHCHILD --> MERGE["addKeyDefinitions merges by key name:\n  if key name already exists in child →\n    prepend incoming definers (ancestor wins)\n  if key name is new →\n    add as new definition"]

    MERGE --> RECURSE["Recurse: visitKeySpace(child)\nfor each child"]

    RECURSE --> DONE(["All descendants now contain\nfully merged visible key set"])
```

**Effect:** After push-down, content anywhere in the map tree can resolve keys defined in any ancestor scope without qualification, and ancestor definitions take precedence over same-name descendant definitions.

---

## Combined precedence model

| Mechanism | Operation | Precedence effect |
|-----------|-----------|-------------------|
| Phase 1 append | `list.append(keyDef)` | Earlier traversal order wins |
| Phase 2 pull-up | Copy + rename to qualified alias | Ancestors gain access to descendant keys via qualified names |
| Phase 3 push-down | `list.prepend(inherited)` | Ancestor definitions override same-name descendant definitions |
