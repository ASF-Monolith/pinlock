"""
PIN Lock Screen for Windows 11 - multi-monitor support
Click the locked screen to reveal the PIN keypad.
Run with: pythonw pinlock.pyw

Configuration is loaded from config.json next to this script.
If the file doesn't exist, it's created automatically with default values.
"""

import os
import sys
import json
import tkinter as tk
import tkinter.messagebox as mb
import ctypes
import ctypes.wintypes


# ─── DEFAULT CONFIGURATION ────────────────────────────────────────
DEFAULT_CONFIG = {
    "correct_pin": "6060",
    "auto_unlock_minutes": 32,
    "max_attempts": 5,
    "lockout_reset_minutes": 5,
}
MIN_PIN_LENGTH = 4

# ─── CONFIG FILENAME ──────────────────────────────────────────────
CONFIG_FILENAME = "config.json"

# Global variables populated from config at startup
CORRECT_PIN           = ""
AUTO_UNLOCK_MINUTES   = 0
MAX_ATTEMPTS          = 0
LOCKOUT_RESET_MINUTES = 0
PIN_LENGTH            = 0


# ─── CONFIG LOADING AND VALIDATION ────────────────────────────────
def get_config_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, CONFIG_FILENAME)


def write_default_config(path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_config():
    config_path = get_config_path()

    # Auto-create on first launch
    if not os.path.exists(config_path):
        try:
            write_default_config(config_path)
        except OSError as e:
            raise ValueError(
                f"Cannot create {CONFIG_FILENAME}:\n{e}\n\n"
                f"Path: {config_path}"
            )
        return validate_config(DEFAULT_CONFIG.copy())

    # Load existing config
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"{CONFIG_FILENAME} contains invalid JSON:\n{e}\n\n"
            f"Path: {config_path}\n\n"
            f"Delete it - a new one will be created on next launch."
        )
    except OSError as e:
        raise ValueError(f"Cannot open {CONFIG_FILENAME}:\n{e}")

    if not isinstance(config, dict):
        raise ValueError(f"{CONFIG_FILENAME} must contain a JSON object {{...}}")

    # Fill missing keys from defaults
    for key, default in DEFAULT_CONFIG.items():
        config.setdefault(key, default)

    return validate_config(config)


def validate_config(config):
    # PIN
    pin = str(config["correct_pin"])
    if not pin.isdigit() or len(pin) < MIN_PIN_LENGTH:
        raise ValueError(
            f"In {CONFIG_FILENAME}: 'correct_pin' must contain digits only "
            f"and be at least {MIN_PIN_LENGTH} characters long.\n\n"
            f"Current value: '{pin}'\n\n"
            f"Tip: write PINs with leading zeros as a string, e.g. \"0123\"."
        )
    config["correct_pin"] = pin

    # Numeric values
    int_rules = {
        "auto_unlock_minutes":   0,  # 0 = disabled
        "max_attempts":          1,
        "lockout_reset_minutes": 1,
    }
    for key, min_val in int_rules.items():
        val = config[key]
        if not isinstance(val, int) or isinstance(val, bool) or val < min_val:
            raise ValueError(
                f"In {CONFIG_FILENAME}: '{key}' must be an integer >= {min_val}.\n\n"
                f"Current value: {val!r}"
            )

    return config


def show_error_and_exit(title, msg):
    """Show error even in pythonw mode (where stderr isn't visible)."""
    try:
        r = tk.Tk()
        r.withdraw()
        mb.showerror(title, msg)
        r.destroy()
    except Exception:
        pass
    print(msg, file=sys.stderr)
    sys.exit(1)


# ─── MONITOR ENUMERATION ──────────────────────────────────────────
def get_all_monitors():
    monitors = []
    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.POINTER(ctypes.wintypes.RECT), ctypes.c_double,
    )
    def cb(hMon, hdcMon, lprc, dw):
        r = lprc.contents
        monitors.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
        return True
    ctypes.windll.user32.EnumDisplayMonitors(None, None, MonitorEnumProc(cb), 0)
    if not monitors:
        u = ctypes.windll.user32
        monitors = [(0, 0, u.GetSystemMetrics(0), u.GetSystemMetrics(1))]
    return monitors


