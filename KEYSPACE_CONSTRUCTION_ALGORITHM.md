# DITA Key Space Construction Algorithm

This document describes how key space construction works in the current Python implementation, centered on `keyspacemgr.py` and supported by `keyspace.py` and `keyspacevisitors.py`.

## Scope of this algorithm

The algorithm constructs a tree of `KeySpace` objects and populates them with `KeyDefinition` objects from a resolved DITA map (`resolvemap.resolveMap()` output). It also prepares peer-map key spaces for deferred (lazy) construction.

The implementation performs construction in three phases:

1. Populate key spaces by walking the resolved map tree.
2. Pull up descendant keys as scope-qualified names.
3. Push down ancestor keys into descendant spaces (with override precedence).

## Core objects and indexes

### KeyspaceManager

`KeyspaceManager` owns all known key spaces and keeps two global indexes:

- `keyspacesByMapUri`: map URI -> key space
- `keyspacesByDefiner`: defining element -> key space

When created with a resolved map, the manager:

1. Creates a root `KeySpace` with initial scope name `#annonymous`.
2. Registers it in manager indexes.
3. Calls `constructKeySpace(rootKeySpace, resolvedMap)`.

### KeySpace

A `KeySpace` contains:

- `keyScopeNames`: set of scope names for this space.
- `keydefsByKeyName`: key name -> list of `KeyDefinition` in priority order.
- `keyspacesByScopeName`: child scope name -> list of child key spaces (priority order).
- `peerKeyscopes`: peer scope name -> peer mapref element(s).

Priority is represented by list ordering. Earlier entries are higher priority.

## Phase 1: Populate spaces and raw key definitions

Entry point: `constructKeySpace(rootKeySpace, resolvedMap)`.

### Step 1.1 Normalize input and bind root definer

If `resolvedMap` is an `ElementTree`, the code uses `.getroot()`. If it is already an element, it is used directly.

The root element is bound as the space definer for `rootKeySpace`, then recursive traversal starts at `_handleElement(rootKeySpace, rootElem)`.

### Step 1.2 Recursive element handling (`_handleElement`)

Traversal is depth-first and pre-order. Behavior by element type:

1. `map/topicmeta`: ignored.
2. `map/reltable`: ignored.
3. `map/map`:
   - If `@keyscope` is present, tokens are added to current key space.
   - Continue with children in same key space.
4. `map/topicref`:
   - If `@scope="peer"`: treat as peer map key scope (`_addPeerMapKeySpace`), do not traverse into peer map content here.
   - Else if `@keyscope` exists: create a child key space (`_addChildKeySpace`).
   - Else if `@keys` exists: add key definitions to current key space (`_addKeyDefinition`).
   - Else: recurse into children in same key space.
5. Other elements: recurse into children.

### Step 1.3 Adding key definitions (`_addKeyDefinition` + `addKeyDefinitionElem`)

For a key-defining element:

1. Read `@keys`, split into individual key names.
2. For each key name, create a `KeyDefinition` tied to that element.
3. Append to `keydefsByKeyName[keyName]` list.

Appending preserves traversal priority (earlier encountered definitions stay first).

After adding the key definitions, children of that key-defining element are still traversed in the same key space.

### Step 1.4 Creating child key spaces (`_addChildKeySpace`)

For `topicref` with `@keyscope`:

1. Split `@keyscope` into scope names.
2. Create child `KeySpace` with `appendKeySpace(elem, *scopeNames)`.
3. If same element also has `@keys`, add those keys to the new child space.
4. Otherwise recurse through children within that child space.

### Step 1.5 Peer map scopes and deferred spaces (`_addPeerMapKeySpace`)

For `topicref` with `@scope="peer"`:

1. Record peer scope names in current key space (`addPeerMapref`).
2. Ask manager to register deferred key space (`addDeferredKeyspace(elem)`).

Deferred key spaces are keyed by absolute target map URI (`urljoin(elem.base, @href)`).

If that map URI already has a key space, scope names are merged into the existing space. Otherwise a new deferred `KeySpace` is created and indexed.

## Phase 2: Pull up descendant keys as qualified names

Entry point: `PullUpVisitor().visit(rootKeySpace)`.

This visitor performs a post-order walk and propagates scope-qualified aliases upward.

For each key space:

1. Visit children and gather key definitions collected from descendants.
2. Add gathered definitions to current key space (`addKeyDefinition`).
3. For each key definition in current key space and each local scope name except `#annonymous`:
   - Copy the key definition object.
   - Rename key as `scopeName.originalKey`.
   - Add this renamed key definition to a collection passed up to ancestors.
4. Special case for root space:
   - Add all collected qualified key definitions to root.

Effect: ancestors can resolve descendant keys using scope-qualified names (for example `subscope.key`).

## Phase 3: Push down ancestor keys into descendants

Entry point: `PushDownVisitor().visit(rootKeySpace)`.

For each parent space:

1. Add all parent key definitions to each child (`child.addKeyDefinitions(parent.getKeyDefinitions())`).
2. Recurse into children.

`addKeyDefinition` merges by key name. If key already exists, incoming key-defining elements are prepended to existing definers, giving incoming definitions higher priority.

Because push-down adds ancestor definitions to child spaces via this prepend behavior, ancestor keys override same-name keys in descendants in the final merged view.

## Construction completion

At the end of `constructKeySpace`, `rootKeySpace.unsetDeferred()` is called. This marks the key space as fully constructed.

For peer spaces, construction may happen later via `constructDeferredKeyspace(keySpace)`, which:

1. Resolves peer map URI from peer mapref.
2. Verifies map file exists and is readable.
3. Resolves that map with `resolvemap.resolveMap()`.
4. Calls `constructKeySpace()` on the deferred key space.

## Precedence model summary

The effective precedence results from three mechanics:

1. Initial population appends key definitions in traversal order.
2. Pull-up adds qualified aliases from descendants into ancestors.
3. Push-down prepends inherited ancestor definitions into descendants, so inherited ancestor definitions win for duplicate names.

For any key name, a `KeySpace` stores a list of definers in priority order; index 0 is the highest-priority definer used by resolution.

## High-level pseudocode

```text
constructKeySpace(rootSpace, resolvedMap):
  rootElem = normalize_to_element(resolvedMap)
  bind rootElem as rootSpace definer

  walk(rootSpace, rootElem):
    if topicmeta or reltable: skip
    elif map:
      add map keyscope names to current space
      walk children in current space
    elif topicref:
      if scope=peer:
        register peer mapref + deferred space
      elif has keyscope:
        child = append child space
        if has keys: add keys in child
        else walk children in child
      elif has keys:
        add keys in current space
        walk children in current space
      else:
        walk children in current space
    else:
      walk children in current space

  PullUpVisitor(rootSpace)
  PushDownVisitor(rootSpace)
  mark rootSpace non-deferred
```

## Practical implications

- A single physical map can back one shared key space even if referenced as peer from multiple places.
- Scope-qualified aliases are synthesized during pull-up, not read directly from map source.
- Final key visibility in each scope is a merged view, not only locally declared keys.
- Peer key spaces can exist as placeholders until the first resolution requires actual construction.