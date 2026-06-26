# codex-image-gen

A Claude/agent **skill** that codifies a reliable way to make **OpenAI Codex** generate an image and actually land the file.

Codex's built-in `image_gen` only truly produces a bitmap inside an **interactive** Codex session; headless `codex exec` does not persist a new file and will falsely report success. This skill therefore always drives an interactive Codex pane and wraps it with "explicit save path → wait for file → verify → recover" so every request ends with a verified image.

> 中文：把「叫 Codex 生成圖片並拿到檔案」變成一條可重複的流程。固定走互動式 Codex（tmux pane），明確要求存到絕對路徑、背景等檔、驗證長寬比，落檔失敗再從快取或 session rollout 還原。

## What it does

- Drives an **interactive** Codex pane via `tmux send-keys` (never headless `codex exec`).
- Forces an explicit absolute save path and lets Codex (YOLO mode) write the file itself.
- Waits for the file with a background `until`-loop (foreground `sleep` is blocked in some harnesses).
- Verifies the result and target aspect ratio with `ffprobe` / PIL.
- Falls back to the `~/.codex/generated_images` cache, then to base64 recovery from the newest session rollout JSONL.

## Install

Copy the repository contents into your agent's skills directory as a folder named `codex-image-gen`:

```bash
cp -a . ~/.claude/skills/codex-image-gen
```

The skill is then available as `codex-image-gen`. (Trigger descriptions are loaded at session start, so restart the agent session after installing.)

## Prerequisites (host environment)

- A logged-in **Codex CLI** (ChatGPT login; no `OPENAI_API_KEY` required for the built-in `image_gen`).
- An **interactive** Codex running in a tmux pane (default target `codex-room.1`).
- `ffmpeg`/`ffprobe` or Python **Pillow** for verification.

## Helper script

`scripts/codex_image.py` provides three subcommands (all paths overridable for portability):

```bash
python3 scripts/codex_image.py verify  <path> --ratio 9:16     # validate image + aspect ratio
python3 scripts/codex_image.py locate  --since <epoch> --copy-to <path>   # newest cached Codex image
python3 scripts/codex_image.py recover --out <path>            # decode image from newest rollout base64
```

## Layout

- `SKILL.md` — routing + workflow skeleton.
- `scripts/codex_image.py` — verify / locate / recover helper.
- `references/` — progressive-disclosure docs (start at `references/index.md`).
- `assets/evals/` — trigger + functional evals and regression gates.
- `skill_lifecycle.yaml` — owner, status, support matrix.

## License

MIT — see [LICENSE](LICENSE). © 2026 Openclaw-Metis.
