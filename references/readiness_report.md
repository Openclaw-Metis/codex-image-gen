# codex-image-gen — Readiness Report（發布證據）

Skill version: 2026.10.20
Audit date: 2026-10-20
Previous version: 2026.6.26（commit `e6a6c45`）
Change type: 失敗驅動修訂（SkillOps Studio `evolve` → `revise`），evidence level E2。
Host for this round: Windows 11 Home 10.0.26300，Claude Code desktop（Git Bash + PowerShell 5.1），Python 3.13，ffmpeg 9.0.1，Codex 桌面 App 26.1013.4894.0（內建 codex-cli 0.163.0-alpha.10.2，ChatGPT 登入）。

本頁只記錄本輪實際執行過的命令與結果。2026.6.26 初版的證據保留在 `e6a6c45` 的同名檔案。

## 本輪修正的常見錯誤（失敗紀錄）

| ID | 分類 | 觀察（來源、日期） | 2026.10.20 的修正 |
|----|------|--------------------|-------------------|
| F1 | environment_drift | Windows 宿主沒有 tmux、沒有 WSL，PATH 上也沒有 `codex`；Step 0 只能停止回報（實機 session，2026-10-20）。 | Step 0 改為選擇驅動方式；新增 Windows 分支與 `references/windows-host.md`。 |
| F2 | tool_contract | Codex 桌面 App 內建的 `codex.exe` 不加 `--no-daemon` 時，互動 TUI 印出 `this CLI has no complete local package` 後結束（同上）。 | `find-cli` 子命令在 stderr 提示 `--no-daemon`；SKILL.md 與 tool_rules 要求加上。 |
| F3 | resource | CLI 位於含版本號的 MSIX 安裝資料夾，路徑會隨 App 更新改變（同上）。 | `codex_image.py find-cli` 每次以 `Get-AppxPackage` 重新解析。 |
| F4 | instruction | 命令寫死 `python3` 與相對的 `scripts/` 路徑；Windows 的 `python3` 是 Store stub（同上）。 | 命令改為 `python <skill_dir>/scripts/codex_image.py`，Windows 規則寫明用 `python`。 |
| F5 | resource | 原版 stage gate FAIL：skill 根目錄含 `README.md`、`metadata` 非單行 JSON、21 個檔案未在使用點引用、4 份 `[TODO]` 參考文件與 4 份空 schema（`stage_gate.py --stage evolve`，2026-10-20）。 | README 移到 `.github/`；metadata 改單行 JSON；資源改在使用點連結；空殼檔案移除。 |
| F6 | safety | 目標檔若已存在，舊版等檔迴圈 `[ -f <path> ]` 會立刻成立，把舊檔當成本次結果；`locate --copy-to`／`recover --out` 也會直接覆寫既有檔，與 Ask first 政策矛盾（程式檢視與安全稽核 `model_budget_missing`、`untrusted_content_boundary_missing` 等發現，2026-10-20）。 | `verify --since` 擋舊檔；`--copy-to`／`--out` 改 no-clobber 加 `--overwrite`；Step 0 先詢問覆寫；SKILL.md 新增「安全與成本控制」（呼叫上限、不可信資料、供應商允許清單、最小權限、路徑邊界、回復）。 |

## 命令與結果

| 命令 | 結果 |
|------|------|
| `python scripts/test_codex_image.py`（2026.10.20） | 11/11 PASS |
| 同一組測試套用 `e6a6c45` 的 `codex_image.py` | 5 PASS、1 FAIL、5 ERROR：`find-cli` 四案、`--since` 舊檔與 no-clobber 兩案失敗，重現 F1–F3、F6 |
| `python scripts/codex_image.py find-cli`（實機） | exit 0，回傳桌面 App 內建 `codex.exe`，stderr 提示 `--no-daemon` |
| `python scripts/codex_image.py verify <實機輸出> --ratio 16:9 --since 1792494650`（2026.10.20 版） | PASS，1672x941，ratio 1.7768 |
| 實機出圖：互動 TUI，`--no-daemon --no-alt-screen -a never -s workspace-write -C <輸出目錄>`，prompt 為位置參數 | Codex 自行存檔（direct save），約 75 秒；`verify --ratio 16:9` → 1672x941，ratio 1.7768，2,753,155 B，PASS；檔案與 `generated_images` 快取內容相同 |
| 同一請求不加 `--no-daemon` | TUI 印出 `this CLI has no complete local package` 後結束（F2 的原始觀察） |

## 格式、結構與 gate 結果

Final status: PASS（本地 deterministic stage gate，不含 live benchmark）

| 命令（SkillOps Studio validator 3.7.0） | 結果 |
|------|------|
| `stage_gate.py --stage evolve`（修改前，`e6a6c45`） | FAIL：README 在 skill 根目錄、metadata 非單行 JSON、21 個 unreferenced_file |
| `stage_gate.py --stage evolve --require-security` | PASS |
| `stage_gate.py --stage revise --require-security` | PASS（含 rollback 證據檢查） |
| `release_gate.py --stage publish` | PASS |

各 audit：stage_contract、format、skill_references、unreferenced_files、skill_consistency、eval_assets（14 案；direct／indirect／negative；zh／en／mixed）與 skill_security 均 PASS。instruction_control 為 advisory，無 blocking finding。capability_chain、tool_execution_skill 不適用（一般 skill，SKIPPED）。`benchmark` SKIPPED：沒有 frozen live paired benchmark。

## 未涵蓋

- Linux／macOS 的 tmux 分支本輪未重跑；該分支的指令文字只改了 `python` 與 `<skill_dir>` 路徑寫法。
- 非 ASCII prompt 的處理（eval 13）只定義行為，未以實機驗證。
- 沒有 frozen live paired benchmark，lifecycle 維持 `draft`。

## Rollback

Rollback：checkout `e6a6c45`，或 revert 本次 commit；本次沒有改名、拆分或資料遷移，回復後不需額外清理。
