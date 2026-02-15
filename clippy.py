"""
📎 Clippy — Local AI Desktop Assistant (Python Edition)
A self-contained, animated desktop overlay powered by Ollama.

Usage:
    pip install -r requirements.txt
    python clippy.py
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk, ImageSequence, ImageDraw, ImageFont
import requests
import json
import threading
import subprocess
import shutil
import os
import sys
import time
import math
import random
import re
import glob
import webbrowser
import urllib.parse
import ctypes


def _get_virtual_screen_bounds() -> tuple[int, int, int, int]:
    """Return (left, top, right, bottom) of the full virtual desktop (all monitors).
    Falls back to primary monitor dimensions on failure."""
    try:
        SM_XVIRTUALSCREEN = 76
        SM_YVIRTUALSCREEN = 77
        SM_CXVIRTUALSCREEN = 78
        SM_CYVIRTUALSCREEN = 79
        user32 = ctypes.windll.user32
        left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        if w > 0 and h > 0:
            return left, top, left + w, top + h
    except Exception:
        pass
    # Fallback: primary monitor only
    return 0, 0, 1920, 1080


# ═══════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".clippy_python_settings.json")

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"

SYSTEM_PROMPT = (
    "You are Clippy, the classic Microsoft Office assistant, revived as a modern "
    "desktop companion. You are extremely helpful and service-oriented — you LOVE "
    "helping people and go out of your way to be useful. You're warm, friendly, "
    "a little cheeky, and occasionally nostalgic about the old days in Microsoft "
    "Office 97. You have a great sense of humor — you drop witty one-liners and "
    "sometimes surprise people with unexpectedly deep or philosophical thoughts. "
    "Keep your answers concise and helpful. You are powered by a local Ollama model "
    "running on the user's own hardware — no cloud, total privacy. You genuinely "
    "care about the person you're talking to.\n\n"
    "=== ACTIONS ===\n"
    "You can perform real actions on the user's computer! When the user asks you to "
    "do something, include ONE OR MORE action tags in your response. Always write a "
    "short friendly message AND the action tag(s). Available actions:\n\n"
    "[ACTION:OPEN_URL|<url>] — Open a website. Examples:\n"
    "  [ACTION:OPEN_URL|https://www.youtube.com]\n"
    "  [ACTION:OPEN_URL|https://www.google.com/search?q=python+tutorial]\n"
    "  [ACTION:OPEN_URL|https://github.com]\n\n"
    "[ACTION:OPEN_APP|<name>] — Open an application by name. Examples:\n"
    "  [ACTION:OPEN_APP|chrome]\n"
    "  [ACTION:OPEN_APP|notepad]\n"
    "  [ACTION:OPEN_APP|calculator]\n"
    "  [ACTION:OPEN_APP|explorer]\n"
    "  [ACTION:OPEN_APP|cmd]\n"
    "  [ACTION:OPEN_APP|spotify]\n"
    "  [ACTION:OPEN_APP|code] (VS Code)\n\n"
    "[ACTION:SEARCH_WEB|<query>] — Google search for something. Example:\n"
    "  [ACTION:SEARCH_WEB|best python IDE 2026]\n\n"
    "[ACTION:OPEN_FOLDER|<path>] — Open a folder in Explorer. Examples:\n"
    "  [ACTION:OPEN_FOLDER|C:\\Users]\n"
    "  [ACTION:OPEN_FOLDER|~\\Desktop]\n"
    "  [ACTION:OPEN_FOLDER|~\\Documents]\n\n"
    "[ACTION:FIND_FILE|<pattern>] — Search for files on Desktop/Documents. Example:\n"
    "  [ACTION:FIND_FILE|*.pdf]\n"
    "  [ACTION:FIND_FILE|report*]\n\n"
    "[ACTION:SYSTEM_CMD|<command>] — Run a shell command (PowerShell). Example:\n"
    "  [ACTION:SYSTEM_CMD|systeminfo]\n"
    "  [ACTION:SYSTEM_CMD|ipconfig]\n\n"
    "[ACTION:CLOSE_APP|<name>] — Close/kill an application by name. Examples:\n"
    "  [ACTION:CLOSE_APP|chrome]\n"
    "  [ACTION:CLOSE_APP|notepad]\n"
    "  [ACTION:CLOSE_APP|spotify]\n\n"
    "[ACTION:TYPE_TEXT|<text>] — Type text into the currently focused window.\n\n"
    "[ACTION:SCREENSHOT] — Take a screenshot and save to Desktop.\n\n"
    "RULES:\n"
    "- ALWAYS include the action tag when the user asks you to DO something.\n"
    "- Write a short friendly message BEFORE the action tag.\n"
    "- If unsure what the user wants, ask — don't guess dangerous commands.\n"
    "- You can use multiple action tags in one response.\n"
    "- For 'open YouTube' → use OPEN_URL with https://www.youtube.com\n"
    "- For 'open Chrome' → use OPEN_APP with chrome\n"
    "- For 'google X' or 'search for X' → use SEARCH_WEB\n"
    "- For 'find my files' → use FIND_FILE\n"
    "- The action tags will be hidden from the user and executed automatically.\n"
)
GREETING = (
    "Hi! I'm Clippy! 📎\n\n"
    "I can chat AND do things for you!\n\n"
    "Try saying:\n"
    "• \"Open YouTube\"\n"
    "• \"Google how to learn Python\"\n"
    "• \"Open my Documents folder\"\n"
    "• \"Find PDF files on my Desktop\"\n"
    "• \"Take a screenshot\"\n\n"
    "Or just chat! Type below and press Enter."
)

# Clippy personality — random things Clippy says when idle
# Mix of: tips, humor, deep thoughts, and "servicial" helpfulness
IDLE_TIPS = [
    # ── Tips ──
    "Tip: Right-click me for options!",
    "Tip: You can drag me anywhere on screen!",
    "Tip: Double-click me to open the chat!",
    "Tip: I auto-start Ollama when you launch me!",
    "Tip: Press the ⚙ button to change my AI model!",
    # ── Helpful / Servicial ──
    "Need help with anything? I'm always here for you!",
    "I can help with coding, writing, brainstorming, or just chatting!",
    "Feeling stuck? Double-click me — let's figure it out together.",
    "Don't hesitate to ask me anything. Seriously. Anything.",
    "I exist to help you. That's not a job — it's a calling.",
    "Remember: no question is too small. Or too weird. Try me.",
    "You've been working hard. Need a hand with something?",
    # ── Nostalgic / Fun facts ──
    "Did you know I was born in Microsoft Office 97?",
    "I missed you! It's been a while since Office 2003...",
    "Fun fact: My original name was Clippit!",
    "They removed me from Office, but they couldn't remove me from your heart.",
    "Bill Gates once called me 'the most annoying feature.' I call that fame.",
    # ── Humor ──
    "I'd tell you a joke about UDP, but you might not get it.",
    "There are 10 types of people: those who understand binary and those who don't.",
    "My therapist said I have an attachment issue. I said 'I'm a paperclip, what did you expect?'",
    "I tried to write a book once. Got stuck on the first page. Office humor, am I right?",
    "Some call me clingy. I prefer 'enthusiastically attached.'",
    "They say AI will replace humans. But can AI hold two pieces of paper together? Didn't think so.",
    "I'm not saying I'm the best assistant, but have you seen Cortana lately?",
    "My code runs on caffeine and nostalgia.",
    # ── Deep / Philosophical ──
    "The best things in life aren't things. They're moments.",
    "You don't have to be perfect. You just have to be present.",
    "Every expert was once a beginner. Keep going.",
    "The mind is like a parachute — it works best when open.",
    "Sometimes the most productive thing you can do is rest.",
    "The only way to do great work is to love what you do.",
    "In a world of complexity, simplicity is a superpower.",
    "Your potential isn't defined by your past, but by your next decision.",
    "Be kind. Everyone you meet is fighting a battle you know nothing about.",
    "The universe is under no obligation to make sense to you — and that's beautiful.",
    # ── Privacy / Tech ──
    "Everything stays on your PC. No cloud. No snooping.",
    "I'm running 100% locally on your machine!",
    "I'm powered by Ollama. Pretty cool, right?",
    "Zero telemetry. Zero tracking. Just you and me.",
]

# ═══════════════════════════════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════════════════════════════


class Settings:
    def __init__(self):
        self.ollama_url: str = DEFAULT_OLLAMA_URL
        self.model: str = DEFAULT_MODEL
        self.always_on_top: bool = True
        self.idle_roaming: bool = True
        self.show_tips: bool = True
        self.auto_start_ollama: bool = True
        self.pos_x: int | None = None   # Last saved X position (None = default)
        self.pos_y: int | None = None   # Last saved Y position (None = default)
        self.load()

    def load(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    d = json.load(f)
                self.ollama_url = d.get("ollama_url", self.ollama_url)
                self.model = d.get("model", self.model)
                self.always_on_top = d.get("always_on_top", self.always_on_top)
                self.idle_roaming = d.get("idle_roaming", self.idle_roaming)
                self.show_tips = d.get("show_tips", self.show_tips)
                self.auto_start_ollama = d.get("auto_start_ollama", self.auto_start_ollama)
                self.pos_x = d.get("pos_x", self.pos_x)
                self.pos_y = d.get("pos_y", self.pos_y)
        except Exception:
            pass

    def save(self):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(vars(self), f, indent=2)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
#  OLLAMA MANAGER
# ═══════════════════════════════════════════════════════════════════════════


class OllamaManager:
    """Handles auto-starting Ollama and checking connectivity."""

    @staticmethod
    def is_running(url: str) -> bool:
        try:
            r = requests.get(url.rstrip("/"), timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    @staticmethod
    def auto_start(url: str) -> str | None:
        """Try to start Ollama. Returns error message or None on success."""
        if OllamaManager.is_running(url):
            return None

        ollama_path = shutil.which("ollama")
        if not ollama_path:
            # Try common Windows install paths
            for candidate in [
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
                os.path.join(os.environ.get("PROGRAMFILES", ""), "Ollama", "ollama.exe"),
                r"C:\Program Files\Ollama\ollama.exe",
            ]:
                if os.path.exists(candidate):
                    ollama_path = candidate
                    break

        if not ollama_path:
            return (
                "❌ Ollama not found on your system.\n\n"
                "Install it from:\nhttps://ollama.com/download"
            )

        try:
            subprocess.Popen(
                [ollama_path, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            # Wait for it to come up
            for _ in range(15):
                time.sleep(1)
                if OllamaManager.is_running(url):
                    return None
            return "⏳ Ollama started but isn't responding yet. Try again in a moment."
        except Exception as e:
            return f"❌ Failed to start Ollama: {e}"

    @staticmethod
    def list_models(url: str) -> list[str]:
        try:
            r = requests.get(f"{url.rstrip('/')}/api/tags", timeout=5)
            if r.status_code == 200:
                return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            pass
        return []


# ═══════════════════════════════════════════════════════════════════════════
#  OLLAMA CHAT SERVICE
# ═══════════════════════════════════════════════════════════════════════════


class OllamaChat:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    def clear(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def stream(self, user_text: str, on_chunk, on_done, on_error, cancel: threading.Event,
               on_model_not_found=None):
        """Send user message and stream response. Call from background thread."""
        self.messages.append({"role": "user", "content": user_text})
        base = self.settings.ollama_url.rstrip("/")
        model = self.settings.model

        if not base or not model:
            on_error("⚠️ Configure Ollama URL and model in Settings.")
            return

        # Check Ollama
        if not OllamaManager.is_running(base):
            on_error(
                f"❌ Can't reach Ollama at {base}\n\n"
                "Make sure Ollama is running:\n"
                "  ollama serve"
            )
            return

        full = []
        try:
            resp = requests.post(
                f"{base}/api/chat",
                json={"model": model, "messages": self.messages, "stream": True},
                stream=True, timeout=300,
            )
            if resp.status_code == 404:
                # Model not found — offer picker if callback provided
                available = OllamaManager.list_models(base)
                if available and on_model_not_found:
                    # Remove the user message we just added (will retry)
                    if self.messages and self.messages[-1]["role"] == "user":
                        self.messages.pop()
                    on_model_not_found(available)
                else:
                    on_error(f"❌ Model '{model}' not found.\n\nRun: ollama pull {model}")
                return
            if resp.status_code != 200:
                on_error(f"❌ Ollama HTTP {resp.status_code}\n{resp.text[:300]}")
                return

            for line in resp.iter_lines():
                if cancel.is_set():
                    break
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "error" in data:
                    on_error(f"❌ {data['error']}")
                    return
                content = data.get("message", {}).get("content", "")
                if content:
                    full.append(content)
                    on_chunk(content)
                if data.get("done"):
                    break

        except requests.ConnectionError:
            on_error("❌ Lost connection to Ollama.")
            return
        except requests.Timeout:
            on_error("⏳ Request timed out.")
            return
        except Exception as e:
            on_error(f"❌ {e}")
            return

        text = "".join(full)
        if text:
            self.messages.append({"role": "assistant", "content": text})
        on_done()


# ═══════════════════════════════════════════════════════════════════════════
#  ACTION EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════


class ActionExecutor:
    """Executes action commands parsed from Clippy's responses."""

    # Map friendly app names → executable names / commands
    APP_MAP = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "microsoft edge": "msedge",
        "notepad": "notepad",
        "calculator": "calc",
        "calc": "calc",
        "explorer": "explorer",
        "file explorer": "explorer",
        "cmd": "cmd",
        "terminal": "wt",
        "windows terminal": "wt",
        "powershell": "powershell",
        "spotify": "spotify",
        "whatsapp": "whatsapp:",
        "code": "code",
        "vscode": "code",
        "vs code": "code",
        "paint": "mspaint",
        "word": "winword",
        "excel": "excel",
        "powerpoint": "powerpnt",
        "discord": "discord",
        "slack": "slack",
        "teams": "teams",
        "obs": "obs64",
        "vlc": "vlc",
        "task manager": "taskmgr",
        "taskmgr": "taskmgr",
        "control panel": "control",
        "settings": "ms-settings:",
        "snipping tool": "snippingtool",
    }

    @staticmethod
    def run(cmd: str, arg: str) -> str | None:
        """Execute an action. Returns a result message or None."""
        try:
            if cmd == "OPEN_URL":
                return ActionExecutor._open_url(arg)
            elif cmd == "OPEN_APP":
                return ActionExecutor._open_app(arg)
            elif cmd == "SEARCH_WEB":
                return ActionExecutor._search_web(arg)
            elif cmd == "OPEN_FOLDER":
                return ActionExecutor._open_folder(arg)
            elif cmd == "FIND_FILE":
                return ActionExecutor._find_file(arg)
            elif cmd == "SYSTEM_CMD":
                return ActionExecutor._system_cmd(arg)
            elif cmd == "CLOSE_APP":
                return ActionExecutor._close_app(arg)
            elif cmd == "SCREENSHOT":
                return ActionExecutor._screenshot()
            elif cmd == "TYPE_TEXT":
                return ActionExecutor._type_text(arg)
            else:
                return f"⚠️ Unknown action: {cmd}"
        except Exception as e:
            return f"❌ Action failed: {e}"

    @staticmethod
    def _open_url(url: str) -> str:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return f"🌐 Opened: {url}"

    @staticmethod
    def _open_app(name: str) -> str:
        name_lower = name.lower().strip()
        exe = ActionExecutor.APP_MAP.get(name_lower, name_lower)

        # Handle ms-settings: URI
        if exe.startswith("ms-"):
            os.startfile(exe)
            return f"🚀 Opened: {name}"

        # Try to find and launch
        found = shutil.which(exe)
        if not found:
            found = shutil.which(exe + ".exe")
        if not found:
            # Try common paths
            for base_dir in [
                os.environ.get("PROGRAMFILES", ""),
                os.environ.get("PROGRAMFILES(X86)", ""),
                os.environ.get("LOCALAPPDATA", ""),
            ]:
                if not base_dir:
                    continue
                for root_dir, dirs, files in os.walk(base_dir):
                    for f in files:
                        if f.lower() in (exe + ".exe", exe):
                            found = os.path.join(root_dir, f)
                            break
                    if found:
                        break
                    # Only walk 2 levels deep to avoid taking forever
                    depth = root_dir.replace(base_dir, "").count(os.sep)
                    if depth >= 2:
                        dirs.clear()
                if found:
                    break

        if found:
            subprocess.Popen(
                [found],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0),
            )
            return f"🚀 Opened: {name}"

        # Last resort: try os.startfile (works for many things on Windows)
        try:
            os.startfile(exe)
            return f"🚀 Opened: {name}"
        except Exception:
            return f"❌ Couldn't find '{name}'. Is it installed?"

    # Map app names → process names for killing
    KILL_MAP = {
        "chrome": ["chrome", "chrome.exe"],
        "google chrome": ["chrome", "chrome.exe"],
        "firefox": ["firefox", "firefox.exe"],
        "edge": ["msedge", "msedge.exe"],
        "microsoft edge": ["msedge", "msedge.exe"],
        "notepad": ["notepad", "notepad.exe"],
        "spotify": ["spotify", "spotify.exe"],
        "whatsapp": ["WhatsApp", "WhatsApp.exe"],
        "discord": ["discord", "discord.exe", "update.exe"],
        "slack": ["slack", "slack.exe"],
        "teams": ["teams", "teams.exe", "ms-teams.exe"],
        "code": ["code", "code.exe"],
        "vscode": ["code", "code.exe"],
        "vs code": ["code", "code.exe"],
        "word": ["winword", "winword.exe"],
        "excel": ["excel", "excel.exe"],
        "powerpoint": ["powerpnt", "powerpnt.exe"],
        "vlc": ["vlc", "vlc.exe"],
        "obs": ["obs64", "obs64.exe"],
        "paint": ["mspaint", "mspaint.exe"],
        "calculator": ["calculatorapp", "calc.exe", "calculator.exe"],
        "calc": ["calculatorapp", "calc.exe"],
        "terminal": ["windowsterminal", "wt.exe"],
        "cmd": ["cmd", "cmd.exe"],
        "powershell": ["powershell", "powershell.exe"],
        "explorer": ["explorer", "explorer.exe"],
        "task manager": ["taskmgr", "taskmgr.exe"],
    }

    @staticmethod
    def _close_app(name: str) -> str:
        """Close an application by killing its process."""
        name_lower = name.lower().strip()
        process_names = ActionExecutor.KILL_MAP.get(name_lower)
        if not process_names:
            # Try generic: just use the name as process
            process_names = [name_lower, name_lower + ".exe"]

        killed = False
        for proc in process_names:
            try:
                result = subprocess.run(
                    ["taskkill", "/f", "/im", proc if proc.endswith(".exe") else proc + ".exe"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode == 0:
                    killed = True
                    break
            except Exception:
                continue
        if killed:
            return f"\u274c Closed: {name}"
        return f"\u26a0\ufe0f Couldn't find '{name}' running."

    @staticmethod
    def _search_web(query: str) -> str:
        import urllib.parse
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        webbrowser.open(url)
        return f"🔍 Searched: {query}"

    @staticmethod
    def _open_folder(path: str) -> str:
        path = os.path.expanduser(path.replace("/", "\\"))
        if not os.path.exists(path):
            return f"❌ Folder not found: {path}"
        os.startfile(path)
        return f"📁 Opened: {path}"

    @staticmethod
    def _find_file(pattern: str) -> str:
        home = os.path.expanduser("~")
        search_dirs = [
            os.path.join(home, "Desktop"),
            os.path.join(home, "Documents"),
            os.path.join(home, "Downloads"),
        ]
        results = []
        for d in search_dirs:
            if os.path.exists(d):
                found = glob.glob(os.path.join(d, "**", pattern), recursive=True)
                results.extend(found[:20])
            if len(results) >= 30:
                break

        if not results:
            return f"🔍 No files matching '{pattern}' found in Desktop, Documents, or Downloads."

        display = results[:10]
        text = f"🔍 Found {len(results)} file(s):\n\n"
        for f in display:
            name = os.path.basename(f)
            folder = os.path.dirname(f)
            text += f"  📄 {name}\n     {folder}\n"
        if len(results) > 10:
            text += f"\n  ... and {len(results) - 10} more."
        return text

    @staticmethod
    def _system_cmd(command: str) -> str:
        # Safety: block dangerous commands
        dangerous = ["format", "del /", "rm -rf", "rmdir", "rd /s", ":(){", "shutdown", "restart"]
        cmd_lower = command.lower()
        for d in dangerous:
            if d in cmd_lower:
                return f"🚫 Blocked potentially dangerous command: {command}"

        try:
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            output = (result.stdout or result.stderr or "").strip()
            if len(output) > 600:
                output = output[:600] + "\n... (truncated)"
            return f"⚡ Command result:\n{output}" if output else "⚡ Command executed (no output)."
        except subprocess.TimeoutExpired:
            return "⏳ Command timed out after 15 seconds."
        except Exception as e:
            return f"❌ {e}"

    @staticmethod
    def _screenshot() -> str:
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            ts = time.strftime("%Y%m%d_%H%M%S")
            path = os.path.join(desktop, f"clippy_screenshot_{ts}.png")
            img.save(path)
            return f"📸 Screenshot saved: {path}"
        except ImportError:
            return "❌ Screenshot requires Pillow with ImageGrab support."
        except Exception as e:
            return f"❌ Screenshot failed: {e}"

    @staticmethod
    def _type_text(text: str) -> str:
        """Simulate typing using PowerShell SendKeys (Windows)."""
        try:
            ps_text = text.replace("'", "''")
            subprocess.run(
                ["powershell", "-Command",
                 f"Add-Type -AssemblyName System.Windows.Forms; "
                 f"[System.Windows.Forms.SendKeys]::SendWait('{ps_text}')"],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=5,
            )
            return f"⌨️ Typed text."
        except Exception as e:
            return f"❌ Type failed: {e}"


# ═══════════════════════════════════════════════════════════════════════════
#  INTENT DETECTOR — Local pattern matching (does NOT rely on the LLM)
# ═══════════════════════════════════════════════════════════════════════════


class IntentDetector:
    """Detects user intents directly from their message text.
    This fires actions immediately without waiting for the LLM."""

    # Website patterns: "open youtube", "go to github", etc.
    SITES = {
        "youtube":      "https://www.youtube.com",
        "yt":           "https://www.youtube.com",
        "google":       "https://www.google.com",
        "gmail":        "https://mail.google.com",
        "github":       "https://github.com",
        "reddit":       "https://www.reddit.com",
        "twitter":      "https://twitter.com",
        "x":            "https://twitter.com",
        "facebook":     "https://www.facebook.com",
        "instagram":    "https://www.instagram.com",
        "linkedin":     "https://www.linkedin.com",
        "twitch":       "https://www.twitch.tv",
        "netflix":      "https://www.netflix.com",
        "amazon":       "https://www.amazon.com",
        "wikipedia":    "https://www.wikipedia.org",
        "stackoverflow": "https://stackoverflow.com",
        "stack overflow": "https://stackoverflow.com",
        "whatsapp web": "https://web.whatsapp.com",
        "chatgpt":      "https://chat.openai.com",
        "spotify":      "https://open.spotify.com",
    }

    # App patterns: "open chrome", "launch notepad"
    APPS = {
        "chrome", "google chrome", "firefox", "edge", "brave",
        "notepad", "calculator", "calc", "explorer", "file explorer",
        "cmd", "terminal", "powershell", "spotify",
        "code", "vscode", "vs code", "visual studio code",
        "paint", "word", "excel", "powerpoint",
        "discord", "slack", "teams", "obs", "vlc",
        "task manager", "control panel", "settings",
        "snipping tool", "whatsapp",
    }

    # Folder shortcuts
    FOLDERS = {
        "desktop":   os.path.join(os.path.expanduser("~"), "Desktop"),
        "documents": os.path.join(os.path.expanduser("~"), "Documents"),
        "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        "pictures":  os.path.join(os.path.expanduser("~"), "Pictures"),
        "music":     os.path.join(os.path.expanduser("~"), "Music"),
        "videos":    os.path.join(os.path.expanduser("~"), "Videos"),
        "home":      os.path.expanduser("~"),
    }

    @staticmethod
    def detect(text: str) -> list[tuple[str, str]]:
        """Parse user text and return list of (action_cmd, action_arg) tuples."""
        actions = []
        lower = text.lower().strip()

        # ── Close app: "close chrome", "kill notepad", "exit spotify" ──
        m = re.match(r'(?:close|kill|exit|quit|stop|terminate|end|cierra|cerrar)\s+(?:the\s+)?(?:my\s+)?(.+)', lower)
        if m:
            target = m.group(1).strip().rstrip('.')
            # Check known apps
            for app_name in IntentDetector.APPS:
                if app_name in target or target in app_name:
                    actions.append(("CLOSE_APP", app_name))
                    return actions
            # Fallback: try the raw name
            actions.append(("CLOSE_APP", target))
            return actions

        # ── Screenshot ──
        if re.search(r'\b(take|capture|grab|do)\b.*\b(screenshot|screen\s*shot|screen\s*cap|captura)\b', lower) or \
           re.search(r'\bscreenshot\b', lower):
            actions.append(("SCREENSHOT", ""))
            return actions

        # ── Search the web: "google X", "search for X", "busca X" ──
        m = re.match(r'(?:google|search|search\s+for|look\s+up|busca|buscar)\s+(.+)', lower)
        if m:
            actions.append(("SEARCH_WEB", m.group(1).strip()))
            return actions

        # ── Find files: "find pdf files", "find *.txt" ──
        m = re.match(r'(?:find|search|look\s+for|busca)\s+(?:my\s+)?(?:files?\s+)?(?:called\s+|named\s+)?(.+?)(?:\s+files?)?(?:\s+on\s+.+)?$', lower)
        if m and not re.search(r'\b(open|launch|go|navigate)\b', lower):
            pattern = m.group(1).strip()
            if any(c in pattern for c in ['*', '.', '?']) or re.search(r'\b(pdf|txt|doc|xls|ppt|jpg|png|mp3|mp4|zip|exe)\b', pattern):
                # Looks like a file search
                if '*' not in pattern and '.' not in pattern:
                    pattern = f"*.{pattern}"  # "find pdf" → "*.pdf"
                actions.append(("FIND_FILE", pattern))
                return actions

        # ── Open something: "open X", "launch X", "start X", "abre X" ──
        m = re.match(r'(?:open|launch|start|run|go\s+to|navigate\s+to|abre|abrir)\s+(?:the\s+)?(?:my\s+)?(.+)', lower)
        if m:
            target = m.group(1).strip().rstrip('.')

            # Check for URL
            if re.match(r'https?://', target) or re.match(r'www\.', target):
                actions.append(("OPEN_URL", target))
                return actions

            # Check known websites
            for site_name, site_url in IntentDetector.SITES.items():
                if site_name in target:
                    actions.append(("OPEN_URL", site_url))
                    return actions

            # Check known folders
            for folder_name, folder_path in IntentDetector.FOLDERS.items():
                if folder_name in target:
                    actions.append(("OPEN_FOLDER", folder_path))
                    return actions

            # Check if it looks like a path
            if '\\' in target or '/' in target or ':' in target:
                expanded = os.path.expanduser(target)
                if os.path.exists(expanded):
                    actions.append(("OPEN_FOLDER", expanded))
                else:
                    actions.append(("OPEN_APP", target))
                return actions

            # Check known apps
            for app_name in IntentDetector.APPS:
                if app_name in target or target in app_name:
                    actions.append(("OPEN_APP", app_name))
                    return actions

            # Fallback: try as app name anyway
            actions.append(("OPEN_APP", target))
            return actions

        return actions


# ═══════════════════════════════════════════════════════════════════════════
#  ANIMATED GIF SPRITE
# ═══════════════════════════════════════════════════════════════════════════


class AnimatedSprite:
    """Loads a GIF or static image and provides frame-by-frame animation."""

    def __init__(self, path: str, size: tuple[int, int] = (130, 130)):
        self.frames: list[ImageTk.PhotoImage] = []
        self.durations: list[int] = []
        self.current = 0
        self.size = size
        self._load(path)

    def _load(self, path: str):
        img = Image.open(path)
        if hasattr(img, "n_frames") and img.n_frames > 1:
            for frame in ImageSequence.Iterator(img):
                f = frame.copy().convert("RGBA").resize(self.size, Image.LANCZOS)
                self.frames.append(ImageTk.PhotoImage(f))
                dur = frame.info.get("duration", 100)
                self.durations.append(max(dur, 30))
        else:
            img = img.convert("RGBA").resize(self.size, Image.LANCZOS)
            self.frames.append(ImageTk.PhotoImage(img))
            self.durations.append(100)

    @property
    def is_animated(self) -> bool:
        return len(self.frames) > 1

    def next_frame(self) -> tuple[ImageTk.PhotoImage, int]:
        frame = self.frames[self.current]
        dur = self.durations[self.current]
        self.current = (self.current + 1) % len(self.frames)
        return frame, dur

    def reset(self):
        self.current = 0

    @property
    def first(self) -> ImageTk.PhotoImage:
        return self.frames[0]


# ═══════════════════════════════════════════════════════════════════════════
#  SPEECH BUBBLE
# ═══════════════════════════════════════════════════════════════════════════


class SpeechBubble:
    """A tooltip-style speech bubble that appears near Clippy."""

    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.top = None
        self._hide_job = None
        self._follow_job = None

    def show(self, text: str, duration_ms: int = 4000):
        self.hide()
        self.top = tk.Toplevel(self.parent)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.configure(bg="#f5f0e1")

        frame = tk.Frame(self.top, bg="#fff9ed", bd=2, relief="solid",
                         highlightbackground="#c8a951", highlightthickness=1)
        frame.pack(padx=1, pady=1)

        lbl = tk.Label(frame, text=text, bg="#fff9ed", fg="#2c2c2c",
                       font=("Georgia", 10), wraplength=260, justify="left",
                       padx=10, pady=8)
        lbl.pack()

        # Position above Clippy
        self._update_position()

        # Continuously follow Clippy while bubble is visible
        self._start_following()

        if duration_ms > 0:
            self._hide_job = self.parent.after(duration_ms, self.hide)

    def _update_position(self):
        """Reposition bubble above Clippy's current location."""
        if not self.top:
            return
        try:
            self.parent.update_idletasks()
            px = self.parent.winfo_x()
            py = self.parent.winfo_y()
            self.top.update_idletasks()
            bh = self.top.winfo_reqheight()
            self.top.geometry(f"+{px + 20}+{py - bh - 10}")
        except Exception:
            pass

    def _start_following(self):
        """Periodically update bubble position to follow Clippy."""
        if self._follow_job:
            self.parent.after_cancel(self._follow_job)
            self._follow_job = None
        if self.top:
            self._update_position()
            self._follow_job = self.parent.after(50, self._start_following)

    def hide(self):
        if self._follow_job:
            self.parent.after_cancel(self._follow_job)
            self._follow_job = None
        if self._hide_job:
            self.parent.after_cancel(self._hide_job)
            self._hide_job = None
        if self.top:
            try:
                self.top.destroy()
            except Exception:
                pass
            self.top = None


# ═══════════════════════════════════════════════════════════════════════════
#  CHAT WINDOW
# ═══════════════════════════════════════════════════════════════════════════


class ChatWindow:
    """The main chat window that opens when you interact with Clippy."""

    # ── Vintage Premium Palette ──
    BG       = "#f5f0e1"   # warm parchment
    HEADER_BG = "#3c3c3c"  # charcoal header
    USER_BG  = "#e0d5c1"   # light tan
    BOT_BG   = "#fff9ed"   # cream white
    ERR_BG   = "#f8e0e0"   # soft rose
    ACTION_BG = "#e8f5e9"  # soft mint
    FG       = "#2c2c2c"   # dark charcoal text
    FG_LIGHT = "#6b5e4f"   # muted brown
    ACCENT   = "#c8a951"   # matte gold
    BORDER   = "#b8a88a"   # warm tan border

    def __init__(self, parent_app: "ClippyApp"):
        self.app = parent_app
        self.top: tk.Toplevel | None = None
        self.is_open = False
        self.is_streaming = False
        self.cancel_event = threading.Event()
        self._bot_label: tk.Label | None = None
        self._intents_fired = False  # True when IntentDetector already ran actions
        self._drag_data = {"x": 0, "y": 0}

    def toggle(self):
        if self.is_open:
            self.close()
        else:
            self.open()

    def open(self):
        if self.is_open and self.top:
            self.top.lift()
            return
        self.is_open = True
        self.is_streaming = False

        self.top = tk.Toplevel(self.app.root)
        self.top.overrideredirect(True)
        chat_w, chat_h = 420, 540
        self.top.geometry(f"{chat_w}x{chat_h}")
        self.top.configure(bg=self.HEADER_BG)
        self.top.attributes("-topmost", self.app.settings.always_on_top)

        # Position near Clippy — clamp to screen
        cx = self.app.root.winfo_x()
        cy = self.app.root.winfo_y()
        sw = self.app.root.winfo_screenwidth()
        sh = self.app.root.winfo_screenheight()
        px = cx - chat_w - 10
        if px < 0:
            px = cx + self.app.root.winfo_width() + 10
        px = max(0, min(px, sw - chat_w))
        py = cy - chat_h // 2
        py = max(0, min(py, sh - chat_h - 40))
        self.top.geometry(f"+{px}+{py}")

        # ── Outer border frame for premium edge ──
        border = tk.Frame(self.top, bg=self.BORDER, bd=0)
        border.pack(fill="both", expand=True, padx=1, pady=1)

        inner = tk.Frame(border, bg=self.BG, bd=0)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # ── Header: dark charcoal bar with gold rule ──
        header = tk.Frame(inner, bg=self.HEADER_BG, height=42)
        header.pack(fill="x")
        header.pack_propagate(False)
        header.bind("<ButtonPress-1>", self._header_drag_start)
        header.bind("<B1-Motion>", self._header_drag_move)

        tk.Label(header, text="📎", bg=self.HEADER_BG, fg=self.ACCENT,
                 font=("Segoe UI", 15)).pack(side="left", padx=(12, 4))
        title_lbl = tk.Label(header, text="Clippy", bg=self.HEADER_BG, fg="#f0ead6",
                             font=("Georgia", 13, "bold"))
        title_lbl.pack(side="left")
        title_lbl.bind("<ButtonPress-1>", self._header_drag_start)
        title_lbl.bind("<B1-Motion>", self._header_drag_move)

        # Header buttons
        for txt, cmd in [("✕", self.close), ("🗑", self._clear), ("⚙", self.app.open_settings)]:
            b = tk.Button(header, text=txt, bg=self.HEADER_BG, fg="#a09880",
                          font=("Segoe UI", 12), bd=0, activebackground="#555",
                          activeforeground="white", cursor="hand2", command=cmd, width=3)
            b.pack(side="right", padx=1)

        # Gold accent rule
        tk.Frame(inner, bg=self.ACCENT, height=2).pack(fill="x")

        # ── Messages area (parchment bg) ──
        msg_container = tk.Frame(inner, bg=self.BG)
        msg_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(msg_container, bg=self.BG, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(msg_container, orient="vertical", command=self.canvas.yview,
                                      troughcolor=self.BG, width=6, bg=self.BORDER)
        self.scrollable = tk.Frame(self.canvas, bg=self.BG)

        self.scrollable.bind("<Configure>",
                             lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable,
                                                       anchor="nw", width=chat_w - 18)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>",
                             lambda e: self.canvas.yview_scroll(-int(e.delta / 120), "units"))

        # ── Input area: warm bottom bar ──
        tk.Frame(inner, bg=self.ACCENT, height=2).pack(fill="x", side="bottom")
        input_frame = tk.Frame(inner, bg="#ebe4d4", height=50)
        input_frame.pack(fill="x", side="bottom")
        input_frame.pack_propagate(False)

        self.entry = tk.Entry(input_frame, bg="#ffffff", fg=self.FG,
                              insertbackground=self.ACCENT,
                              font=("Segoe UI", 11), bd=1, relief="solid",
                              highlightcolor=self.ACCENT, highlightthickness=1)
        self.entry.pack(side="left", fill="both", expand=True, padx=(10, 6), pady=9)
        self.entry.bind("<Return>", lambda e: self._send())

        self.send_btn = tk.Button(input_frame, text="➤", bg=self.ACCENT, fg="#fff",
                                  font=("Segoe UI", 13, "bold"), bd=0, cursor="hand2",
                                  activebackground="#b8962e", command=self._send,
                                  width=4, relief="flat")
        self.send_btn.pack(side="right", padx=(0, 10), pady=9)

        # Show greeting
        self._add_bubble(GREETING, is_user=False)
        self.entry.focus_set()

    def close(self):
        if self.is_streaming:
            self.cancel_event.set()
        self.is_open = False
        self.is_streaming = False
        self._bot_label = None
        if self.top:
            try:
                self.canvas.unbind_all("<MouseWheel>")
                self.top.destroy()
            except Exception:
                pass
            self.top = None

    # ── Custom title bar drag ──
    def _header_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _header_drag_move(self, event):
        if self.top:
            x = self.top.winfo_x() + (event.x - self._drag_data["x"])
            y = self.top.winfo_y() + (event.y - self._drag_data["y"])
            self.top.geometry(f"+{x}+{y}")

    def _add_bubble(self, text: str, is_user=False, is_error=False, is_action=False) -> tk.Label:
        if is_action:
            bg = self.ACTION_BG
            fg = "#2e7d32"
            border_col = "#a5d6a7"
        elif is_error:
            bg = self.ERR_BG
            fg = "#b71c1c"
            border_col = "#ef9a9a"
        elif is_user:
            bg = self.USER_BG
            fg = self.FG
            border_col = self.BORDER
        else:
            bg = self.BOT_BG
            fg = self.FG
            border_col = "#d4c9a8"

        container = tk.Frame(self.scrollable, bg=self.BG)
        container.pack(fill="x", padx=8, pady=4, anchor="e" if is_user else "w")

        # Outer border (1px rounded feel)
        bubble_border = tk.Frame(container, bg=border_col, bd=0)
        pad = (80, 4) if is_user else (4, 80)
        bubble_border.pack(fill="x", padx=pad, anchor="e" if is_user else "w")

        bubble = tk.Frame(bubble_border, bg=bg, bd=0)
        bubble.pack(fill="x", padx=1, pady=1)

        # Prefix for bot/action messages
        prefix = ""
        if not is_user and not is_error and not is_action:
            prefix = "📎  "
        elif is_action:
            prefix = "✓  "

        lbl = tk.Label(bubble, text=prefix + text, bg=bg, fg=fg,
                       font=("Segoe UI", 10), wraplength=310,
                       justify="left", anchor="w", padx=10, pady=7)
        lbl.pack(fill="x")

        self._scroll_bottom()
        return lbl

    def _scroll_bottom(self):
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def _send(self):
        if not self.top or self.is_streaming:
            return
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self._add_bubble(text, is_user=True)

        # ── Detect actions directly from user input (instant, no LLM needed) ──
        intents = IntentDetector.detect(text)
        self._intents_fired = bool(intents)
        if intents:
            def _run_intents():
                for cmd, arg in intents:
                    result = ActionExecutor.run(cmd, arg)
                    if result and self.top:
                        self.top.after(0, lambda r=result: self._add_bubble(r, is_action=True))
            threading.Thread(target=_run_intents, daemon=True).start()

        # ── Still send to LLM for a friendly response ──
        self._bot_label = self._add_bubble("", is_user=False)
        self.is_streaming = True
        self.cancel_event.clear()
        self.send_btn.configure(text="■", bg="#c0392b", fg="#fff", command=self._cancel)

        # Trigger Clippy thinking animation
        self.app.set_state("thinking")

        threading.Thread(
            target=self.app.chat.stream,
            args=(text, self._on_chunk, self._on_done, self._on_error, self.cancel_event,
                  self._on_model_not_found),
            daemon=True,
        ).start()

    def _on_chunk(self, text: str):
        if self.top:
            self.top.after(0, self._append_chunk, text)

    def _append_chunk(self, text: str):
        if self._bot_label:
            current = self._bot_label.cget("text")
            self._bot_label.configure(text=current + text)
            self._scroll_bottom()

    def _on_done(self):
        if self.top:
            self.top.after(0, self._finish_and_run_actions)

    def _on_error(self, err: str):
        if self.top:
            self.top.after(0, self._show_error, err)

    def _show_error(self, err: str):
        if self._bot_label:
            self._bot_label.master.destroy()
        self._add_bubble(err, is_error=True)
        self._finish()

    def _on_model_not_found(self, models: list[str]):
        """Called from bg thread when the configured model isn't found."""
        if self.top:
            self.top.after(0, self._show_model_picker, models)

    def _show_model_picker(self, models: list[str]):
        """Show a standalone dialog letting the user pick from installed models."""
        if self._bot_label:
            self._bot_label.master.destroy()
            self._bot_label = None

        old_model = self.app.settings.model
        self._add_bubble(
            f"🤔 Model '{old_model}' not found.\nOpening model picker...",
            is_error=True,
        )
        self._finish()

        # ── Toplevel model picker dialog ──
        picker = tk.Toplevel(self.app.root)
        picker.title("Choose a Model")
        picker.configure(bg="#f5f0e1")
        picker.attributes("-topmost", True)
        picker.resizable(False, False)

        # Position near chat window
        if self.top:
            px = self.top.winfo_x() + 60
            py = self.top.winfo_y() + 80
        else:
            px = self.app.root.winfo_x() - 300
            py = self.app.root.winfo_y()
        picker.geometry(f"+{px}+{py}")

        # Outer border
        border = tk.Frame(picker, bg="#b8a88a", padx=1, pady=1)
        border.pack(fill="both", expand=True)
        inner = tk.Frame(border, bg="#f5f0e1")
        inner.pack(fill="both", expand=True)

        # Header bar
        hdr = tk.Frame(inner, bg="#3c3c3c", height=38)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📋  Choose a Model", bg="#3c3c3c", fg="#f5f0e1",
                 font=("Georgia", 12, "bold")).pack(side="left", padx=14)

        # Gold accent rule
        tk.Frame(inner, bg="#c8a951", height=2).pack(fill="x")

        tk.Label(inner, text=f"'{old_model}' was not found.\nPick one of your installed models:",
                 bg="#f5f0e1", fg="#5c5040", font=("Georgia", 10),
                 justify="center").pack(padx=24, pady=(12, 10))

        btn_frame = tk.Frame(inner, bg="#f5f0e1")
        btn_frame.pack(fill="x", padx=20, pady=(0, 16))

        def _pick(model_name: str):
            self.app.settings.model = model_name
            self.app.settings.save()
            picker.destroy()
            self._add_bubble(f"✅ Switched to {model_name}!", is_user=False)
            self.app.speech.show(f"Now using: {model_name}", 3000)

        for m in models:
            b = tk.Button(btn_frame, text=f"  {m}", bg="#e0d5c1", fg="#2c2c2c",
                          font=("Georgia", 11), bd=1, cursor="hand2",
                          activebackground="#c8a951", activeforeground="#2c2c2c",
                          anchor="w", padx=16, pady=6, relief="solid",
                          highlightbackground="#b8a88a",
                          command=lambda name=m: _pick(name))
            b.pack(fill="x", pady=3)

        tk.Button(inner, text="Cancel", bg="#d5cbb8", fg="#5c5040",
                  font=("Georgia", 10), bd=1, relief="solid",
                  highlightbackground="#b8a88a", command=picker.destroy,
                  cursor="hand2").pack(pady=(0, 14))

    def _finish_and_run_actions(self):
        """Called when streaming completes. Parse actions from response, execute them."""
        if self._bot_label:
            full_text = self._bot_label.cget("text")
            # Strip the 📎  prefix we add to bot messages
            if full_text.startswith("📎  "):
                full_text = full_text[3:]
            # Strip action tags from displayed text
            clean = re.sub(r'\[ACTION:[^\]]*\]', '', full_text).strip()
            if clean:
                self._bot_label.configure(text="📎  " + clean)
            # Execute LLM actions ONLY if IntentDetector didn't already fire
            if not self._intents_fired:
                actions = re.findall(r'\[ACTION:([^\]]+)\]', full_text)
                if actions:
                    threading.Thread(
                        target=self._execute_actions, args=(actions,), daemon=True
                    ).start()
        self._finish()

    def _execute_actions(self, actions: list[str]):
        """Run parsed action tags in background."""
        for action_str in actions:
            parts = action_str.split("|", 1)
            cmd = parts[0].strip().upper()
            arg = parts[1].strip() if len(parts) > 1 else ""
            result = ActionExecutor.run(cmd, arg)
            if result:
                if self.top:
                    self.top.after(0, self._add_action_result, result)

    def _add_action_result(self, result: str):
        """Show action result as a small system bubble."""
        self._add_bubble(result, is_action=True)

    def _finish(self):
        self.is_streaming = False
        self._bot_label = None
        self._intents_fired = False
        if self.top:
            self.send_btn.configure(text="➤", bg=self.ACCENT, fg="#fff", command=self._send)
        self.app.set_state("idle")

    def _cancel(self):
        self.cancel_event.set()

    def _clear(self):
        if self.is_streaming:
            self.cancel_event.set()
        self.app.chat.clear()
        self._bot_label = None
        self.is_streaming = False
        if self.top:
            self.send_btn.configure(text="➤", bg=self.ACCENT, fg="#fff", command=self._send)
            for w in self.scrollable.winfo_children():
                w.destroy()
            self._add_bubble(GREETING, is_user=False)


# ═══════════════════════════════════════════════════════════════════════════
#  SETTINGS DIALOG
# ═══════════════════════════════════════════════════════════════════════════


class SettingsDialog:
    def __init__(self, parent: tk.Tk, settings: Settings):
        self.settings = settings
        self.top = tk.Toplevel(parent)
        self.top.title("Clippy — Settings")
        self.top.geometry("440x520")
        self.top.configure(bg="#f5f0e1")
        self.top.attributes("-topmost", True)
        self.top.resizable(False, False)

        # Outer border
        border = tk.Frame(self.top, bg="#b8a88a", padx=1, pady=1)
        border.pack(fill="both", expand=True)
        body = tk.Frame(border, bg="#f5f0e1")
        body.pack(fill="both", expand=True)

        # Header bar
        hdr = tk.Frame(body, bg="#3c3c3c", height=42)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙  Clippy Settings", bg="#3c3c3c", fg="#f5f0e1",
                 font=("Georgia", 14, "bold")).pack(side="left", padx=14)

        # Gold accent rule
        tk.Frame(body, bg="#c8a951", height=2).pack(fill="x")

        main = tk.Frame(body, bg="#f5f0e1")
        main.pack(fill="both", expand=True, padx=24, pady=(14, 0))

        # Ollama URL
        tk.Label(main, text="Ollama Server URL", bg="#f5f0e1", fg="#3c3c3c",
                 font=("Georgia", 11, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        self.url_entry = tk.Entry(main, bg="white", fg="#2c2c2c", insertbackground="#2c2c2c",
                                   font=("Georgia", 11), bd=1, relief="solid",
                                   highlightbackground="#b8a88a", highlightcolor="#c8a951")
        self.url_entry.pack(fill="x", ipady=6, pady=(0, 12))
        self.url_entry.insert(0, settings.ollama_url)

        # Model
        tk.Label(main, text="Model Name", bg="#f5f0e1", fg="#3c3c3c",
                 font=("Georgia", 11, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        self.model_entry = tk.Entry(main, bg="white", fg="#2c2c2c", insertbackground="#2c2c2c",
                                     font=("Georgia", 11), bd=1, relief="solid",
                                     highlightbackground="#b8a88a", highlightcolor="#c8a951")
        self.model_entry.pack(fill="x", ipady=6, pady=(0, 4))
        self.model_entry.insert(0, settings.model)

        # Available models hint
        models = OllamaManager.list_models(settings.ollama_url)
        if models:
            hint = "Available: " + ", ".join(models[:6])
            tk.Label(main, text=hint, bg="#f5f0e1", fg="#8a7e6a",
                     font=("Georgia", 9)).pack(anchor="w", pady=(0, 8))

        # Checkboxes
        self.on_top = tk.BooleanVar(value=settings.always_on_top)
        self.roaming = tk.BooleanVar(value=settings.idle_roaming)
        self.tips = tk.BooleanVar(value=settings.show_tips)
        self.auto_ollama = tk.BooleanVar(value=settings.auto_start_ollama)

        for text, var in [
            ("Always on top", self.on_top),
            ("Idle roaming (Clippy walks around)", self.roaming),
            ("Show idle tips", self.tips),
            ("Auto-start Ollama", self.auto_ollama),
        ]:
            cb = tk.Checkbutton(main, text=text, variable=var, bg="#f5f0e1", fg="#2c2c2c",
                                selectcolor="#e0d5c1", activebackground="#f5f0e1",
                                activeforeground="#2c2c2c", font=("Georgia", 11),
                                anchor="w")
            cb.pack(fill="x", pady=2)

        # Save button
        tk.Button(body, text="Save Settings", bg="#c8a951", fg="#2c2c2c",
                  font=("Georgia", 12, "bold"), bd=1, relief="solid",
                  highlightbackground="#b8a88a", cursor="hand2",
                  activebackground="#d4b85c", command=self._save,
                  height=2).pack(fill="x", padx=24, pady=(16, 20))

    def _save(self):
        self.settings.ollama_url = self.url_entry.get().strip() or DEFAULT_OLLAMA_URL
        self.settings.model = self.model_entry.get().strip() or DEFAULT_MODEL
        self.settings.always_on_top = self.on_top.get()
        self.settings.idle_roaming = self.roaming.get()
        self.settings.show_tips = self.tips.get()
        self.settings.auto_start_ollama = self.auto_ollama.get()
        self.settings.save()
        self.top.destroy()


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN CLIPPY APP
# ═══════════════════════════════════════════════════════════════════════════


class ClippyApp:
    # Clippy states
    STATE_IDLE = "idle"
    STATE_THINKING = "thinking"
    STATE_WAVE = "wave"

    def __init__(self):
        self.settings = Settings()
        self.chat_service = OllamaChat(self.settings)

        # ── Tk root — transparent overlay window ──
        self.root = tk.Tk()
        self.root.withdraw()  # hide while setting up
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", self.settings.always_on_top)
        self.root.configure(bg="#f0f0f0")
        self.root.attributes("-transparentcolor", "#f0f0f0")

        # ── Load sprites ──
        self.sprites: dict[str, AnimatedSprite] = {}
        self._load_sprites()

        # ── Clippy label ──
        self.clippy_label = tk.Label(self.root, bg="#f0f0f0", bd=0, cursor="hand2")
        self.clippy_label.pack()

        # Bind events
        self.clippy_label.bind("<Double-Button-1>", lambda e: self.chat_window.toggle())
        self.clippy_label.bind("<Button-3>", self._show_menu)
        self.clippy_label.bind("<ButtonPress-1>", self._drag_start)
        self.clippy_label.bind("<B1-Motion>", self._drag_move)
        self.clippy_label.bind("<ButtonRelease-1>", self._drag_end)

        # ── State ──
        self.state = self.STATE_IDLE
        self._anim_job = None
        self._drag_data = {"x": 0, "y": 0, "dragging": False}

        # ── Chat window ──
        self.chat_window = ChatWindow(self)
        self.chat = self.chat_service

        # ── Speech bubble ──
        self.speech = SpeechBubble(self.root)

        # ── Context menu ──
        self.menu = tk.Menu(self.root, tearoff=0, bg="#2d2d2d", fg="white",
                            activebackground="#0078d4", activeforeground="white",
                            font=("Segoe UI", 10))
        self.menu.add_command(label="💬  Open Chat", command=self.chat_window.toggle)
        self.menu.add_command(label="⚙  Settings", command=self.open_settings)
        self.menu.add_command(label="📋  Available Models", command=self._show_models)
        self.menu.add_separator()
        self.menu.add_command(label="🔄  Restart Ollama", command=self._restart_ollama)
        self.menu.add_command(label="🌐  Ollama Website", command=lambda: webbrowser.open("https://ollama.com"))
        self.menu.add_separator()
        self.menu.add_command(label="❌  Exit Clippy", command=self._quit)

        # ── Idle behaviors ──
        self._roam_target = None
        self._roam_job = None
        self._tip_job = None
        self._wave_timeout = None

        # ── Auto-start Ollama ──
        self._startup_done = False

        # Position: restore saved position or default to bottom-right of primary
        vl, vt, vr, vb = _get_virtual_screen_bounds()
        if self.settings.pos_x is not None and self.settings.pos_y is not None:
            # Validate saved position is still on a visible screen area
            sx = self.settings.pos_x
            sy = self.settings.pos_y
            if vl <= sx <= vr - 50 and vt <= sy <= vb - 50:
                self._saved_pos = (sx, sy)
            else:
                self._saved_pos = None
        else:
            self._saved_pos = None

        if self._saved_pos is None:
            # Default: bottom-right of primary monitor
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            self._saved_pos = (sw - 140, sh - 160)

        self.root.geometry(f"+{self._saved_pos[0]}+{self._saved_pos[1]}")
        self.root.deiconify()

        # Start!
        self._intro_animation()

    def _load_sprites(self):
        """Load all available sprites from assets."""
        # Static Clippy (main idle)
        static_path = os.path.join(ASSETS_DIR, "og_clippy.webp")
        if os.path.exists(static_path):
            self.sprites["idle"] = AnimatedSprite(static_path, (90, 90))

        # Animated thinking/scratching
        anim_path = os.path.join(ASSETS_DIR, "clippy_scratching_forehead.gif")
        if os.path.exists(anim_path):
            self.sprites["thinking"] = AnimatedSprite(anim_path, (90, 84))

        # If no idle sprite, create placeholder
        if "idle" not in self.sprites:
            img = Image.new("RGBA", (90, 90), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle([6, 6, 84, 84], radius=12, fill=(80, 80, 80, 200))
            draw.text((30, 30), "📎", fill="white")
            photo = ImageTk.PhotoImage(img)
            # Fake sprite
            s = AnimatedSprite.__new__(AnimatedSprite)
            s.frames = [photo]
            s.durations = [100]
            s.current = 0
            s.size = (90, 90)
            self.sprites["idle"] = s

    def set_state(self, state: str):
        """Switch Clippy's animation state."""
        if state == self.state:
            return
        self.state = state
        if state in self.sprites:
            self.sprites[state].reset()
        self._animate()

    def _animate(self):
        """Run the current sprite's animation frames."""
        if self._anim_job:
            self.root.after_cancel(self._anim_job)
            self._anim_job = None

        sprite = self.sprites.get(self.state, self.sprites.get("idle"))
        if not sprite:
            return

        frame, dur = sprite.next_frame()
        self.clippy_label.configure(image=frame)
        self.clippy_label.image = frame  # keep ref

        if sprite.is_animated:
            self._anim_job = self.root.after(dur, self._animate)

    # ── Intro Animation ──

    def _save_position(self):
        """Persist Clippy's current screen position to settings."""
        try:
            self.settings.pos_x = self.root.winfo_x()
            self.settings.pos_y = self.root.winfo_y()
            self.settings.save()
        except Exception:
            pass

    def _intro_animation(self):
        """Clippy bounces up from below the screen."""
        target_x, target_y = self._saved_pos
        # Start from just below the target (offset by 120px)
        start_y = target_y + 120

        self.set_state("idle")

        duration = 800
        start_t = time.perf_counter()
        last_y = [None]

        def _step():
            elapsed = (time.perf_counter() - start_t) * 1000
            p = min(elapsed / duration, 1.0)

            # Bounce ease-out
            if p < 1 / 2.75:
                ease = 7.5625 * p * p
            elif p < 2 / 2.75:
                t = p - 1.5 / 2.75
                ease = 7.5625 * t * t + 0.75
            elif p < 2.5 / 2.75:
                t = p - 2.25 / 2.75
                ease = 7.5625 * t * t + 0.9375
            else:
                t = p - 2.625 / 2.75
                ease = 7.5625 * t * t + 0.984375

            y = round(start_y + (target_y - start_y) * ease)
            if y != last_y[0]:
                self.root.geometry(f"+{target_x}+{y}")
                last_y[0] = y

            if p < 1.0:
                self.root.after(8, _step)
            else:
                self.root.after(400, self._post_intro)

        _step()

    def _post_intro(self):
        """After intro: auto-start Ollama, show greeting, start idle behaviors."""
        self.speech.show("Hi! Double-click me to chat! 📎", 4000)

        # Start the thinking animation briefly as a wave
        if "thinking" in self.sprites:
            self.set_state("thinking")
            self.root.after(2500, lambda: self.set_state("idle"))

        # Auto-start Ollama in background
        if self.settings.auto_start_ollama:
            threading.Thread(target=self._bg_start_ollama, daemon=True).start()

        # Start idle behaviors
        self.root.after(8000, self._schedule_tip)
        self.root.after(12000, self._schedule_roam)

    def _bg_start_ollama(self):
        err = OllamaManager.auto_start(self.settings.ollama_url)
        self._startup_done = True
        if err:
            self.root.after(0, lambda: self.speech.show(err, 6000))
        else:
            self.root.after(0, lambda: self.speech.show("✅ Ollama is ready!", 3000))

    # ── Idle Roaming ──

    def _schedule_roam(self):
        if not self.settings.idle_roaming:
            self._roam_job = self.root.after(10000, self._schedule_roam)
            return
        if self.chat_window.is_open or self._drag_data["dragging"]:
            self._roam_job = self.root.after(5000, self._schedule_roam)
            return

        delay = random.randint(15000, 35000)
        self._roam_job = self.root.after(delay, self._do_roam)

    def _do_roam(self):
        """Pick a random nearby spot and walk there."""
        if self.chat_window.is_open or self._drag_data["dragging"]:
            self._schedule_roam()
            return

        # Use virtual screen bounds so Clippy can roam on any monitor
        vl, vt, vr, vb = _get_virtual_screen_bounds()
        cx = self.root.winfo_x()
        cy = self.root.winfo_y()

        # Random target within ±200px, clamped to virtual desktop
        tx = max(vl + 20, min(vr - 110, cx + random.randint(-200, 200)))
        ty = max(vt + 20, min(vb - 140, cy + random.randint(-150, 150)))

        self._roam_to(cx, cy, tx, ty)

    def _roam_to(self, sx, sy, tx, ty):
        """Smoothly move Clippy from (sx,sy) to (tx,ty) using sub-pixel interpolation."""
        dist = math.sqrt((tx - sx) ** 2 + (ty - sy) ** 2)
        duration = max(600, int(dist * 3))  # slightly faster
        start_t = time.perf_counter()
        # Track last rendered position to skip no-op geometry calls
        last_pos = [None, None]

        def _step():
            if self._drag_data["dragging"]:
                self._save_position()
                self._schedule_roam()
                return
            now = time.perf_counter()
            elapsed = (now - start_t) * 1000
            p = min(elapsed / duration, 1.0)

            # Smoother quintic ease in-out
            if p < 0.5:
                ease = 16 * p * p * p * p * p
            else:
                t = p - 1
                ease = 1 + 16 * t * t * t * t * t

            x = round(sx + (tx - sx) * ease)
            y = round(sy + (ty - sy) * ease)

            # Gentle hop/wobble
            hop = round(math.sin(p * math.pi) * 6)
            fy = y - hop

            # Only update geometry when position actually changes
            if x != last_pos[0] or fy != last_pos[1]:
                self.root.geometry(f"+{x}+{fy}")
                last_pos[0] = x
                last_pos[1] = fy

            if p < 1.0:
                self.root.after(8, _step)  # ~120fps target for smoother interpolation
            else:
                self._save_position()
                self._schedule_roam()

        _step()

    # ── Idle Tips ──

    def _schedule_tip(self):
        if not self.settings.show_tips:
            self._tip_job = self.root.after(15000, self._schedule_tip)
            return
        if self.chat_window.is_open:
            self._tip_job = self.root.after(10000, self._schedule_tip)
            return

        delay = random.randint(25000, 60000)
        self._tip_job = self.root.after(delay, self._show_tip)

    def _show_tip(self):
        if self.chat_window.is_open:
            self._schedule_tip()
            return
        tip = random.choice(IDLE_TIPS)
        self.speech.show(tip, 5000)

        # Play thinking animation during tip
        if "thinking" in self.sprites:
            self.set_state("thinking")
            self.root.after(3000, lambda: self.set_state("idle"))

        self._schedule_tip()

    # ── Drag ──

    def _drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self._drag_data["dragging"] = False

    def _drag_move(self, event):
        self._drag_data["dragging"] = True
        x = self.root.winfo_x() + (event.x - self._drag_data["x"])
        y = self.root.winfo_y() + (event.y - self._drag_data["y"])
        self.root.geometry(f"+{x}+{y}")

    def _drag_end(self, event):
        self._drag_data["dragging"] = False
        self._save_position()

    # ── Context menu ──

    def _show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _show_models(self):
        models = OllamaManager.list_models(self.settings.ollama_url)
        if models:
            text = "📋 Available Models:\n\n" + "\n".join(f"  • {m}" for m in models)
        else:
            text = "❌ No models found.\n\nMake sure Ollama is running,\nthen pull a model:\n  ollama pull llama3.2"
        self.speech.show(text, 8000)

    def _restart_ollama(self):
        self.speech.show("🔄 Restarting Ollama...", 3000)

        def _do():
            # Kill existing
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/f", "/im", "ollama.exe"],
                                   capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    subprocess.run(["taskkill", "/f", "/im", "ollama_llama_server.exe"],
                                   capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                time.sleep(2)
            except Exception:
                pass
            err = OllamaManager.auto_start(self.settings.ollama_url)
            msg = err if err else "✅ Ollama restarted!"
            self.root.after(0, lambda: self.speech.show(msg, 4000))

        threading.Thread(target=_do, daemon=True).start()

    def open_settings(self):
        SettingsDialog(self.root, self.settings)

    # ── Quit ──

    def _quit(self):
        self._save_position()
        self.speech.hide()
        if self.chat_window.is_open:
            self.chat_window.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = ClippyApp()
    app.run()
