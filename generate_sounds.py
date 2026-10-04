#!/usr/bin/env python3
"""
Sound Generator for the Claude Code Hook Demo
=============================================
Creates the .wav files that main.py plays, so you don't need to download anything.

    sounds/beeps/<name>.wav  - short synthesized tones (pure Python, any OS)
    sounds/voice/<name>.wav  - spoken words (Windows built-in speech engine)

Run once:  python generate_sounds.py
"""

import math
import struct
import subprocess
import sys
import wave
from pathlib import Path

SOUNDS_DIR = Path(__file__).parent / "sounds"
SAMPLE_RATE = 44100

# Every sound name used in main.py's SOUND_MAP.
# beeps: list of (frequency_hz, duration_seconds) notes played one after another
# voice: the phrase the speech engine will say
SOUNDS = {
    "ready":  {"beeps": [(523, 0.12), (659, 0.12), (784, 0.20)], "voice": "Ready"},
    "edit":   {"beeps": [(880, 0.08)],                            "voice": "Editing"},
    "list":   {"beeps": [(660, 0.07), (660, 0.07)],               "voice": "Updating list"},
    "commit": {"beeps": [(392, 0.10), (523, 0.18)],               "voice": "Committing"},
    "pr":     {"beeps": [(523, 0.08), (784, 0.08), (1047, 0.15)], "voice": "Pull request"},
    "test":   {"beeps": [(440, 0.08), (554, 0.08), (440, 0.08)],  "voice": "Running tests"},
    "bash":   {"beeps": [(330, 0.08)],                            "voice": "Running command"},
}

# sounds/lifecycle/<HookEventName>.wav - one spoken phrase per hook event,
# listed in the order they fire during a session (used when MODE = "lifecycle")
LIFECYCLE = {
    # --- once per session ---
    "SessionStart":        "Session start",
    # --- once per prompt (turn) ---
    "UserPromptSubmit":    "Prompt submitted",
    "UserPromptExpansion": "Command expanded",
    # --- once per tool call (the agentic loop) ---
    "PreToolUse":          "Pre tool",
    "PermissionRequest":   "Permission request",
    "PermissionDenied":    "Permission denied",
    "PostToolUse":         "Post tool",
    "PostToolUseFailure":  "Tool failed",
    "PostToolBatch":       "Batch done",
    "SubagentStart":       "Subagent start",
    "SubagentStop":        "Subagent stop",
    "TaskCreated":         "Task created",
    "TaskCompleted":       "Task completed",
    # --- end of turn ---
    "Stop":                "Stop. Your turn",
    "StopFailure":         "Stop failure",
    # --- can happen at any time ---
    "Notification":        "Notification",
    "PreCompact":          "Pre compact",
    "PostCompact":         "Post compact",
    # --- once per session ---
    "SessionEnd":          "Session end",
}


def write_beep(path, notes):
    """Synthesize a sine-wave melody and save it as a 16-bit mono .wav file."""
    frames = bytearray()
    for freq, duration in notes:
        total = int(SAMPLE_RATE * duration)
        fade = int(SAMPLE_RATE * 0.01)  # 10 ms fade in/out avoids clicking
        for i in range(total):
            envelope = min(1.0, i / fade, (total - i) / fade)
            sample = 0.4 * envelope * math.sin(2 * math.pi * freq * i / SAMPLE_RATE)
            frames += struct.pack("<h", int(sample * 32767))
        frames += b"\x00\x00" * int(SAMPLE_RATE * 0.02)  # tiny gap between notes

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(bytes(frames))


def write_voice(path, phrase, rate=1):
    """Use Windows' System.Speech (via PowerShell) to record a spoken phrase."""
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Rate = {rate}; "
        f"$s.SetOutputToWaveFile('{path}'); "
        f"$s.Speak('{phrase}'); "
        "$s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)


def main():
    beeps_dir = SOUNDS_DIR / "beeps"
    voice_dir = SOUNDS_DIR / "voice"
    lifecycle_dir = SOUNDS_DIR / "lifecycle"
    for d in (beeps_dir, voice_dir, lifecycle_dir):
        d.mkdir(parents=True, exist_ok=True)

    for name, spec in SOUNDS.items():
        write_beep(beeps_dir / f"{name}.wav", spec["beeps"])
        print(f"beeps/{name}.wav")

    if sys.platform == "win32":
        for name, spec in SOUNDS.items():
            write_voice(voice_dir / f"{name}.wav", spec["voice"])
            print(f"voice/{name}.wav")
        # Spoken faster: tool events fire in quick bursts, so short clips overlap less
        for event, phrase in LIFECYCLE.items():
            write_voice(lifecycle_dir / f"{event}.wav", phrase, rate=3)
            print(f"lifecycle/{event}.wav")
    else:
        print("Skipping voice set (needs Windows speech engine). "
              "On macOS try: say -o sounds/voice/ready.wav --data-format=LEI16 Ready")


if __name__ == "__main__":
    main()
