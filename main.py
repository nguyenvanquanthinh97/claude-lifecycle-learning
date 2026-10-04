#!/usr/bin/env python3
"""
Claude Code Hook Handler
=============================================
This script handles events from Claude Code and plays sounds for different actions.
It demonstrates event-driven programming and pattern matching in Python.
"""

import sys
import json
import subprocess
from pathlib import Path
import re

# ===== CONFIGURATION =====
# "lifecycle": speak the name of EVERY hook event (sounds/lifecycle/<Event>.wav),
#              so you can hear the order Claude Code fires them in
# "tools":     one sound per tool / bash command, using SOUND_MAP below
MODE = "lifecycle"

# Sound set for "tools" mode: "voice" (spoken words) or "beeps" (simple tones)
SOUNDS_TYPE = "beeps"

# ===== SOUND MAPPINGS =====
# This dictionary maps Claude Code events and tools to sound files
SOUND_MAP = {
    # System events - when Claude starts/stops
    "Notification": "ready",    # Claude is ready to help
    "Stop": "ready",           # Task completed
    "SubagentStop": "ready",   # Subtask completed

    # File editing tools - all use the same "edit" sound
    "Edit": "edit",            # Single file edit
    "MultiEdit": "edit",       # Multiple edits in one file
    "Write": "edit",           # Write new file
    "NotebookEdit": "edit",    # Edit Jupyter notebook

    # Task management
    "TodoWrite": "list",       # Update todo list

    # Bash command patterns - matched using regular expressions
    # Format: (regex_pattern, sound_name)
    "bash_patterns": [
        (r'^git commit', "commit"),                              # Git commits
        (r'^gh pr', "pr"),                                      # GitHub pull requests
        (r'^bundle exec rspec|^rspec|^bin/rspec', "test"),     # Ruby tests
        (r'^npm test|^yarn test|^pytest|^go test', "test"),    # Various test runners
        (r'.*', "bash"),  # Fallback: play "bash" sound for any unmatched Bash command
        # Add your own patterns here!
    ]
}

def player_command(file_path):
    """
    Build the command that plays an audio file on the current OS.

    The hook script must exit quickly (Claude waits for it), so we launch the
    player as a separate background process instead of playing inline.
    """
    if sys.platform == "win32":
        # winsound is built into Python on Windows; run it in a child Python
        # process so the sound keeps playing after this hook script exits
        code = "import sys, winsound; winsound.PlaySound(sys.argv[1], winsound.SND_FILENAME)"
        return [sys.executable, "-c", code, str(file_path)]
    if sys.platform == "darwin":
        return ["afplay", str(file_path)]          # macOS audio player
    return ["aplay", "-q", str(file_path)]         # Linux (ALSA)


def play_sound(sound_name, sound_set):
    """
    Play a sound file in the background (Windows, macOS or Linux).

    Args:
        sound_name: Name of the sound file (without extension)
        sound_set:  Sub-folder of sounds/ ("beeps", "voice" or "lifecycle")

    Returns:
        True if sound played successfully, False otherwise
    """
    # Security check: Prevent directory traversal attacks
    if "/" in sound_name or "\\" in sound_name or ".." in sound_name:
        print(f"Invalid sound name: {sound_name}", file=sys.stderr)
        return False

    # Build the path to the sound file
    script_dir = Path(__file__).parent
    sounds_dir = script_dir / "sounds" / sound_set

    # Try different audio formats (winsound/aplay only understand .wav)
    for extension in ['.wav', '.mp3']:
        file_path = sounds_dir / f"{sound_name}{extension}"

        if file_path.exists():
            try:
                # Play sound in background so we don't block Claude
                subprocess.Popen(
                    player_command(file_path),
                    stdin=subprocess.DEVNULL,             # Don't inherit Claude's pipes,
                    stdout=subprocess.DEVNULL,            # otherwise Claude would wait
                    stderr=subprocess.DEVNULL,            # for the sound to finish
                    # Windows: no console window flash, detach from the hook process
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                return True
            except (FileNotFoundError, OSError) as e:
                # Log error but don't crash
                print(f"Error playing sound {file_path.name}: {e}", file=sys.stderr)
                return False

    # Sound not found - fail silently to avoid disrupting Claude's work
    return False

def log_hook_data(hook_data):
    """
    Append the full hook_data to hook_handler.jsonl (one JSON object per line)
    so you can inspect exactly what Claude sends for each event.
    """
    try:
        log_path = Path(__file__).parent / "hook_handler.jsonl"
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(hook_data, ensure_ascii=False) + "\n")
    except Exception as e:
        # Fail silently, but print to stderr for visibility
        print(f"Failed to log hook_data: {e}", file=sys.stderr)


