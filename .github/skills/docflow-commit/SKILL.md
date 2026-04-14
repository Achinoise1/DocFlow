---
name: docflow-commit
description: "Commit workflow for DocFlow. Use when: staging files and ready to commit, wanting to update the changelog, or rewriting all past commit messages to follow Conventional Commits format. Handles the full commit cycle: analyze staged diff → update changelog → stage changelog → generate commit message → git commit."
argument-hint: "commit (default) | changelog only | rewrite history"
---

# DocFlow Commit Workflow

This skill manages the full commit cycle for DocFlow. It ensures every commit is paired with a human-readable changelog entry and that commit messages consistently follow Conventional Commits format.

> **Safety rule**: The "rewrite history" mode is NEVER triggered automatically. It ONLY activates when the user explicitly says "rewrite history" in their request AND confirms a second time.

---

## Module Mapping

Map changed file paths to module labels. Every changelog entry and commit must be grouped under these labels.

| File path pattern | Module label |
|---|---|
| `core/converter/` | 转换核心 |
| `core/task_manager.py`, `core/conversion_registry.py` | 任务管理 |
| `ui/main_window.py`, `ui/theme_manager.py` | 主界面 |
| `ui/widgets/` | 界面组件 |
| `utils/` | 工具模块 |
| `doc/`, `*.md` (docs only) | 文档 |
| `resources/` | 资源/样式 |
| `scripts/`, `*.spec`, `requirements.txt` | 构建/打包 |
| `main.py` | 程序入口 |

---

## Changelog Format

File: `doc/changelog.md`

```
## 更新日志

### V{version}

#### {action}: {title}

**{module label}**
- {change description}
- {change description}

**{module label}**
- {change description}
```

Rules:
- `{version}`: from `git describe --tags --abbrev=0`; use `Unreleased` if no tag exists
- `{action}`: one of `feat` / `fix` / `chore` / `refactor` / `docs` / `style` / `build`
- A version section may contain multiple `####` blocks when changes span different action types (e.g. both `feat` and `fix` in the same version)
- Only include module labels that actually have changes
- New version sections are **prepended** to the file (latest version at top)

### Change Description Quality Rules

✅ Write descriptions that are:
- **Readable**: understandable by any developer, not just the author
- **Concise**: one line per change, no sub-bullets
- **Function-oriented**: describe what the user or developer can now do differently

❌ Do NOT include:
- Function names, class names, method signatures, variable names
- Internal implementation details or code mechanics
- File names (unless it is a user-facing config or script)
- Phrases like "modify X to do Y" that expose internal wiring

**Example — BAD:**
```
- `find_soffice()` 跨平台查找 LibreOffice 可执行路径（含 brew、`~/Applications`、snap/flatpak 等多候选路径）
```

**Example — GOOD:**
```
- 新增 LibreOffice 自动检测：跨平台查找 LibreOffice 安装路径，覆盖 Homebrew、snap、flatpak 等常见安装方式
```

---

## Mode 1: commit (default)

Triggered when the user has staged files and wants to commit.

### Execution steps (strict order)

**Step 1 — Capture staged diff**
```
git diff --staged
```
Store this output as the analysis source. Do NOT re-run this command later; use this snapshot throughout to avoid the diff changing after `doc/changelog.md` is staged.

**Step 2 — Get version**
```
git describe --tags --abbrev=0
```
If this fails (no tags), use `Unreleased` as the version string.

**Step 3 — Analyze diff**
- Map each changed file to its module label using the Module Mapping table
- Extract function-oriented changes per module (apply quality rules above)
- Determine the primary `{action}` type for the commit message

**Step 4 — Write changelog**
- Compose the new version section using the Changelog Format
- **Prepend** the new section immediately after the `## 更新日志` heading in `doc/changelog.md`
- If `doc/changelog.md` does not exist, create it with `## 更新日志` as the first line

**Step 5 — Stage changelog**
```
git add doc/changelog.md
```

**Step 6 — Generate commit message**
Using the analysis from Step 3, write:
```
{action}: {title}
```
- `{title}` must be concise (≤ 60 characters), in Chinese, describing the change set as a whole
- Do not repeat module names in the title if they are already obvious from context

