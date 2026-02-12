"""
📎 Clippy — No-Console Launcher
Double-click this file to run Clippy without a terminal window.
"""
import os, sys

# Ensure working directory is correct (for asset loading)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from clippy import ClippyApp

ClippyApp().run()