def get_sound_for_event(hook_data):
    """
    Determine which sound to play based on Claude's action.

    Args:
        hook_data: Dictionary containing event information from Claude

    Returns:
        Sound name (string) or None if no sound should play
    """

    event_name = hook_data.get("hook_event_name", "")  # e.g., "Notification", "PreToolUse"
    tool_name = hook_data.get("tool_name", "")          # e.g., "Edit", "Bash", "TodoWrite"

    # Step 1: Check if this is a system event (like Claude starting up)
    if event_name in SOUND_MAP:
        return SOUND_MAP[event_name]

    # Step 2: Check if this is a known tool (like Edit or TodoWrite)
    if tool_name in SOUND_MAP:
        return SOUND_MAP[tool_name]

    # Step 3: Special handling for Bash commands
    # We look at the actual command to decide which sound to play
    if tool_name == "Bash" and event_name == "PreToolUse":
        # Get the actual bash command Claude is about to run
        command = hook_data.get("tool_input", {}).get("command", "")

        # Check each pattern to see if it matches the command
        for regex_pattern, sound_name in SOUND_MAP["bash_patterns"]:
            if re.match(regex_pattern, command, re.IGNORECASE):
                return sound_name

    # Step 4: No matching sound found
    return None

def main():
    """
    Main program - this runs when Claude triggers a hook.

    How it works:
    1. Claude sends event data as JSON through stdin
    2. We parse the JSON to understand what Claude is doing
    3. We decide which sound to play (if any)
    4. We play the sound and exit
    """
    try:
        # Step 1: Read the event data from Claude
        # Claude sends JSON data through stdin (standard input)
        input_data = json.load(sys.stdin)
        log_hook_data(input_data)

        # Step 2: Figure out which sound to play
        if MODE == "lifecycle":
            # The event name IS the sound name: "PreToolUse" -> lifecycle/PreToolUse.wav
            # (events without a .wav file are simply silent)
            sound_name = input_data.get("hook_event_name", "")
            sound_set = "lifecycle"
        else:
            sound_name = get_sound_for_event(input_data)
            sound_set = SOUNDS_TYPE

        # Step 3: Play the sound (if we found one)
        if sound_name:
            play_sound(sound_name, sound_set)

        # Step 4: Exit successfully
        # Hook exit codes matter to Claude Code:
        #   0     = success, Claude continues normally
        #   2     = BLOCKING error: for PreToolUse the tool call is cancelled and
        #           stderr is shown to Claude (useful for guard-rail hooks!)
        #   other = non-blocking error: stderr is shown to you, Claude continues
        # A sound hook should never block, so we use 0 here and 1 below.
        sys.exit(0)

    except json.JSONDecodeError as e:
        # Handle case where Claude sent invalid JSON
        print(f"Error parsing JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Handle any other unexpected errors
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


# ===== EXAMPLE EVENT DATA FROM CLAUDE =====
# Here's what Claude sends us for different events:
#
# When editing a file:
# {
#   "hook_event_name": "PreToolUse",
#   "tool_name": "Edit",
#   "tool_input": {
#     "file_path": "/path/to/file.py",
#     "old_string": "old code",
#     "new_string": "new code"
#   }
# }
#
# When running a bash command:
# {
#   "hook_event_name": "PreToolUse",
#   "tool_name": "Bash",
#   "tool_input": {
#     "command": "git commit -m 'Update feature'"
#   }
# }
#
# When Claude is ready:
# {
#   "hook_event_name": "Notification"
# }


# Entry point - Python calls main() when the script runs
if __name__ == "__main__":
    main()