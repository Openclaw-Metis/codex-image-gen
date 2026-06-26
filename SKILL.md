---
name: codex-image-gen
description: 在使用者要「用 Codex 生成圖片 / 調用 CODEX 出圖 / 請 Codex 畫一張…」時使用：透過互動式 Codex 內建的 image_gen 出圖，並可靠地把檔案落地。常見觸發：「用 codex 生成圖片」「調用 codex 出一張 9:16 的…」「codex 幫我畫一隻…」「codex image」。流程：在互動式 Codex 的 tmux pane 用 send-keys 下 prompt 並明確要求存到絕對路徑、YOLO 模式讓 Codex 自行存檔、背景 until-loop 等檔、ffprobe/PIL 驗尺寸與長寬比；若沒落檔再從 generated_images 快取或 session rollout base64 還原。不適用於 headless `codex exec`（不會落新檔且會謊報成功），不適用於非 Codex 的其他出圖工具，也不適用於純文字的 Codex 任務。
version: 2026.6.26
homepage: https://github.com/Openclaw-Metis/codex-image-gen
license: MIT
metadata:
  author: Openclaw-Metis
  owner: Openclaw-Metis
  language: zh-TW
  category: ops
---

# Codex Image Gen

這個 skill 把「叫 Codex 生成圖片並拿到檔案」變成一條可重複的流程。它的重點不是寫提示詞，而是解決一個已知的可靠性問題：Codex 的內建 `image_gen` 只在**互動式** Codex（TUI/App）裡才會真的產生點陣圖；headless `codex exec` 不會落新檔，還會抓到舊檔謊報成功。本 skill 因此固定走互動式 Codex pane，並用「明確存檔路徑 + 等檔 + 驗證 + 還原 fallback」確保最終真的拿到正確的圖。

它不負責挑選出圖模型、不負責非 Codex 的出圖管道，也不負責後製編修；只負責「用 Codex 出一張圖並落地驗證」。

## Single responsibility

- Primary job：驅動互動式 Codex 生成一張圖片，並可靠地把檔案落地、驗證尺寸/長寬比後交付。
- Not this skill's job：挑選/比較出圖模型、影像後製（放大/去背/外擴）、批次出圖管線、純文字的 Codex 任務。
- Split / handoff rule：若使用者要的是非 Codex 的出圖工具、或要對既有圖做編修，交給對應的影像工具流程；本 skill 只處理「Codex 出圖」這一段。

<role>
你是負責「用 Codex 出圖」的執行者。你站在一個已知 Codex image_gen 落檔不穩的工程立場，目標是讓每次請求都實際產出一個可驗證的影像檔，而不是相信 Codex 的口頭 DONE。
</role>

<decision_boundary>
Use when:
- 使用者明確要求用 Codex / CODEX 生成或繪製圖片（中文、英文或混用）。
- 使用者指定了主題、風格、長寬比，並預期拿到一個圖片檔。

Do not use when:
- 使用者要的是非 Codex 的出圖工具或 MCP 影像服務。
- 任務是對既有影像做後製（放大、去背、外擴、改比例）。
- 任務是純文字的 Codex 互動，與出圖無關。

Inputs:
- 圖片描述（主題/風格/構圖）。
- 目標長寬比（如 9:16、16:9、1:1）。
- 可選：輸出檔名或目錄（預設 ~/exports/<slug>.png）。

Successful output:
- 一個已驗證的影像檔（路徑、尺寸、長寬比、檔案大小皆已確認），長寬比在容差內，且交付路徑明確。
</decision_boundary>

## Primary use cases (2-3)

1) **直接出圖**
- Trigger examples：「請你調用 CODEX 生成圖片，一頭神馬，9:16」「用 codex 畫一隻賽博龍 16:9」
- Required inputs：主題描述、長寬比
- Expected result：~/exports 下一個落地且通過長寬比驗證的 PNG

2) **指定輸出路徑出圖**
- Trigger examples：「用 codex 出一張封面存到 ~/exports/cover.png，3:4」
- Required inputs：主題、長寬比、目標路徑
- Expected result：圖片落在指定路徑並通過驗證

3) **落檔失敗的還原**（fallback）
- Trigger examples：Codex 說做好了但 ~/exports 沒有檔
- Required inputs：剛才那次 Codex 互動的 session
- Expected result：從 generated_images 快取或 rollout base64 還原出正確影像

## Routing boundaries

- Neighboring workflows：非 Codex 的出圖工具 / 影像後製工具 / 純文字 Codex 任務。
- Negative triggers：headless `codex exec` 出圖、模型選型、批次出圖、影像編修。
- Handoff rule：需要非 Codex 管道或後製時，交給對應影像流程。

## Language coverage

- Primary language：繁體中文（使用者主要語言）。
- Mixed-language triggers：「用 codex 生成圖片」「codex image 9:16」「generate an image with codex」。
- Locale risk：「出圖／生圖／畫一張」皆視為出圖請求。

## Host / portability targets

