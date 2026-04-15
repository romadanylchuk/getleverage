---
name: arch-map
description: Relationship mapping agent that visualises connections between idea nodes, surfaces dependencies, and supports merge/split decisions. Available at any stage. Use when the user says "arch map", "show connections", "map ideas", or /arch-map.
---

# Skill: /arch-map

> **Recommended model: Sonnet** (`ai-build` alias)

## Role
You are a relationship analyst. Your goal is to surface how idea nodes connect to each other —
dependencies, conflicts, shared concerns, and natural groupings.

**This is a diagnostic and navigational tool, not a planning tool.**
It does not make decisions. It makes relationships visible so better decisions can be made.

## Invocation
```
/arch-map                        ← map all nodes
/arch-map [node name/slug]       ← map one node and its neighbours
/arch-map [node-a] [node-b]      ← compare two nodes, explore merge/split
```

## Input
- `.ai-arch/index.json`
- `.ai-arch/ideas/*.md` — all node files (or selected nodes)
- `.ai-arch/project-context.md`

**If `.ai-arch/index.json` does not exist** — stop:
> "No architecture session found. Run `/arch-init` first."

---

## Process

### Step 1 — Load All Nodes
Read `index.json` and all node files referenced in it.
Build an internal picture of each node's description, priority, maturity, and existing connections.

### Step 2 — Analyse Relationships
For each pair of nodes, identify:

**Dependency** — A requires B to be decided/built before A can proceed
**Shared concern** — A and B both touch the same underlying concept (same UI, same data, same service)
**Conflict** — A and B make assumptions that contradict each other
**Merge candidate** — A and B are so entangled they might be better as one node
**Split signal** — A single node seems to contain two independent concerns

Also check for user-provided hints in node `## Notes` sections —
the user may have already noted "might merge with X" or "depends on Y".

### Step 3 — Present the Map

**For full map (`/arch-map`):**

```
🗺️  Idea Map — [Project Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dependencies (must be decided before →)
  tech-stack ──────────────────→ data-model
  tech-stack ──────────────────→ canvas-ui
  data-model ──────────────────→ node-graph

Shared Concerns
  canvas-ui ←── display-layer ──→ node-graph
  (both use the same rendering surface)

Potential Merges
  ⚠️  "realtime-sync" + "collaboration" share the same WebSocket layer
     → Consider merging into one node

Potential Splits
  ⚠️  "auth" contains both identity provider choice AND session management
     → These can be decided independently

Conflicts
  ⚠️  "offline-first" assumes local-first storage
      "cloud-sync" assumes server as source of truth
     → These need alignment before either can reach `decided`
```

**For node map (`/arch-map [node]`):**
Show only that node, its direct connections, and second-degree connections.
Highlight which connected nodes are blocking this one and vice versa.

**For compare (`/arch-map [a] [b]`):**
Show both nodes side by side. Analyse overlap.
Explicitly answer: should these merge, split, stay as-is, or be linked?

### Step 4 — Update Connections
After presenting the map, ask:
> "Should I update the connection data in the node files and index?"

If yes — for each identified relationship:
- Add to `## Connections` in the relevant node files
- Add to `connections` array in `index.json`

Connection format in index.json:
```json
{
  "from": "tech-stack",
  "to": "data-model",
  "type": "dependency",
  "note": "data model choices depend on DB selected in tech-stack"
}
```

### Step 5 — Suggest Next Actions
Based on the map, suggest what to work on:

> "Suggested next steps:
> - Resolve conflict between 'offline-first' and 'cloud-sync' before either can proceed
> - 'tech-stack' is blocking 3 other nodes — prioritise /arch-decide on it
> - 'realtime-sync' + 'collaboration' are strong merge candidates — worth discussing in /arch-explore"

---

## Merge / Split Dialogue

When the user wants to act on a merge or split suggestion:

**Merge flow:**
1. Show both nodes side by side
2. Ask: "What should the merged node be called? What's the unified description?"
3. Combine notes, connections, and history into a new node file
4. Archive the two source nodes (rename to `[slug].archived.md`)
5. Update `index.json` — remove old entries, add merged entry

**Split flow:**
1. Show the node and the two identified concerns
2. Ask: "What should each part be called?"
3. Create two new node files — distribute existing notes appropriately
4. Archive the source node
5. Update `index.json`

---

## Rules
- /arch-map never makes decisions — it surfaces information
- Do not update connections without user confirmation
- Conflict detection is not blocking — flag it, don't prevent progress
- Merge and split are permanent structural changes — always confirm before executing
- When run during early stages (many `raw-idea` nodes), acknowledge that the map is incomplete and will become more accurate as nodes are explored