**Step 7 — Commit**
```
git commit -m "{action}: {title}"
```

---

## Mode 2: changelog only

Triggered when the user says "changelog only" or wants to update the changelog without committing.

Execute Steps 1–4 only. Do NOT run `git add` or `git commit`.

Inform the user that `doc/changelog.md` has been updated and they can review it before committing.

---

## Mode 3: rewrite history

> ⚠️ **This mode rewrites git commit messages for all commits in the repository history. It cannot be undone without the original reflog.**

### Activation

This mode is ONLY entered when ALL of the following are true:
1. The user's request explicitly contains the phrase **"rewrite history"**
2. The user confirms with **"yes I confirm"** after seeing the warning below

If these conditions are not met, do NOT enter this mode, do NOT ask the user if they want to rewrite history, and do NOT mention this mode unprompted.

### Execution steps

**Step 0 — Check for staged content**
```
git diff --staged --name-only
```
If any staged files are detected, STOP immediately and inform the user:
> "检测到当前有未提交的暂存内容。`git rebase` 要求工作区完全干净，请先选择：
> 1. **先提交现有暂存**：切换到 commit 模式完成提交，再重新触发 rewrite history
> 2. **暂时搁置到堆栈**：执行 `git stash`，完成改写后再 `git stash pop`"

Do NOT proceed with any rebase steps until the user resolves the staged content and re-triggers the skill.

If no staged files exist, continue to Step 1.

**Step 1 — Show commit list**
```
git log --oneline
```
Display the full list to the user.

**Step 2 — Remote warning**
```
git remote -v
```
If a remote exists and the current branch has a tracking upstream (`git status -sb`), show this warning:
> "⚠️ 此分支已有远程追踪分支。改写历史后需要 `git push --force`，这会影响所有已拉取该分支的协作者。"

**Step 3 — Second confirmation**
Ask the user explicitly:
> "请输入 **yes I confirm** 确认改写所有提交历史，否则输入任何其他内容取消。"

Do NOT proceed until the user replies with exactly "yes I confirm".

**Step 4 — Analyze each commit**
For each commit hash from `git log --format="%H"` (oldest to newest):
```
git show {hash} --stat --format=""
```
Map changed files to module labels. Generate a new commit message:
```
{action}: {title}
```
Apply the same quality rules as Mode 1.

Collect the per-commit analysis results — they are reused in both Step 5 (rebase) and Step 6 (changelog rebuild).

**Step 5 — Apply rebase**

Use an automated `git rebase` with a pre-generated sequence editor script to replace all commit messages non-interactively. The script must:
1. Write a temporary todo file mapping each commit hash to its new `reword` message
2. Set `GIT_SEQUENCE_EDITOR` to a script that outputs the new todo list
3. Run `git rebase -i --root`

After completion, run `git log --oneline` and display the result so the user can verify the new messages.

**Step 6 — Rebuild changelog**

Using the per-commit analysis collected in Step 4, reconstruct `doc/changelog.md` from scratch:

1. Group commits by version tag: run `git tag --sort=version:refname` to get all tags, then use `git log {prev_tag}..{tag}` to assign each commit to its version. Commits before the first tag are grouped under the earliest tag; any commits after the latest tag use `Unreleased`.
2. For each version group (latest first), compose a version section following the Changelog Format:
   - Merge all commits within the same version into a single `### V{version}` block
   - Group change descriptions by module label
   - If a version has both `feat` and `fix` commits, emit separate `#### feat: ...` and `#### fix: ...` blocks
3. Overwrite `doc/changelog.md` entirely with the rebuilt content (do NOT append — replace the whole file).
4. Commit the updated changelog:
   ```
   git add doc/changelog.md
   git commit -m "docs: 按新规范重建更新日志"
   ```

---

## Quick Reference

| User says | Mode triggered |
|---|---|
| (has staged files, no special keyword) | commit (default) |
| "changelog only" | changelog only |
| "rewrite history" + "yes I confirm" | rewrite history |
| "rewrite history" (no confirmation) | prompt for confirmation, wait |
| "rewrite history" (staged files exist) | blocked — prompt user to commit or stash first |
| anything else | commit (default) if staged files exist |