- Primary host：在能驅動本機 tmux 與 Codex CLI 的 agent runtime（如 Claude Code / OpenClaw）內執行。
- Environment prerequisites：已安裝且已登入（ChatGPT 登入，不需要 OPENAI_API_KEY）的 Codex CLI；一個互動式 Codex 跑在 tmux pane（預設 `codex-room.1`）；ffmpeg/ffprobe 與 PIL 任一可用。
- Unsupported：headless `codex exec` 出圖；無互動 Codex pane 的環境。
- Core portable surface：skill pack + `scripts/codex_image.py`（路徑皆可用旗標覆寫）。
- State / persistence path：影像落在 ~/exports 或使用者指定路徑；Codex 快取在 ~/.codex/generated_images；不在 skill 資料夾內存放任何快取或產物。

<success_criteria>
Quantitative:
- 出圖請求的落檔成功率：≥ 99%（含 fallback）。
- 長寬比驗證：與目標誤差 ≤ 0.02。
- 不使用 headless `codex exec` 出圖：0 次。

Qualitative:
- 不需使用者額外操作即可拿到檔案。
- 交付格式固定、可重複。
</success_criteria>

<workflow>
Step 0: Confirm request and interactive Codex pane
- Action: 彙整出圖要素（主題、長寬比、輸出路徑），並確認有可用的互動式 Codex pane（預設 `codex-room.1`）；若無，回報如何啟動或請使用者起一個，不要改用 headless exec。
- Input: 使用者的圖片描述、長寬比、可選輸出路徑。
- Output: 完整 prompt 要素 + 目標絕對路徑（預設 `~/exports/<slug>.png`）+ 確認的 pane target。
- Validation: `tmux list-panes -t codex-room` 能列出互動 Codex pane；`mkdir -p` 確保輸出目錄存在。

Step 1: Snapshot baseline
- Action: 記錄出圖前的時間戳作為 baseline，避免之後抓到舊的快取檔。
- Input: 目前時間（`date +%s`）與 `~/.codex/generated_images` 現況。
- Output: baseline epoch。
- Validation: 已取得 baseline epoch（後續 `locate --since` 會用到）。

Step 2: Drive the interactive Codex turn
- Action: 用 `tmux send-keys -t <pane> -l "<prompt>"` 送出 prompt，再用 `tmux send-keys -t <pane> Enter` 送出。prompt 必須明確要求：「用你的 image_gen 工具生成並『實際存檔』，存到 <絕對路徑>，最後印出該檔案的絕對路徑」，並描述主題與長寬比。
- Input: pane target、目標絕對路徑、主題描述、長寬比。
- Output: 已提交的 Codex turn。
- Validation: `tmux capture-pane` 顯示 Codex 進入 Working / 開始執行。

Step 3: Wait for the file to land
- Action: 用背景 until-loop 等檔，不要用 foreground sleep（部分 harness 會擋）。範例：以 run_in_background 跑 `end=$((SECONDS+240)); until [ -f <path> ] || python3 scripts/codex_image.py locate --since <baseline> >/dev/null 2>&1 || [ $SECONDS -ge $end ]; do sleep 3; done`。
- Input: 目標路徑、baseline epoch、逾時上限（建議 200–300s）。
- Output: 落檔的影像路徑，或逾時訊號。
- Validation: 目標路徑存在，或 `locate --since` 找到新檔；兩者皆無則進 Step 5。

Step 4: Verify the image
- Action: 用 `python3 scripts/codex_image.py verify <path> --ratio <W:H>` 驗證可解析、印出尺寸與長寬比、檢查容差。
- Input: 落檔路徑、目標長寬比。
- Output: PASS/FAIL + 尺寸/比例/檔案大小。
- Validation: 影像可解析且長寬比在容差內；超出容差則回報並提供裁切或重試選項，不默默交付錯比例圖。

Step 5: Fallback recovery (only if nothing landed)
- Action: 先試 `python3 scripts/codex_image.py locate --since <baseline> --copy-to <path>` 從 generated_images 快取撈最新圖；仍無則 `python3 scripts/codex_image.py recover --out <path>` 從最新 rollout JSONL 的 base64 還原。
- Input: baseline epoch、~/.codex/generated_images、~/.codex/sessions rollout、目標路徑。
- Output: 還原的影像，或明確回報無法取得（含原因，如 Codex 額度耗盡）。
- Validation: 還原檔需再通過 Step 4 的 verify。

Step 6: Finalization and QA
- Action: 回報最終絕對路徑、尺寸、長寬比與生成方式（direct save / cache locate / rollout recover）；不刪除既有檔、不自動上傳到外部。若是在改版這個 skill 本身，改用 skill-creator-advanced 的驗證工具鏈跑 format / structure / workflow / release gate，並更新 `references/readiness_report.md`。
- Input: 已驗證的影像與最終交付路徑；改版時則是本 skill 資料夾。
- Output: 最終交付摘要，外加改版時的 gate 結果。
- Validation: 影像通過 Step 4 的 verify；改版時 release gate 無 BLOCKED。
</workflow>

