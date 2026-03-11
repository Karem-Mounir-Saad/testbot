# GitHub Issue & PR Close Guide

> **Use after manually merging changes via the [Merge Guide](MERGE_GUIDE.md).**

This guide provides templates for closing PRs and issues with clear, consistent messages.

**Replace placeholders: `<HASH>`, `<COMMIT_MSG>`, `<WORK_BRANCH>`, `<PR_NUMBER>`, `<ISSUE_NUMBER>`**

---

## Step 1: Close a PR (After Manual Merge)

```bash
gh pr close <PR_NUMBER> --comment "Merged manually via <WORK_BRANCH> branch through dev → main."
```

---

## Step 2: Close an Issue (After Fix is Merged)

```bash
gh issue close <ISSUE_NUMBER> --comment "$(cat <<'EOF'
## Resolved

**Commit:** `<HASH>` — `<COMMIT_MSG>`
**Branch:** `<WORK_BRANCH>`
**Merged:** `<WORK_BRANCH>` → `dev` → `main`

### Changes
- <what was fixed or changed>
- <additional changes>

### Related
- PR #<PR_NUMBER> (closed — same changes merged manually)
EOF
)"
```

---

## Quick One-Liners

### Close PR + Issue together

```bash
gh pr close <PR_NUMBER> --comment "Merged manually via <WORK_BRANCH> through dev → main." && \
gh issue close <ISSUE_NUMBER> --comment "Resolved in commit <HASH> on <WORK_BRANCH>. Merged through dev → main."
```

### Close issue with short message

```bash
gh issue close <ISSUE_NUMBER> --comment "Fixed in <HASH> — merged via <WORK_BRANCH> → dev → main."
```

---

## Comment Templates

### Minimal

```
Fixed in `<HASH>` — merged via `<WORK_BRANCH>` → `dev` → `main`.
```

### Standard

```
## Resolved

**Commit:** `<HASH>` — `<COMMIT_MSG>`
**Branch:** `<WORK_BRANCH>`
**Merged:** `<WORK_BRANCH>` → `dev` → `main`

### Changes
- <bullet points>

### Related
- PR #<PR_NUMBER>
```

### With Context (for bugs/issues)

```
## Resolved

**Commit:** `<HASH>` — `<COMMIT_MSG>`
**Branch:** `<WORK_BRANCH>`
**Merged:** `<WORK_BRANCH>` → `dev` → `main`

### Root Cause
<brief explanation of what caused the issue>

### Fix
- <what was changed to fix it>

### Related
- PR #<PR_NUMBER>
```

---

## Examples

### Example: Close PR

```bash
gh pr close 121 --comment "Merged manually via karem branch through dev → main."
```

### Example: Close Issue

```bash
gh issue close 126 --comment "$(cat <<'EOF'
## Resolved

**Commit:** `2897ab6` — `fix(player): improve video controls layout and remove dead code`
**Branch:** `karem`
**Merged:** `karem` → `dev` → `main`

### Changes
- Wrap controls with ClipRect to prevent overflow on small screens
- Fix RTL seek controls direction with Directionality(ltr)
- Rearrange bottom bar layout
- Remove 93 lines of unused code

### Related
- PR #121 (closed — same changes merged manually)
EOF
)"
```

---

## Team Notes

- Use `<WORK_BRANCH>` as `karem` or `hadi`.
- Do not mention `staging` in close comments for this project.
- Always describe merges as: `<WORK_BRANCH>` → `dev` → `main`.
