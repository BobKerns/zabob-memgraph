# Git Subtree Sync Guide

This directory exists in two repositories:

- **[net-history](https://github.com/BobKerns/net-history)** - Canonical preservation archive
- **[zabob-memgraph](https://github.com/BobKerns/zabob-memgraph)** - Contextual copy showing tools used in curation

They're linked via git subtree, allowing bidirectional sync while maintaining independent repositories.

## Why Subtrees?

- No submodule complexity
- Files exist as regular files in both repos
- Easy for users (they don't even know it's a subtree)
- Bidirectional sync preserves full history
- Redundancy serves preservation goals

## Setup (for zabob-memgraph maintainers)

If you need to recreate the subtree connection:

```bash
# In zabob-memgraph repo
git remote add net-history git@github.com:BobKerns/net-history.git
git subtree add --prefix=docs/historical net-history main
```

## Sync Operations

### Pull Updates from net-history → zabob-memgraph

```bash
# In zabob-memgraph repo
git subtree pull --prefix=docs/historical net-history main
```

### Push Changes from zabob-memgraph → net-history

```bash
# In zabob-memgraph repo
git subtree push --prefix=docs/historical net-history main
```

## Normal Workflow

**If editing in net-history (recommended for doc-focused work)**:

1. Edit and commit in net-history
2. Push to net-history
3. Pull into zabob-memgraph when convenient

**If editing in zabob-memgraph (e.g., while working on code)**:

1. Edit and commit in zabob-memgraph
2. Push to zabob-memgraph
3. Push to net-history to sync: `git subtree push --prefix=docs/historical net-history main`

## Best Practices

- **Edit where it makes sense** - either repo is fine
- **Full history preserved** - no squashing, maintains complete provenance
- **Sync regularly** but not obsessively - periodic syncs work fine
- **Conflicts are rare** if you're the only editor in both repos

## The Preservation Strategy

Both repos preserve the content. Redundancy is good for preservation:

- **net-history**: Canonical source, focused on preservation, can outlive any specific project
- **zabob-memgraph**: Contextual copy, shows connection to tools used in curation

Cross-references in READMEs explain the relationship. If one disappears, the other survives.

## Troubleshooting

**Merge conflicts during pull:**

```bash
# Resolve conflicts in docs/historical/
git add docs/historical/
git commit -m "Resolve subtree merge conflicts"
```

**Want to see subtree history:**

```bash
git log --all --graph --decorate --oneline --simplify-by-decoration \
  -- docs/historical
```

**Forgot to add --squash initially:**
Good! Full history is better for preservation. Squashing loses provenance.

**History looks complex:**
That's normal with subtrees. The full history is valuable for understanding how documents evolved.

**Advanced: Interactive rebase:**
If you need to clean up history before syncing, `git rebase -i` works, but most users won't need this. The raw history is fine for preservation purposes.

---

**Related**: See [AUTHORSHIP.md](AUTHORSHIP.md) for voice and attribution guidelines.
