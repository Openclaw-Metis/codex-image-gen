# codex-image-gen

A Claude/agent **skill** that codifies a reliable way to make **OpenAI Codex** generate an image and actually land the file.

Codex's built-in `image_gen` only truly produces a bitmap inside an **interactive** Codex session; headless `codex exec` does not persist a new file and will falsely report success. This skill therefore always drives an interactive Codex session and wraps it with "explicit save path → wait for file → verify → recover" so every request ends with a verified image.

> 中文：把「叫 Codex 生成圖片並拿到檔案」變成一條可重複的流程。固定走互動式 Codex（Linux/macOS 用 tmux pane，Windows 用桌面 App 內建的 codex.exe 從互動終端啟動），明確要求存到絕對路徑、背景等檔、驗證長寬比，落檔失敗再從快取或 session rollout 還原。

## What it does

- Drives an **interactive** Codex session, never headless `codex exec`:
  - Linux/macOS: a tmux pane via `tmux send-keys`.
  - Windows (no tmux): the Codex CLI bundled with the Codex desktop app, launched with `--no-daemon` from the host's interactive terminal, with the prompt passed as the positional argument.
- Forces an explicit absolute save path and lets Codex write the file itself.
- Waits for the file with a background `until`-loop (foreground `sleep` is blocked in some harnesses).
- Verifies the result and target aspect ratio with `ffprobe` / PIL.
- Falls back to the `~/.codex/generated_images` cache, then to base64 recovery from the newest session rollout JSONL.

## Install

Clone the repository into your agent's skills directory as a folder named `codex-image-gen`:

```bash
git clone https://github.com/Openclaw-Metis/codex-image-gen.git ~/.claude/skills/codex-image-gen
```

The skill is then available as `codex-image-gen`. (Trigger descriptions are loaded at session start, so restart the agent session after installing.)

## Prerequisites (host environment)

- A logged-in **Codex CLI** (ChatGPT login; no `OPENAI_API_KEY` required for the built-in `image_gen`): either `codex` on `PATH`, or on Windows the copy bundled with the Codex desktop app.
- An interactive driver: a tmux pane (default target `codex-room.1`) on Linux/macOS, or a terminal tool on Windows (verified with Claude Code desktop's terminal panel).
- `ffmpeg`/`ffprobe` or Python **Pillow** for verification.

## Helper script

`scripts/codex_image.py` provides four subcommands (all paths overridable for portability):

```bash
python scripts/codex_image.py find-cli                       # codex on PATH, else the Windows desktop-app bundle
python scripts/codex_image.py verify  <path> --ratio 9:16 --since <epoch>   # validate image, aspect ratio, freshness
python scripts/codex_image.py locate  --since <epoch> --copy-to <path>   # newest cached Codex image
python scripts/codex_image.py recover --out <path>            # decode image from newest rollout base64
```

`--copy-to` and `--out` never replace an existing file unless `--overwrite` is passed.

Regression tests (stdlib only): `python scripts/test_codex_image.py`.

## Layout

- `SKILL.md` — routing + workflow; every resource is linked where it is used.
- `scripts/codex_image.py` — find-cli / verify / locate / recover helper; `scripts/test_codex_image.py` — its tests.
- `references/windows-host.md` — Windows host procedure and troubleshooting.
- `references/` — readiness report, migration governance, manual review checklist.
- `assets/evals/` — trigger + functional evals and regression gates.
- `skill_lifecycle.yaml` — owner, status, support matrix.

## License

MIT — see [LICENSE](../LICENSE). © 2026 Openclaw-Metis.
