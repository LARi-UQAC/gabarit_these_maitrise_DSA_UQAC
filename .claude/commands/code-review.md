---
name: code-review
description: "Code review for all projects (CostEstimator, AssistPilot, OpForecast, SimulationCuveAluminium). Checks bugs, security, style, naming, docstrings, and test coverage against project rules. Trigger for any explicit review request or autonomously when code quality needs verification."
metadata:
  version: "1.0.0"
---

# Code Review

Review changed code for bugs, security vulnerabilities, style violations, and quality problems.
Apply rules from `.claude/rules/` (code-style, security, testing, preferences) if present in the current project.

`$ARGUMENTS` sets the review scope:
- *(empty)* — all uncommitted changes (staged + unstaged)
- `staged` — only staged changes
- `committed` — committed changes not yet on main/master
- `<branch>` — diff against that branch (e.g. `main`, `origin/main`)

---

## 1. Collect the Diff

Run the appropriate git command based on `$ARGUMENTS`:

| Scope | Command |
|-------|---------|
| *(empty)* or `all` | `git diff HEAD` |
| `staged` | `git diff --staged` |
| `committed` | `git log --oneline main..HEAD` then `git diff main...HEAD` |
| branch name | `git diff $ARGUMENTS...HEAD` |

If no git repository is found, scan all files modified in the current session instead.

Also run `git status` to list affected files and identify the project type (Blazor/C#, Python, TypeScript/React, LaTeX).

---

## 2. Detect Project Type and Load Rules

Identify active project(s) from file extensions and folder names:

| Indicator | Project | Rule files to apply |
|-----------|---------|-------------------|
| `*.razor`, `*.cs`, `*.csproj` | CostEstimator — Frontend | code-style (C# section), preferences |
| `api/`, `*.py` Flask routes | CostEstimator — API | code-style (Python), security, testing |
| `cost_estimator_project/`, `*.py` ML/CV | CostEstimator — Engine | code-style (Python), testing |
| `*.tsx`, `*.ts`, `vite.config.*` | AssistPilot — React | code-style (JS section) |
| `*.tex`, `*.tikz`, `*.bib` | OpForecast / SimAluminium | LaTeX conventions |
| Mixed | Multi-layer | Apply all relevant rule sets |

Read the rule files found at `.claude/rules/` in the current working directory.

---

## 3. Analyze — Check Against Rules

For each changed file, evaluate the following in order:

### A. Correctness & Bugs
- Logic errors, off-by-one, null dereferences, unhandled edge cases
- Python: missing type hints, wrong venv usage (`cost_estimator_project/.venv` vs root `.venv`)
- C#: missing `await`, wrong `@rendermode`, `HttpClient` called directly instead of `CostEstimatorApiClient`
- React: missing TypeScript types, `any` usage

### B. Security (Python/Flask)
- Session IDs not from `uuid4()`, or user-supplied session IDs accepted
- File uploads missing `secure_filename()`, extension check, or `%PDF` magic-byte validation
- Missing field validation at route entry (must return 400 immediately)
- Bounding box inputs not validated (must be int, non-negative, `x2 > x1`)
- `subprocess` called with `shell=True`, string-concatenated SQL, unvalidated file paths from user input
- Audit log writes outside `_FILE_LOCK`

### C. Code Style
**Python:**
- Functions missing type hints
- Classes not `PascalCase`, functions not `snake_case`, constants not `UPPER_SNAKE_CASE`
- Missing module docstring (pipeline stage number + description)
- Function docstring not using the Purpose / Inputs / Outputs format

**C# (Blazor):**
- Classes/methods/properties not `PascalCase`, private fields not `_camelCase`
- UI strings hardcoded in Razor instead of `@L["key"]`
- Raw Bootstrap classes instead of `ce-*` / `--ce-*` design system
- Direct `HttpClient` calls instead of `CostEstimatorApiClient`

**JavaScript/TypeScript:**
- Component files not `PascalCase.razor` or `PascalCase.tsx`
- CSS classes not `ce-kebab-case` (Blazor) or Tailwind utilities (React)

### D. Architecture Conventions
- Blazor: `@rendermode` not `InteractiveServer`
- JS interop: element keyed by object instead of `data-ce-vid` attribute
- `geometry-interop.js` modified without incrementing `?v=N` in `App.razor`
- New Flask route added without updating `.claude/CLAUDE.md` and `docs/reference/api-endpoints.md`
- `form` and `classification` fields on geometry shapes overwriting each other

### E. Testing Gaps
- New public functions with no test coverage
- Integration tests that mock Flask or the analysis engine
- Float comparisons using `assertEqual` instead of `assertAlmostEqual(x, y, places=2)`
- Long-running PDF tests missing a 300-second timeout comment
- Cost formula tests not linking to `docs/formulas/canonical-equations.md`

### F. LaTeX (OpForecast / SimAluminium)
- TiKZ using absolute coordinates instead of relative positioning
- Arrows not perpendicular to blocks, or overlapping elements
- References not peer-reviewed (non-IEEE/Springer/Elsevier/etc.)
- Missing DOI via hyperref
- AI-detectable patterns: zero-width spaces, smart quotes, em dashes, perfect parallel lists

---

## 4. Report Findings

Group all findings by severity:

### 🔴 Critical
Security vulnerabilities, data loss risks, crashes, hardcoded secrets.
*Must fix before merging.*

### 🟡 Warning
Bugs, broken conventions, missing type hints, skipped security checks, wrong render mode.
*Should fix.*

### 🔵 Info
Style nits, missing docstrings, minor naming violations, suggestions.
*Nice to fix.*

Format each finding as:
```
[SEVERITY] file:line — description
  → Fix: one-line suggestion
```

If no issues found, say: **No issues found.** ✅

---

## 5. Fix Issues (Autonomous Workflow)

If the user requests "review and fix" or "fix all issues":

1. Review and collect findings (steps 1–4)
2. Create a task list from Critical and Warning findings
3. Fix each issue systematically
4. Re-run the review to verify
5. Repeat until only Info-level findings remain or the diff is clean

Do not auto-fix Info-level issues unless the user asks.

---

## 6. Review Specific Scopes

**Staged only:**
```
/code-review staged
```

**Against main branch:**
```
/code-review main
```

**Committed but not merged:**
```
/code-review committed
```

Respond in French unless the active file or codebase is in English.
