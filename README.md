# PinLock

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![Dependencies](https://img.shields.io/badge/Dependencies-None-brightgreen)

A lightweight PIN-based screen overlay for Windows 11 that locks your active session without logging out. Built with Python and Tkinter — single-file, no dependencies.

> **Note:** This is a quick-lock overlay for trusted environments (open offices, shared workspaces, home), not a security replacement for `Win+L`. See [Security model](#security-model) below.

## Why PinLock?

The built-in Windows lock (`Win+L`) is great for security, but it has drawbacks for short breaks:

- It interrupts your workflow — you have to re-enter your full Windows password / PIN
- It signals "I'm hiding something" to anyone watching
- It's overkill when you just want to step away for a coffee

PinLock fills that gap. It throws a fullscreen overlay across all your monitors, requires a quick numeric PIN to dismiss, and leaves your session completely intact when you return.

## Features

- **Fullscreen overlay across all monitors** — primary monitor shows the PIN keypad, secondary monitors are blacked out
- **Click or keypress to reveal keypad** — clean idle state, keypad appears with a smooth slide-in animation
- **Configurable PIN length** — 4, 6, 8 digits, whatever you set (minimum 4)
- **Configurable via JSON** — no need to edit source code
- **Brute-force protection** — keypad locks after N failed attempts and auto-unlocks after a cooldown
- **Auto-unlock timer** — optionally unlocks itself after X minutes (in case you forget the PIN or walk away permanently)
- **High-DPI aware** — looks crisp on 4K displays
- **Single file** — drop `pinlock.pyw` into a folder, run it, done

## Requirements

- Windows 10 or 11
- Python 3.8+ (standard library only — no `pip install` needed)

Tkinter is bundled with Python on Windows, so there are no external dependencies.

## Installation

1. Download `pinlock.pyw` (and optionally `config.json`) into a folder of your choice — e.g., `C:\Tools\PinLock\`.
2. Run it once with `pythonw pinlock.pyw`. This creates `config.json` with default values next to the script.
3. Edit `config.json` to set your PIN (see [Configuration](#configuration)).

### Optional: Desktop shortcut

Create a shortcut to `pythonw.exe` with the target:

```
C:\Path\To\Python\pythonw.exe "C:\Tools\PinLock\pinlock.pyw"
```

You can also assign a global hotkey to the shortcut via its Properties → Shortcut key.

### Optional: Custom icon

Place a file named `ikona.ico` next to `pinlock.pyw` and it will be used as the window icon. If absent, the default Tk icon is used.

## Configuration

On first launch, PinLock creates `config.json` in the same folder:

```json
{
  "correct_pin": "6060",
  "auto_unlock_minutes": 32,
  "max_attempts": 5,
  "lockout_reset_minutes": 5
}
```

| Key | Type | Description |
|---|---|---|
| `correct_pin` | string | Your PIN. Must be digits only, minimum 4 characters. Use a string (not a number) to preserve leading zeros — e.g., `"0123"`. |
| `auto_unlock_minutes` | integer | Minutes of being locked before the screen unlocks automatically. Set to `0` to disable. |
| `max_attempts` | integer | Number of wrong PIN attempts before the keypad becomes disabled. Minimum `1`. |
| `lockout_reset_minutes` | integer | After the keypad is disabled, how long to wait before re-enabling it. Minimum `1`. |

**Changes require a restart** of the script. The config is read once at startup.

If the config file is malformed or contains invalid values, PinLock shows a Windows error dialog explaining what's wrong, and exits.

## How it works

1. **Lock activation** — running `pinlock.pyw` immediately darkens all connected monitors with a borderless, always-on-top window. A small `🔒` icon appears in the center as a hint.
2. **Reveal keypad** — clicking anywhere or pressing any key animates a numeric keypad onto the primary monitor.
3. **Enter PIN** — type via mouse or hardware keyboard. Dots above the keypad fill in as you type. Backspace and Enter work as expected.
4. **Wrong PIN** — the keypad shakes, the dots reset, and you see how many attempts remain.
5. **Lockout** — after `max_attempts` failures, the keypad is disabled for `lockout_reset_minutes` minutes, then automatically re-enabled.
6. **Correct PIN** — the overlay disappears instantly and your desktop returns exactly as you left it.

The script uses `overrideredirect(True)` (no title bar), `-topmost` (always on top), and a local Tk grab to keep focus on the lock window.

## Security model

**PinLock is a deterrent, not a security boundary.** It is designed for environments where you trust the people physically near your machine but want a casual barrier against shoulder-surfing, prank screenshots, or curious coworkers.

**What it protects against:**

- Coworkers/family/visitors casually clicking around your desktop while you're away
- Quick glances at open documents, emails, or chats
- Accidental input (kids, pets, elbows on the keyboard)

**What it does NOT protect against:**

- Anyone determined to bypass it. The script can be killed via `Ctrl+Alt+Del → Sign out`, which terminates your session (and PinLock with it).
- Remote attackers. PinLock is a local UI overlay; it provides zero protection over RDP, SSH, or against malware already running in your session.
- Physical attackers with a screwdriver. Your disk contents are accessible to anyone who can boot from a USB stick — use **BitLocker** for that.
- Anyone who can read `config.json`. The PIN is stored in plain text. Treat it as a casual code, not a secret.

**For real security, use `Win+L` plus a strong Windows password and BitLocker.** PinLock is for the gap between "leaving the room for two minutes" and "logging out".

Notably, `Ctrl+Shift+Esc` (Task Manager) does **not** dismiss PinLock — Task Manager opens behind the topmost overlay and is not visible. The only practical bypass is `Ctrl+Alt+Del → Sign out`, which costs the attacker your unsaved work and is socially obvious.

## Limitations

- **Windows only.** Uses Win32 APIs (`EnumDisplayMonitors`, DPI awareness) directly via `ctypes`. No Linux/macOS support.
- **PIN in plain text.** As noted above. Hashing could be added but doesn't fundamentally change the threat model since the script itself can be replaced.
- **No hot-reload of config.** Restart the script after editing `config.json`.
- **No idle auto-activation.** You have to launch the script manually (or via a hotkey/shortcut). Some users wire it to Windows Task Scheduler with an idle trigger.
- **Monitor configuration is read at startup.** Connecting/disconnecting a monitor while locked doesn't update the overlays.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

This is a single-file utility, kept intentionally simple. Bug reports and small improvements welcome via issues/PRs. For larger features (idle auto-lock, hashed PINs, themes, plugin system), feel free to fork — the codebase is small enough to make that practical.
