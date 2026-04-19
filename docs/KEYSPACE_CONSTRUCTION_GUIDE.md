# Key Space Construction Guide (Implementation-Agnostic)

This guide describes a practical, general-purpose approach for constructing key spaces from a DITA map hierarchy. It is written for implementers who want to design their own key space processor, independent of any specific codebase.

## Purpose

A key space construction process should produce a data model that can answer:

- Which key names are available at a given map context?
- Which definition wins when the same key appears multiple times?
- How do scope-qualified key names resolve?
- How are keys in external or peer maps handled?

## Core concepts

Use these conceptual objects, regardless of language or library:

- Key space: A scope-bound collection of key definitions.
- Key definition: A binding from key name to a defining map element (or equivalent metadata object).
- Space definer: The map element that starts a scope (typically root map or map/topicref with @keyscope).
- Scope names: Tokens from @keyscope that name the key space.
- Key precedence list: Ordered list of definitions per key name, highest priority first.

## Recommended outputs

Your constructor should produce:

- A tree of key spaces (root plus descendants).
- Per-space lookup table from key name to ordered definitions.
- Optional indexes:
  - By space-defining element (for context-based lookup).
  - By map URI (for peer/deferred spaces).

## Input assumptions

Most implementations are easier and safer if they consume a resolved map tree first (all maprefs expanded according to your map-resolution policy). If your environment cannot pre-resolve maprefs, account for map expansion during traversal.

## Three-phase algorithm

A robust strategy is a three-phase process.

### Phase 1: Structural population

Traverse the map tree and build:

- Key space hierarchy.
- Local key definitions in each space.
- Peer/deferred space registrations.

During traversal, classify each element:

1. Non-key-bearing structures to skip or special-case (for example reltables or metadata containers).
2. Scope-defining elements (@keyscope) that create child spaces.
3. Key-defining elements (@keys) that add local definitions.
4. Peer map references (@scope="peer") that register external spaces.
5. Everything else, which simply passes traversal to children.

Design note: Keep traversal order deterministic. Deterministic order is essential for predictable precedence.

### Phase 2: Pull-up (qualified visibility)

Make descendant keys visible to ancestors using scope-qualified aliases.

For each descendant key definition:

- Create one or more qualified names using the descendant scope name(s), such as:
  - childscope.key
- Add these aliases to ancestor spaces according to your qualification policy.

Typical result: content in ancestor contexts can resolve references to descendant keys by explicit scope qualification.

### Phase 3: Push-down (inherited visibility and overrides)

Propagate ancestor definitions into descendant spaces.

- Each child inherits ancestor key definitions.
- On key-name collisions, apply your precedence policy consistently.

Typical result: descendant contexts can resolve inherited keys without qualification, while still allowing explicit local behavior where your precedence rules permit it.

## Precedence policy

Define this up front, document it clearly, and enforce it everywhere.

Common policy dimensions:

- Encounter order precedence: earlier or later wins.
- Inheritance precedence: ancestor-over-descendant or descendant-over-ancestor.
- Alias precedence: whether generated qualified aliases can override direct definitions.

Store definitions as ordered lists per key name, even if lookup usually returns only the first definition. This keeps diagnostics and reporting possible.

## Peer map strategy

For peer maps, support lazy construction when possible:

- Register peer scopes during initial traversal.
- Defer full construction until a key resolution requires that peer space.
- Cache constructed peer spaces by canonical map URI to avoid duplicate work.

Validation rules to enforce for peer entries:

- @scope is peer.
- @keyscope exists and has at least one token.
- @href exists and resolves to a readable target (when materializing deferred space).

## Context-based resolution model

Resolution APIs are easier to reason about when they separate concerns:

- Get key space for map context.
- Resolve key in a specific key space.
- Resolve root-qualified key (global entry point).
- Resolve peer-qualified key (cross-space entry point).

If a context element is not itself a space definer, choose a rule such as nearest ancestor scope definer.

## Error handling and diagnostics

Treat construction as a diagnostic-rich process, not only a lookup builder.

Capture and report:

- Invalid peer scope declarations.
- Missing/empty @keys or malformed key tokens.
- Broken URIs and unreadable map targets.
- Ambiguous collisions where policy may surprise users.

Recommended: retain provenance on each key definition (source file URI, element identifier, and traversal position) for explainable resolution.

## Suggested pseudocode

```text
construct_key_spaces(resolved_root):
  root_space = create_root_space(resolved_root)

  traverse(root_space, resolved_root):
    if is_skippable_structure(node):
      return

    if is_peer_reference(node):
      register_peer_space(node)
      return

    if defines_scope(node):
      child_space = create_child_space(node)
      if defines_keys(node):
        add_local_definitions(child_space, node)
      traverse_children(child_space, node)
      return

    if defines_keys(node):
      add_local_definitions(current_space, node)

    traverse_children(current_space, node)

  pull_up_qualified_aliases(root_space)
  push_down_inherited_definitions(root_space)
  return root_space
```

## Testing strategy

At minimum, create tests for:

- Single-space keys with no collisions.
- Nested scopes with qualified references.
- Duplicate key names across ancestor/descendant spaces.
- Multi-token @keyscope behavior.
- Peer scope lazy materialization.
- Cross-map repeated peer references to same target map.
- Deterministic precedence under repeated runs.

Include explainability checks: for any resolved key, verify you can report why that definition won.

## Implementation checklist

- Use canonical URI normalization for map identity.
- Keep traversal deterministic.
- Keep precedence operations explicit (prepend/append semantics).
- Preserve source provenance for each definition.
- Separate construction logic from resolution APIs.
- Add reporting tools (text or structured output) to inspect final spaces.

## Practical guidance

If behavior is unclear, prioritize these invariants:

- Key resolution must be deterministic.
- Scope qualification must be explicit and predictable.
- Cross-space and peer behavior must be diagnosable.
- Precedence rules must be consistent in local, pulled-up, and pushed-down cases.

These invariants matter more than any specific internal data structure.