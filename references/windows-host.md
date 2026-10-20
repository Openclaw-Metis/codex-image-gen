# Windows 宿主執行細節

本文件只在 Step 0 判定「沒有 tmux」且宿主是 Windows 時載入。它把 tmux pane 換成宿主提供的互動終端，其餘等檔、verify、還原步驟與 Linux 流程相同。

## 已驗證環境

- 2026-10-20，Windows 11 Home，Claude Code desktop（Git Bash + PowerShell 5.1）。
- Codex 桌面 App 26.1013.4894.0，內建 `codex-cli 0.163.0-alpha.10.2`，ChatGPT 登入，`image_generation` feature 為 stable。
- 沒有 tmux、沒有 WSL，PATH 上也沒有 `codex`。
- 16:9 請求實得 1672x941（ratio 1.7768），約 75 秒，Codex 自行把圖從 `~/.codex/generated_images/<thread>/exec-*.png` 複製到指定路徑。

## 1. 取得 Codex CLI

執行 `python <skill_dir>/scripts/codex_image.py find-cli`：

- PATH 上有 `codex` 時印出它，照一般方式啟動。
- 否則印出桌面 App（MSIX 套件 `OpenAI.Codex`）內建的 `...\app\resources\codex.exe`，並在 stderr 提示要加 `--no-daemon`。安裝資料夾名稱含 App 版本，每次都以 `find-cli` 重新取得，不要沿用舊路徑。
- 回傳 FAIL 時停止，請使用者安裝 Codex CLI 或桌面 App 並完成 ChatGPT 登入。

Windows 的 `python3` 常是 Microsoft Store 的轉址 stub，命令一律用 `python`（或 `py -3`）。

## 2. 啟動互動式 Codex

PowerShell 啟動命令範本（`<codex.exe>` 來自 find-cli，`<輸出目錄>` 是目標檔所在資料夾）：

```powershell
& '<codex.exe>' --no-daemon --no-alt-screen -a never -s workspace-write -C '<輸出目錄>' '<英文 prompt>'
```

- `--no-daemon`：桌面 App 內建的 CLI 沒有完整本機套件，不加會出現 `this CLI has no complete local package` 並結束。
- `[PROMPT]` 位置參數：互動 TUI 啟動後會直接送出這段 prompt，等同 tmux 的 send-keys + Enter；這仍是互動 session，不是 `codex exec`。
- `-a never -s workspace-write -C '<輸出目錄>'`：Codex 只能寫入輸出目錄，足以自行把圖複製到目標路徑，不需要完整 YOLO（`--dangerously-bypass-approvals-and-sandbox`）。
- `--no-alt-screen`：讓終端讀取工具看得到捲動內容。

prompt 內容照 SKILL.md Step 2 的要求撰寫（用 image_gen、實際存到絕對路徑、印出路徑、長寬比）。

## 3. 由宿主驅動終端

- Claude Code desktop：用 `run_in_terminal` 送出上面整行命令（每次呼叫開一個新分頁），再用 `read_terminal`（`wait_for_output_ms` 15000–60000）讀進度。`run_in_terminal` 只接受單行可列印 ASCII，不能含 `$` 變數、管線或括號運算式，所以 prompt 用英文，路徑與 prompt 用單引號包住，prompt 內不要放單引號。
- 沒有終端工具的宿主：把完整命令交給使用者在自己的 PowerShell 執行，其餘等檔與 verify 照常由 agent 進行。

完成訊號依序是：`Saved to: file:///.../generated_images/...`、Codex 執行複製命令、最後印出目標絕對路徑與 `Worked for ...`。畫面停在 `Working` 不代表失敗，以 Step 3 的等檔結果為準。

## 4. 收尾

拿到檔案並 verify 後，用 `stop_terminal_tab`（`close: true`）關掉該分頁，避免互動 Codex 一直留在背景。

## 疑難排解

| 現象 | 處理 |
|---|---|
| `this CLI has no complete local package` | 關掉分頁，同一行命令加 `--no-daemon` 重跑 |
| `find-cli` 回傳 FAIL | 停止並請使用者安裝 Codex CLI 或桌面 App、完成 ChatGPT 登入 |
| 出現資料夾信任或權限確認畫面 | 請使用者在該分頁回答；本次實測加了 `-a`／`-s` 旗標時未出現 |
| `run_in_terminal` 拒絕命令 | 檢查是否含非 ASCII、`$`、括號或多行；改成英文單行 prompt |
| 逾時仍無檔 | 照 SKILL.md Step 5 先 `locate --since <baseline>`，再 `recover` |
