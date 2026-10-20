# Migration governance

This document defines evidence required before renaming, deprecating, merging, splitting, or retiring this skill.

## Rename
- Record old name, new name, reason, routing compatibility plan, package path impact, registry impact, and references checked.

## Deprecate
- Record deprecation reason, replacement skill or fallback workflow, effective date, removal date, user-facing notice, rollback condition, and eval impact.

## Merge
- Record source skills, target skill, boundary rationale, trigger conflict resolution, follow-through policy conflict resolution, eval migration, and wrapper updates.

## Split
- Record original skill, new target skills, routing boundary, handoff rules, eval redistribution plan, and compatibility aliases.

## Compatibility
- Check package paths, skill names, aliases, catalog entries, README links, registry entries, wrappers, local references, and benchmark workspaces.

## Migration Evidence
- Keep migration_type, from, to, effective_date, compatibility_policy, references_checked, evals_updated, wrappers_updated, and release_gate_result.

## 2026.10.20 相容性紀錄

- migration_type：無（同名、同路徑的加法修訂，未改名、拆分或合併）。
- 行為：tmux 分支的驅動方式不變；新增 Windows 分支（`find-cli` + `--no-daemon` + 宿主互動終端）與 `codex_image.py find-cli` 子命令；`verify` 新增選用的 `--since`。
- 不相容變更：`locate --copy-to` 與 `recover --out` 改為 no-clobber，目標已存在時 FAIL，需加 `--overwrite`（使用者同意後）才會取代。依賴舊行為的呼叫端要補上 `--overwrite`。
- evals_updated 另含 eval 14（目標檔已存在、舊檔不得當成本次結果）。
- 套件路徑：`README.md` 移到 `.github/README.md`（GitHub 仍顯示為首頁），skill 根目錄不再含 README；安裝方式改為 `git clone` 到 `~/.claude/skills/codex-image-gen`。
- 移除的檔案：references 下內容只有 `[TODO]` 的 fusion、migration template、retirement、telemetry 四份 playbook；schemas 下只含 `{"type":"object"}` 的 lifecycle、release evidence、run trace、skill spec 四份空 schema；以及改由 SKILL.md 使用點連結取代的 references 索引頁。這些檔案沒有被任何流程讀取，完整內容可從 `e6a6c45` 取回。
- evals_updated：新增 eval 11–13（Windows 無 tmux、daemon 錯誤重試、非 ASCII prompt）。
- release_gate_result：見 [readiness report](readiness_report.md)。
- Rollback：checkout `e6a6c45`，或 revert 本次 commit。
