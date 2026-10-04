# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A learning demo of Claude Code hooks: `main.py` (Python 3 standard library only) plays a sound for each Claude Code event. `.claude/settings.json` wires it to the 19 lifecycle events listed in `LIFECYCLE` in `generate_sounds.py` (no matchers, so every tool or agent counts). It's active in any Claude Code session opened in this folder. Claude Code passes the event JSON on stdin. There's no build step, no dependencies, and no test suite.

`settings.json` is generated from `LIFECYCLE`. To add or remove an event, edit that dict, regenerate the sounds, and update `settings.json` to match. Some events (`WorktreeCreate`, `Elicitation`) let the hook take over Claude Code's behavior, which is why they were left out on purpose.

## Commands

```bash
python generate_sounds.py   # (re)create sounds/beeps/*.wav (synth) and sounds/voice/*.wav (Windows SAPI)
echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git commit -m x"}}' | python main.py
```

Each run appends the payload as one JSON line to `hook_handler.jsonl`, which is the easiest way to see what Claude actually sends. Use `python`, not `python3`: on this machine `python3` is the Windows Store stub.

## How sounds are chosen

`MODE` in `main.py` controls which sound plays:
- **`"lifecycle"`** (the default): the event name is the file name, so `PreToolUse` plays `sounds/lifecycle/PreToolUse.wav`. Events without a file stay silent.
- **`"tools"`**: `get_sound_for_event` checks in this order:
1. `hook_event_name` in `SOUND_MAP` (`Notification`, `Stop`, `SubagentStop`)
2. `tool_name` in `SOUND_MAP` (`Edit`, `Write`, `TodoWrite`, ...)
3. For `Bash` + `PreToolUse` only: the `bash_patterns` regex list, tried in order with `re.match`. The final `.*` entry is a catch-all, so new patterns must go **before** it.

`play_sound` looks for `sounds/<SOUNDS_TYPE>/<name>.wav` or `.mp3` (`SOUNDS_TYPE` is `"beeps"` or `"voice"`). If no file exists it does nothing. New sound names must also be added to `SOUNDS` in `generate_sounds.py`.

Playback runs in a detached background process (`player_command`: a child Python using `winsound` on Windows, `afplay` on macOS, `aplay` on Linux), with stdio set to `DEVNULL`. That way the hook exits immediately and Claude doesn't wait for the sound. `winsound` only plays `.wav`.

Exit codes: 0 means OK. 2 blocks the tool call and feeds stderr back to Claude. Any other code is a non-blocking error. A sound hook must never exit 2.
