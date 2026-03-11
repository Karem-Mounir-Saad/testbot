# Git Branch Merge Guide

> **Merge Flow:** `karem` / `hadi` → `dev` → `main`

This guide keeps your team branches in sync and avoids “branch is ahead” errors.

**Use `<WORK_BRANCH>` as either `karem` or `hadi`.**

---

## Branch Roles

- `karem`: Karem's working branch
- `hadi`: Hadi's working branch
- `dev`: integration and testing branch
- `main`: production/stable branch

---

## Step 1: Start From Your Work Branch

```bash
# Switch to your branch (karem or hadi)
git checkout <WORK_BRANCH>
git pull origin <WORK_BRANCH>
```

---

## Step 2: Make Your Changes & Commit

```bash
# Stage and commit your changes
git add .
git commit -m "your commit message"
```

---

## Step 3: Push Your Work Branch

```bash
git push origin <WORK_BRANCH>
```

---

## Step 4: Merge Work Branch into Dev

```bash
git checkout dev
git pull origin dev
git merge <WORK_BRANCH>
git push origin dev
```

---

## Step 5: Test on Dev

Run your tests and verify everything works on `dev` before moving to `main`.

---

## Step 6: Merge Dev into Main

```bash
git checkout main
git pull origin main
git merge dev
git push origin main
```

---

## Step 7: Keep Branches Synced (Recommended)

After releasing to `main`, sync `dev`, `karem`, and `hadi` so everyone continues from latest code.

```bash
git checkout dev
git pull origin dev
git merge main
git push origin dev

git checkout karem
git pull origin karem
git merge dev
git push origin karem

git checkout hadi
git pull origin hadi
git merge dev
git push origin hadi
```

---

## Quick One-Liner

```bash
git checkout dev && git pull origin dev && git merge <WORK_BRANCH> && git push origin dev && \
git checkout main && git pull origin main && git merge dev && git push origin main
```

---

## Team Rule

Do **not** merge `karem` or `hadi` directly into `main`.
Always follow:

`karem` / `hadi` → `dev` (test) → `main`

---

## Troubleshooting

### Merge Conflicts

```bash
# View conflicting files
git status

# After manually resolving conflicts
git add .
git commit -m "resolve merge conflicts"
git push
```

### Branch is Behind

```bash
# Always pull before merging
git pull origin <branch-name>
```

### Sync Branches (if out of sync)

```bash
git checkout dev && git pull origin dev && git merge main && git push origin dev
git checkout karem && git pull origin karem && git merge dev && git push origin karem
git checkout hadi && git pull origin hadi && git merge dev && git push origin hadi
```