# ─── MAIN CLASS ───────────────────────────────────────────────────
class PinLock:
    def __init__(self):
        monitors = get_all_monitors()
        primary = monitors[0]
        others  = monitors[1:]

        self.root = tk.Tk()
        self.pin_input       = ""
        self.pin_visible     = False
        self.frame_x         = 0
        self.frame_y         = 0
        self.failed_attempts = 0
        self.locked_out      = False
        self._anim_after_id  = None

        px, py, pw, ph = primary
        self.pw, self.ph = pw, ph

        self.root.configure(bg="#0a0a0f")
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            self.root.iconbitmap(os.path.join(base, "ikona.ico"))
        except Exception:
            pass
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.geometry(f"{pw}x{ph}+{px}+{py}")
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.root.bind("<Escape>", lambda e: "break")
        self.root.bind("<Alt-F4>", lambda e: "break")

        self.canvas = self._draw_bg(self.root, pw, ph)

        self.hint_id = self.canvas.create_text(
            pw // 2, ph // 2,
            text="🔒\n\n",
            font=("Segoe UI", 22, "bold"),
            fill="#2a4a6a",
            justify="center"
        )

        self.pin_frame = tk.Frame(self.root, bg="#141428",
                                  highlightbackground="#253040",
                                  highlightthickness=1)
        self._build_pin_ui(self.pin_frame)
        self.pin_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.pin_frame.lower()

        self.root.bind("<Button-1>", self._show_pin)
        self.root.bind("<KeyPress>", self._on_key)

        for mon in others:
            self._make_overlay(mon)

        if AUTO_UNLOCK_MINUTES > 0:
            ms = AUTO_UNLOCK_MINUTES * 60 * 1000
            self.root.after(ms, self.root.destroy)

        self.root.grab_set()
        self.root.focus_force()
        self.root.mainloop()

    def _draw_bg(self, win, w, h):
        c = tk.Canvas(win, width=w, height=h, highlightthickness=0, bg="#0a0a0f")
        c.place(x=0, y=0)
        step = max(1, h // 200)
        for i in range(0, h, step):
            ratio = i / h
            b = int(10 + ratio * 25)
            color = f"#{10:02x}{10:02x}{b:02x}"
            c.create_rectangle(0, i, w, i + step, fill=color, outline="")
        return c

    def _show_pin(self, event=None):
        if self.pin_visible:
            return
        self.pin_visible = True
        self.canvas.delete(self.hint_id)
        self.pin_frame.lift()
        self._animate_in()

    def _animate_in(self):
        self.root.update_idletasks()
        fw = self.pin_frame.winfo_reqwidth()
        fh = self.pin_frame.winfo_reqheight()
        cx       = (self.pw - fw) // 2
        target_y = (self.ph - fh) // 2
        self.frame_x = cx
        self.frame_y = target_y
        start_y  = self.ph
        steps = 20
        def step(i=0):
            if i > steps:
                self.pin_frame.place(x=cx, y=target_y)
                self._anim_after_id = None
                return
            t    = i / steps
            ease = 1 - (1 - t) ** 3
            y    = int(start_y + (target_y - start_y) * ease)
            self.pin_frame.place(x=cx, y=y)
            self._anim_after_id = self.root.after(10, lambda: step(i + 1))
        step()

    def _build_pin_ui(self, frame):
        tk.Label(frame, text="🔒", font=("Segoe UI Emoji", 42),
                 bg="#141428", fg="#cfd8dc").pack(pady=(28, 24))

        self.dots_var = tk.StringVar(value=("·  " * PIN_LENGTH).rstrip())
        tk.Label(frame, textvariable=self.dots_var,
                 font=("Segoe UI", 24), bg="#141428", fg="#4fc3f7").pack()

        self.error_var = tk.StringVar(value="")
        tk.Label(frame, textvariable=self.error_var,
                 font=("Segoe UI", 10), bg="#141428", fg="#ef5350").pack(pady=(3, 0))

        pad = tk.Frame(frame, bg="#141428")
        pad.pack(pady=(14, 0), padx=28)

        self.buttons = []
        rows = [("1","2","3"), ("4","5","6"), ("7","8","9"), ("⌫","0","↵")]
        for row_vals in rows:
            rf = tk.Frame(pad, bg="#141428")
            rf.pack(pady=4)
            for v in row_vals:
                if v == "⌫":
                    fg, cmd = "#ef9a9a", self._backspace
                elif v == "↵":
                    fg, cmd = "#a5d6a7", self._confirm
                else:
                    fg, cmd = "#e0e0e0", (lambda val=v: self._press(val))
                b = tk.Button(rf, text=v, font=("Segoe UI", 16, "bold"),
                              width=4, height=2, bg="#1e2d3d", fg=fg,
                              activebackground="#2a3f52", activeforeground=fg,
                              relief="flat", bd=0, cursor="hand2", command=cmd)
                b.pack(side="left", padx=4)
                b.bind("<Enter>", lambda e, btn=b: btn.config(bg="#2a3f52"))
                b.bind("<Leave>", lambda e, btn=b: btn.config(bg="#1e2d3d"))
                self.buttons.append((b, fg))

        tk.Label(frame, text=f"Enter your {PIN_LENGTH}-digit PIN to unlock",
                 font=("Segoe UI", 9), bg="#141428", fg="#455a64").pack(pady=(10, 22))

    def _lockout(self):
        self.locked_out = True
        for btn, _ in self.buttons:
            btn.config(
                state="disabled",
                bg="#1a1a1a",
                fg="#3a3a3a",
                cursor="",
                activebackground="#1a1a1a",
            )
            btn.unbind("<Enter>")
            btn.unbind("<Leave>")
        self.dots_var.set("🚫")
        self.error_var.set(
            f"Too many attempts - keypad locked for {LOCKOUT_RESET_MINUTES} min"
        )
        ms = LOCKOUT_RESET_MINUTES * 60 * 1000
        self.root.after(ms, self._reset_lockout)

    def _reset_lockout(self):
        self.locked_out = False
        self.failed_attempts = 0
        self.pin_input = ""
        for btn, fg in self.buttons:
            btn.config(
                state="normal",
                bg="#1e2d3d",
                fg=fg,
                cursor="hand2",
                activebackground="#2a3f52",
                activeforeground=fg,
            )
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#2a3f52"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg="#1e2d3d"))
        self._update_dots()
        self.error_var.set("")

    def _make_overlay(self, monitor):
        x, y, w, h = monitor
        ov = tk.Toplevel(self.root)
        ov.configure(bg="#0a0a0f")
        ov.overrideredirect(True)
        ov.attributes("-topmost", True)
        ov.geometry(f"{w}x{h}+{x}+{y}")
        ov.protocol("WM_DELETE_WINDOW", lambda: None)
        c = self._draw_bg(ov, w, h)
        c.create_text(w // 2, h // 2,
                      text="🔒",
                      font=("Segoe UI", 26, "bold"), fill="#2a3a4a")
        c.bind("<Button-1>", self._show_pin)

    def _on_key(self, event):
        if self.locked_out:
            return
        if not self.pin_visible:
            self._show_pin()
        if event.char.isdigit():
            self._press(event.char)
        elif event.keysym == "BackSpace":
            self._backspace()
        elif event.keysym == "Return":
            self._confirm()

    def _press(self, d):
        if self.locked_out:
            return
        if len(self.pin_input) < PIN_LENGTH:
            self.pin_input += d
            self._update_dots()
            self.error_var.set("")

    def _backspace(self):
        if self.locked_out:
            return
        self.pin_input = self.pin_input[:-1]
        self._update_dots()
        self.error_var.set("")

    def _update_dots(self):
        n = len(self.pin_input)
        filled = "●  " * n
        empty  = "·  " * (PIN_LENGTH - n)
        self.dots_var.set((filled + empty).rstrip())

    def _confirm(self):
        if self.locked_out:
            return
        if not self.pin_input:
            return
        if self.pin_input == CORRECT_PIN:
            self.root.destroy()
        else:
            self.failed_attempts += 1
            remaining = MAX_ATTEMPTS - self.failed_attempts
            if remaining <= 0:
                self._lockout()
            else:
                attempt_word = "attempt" if remaining == 1 else "attempts"
                self.error_var.set(
                    f"❌  Wrong PIN  ({remaining} {attempt_word} remaining)"
                )
            self.pin_input = ""
            self._update_dots()
            self._shake()

    def _shake(self):
        if self._anim_after_id is not None:
            try:
                self.root.after_cancel(self._anim_after_id)
            except Exception:
                pass
            self._anim_after_id = None
        ox = self.frame_x
        oy = self.frame_y
        self.pin_frame.place(x=ox, y=oy)
        for i, off in enumerate([14, -14, 10, -10, 6, -6, 3, -3, 0]):
            self.root.after(i * 30, lambda o=off:
                self.pin_frame.place(x=ox + o, y=oy))


# ─── ENTRY POINT ──────────────────────────────────────────────────
if __name__ == "__main__":
    # Load configuration with error handling (pythonw doesn't show stderr)
    try:
        cfg = load_config()
    except ValueError as e:
        show_error_and_exit("PinLock - configuration error", str(e))

    CORRECT_PIN           = cfg["correct_pin"]
    AUTO_UNLOCK_MINUTES   = cfg["auto_unlock_minutes"]
    MAX_ATTEMPTS          = cfg["max_attempts"]
    LOCKOUT_RESET_MINUTES = cfg["lockout_reset_minutes"]
    PIN_LENGTH            = len(CORRECT_PIN)

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    PinLock()