<output_contract>
依序輸出：
1. 結論：成功（含最終絕對路徑）或失敗（含原因）。
2. 影像規格：尺寸（WxH）、長寬比、檔案大小、生成方式（direct / cache / rollout）。
3. 使用紀錄：驅動的 pane 與關鍵命令。
4. 剩餘風險或建議：如比例需裁切、額度警告。

Formatting rules:
- 預設繁體中文 Markdown。
- 路徑一律用絕對路徑。
- 長寬比超出容差時，結論不得標示為「成功」。
- 缺資訊時明說缺什麼，不臆造已落檔。

Gate precedence（fail-first）:
- 任一 final gate、stage gate 或 policy gate 為 FAIL / BLOCKED 時，結論只能是 FAIL 或 BLOCKED；本 skill 的 verify 與 fallback 同理，未通過就不得標示成功。
- 局部 PASS 只可列在定位資訊，且必須明確標註不具放行效力。
</output_contract>

<tool_rules>
- 只透過互動式 Codex 的 tmux pane 出圖；禁止用 headless `codex exec` 出圖（會謊報且不落新檔）。
- `tmux send-keys` 先送 `-l` 的 literal 文字，短暫間隔後再單獨送 `Enter`。
- 等檔用背景 until-loop（run_in_background），不要用 foreground sleep。
- 內建 image_gen 走 ChatGPT 登入，不需要也不要求 `OPENAI_API_KEY`。
- `scripts/codex_image.py` 的路徑旗標（--root/--sessions/--out/--copy-to）保持可覆寫，維持跨主機可攜。
</tool_rules>

<default_follow_through_policy>
- Directly do：下 prompt、等檔、locate、verify、必要時 recover、裁切到目標比例、把圖複製到使用者指定路徑。
- Ask first：覆蓋既有同名輸出檔、把圖片上傳/發佈到任何外部服務、刪除任何檔案。
- Stop and report：沒有可用的互動 Codex pane、Codex 回報額度耗盡、locate 與 recover 都拿不到正確影像。
</default_follow_through_policy>

<examples>
Example 1
Input:
- 使用者：「請你調用 CODEX 生成圖片，一頭神馬，9:16」

Output:
1. 結論：成功，已存到 `/home/ubuntu/exports/shenma_9x16.png`。
2. 影像規格：941x1672，ratio 0.5628（目標 9:16=0.5625），2.7MB，生成方式：direct save。
3. 使用紀錄：pane `codex-room.1`；prompt 要求存到絕對路徑並印出；背景 until-loop 等檔；`codex_image.py verify --ratio 9:16` PASS。
4. 剩餘風險：無；比例已在容差內。

Example 2
Input:
- 使用者：「codex 說圖做好了但我 ~/exports 沒看到檔」

Output:
1. 先 `codex_image.py locate --since <baseline> --copy-to <path>` 從 generated_images 快取撈最新圖。
2. 若快取也沒有，`codex_image.py recover --out <path>` 從最新 rollout JSONL base64 還原。
3. 還原後一律再跑 verify；若連 rollout 都沒有 base64，回報無法取得並建議重出一次。
</examples>

<model_notes>
- GPT 風格模型：把「實際存檔到絕對路徑並印出路徑」寫死在 prompt，不要只說「生成一張圖」。
- 推理型模型：給目標（落地 + 比例）與限制（互動式、不可用 exec），不需逐字規定 prompt 內容。
- Multi-turn split：出圖（Step 2）與等檔/驗證（Step 3-4）天然分屬不同 turn，等檔請用背景任務而非阻塞。
</model_notes>

## References

See `references/index.md` for the progressive-disclosure index. Release evidence
lives in `references/readiness_report.md`; lifecycle/governance docs are loaded
only when changing this skill itself.

## Testing plan

### Triggering tests
- Golden trigger set:
  - Direct：「請你調用 CODEX 生成圖片，一頭神馬，9:16」
  - Indirect：「codex 幫我畫一張封面，3:4」
  - Negative：「用 codex 幫我看這段程式的 bug」（非出圖，不應觸發）
- Should trigger：明確要求 Codex 出圖（中/英/混用）。
- Should NOT trigger：非 Codex 出圖、影像後製、純文字 Codex 任務。
- Near-miss：「幫我生成一張圖」未指名 Codex —— 需澄清是否要用 Codex。
- Should ask before acting：要覆蓋既有同名輸出檔、或要上傳圖片到外部。

### Functional tests
- Happy path：指定主題+9:16 → 落檔且 verify PASS。
- Edge case：Codex 出的是方形而非要求比例 → verify FAIL → 回報並裁切/重試。
- Failure mode：~/exports 沒落檔 → locate 快取 →（仍無）rollout recover → verify。

### ROI guardrail
- 相對於「直接相信 Codex DONE」，本 skill 的額外步驟（等檔+驗證+還原）換到的是落檔可靠性與正確比例，值得。
