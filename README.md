# Clippy — Local AI Desktop Assistant (Python)

A self-contained, animated desktop companion powered by **Ollama** — 100% local, no cloud, no API keys.

Clippy lives on your desktop as a transparent overlay. He idles, roams, shows tips, and chats with you through a local LLM.

![Clippy](assets/og_clippy.webp)

---

## Features

| Feature | Description |
|---|---|
| **Instant Actions** | Open apps, close programs, search web, take screenshots — instantly! |
| **AI Chat** | Double-click Clippy to open a streaming chat window |
| **100% Local** | Powered by Ollama — no internet, no API keys, no telemetry |
| **Idle Roaming** | Clippy wanders your screen when you're not using him |
| **Random Tips** | Fun tips and nostalgic quotes appear in speech bubbles |
| **Draggable** | Click and drag Clippy anywhere |
| **Auto-Start Ollama** | Ollama is launched automatically if not running |
| **Settings** | Change model, server URL, behaviors |
| **Restart Ollama** | Right-click → Restart Ollama |

---

## Requirements

- **Python 3.10+**
- **Ollama** — [Download here](https://ollama.com/download)
- A pulled model (e.g., `ollama pull llama3.2`)

---

## Quick Start

### 1. Install Ollama

Download and install from [ollama.com/download](https://ollama.com/download).

Then pull a model:

```bash
ollama pull llama3.2
```

> Clippy will auto-start Ollama when launched — you don't need to run `ollama serve` manually.

### 2. Install Python dependencies

```bash
cd clippy-python
pip install -r requirements.txt
```

### 3. Run Clippy

```bash
python clippy.py
```

Clippy will bounce onto your screen!

### 4. Run without Terminal (Windows)

To launch Clippy without the black console window appearing:

- Double-click the **`clippy.pyw`** file.
- Or right-click `clippy.pyw` → **Send to** → **Desktop (create shortcut)**.

---

## Commands & Actions

Clippy can control your PC! Just type natural commands in the chat window.

| Command | Example |
|---|---|
| **Close Apps** | "Close Chrome", "Kill Notepad", "Exit Spotify" |
| **Open Apps** | "Open VS Code", "Launch Calculator", "Start Discord" |
| **Open Websites** | "Open YouTube", "Go to GitHub", "Reddit" |
| **Search Web** | "Google how to center a div", "Search for pizza near me" |
| **Manage Files** | "Find PDF files on desktop", "Open my Documents" |
| **Screenshots** | "Take a screenshot", "Capture screen" |
| **System** | "Open Task Manager", "Open Control Panel" |

> **Note:** Actions like closing apps happen instantly via local intent detection. Complex requests ("Open that website about...") are handled by the AI model.

---

## How to Use

| Action | What it does |
|---|---|
| **Double-click** Clippy | Open/close the chat window |
| **Right-click** Clippy | Context menu (settings, models, restart, exit) |
| **Click + drag** | Move Clippy around your screen |
| **Type + Enter** | Send a message in the chat window |
| **Settings button** in chat | Open settings |
| **Clear button** in chat | Clear conversation |
| **Close button** in chat | Close chat |

---

## Settings

Access settings via **right-click → Settings** or the ⚙ button in chat.

| Setting | Default | Description |
|---|---|---|
| Ollama Server URL | `http://localhost:11434` | Where Ollama is running |
| Model Name | `llama3.2` | Which model to use |
| Always on top | ✅ | Keep Clippy above other windows |
| Idle roaming | ✅ | Clippy wanders when idle |
| Show idle tips | ✅ | Random tips in speech bubbles |
| Auto-start Ollama | ✅ | Launch Ollama automatically |

Settings are saved to `~/.clippy_python_settings.json`.

---

## Project Structure

```
clippy-python/
├── clippy.py              # Main application (self-contained)
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── assets/
    ├── og_clippy.webp     # Original Clippy static sprite
    └── clippy_scratching_forehead.gif  # Animated thinking sprite
```

---

## Troubleshooting

### Clippy says "Ollama not found"

1. Install Ollama from [ollama.com/download](https://ollama.com/download)
2. Make sure `ollama` is in your PATH, or install to the default location
3. Run `ollama serve` manually, then restart Clippy

### Clippy says "Model not found"

Pull the model first:

```bash
ollama pull llama3.2
```

### Chat is slow

Try a smaller model:

```bash
ollama pull phi3
# Then change the model in Clippy Settings
```

### Clippy doesn't appear

- Check your taskbar — Clippy may be behind other windows
- Try running with `python clippy.py` from a terminal to see errors
- Make sure Pillow is installed: `pip install Pillow`

### Transparent background shows a gray box

- This uses tkinter's `-transparentcolor` attribute (Windows only)
- On Linux/macOS, the transparent overlay may not work — Clippy will have a gray background

---

## Add More Animations

Drop additional GIF files into the `assets/` folder. To use them, edit `clippy.py` and add entries in the `_load_sprites()` method:

```python
my_anim_path = os.path.join(ASSETS_DIR, "my_animation.gif")
if os.path.exists(my_anim_path):
    self.sprites["my_state"] = AnimatedSprite(my_anim_path, (130, 130))
```

---

## 📜 License

MIT License — see the root [LICENSE.txt](../LICENSE.txt).

---

*Made with nostalgia for the golden age of desktop assistants.*
