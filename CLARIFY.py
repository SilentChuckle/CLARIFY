"""
CLARIFY - File Organization Tool
================================

Written by SilentChuckle

WHAT THIS PROGRAM DOES
    Clarify tidies a messy folder. You point it at a "source" folder, tick how you want files grouped,
    and it MOVES every file into a neat tree of subfolders, for example:
        Sorted / Images / 2026 / 10-October / photo.jpg
    It is the one organizer in this collection - everything useful from the older organizer scripts
    (timestamp renaming, preview mode, age-based sorting) has been merged into it.

HOW IT WORKS (the big picture)
    1. Walk through every file in the source folder (skipping Windows system folders and any
       "Protected Folders" you add).
    2. For each file, build its destination folder from the "criteria" you ticked, in the order you
       chose (extension, year, month, day, hour, category, weekday, quarter, size, age).
    3. Move the file there. If a file with the same name is already there:
         - and it is an exact copy (same SHA-256 fingerprint)  -> the extra copy is deleted ("purged");
         - and it is different                                  -> the new file gets a number, e.g. name_1.jpg.
       Nothing is ever overwritten.
    4. Optionally delete zero-byte (empty) files and empty folders, rename files by their date/time,
       and give your own account full access to files that Windows locked you out of.

HOW TO USE IT
    Double-click this file, or run:  python SilentChuckle-clarify_file_organizer_v3.py --source D:\\Downloads --dest D:\\Sorted
    Tick "Preview only" first to see what WOULD happen without touching a single file.

SAFETY
    * System folders (Windows, Program Files, $Recycle.Bin ...) and your Protected Folders are never touched.
    * Exempt keywords / exempt paths protect EVERYTHING below a matching folder (sorting, access, cleanup).
    * Preview mode moves, renames and deletes nothing.
    * Duplicates are only purged when name AND SHA-256 fingerprint match exactly.
    * Settings are saved next to this script in clarify_config.json; the optional error log
      (clarify_error.log) lists file paths only - no file contents.

REQUIREMENTS
    Only Python's built-in library - nothing to install.

Author : SilentChuckle (with Claude support)
Created: 2026-10-21
Updated: 2026-10-26  (window rebuilt: auto-sizes to the screen, scrolls, collapsible sections; exempt
                      keywords/paths now protect the WHOLE subtree in every phase)

License: MIT
    Copyright (c) 2026 SilentChuckle
    Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
    associated documentation files (the "Software"), to deal in the Software without restriction,
    including without limitation the rights to use, copy, modify, merge, publish, distribute,
    sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:
    The above copyright notice and this permission notice shall be included in all copies or
    substantial portions of the Software.
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
    BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
from __future__ import annotations


# @@BEGIN BLOCK_A@@
# =====================================================================================
# STEP 1 - HIDE THE BLACK CONSOLE WINDOW, AND LEAVE NO FILES BEHIND WITHOUT PERMISSION
# =====================================================================================
# Windows opens a black "console" window when a script is started with python.exe. This program has
# its own window, so the console is just clutter. If we were started with python.exe we immediately
# start a second copy with pythonw.exe (the "windowless" Python) and quit this copy. The environment
# variable _GUI_RELAUNCHED stops the new copy from doing the same thing again. This only happens when the
# script is RUN (not when another program imports it), and - for programs that also work from the command
# line - only when no command-line arguments were given.
import os as _os, sys as _sys
# Nothing is written to disk just by running this program unless you ask for it. Python normally caches
# compiled imports in a '__pycache__' folder next to the script; we turn that off so none appears. (If a
# '__pycache__' is ever left behind by something else, the cleanup below removes it when the program closes.)
_sys.dont_write_bytecode = True
import atexit as _atexit
@_atexit.register
def _remove_pycache():
    import shutil as _sh
    _pc = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "__pycache__")
    _sh.rmtree(_pc, ignore_errors=True)
if (_sys.platform == "win32" and __name__ == "__main__" and _sys.executable.lower().endswith("python.exe")
        and _os.environ.get("_GUI_RELAUNCHED") != "1"
        and not (globals().get("RELAUNCH_ONLY_WITHOUT_ARGUMENTS") and len(_sys.argv) > 1)):
    _pyw = _sys.executable[:-len("python.exe")] + "pythonw.exe"          # path of the windowless Python
    if _os.path.exists(_pyw):
        import subprocess as _sp
        _sp.Popen([_pyw, _os.path.abspath(__file__)] + _sys.argv[1:], env=dict(_os.environ, _GUI_RELAUNCHED="1"))
        _sys.exit(0)                                                      # this console copy is finished
# Without a console, print() has nowhere to go. Anything printed (and any crash message) is normally lost,
# which makes problems hard to report - but we never save that to a ".log" file on disk unless you have
# opted in, either with the environment variable SILENTCHUCKLE_SAVE_LOGS=1 or by placing a file named
# "<this script>.logs_enabled" next to it. Without opt-in, the text is only kept in memory and shown once
# in a pop-up if the program exits with something to report - nothing touches the disk either way unless
# you asked for it. (Programs must never print passwords or other private data.)
_LOG_OPT_IN = (_os.environ.get("SILENTCHUCKLE_SAVE_LOGS") == "1"
               or _os.path.exists(_os.path.splitext(_os.path.abspath(__file__))[0] + ".logs_enabled"))
if _sys.stdout is None or _sys.stderr is None:
    class _LazyLog:
        def __init__(self):
            self._buffer = []                                            # used only when not opted in
        def write(self, text):
            if _LOG_OPT_IN:
                with open(_os.path.splitext(_os.path.abspath(__file__))[0] + ".log", "a", encoding="utf-8") as f:
                    f.write(text)
            else:
                self._buffer.append(text)
        def flush(self):
            pass
    _log = _LazyLog()
    _sys.stdout = _sys.stdout or _log
    _sys.stderr = _sys.stderr or _log
    if not _LOG_OPT_IN:
        @_atexit.register
        def _show_unsaved_output():
            text = "".join(_log._buffer).strip()
            if not text:
                return
            try:
                import tkinter as _tk
                from tkinter import messagebox as _mb
                _r = _tk.Tk(); _r.withdraw(); _r.attributes("-topmost", True)
                _mb.showerror("Something was reported (not saved to disk)",
                              text[-1500:] + "\n\nTo save this to a .log file next time, create a file "
                              "named '" + _os.path.basename(_os.path.splitext(__file__)[0]) + ".logs_enabled' "
                              "next to this script.", parent=_r)
                _r.destroy()
            except Exception:
                pass
# @@END BLOCK_A@@

# =====================================================================================
# STEP 2 - SAY WHAT THIS PROGRAM NEEDS
# =====================================================================================
# {"name you `import`": "name pip knows it by"}.  Clarify only uses Python's built-in tools, so the
# lists are empty - but the check in STEP 3 still runs, so the structure is the same in every program.
REQUIRED_PACKAGES = {}
REQUIRED_TOOLS = {}

# @@BEGIN BLOCK_B@@
# =====================================================================================
# STEP 3 - CHECK THAT EVERYTHING THIS PROGRAM NEEDS IS INSTALLED (before any real work starts)
# =====================================================================================
# A "dependency" is an add-on package (written by other people) or an outside program that this
# program uses. If one is missing the program would crash halfway through its job, so we look FIRST.
# If something is missing we ask permission to install it - nothing is ever installed without
# your OK. The names to look for are listed in REQUIRED_PACKAGES / REQUIRED_TOOLS in STEP 2.
import shutil as _shutil, subprocess as _subprocess, importlib as _importlib, importlib.util as _importlib_util
import os as _os, sys as _sys


def find_missing_dependencies(packages, tools=None):
    """Return (missing_pip_names, missing_tools). Nothing is installed here - this only looks.
    packages: {"name used in `import`": "name pip knows it by"}, e.g. {"PIL": "pillow"}
    tools:    {"program name": "winget package id"}, e.g. {"ffmpeg": "Gyan.FFmpeg"}"""
    missing_packages = [pip_name for module, pip_name in packages.items()
                        if _importlib_util.find_spec(module) is None]       # None = Python cannot find it
    missing_tools = {exe: winget_id for exe, winget_id in (tools or {}).items()
                     if _shutil.which(exe) is None}                           # not found on the PATH
    return missing_packages, missing_tools


def _ask_yes_no(title, text):
    """Ask a Yes/No question: in the terminal if one is attached, otherwise in a pop-up window."""
    if _sys.stdin is not None and _sys.stdin.isatty():
        try:
            return input(text + "\n[y/N] ").strip().lower().startswith("y")
        except (EOFError, OSError):                      # nobody is there to answer -> safest answer is "no"
            return False
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()                                  # we only want the pop-up, not an empty window
        root.attributes("-topmost", True)
        answer = messagebox.askyesno(title, text, parent=root)
        root.destroy()
        return answer
    except Exception:
        return False                                     # no way to ask -> safest answer is "do not install"


def _tell(title, text, error=False):
    """Show a message in the terminal or in a pop-up window."""
    if _sys.stdin is not None and _sys.stdin.isatty():
        print(text)
        return
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        (messagebox.showerror if error else messagebox.showinfo)(title, text, parent=root)
        root.destroy()
    except Exception:
        print(text)


def _run_with_wait_window(command, message):
    """Run a slow command (like pip) while showing a small 'please wait' window so the program does
    not look frozen. Returns the finished process (return code + captured output)."""
    import threading
    result = {}
    flags = getattr(_subprocess, "CREATE_NO_WINDOW", 0)                  # do not flash a console window
    worker = threading.Thread(target=lambda: result.update(
        done=_subprocess.run(command, capture_output=True, text=True, creationflags=flags)))
    worker.start()
    try:
        import tkinter as tk
        window = tk.Tk()
        window.title("Please wait")
        tk.Label(window, text=message, padx=30, pady=25).pack()
        window.attributes("-topmost", True)
        while worker.is_alive():                                          # keep the window alive while pip works
            window.update()
            worker.join(0.05)
        window.destroy()
    except Exception:
        worker.join()                                                     # no window possible: just wait
    return result["done"]


def ensure_dependencies(packages, tools=None):
    """Check dependencies; if any are missing, offer to install them. Exits the program if the user
    says no or the install fails; returns normally when everything is present."""
    missing_packages, missing_tools = find_missing_dependencies(packages, tools)
    if not missing_packages and not missing_tools:
        return                                          # everything is here -> carry on with the real work

    if missing_packages:                                # ---- missing Python packages: install with pip
        names = "\n  - ".join(missing_packages)
        if not _ask_yes_no("Missing components",
                           f"This program needs these Python packages:\n  - {names}\n\n"
                           "They will be downloaded from PyPI (the official Python package site).\n"
                           "Install them now?"):
            _sys.exit(0)
        python = _sys.executable                                          # pythonw.exe cannot run pip well,
        if python.lower().endswith("pythonw.exe") and _os.path.exists(python[:-11] + "python.exe"):
            python = python[:-11] + "python.exe"                          # so use its console twin
        # The package names come from the list written above - never from user input - so nothing
        # untrusted can reach this command, and no shell is involved.
        done = _run_with_wait_window([python, "-m", "pip", "install", "--disable-pip-version-check", *missing_packages],
                                     "Installing: " + ", ".join(missing_packages) + "\nThis can take a few minutes...")
        _importlib.invalidate_caches()                                    # let Python notice the new packages
        if done.returncode != 0 or find_missing_dependencies(packages)[0]:
            _tell("Install failed", "Could not install the required packages.\n\n" + (done.stderr or "")[-600:], True)
            _sys.exit(1)

    for exe, winget_id in missing_tools.items():        # ---- missing outside programs (e.g. ffmpeg)
        if winget_id and _shutil.which("winget") and _ask_yes_no(
                "Missing program", f"This program needs '{exe}', which is not installed.\n"
                                   f"Install it with the Windows Package Manager (winget id: {winget_id})?"):
            done = _run_with_wait_window(["winget", "install", "--id", winget_id, "-e", "--silent",
                                          "--accept-source-agreements", "--accept-package-agreements"],
                                         f"Installing {exe}...")
            _tell("Restart needed", f"{exe} was installed. Please close and re-open this program so Windows "
                                    "can find it." if done.returncode == 0 else f"Could not install {exe}.", done.returncode != 0)
        else:
            _tell("Missing program", f"This program needs '{exe}'. Please install it and start the program again.", True)
        _sys.exit(1)


ensure_dependencies(REQUIRED_PACKAGES, REQUIRED_TOOLS)         # <- the actual check happens here
# @@END BLOCK_B@@

# =====================================================================================
# STEP 4 - LOAD THE TOOLS WE USE (imports)
# =====================================================================================
# Each line below loads a ready-made toolbox from Python's standard library.
import argparse                      # reads options typed after the program name (--source, --dest ...)
import getpass                       # finds out which Windows user is running the program
import hashlib                       # makes SHA-256 "fingerprints" so we can tell if two files are identical
import json                          # saves and loads the settings file
import os                            # file and folder operations
import queue                         # a safe mailbox for passing messages from the worker thread to the window
import shutil                        # moves files
import subprocess                    # runs the Windows "icacls" permission command
import sys
import threading                     # lets the work run in the background so the window never freezes
import tkinter as tk                 # the window toolkit
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

# =====================================================================================
# STEP 5 - SETTINGS (constants). Change these to change behaviour.
# =====================================================================================
SCRIPT_DIR = Path(__file__).resolve().parent                 # the folder this script lives in
CONFIG_FILE = SCRIPT_DIR / "clarify_config.json"             # your saved choices
DEFAULT_ERROR_LOG = SCRIPT_DIR / "clarify_error.log"         # optional list of things that went wrong
HASH_BLOCK_SIZE = 1024 * 1024                                # read files 1 MB at a time when fingerprinting
ICACLS_TIMEOUT_SECONDS = 30                                  # give up on one permission change after 30 s
UI_POLL_MS = 100                                             # how often the window checks for new messages
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)       # stops a console flashing when we run icacls
RENAME_MODES = ("Full", "Prefix", "Suffix")                  # how the date/time is added to a file name

# The tick-boxes in the window -> the short key the engine understands.
SORT_CRITERIA_MAP = {
    "File Extension": "ext",
    "Year": "year",
    "Month": "month",
    "Day": "day",
    "Hour": "hour",
    "File Category": "category",
    "Day of Week": "day_of_week",
    "Quarter": "quarter",
    "Size Range": "size_range",
    "File Age": "age",
}

# Folders Windows needs - Clarify refuses to touch these.
SKIP_FOLDER_NAMES = {
    "$recycle.bin", "recycle.bin", "system volume information", "pagefile.sys",
    "hiberfil.sys", "swapfile.sys", "windows", "program files",
    "program files (x86)", "programdata", "boot", "efi", "recovery",
}

# Which extensions count as which "File Category".
FILE_CATEGORIES = {
    "Images": {"jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "tiff", "ico"},
    "Documents": {"pdf", "docx", "doc", "txt", "rtf", "odt", "xlsx", "csv", "pptx"},
    "Audio": {"mp3", "wav", "flac", "aac", "ogg", "m4a"},
    "Video": {"mp4", "mkv", "avi", "mov", "wmv", "flv", "webm"},
    "Archives": {"zip", "rar", "7z", "tar", "gz", "bz2", "iso"},
    "Code": {"py", "js", "html", "css", "cpp", "c", "cs", "java", "json", "xml", "sh"},
}


class OperationCancelled(Exception):
    """Raised inside the worker when you press Stop. It is not an error - it just unwinds the work."""


def _noop(_message):
    """A logger that does nothing (used when verbose output or the error log is switched off)."""


# =====================================================================================
# STEP 6 - SMALL HELPER FUNCTIONS (each does exactly one little job)
# =====================================================================================
def check_admin_privileges():
    """True if Clarify is running as Administrator (needed to change file permissions)."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except (AttributeError, OSError):
        return False


def normalize(path):
    """One standard spelling of a path (absolute, correct case) so two paths can be compared fairly."""
    return os.path.normcase(os.path.abspath(path))


def _path_parts_below(path, source):
    """The folder/file names of `path` that lie BELOW `source` (the source folder's own name is NOT
    included). If `path` is not under `source` (or on another drive) only its own name is returned."""
    try:
        rel = os.path.relpath(path, source)
    except ValueError:                                         # different drives cannot be compared
        return [os.path.basename(path)]
    if rel == ".":
        return []
    if rel.startswith(".."):
        return [os.path.basename(path)]
    return [part for part in rel.split(os.sep) if part]


def should_skip_system_paths(path, protected=(), keywords=(), source=None):
    """True if `path` is a Windows system location, sits inside one of your Protected Folders / exempt
    paths, or (when `keywords` are given) has an exempt keyword in its own name.
    When `source` is given, EVERY name between the source and `path` is checked against the keywords and
    the system-folder names, so a folder that matches excludes its whole subtree.
    NOTE: the source folder's own name is deliberately never matched against keywords - keywords are
    matched on names below the source - so a source called 'SilentChuckle-inbox' does not silently
    exclude the entire run."""
    path_lower = path.lower()
    if os.path.basename(path_lower) in SKIP_FOLDER_NAMES:
        return True
    keywords = [k.lower() for k in keywords if k and k.strip()]   # an empty keyword would match every name
    if keywords:
        names = [n.lower() for n in _path_parts_below(path, source)] if source else [os.path.basename(path_lower)]
        if any(word in name for name in names for word in keywords):
            return True
    if source and any(n.lower() in SKIP_FOLDER_NAMES for n in _path_parts_below(path, source)):
        return True
    if "system volume information" in path_lower or "recycle.bin" in path_lower:
        return True
    norm = normalize(path)
    for folder in protected:
        try:
            # commonpath == folder means "path is inside folder"
            if os.path.commonpath([norm, folder]) == folder:
                return True
        except ValueError:          # different drives (C: vs D:) cannot share a path - so not inside
            continue
    return False


def walk_unprotected(directory, protected, keywords=()):
    """Like os.walk, but silently skips system, protected and exempt files/folders (exempt keywords are
    matched against file and folder names below `directory`). A skipped folder is never entered, so
    everything under it is skipped too. Yields (folder, [file names])."""
    for root, dirs, files in os.walk(directory):
        if should_skip_system_paths(root, protected, keywords, directory):
            dirs.clear()                                   # do not descend any deeper into this folder
            continue
        dirs[:] = [d for d in dirs
                   if not should_skip_system_paths(os.path.join(root, d), protected, keywords, directory)]
        yield root, [f for f in files
                     if not should_skip_system_paths(os.path.join(root, f), protected, keywords, directory)]


def current_user_principal():
    """The Windows account name in the form icacls wants, e.g. 'MYPC\\silent'."""
    user = getpass.getuser()
    domain = os.environ.get("USERDOMAIN", "")
    return f"{domain}\\{user}" if domain else user


def grant_my_access(path):
    """Give THIS Windows account Full control of `path` (fixes 'access denied' on old/other-user files).
    Security note: the old version granted 'Everyone', which exposed files to every account on the
    PC. Granting only yourself fixes the same problem without that risk."""
    try:
        result = subprocess.run(["icacls", path, "/grant", f"{current_user_principal()}:F", "/C"],
                                capture_output=True, text=True, timeout=ICACLS_TIMEOUT_SECONDS,
                                creationflags=NO_WINDOW)
        return result.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def set_access_recursive(directory, protected, log=_noop, should_stop=lambda: False, dry_run=False, keywords=()):
    """Apply grant_my_access to a folder and everything in it. Returns (changed, errors)."""
    changed = errors = 0
    for root, files in walk_unprotected(directory, protected, keywords):
        for path in [root] + [os.path.join(root, f) for f in files]:
            if should_stop():
                raise OperationCancelled
            if dry_run:
                log(f"[preview] would grant access: {path}")
                changed += 1
            elif grant_my_access(path):
                changed += 1
                log(f"Access: {path}")
            else:
                errors += 1
                log(f"Access FAILED: {path}")
    return changed, errors


def get_file_hash(file_path):
    """SHA-256 'fingerprint' of a file's contents: two files with the same fingerprint are identical.
    Returns None if the file cannot be read."""
    try:
        with open(file_path, "rb") as f:
            if hasattr(hashlib, "file_digest"):               # Python 3.11+: fast built-in helper
                return hashlib.file_digest(f, "sha256").hexdigest()
            sha256 = hashlib.sha256()
            for block in iter(lambda: f.read(HASH_BLOCK_SIZE), b""):
                sha256.update(block)
            return sha256.hexdigest()
    except OSError:
        return None


def get_file_extension(filename):
    """'Photo.JPG' -> 'jpg'. Files with no extension are called 'no-extension'."""
    ext = Path(filename).suffix[1:].lower()
    return ext if ext else "no-extension"


def get_file_category(ext):
    """'jpg' -> 'Images'. Anything unknown is 'Other'."""
    for category, exts in FILE_CATEGORIES.items():
        if ext in exts:
            return category
    return "Other"


def get_size_range(size_bytes):
    """Turn a size in bytes into a friendly bucket name."""
    mb = size_bytes / (1024 * 1024)
    if mb < 1:
        return "under 1MB"
    if mb < 100:
        return "1MB - 100MB"
    if mb < 1000:
        return "100MB - 1GB"
    return "over 1GB"


def get_age_bucket(modified, now=None):
    """How old is a file? (Merged in from the retired 'archive old files' / 'downloads cleaner' tools.)"""
    age = (now or datetime.now()) - modified
    if age <= timedelta(days=30):
        return "1 - Last 30 days"
    if age <= timedelta(days=90):
        return "2 - 30 to 90 days"
    if age <= timedelta(days=365):
        return "3 - 90 days to 1 year"
    return "4 - Over 1 year"


def compute_nested_folder_path(file_path, base_dest_dir, active_criteria_keys):
    """Build the destination folder for one file from the ticked criteria, outermost first.
    Example with ['category', 'year']:  <dest>/Images/2026"""
    if not active_criteria_keys:
        return base_dest_dir                                  # no criteria -> everything goes straight in

    ext = get_file_extension(file_path)
    try:
        dt = datetime.fromtimestamp(os.path.getmtime(file_path))   # "modified" date of the file
    except OSError:
        dt = datetime.now()
    try:
        size = os.path.getsize(file_path)
    except OSError:
        size = 0

    # Each entry is a tiny recipe that is only run if that criterion was actually ticked.
    parts = {
        "ext": lambda: ext,
        "year": lambda: dt.strftime("%Y"),
        "month": lambda: dt.strftime("%m-%B"),
        "day": lambda: dt.strftime("%d"),
        "hour": lambda: dt.strftime("%H_00"),
        "category": lambda: get_file_category(ext),
        "day_of_week": lambda: dt.strftime("%A"),
        "quarter": lambda: f"Q{(dt.month - 1) // 3 + 1}",
        "size_range": lambda: get_size_range(size),
        "age": lambda: get_age_bucket(dt),
    }
    return os.path.join(base_dest_dir, *(parts[key]() for key in active_criteria_keys if key in parts))


def build_timestamp_name(file_path, mode, original_name, counter=0):
    """New file name that contains the file's creation date/time (merged in from 'Fast-With-Rename').
    mode 'Full'   -> 05-10-2026--14-30-09.jpg
    mode 'Prefix' -> 05-10-2026--14-30-09_holiday.jpg
    mode 'Suffix' -> holiday_05-10-2026--14-30-09.jpg
    counter > 0 adds '-(1)', '-(2)' ... so two files from the same second never collide."""
    try:
        stamp = os.path.getctime(file_path)                   # creation time on Windows
    except OSError:
        try:
            stamp = os.path.getmtime(file_path)               # fall back to "modified"
        except OSError:
            stamp = datetime.now().timestamp()
    time_text = datetime.fromtimestamp(stamp).strftime("%d-%m-%Y--%H-%M-%S")
    if counter > 0:
        time_text = f"{time_text}-({counter})"
    stem, extension = Path(original_name).stem, Path(original_name).suffix
    if mode == "Prefix":
        new_stem = f"{time_text}_{stem}"
    elif mode == "Suffix":
        new_stem = f"{stem}_{time_text}"
    else:                                                     # "Full" (also the safe default)
        new_stem = time_text
    return f"{new_stem}{extension}"


def choose_target_path(file_path, target_folder, rename_mode):
    """Decide the final path inside `target_folder`: the original name, or a unique timestamp name."""
    original = os.path.basename(file_path)
    if rename_mode not in RENAME_MODES:
        return os.path.join(target_folder, original)
    counter = 0
    while True:                                               # keep trying -(1), -(2) ... until the name is free
        candidate = os.path.join(target_folder, build_timestamp_name(file_path, rename_mode, original, counter))
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def _is_link(path):
    """True for symbolic links and junctions (we never delete those as 'empty folders')."""
    return os.path.islink(path) or getattr(os.path, "isjunction", lambda _p: False)(path)


def remove_empty_dirs(path, protected=(), log=_noop, dry_run=False, keywords=()):
    """Delete folders that have nothing in them (never system/protected/exempt ones). Returns how many.
    Folders excluded by a keyword, an exempt path or a protected path are never entered, so nothing
    below them is removed. In preview mode folders that would only hold other removed folders count too."""
    removed = 0
    # Phase 1: collect candidate folders top-down, PRUNING excluded folders so their subtree is never seen.
    candidates = []
    for root, dirs, _files in os.walk(path):
        if should_skip_system_paths(root, protected, keywords, path):
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if not should_skip_system_paths(os.path.join(root, d), protected, keywords, path)
                   and not _is_link(os.path.join(root, d))]
        candidates.extend(os.path.join(root, d) for d in dirs)
    # Phase 2: deepest first, so a folder that only held empty folders becomes empty itself.
    candidates.sort(key=lambda p: p.count(os.sep), reverse=True)
    gone = set()
    for dir_path in candidates:
        try:
            entries = [e for e in os.listdir(dir_path) if os.path.join(dir_path, e) not in gone]
            if entries:
                continue
            if dry_run:
                log(f"[preview] would remove empty folder: {dir_path}")
            else:
                os.rmdir(dir_path)                            # rmdir only works on EMPTY folders - a safety net
                log(f"Removed empty: {dir_path}")
            gone.add(dir_path)
            removed += 1
        except OSError:
            pass
    return removed


def remove_empty_parents(start_dir, stop_dir):
    """After moving a file out, delete its folder (and parents) if they are now empty - but never
    go above `stop_dir` (the source folder itself)."""
    stop = normalize(stop_dir)
    current = start_dir
    while normalize(current) != stop and os.path.dirname(current) != current:
        try:
            if os.listdir(current):
                break                                         # still has something in it - stop climbing
            os.rmdir(current)
        except OSError:
            break
        current = os.path.dirname(current)


def move_file_with_overwrite_check(src, dst, error_log=_noop):
    """Move `src` to `dst` WITHOUT ever overwriting. Returns (final_path, outcome) or (None, 'error').
    outcome is one of: 'moved', 'renamed' (name taken -> got a _N suffix), 'duplicate' (exact copy purged)."""
    try:
        if not os.path.exists(dst):                           # easy case: the name is free
            shutil.move(src, dst)
            return dst, "moved"

        # The name is taken. Different sizes mean the files cannot be identical, so skip the slow hashing.
        same_size = os.path.getsize(src) == os.path.getsize(dst)
        if same_size:
            src_hash, dst_hash = get_file_hash(src), get_file_hash(dst)
            if src_hash is None or dst_hash is None:
                error_log(f"Could not fingerprint during move: {src} or {dst}, skipped.")
                return None, "error"
            if src_hash == dst_hash:                          # exact copy already there -> delete the extra
                os.remove(src)
                return dst, "duplicate"

        # Different content, same name: find a free name_1, name_2 ...
        base, ext = os.path.splitext(dst)
        counter = 1
        new_dst = f"{base}_{counter}{ext}"
        while os.path.exists(new_dst):
            counter += 1
            new_dst = f"{base}_{counter}{ext}"
        shutil.move(src, new_dst)
        return new_dst, "renamed"
    except OSError as e:
        error_log(f"Error moving file '{src}' -> '{dst}': {e}")
        return None, "error"


# =====================================================================================
# STEP 7 - THE ENGINE: organize every file
# =====================================================================================
def organize_files_with_dedup(source_dir, dest_dir, active_criteria_keys, protected=(),
                              delete_zero_byte=False, remove_emptied_dirs=True,
                              rename_mode=None, dry_run=False,
                              log=_noop, error_log=_noop, should_stop=lambda: False, keywords=()):
    """Walk the source folder and move each file into its place in the destination.
    Returns a dict of counters: moved, skipped, zero_byte_deleted, duplicates_removed."""

    def report(msg):                                          # message goes to the window AND the error log
        log(msg)
        error_log(msg)

    def check_stop():
        if should_stop():
            raise OperationCancelled

    counts = {"moved": 0, "skipped": 0, "zero_byte_deleted": 0, "duplicates_removed": 0}

    for root, names in walk_unprotected(source_dir, protected, keywords):   # (1) visit each folder
        check_stop()
        for name in names:                                        # (2) visit each file in it
            check_stop()
            file_path = os.path.join(root, name)
            try:
                size = os.path.getsize(file_path)
            except OSError as e:
                report(f"Could not read size: {file_path} ({e}), skipped")
                continue

            # (3) optional: empty (0-byte) files are deleted instead of moved
            if delete_zero_byte and size == 0:
                if dry_run:
                    log(f"[preview] would delete zero-byte file: {file_path}")
                    counts["zero_byte_deleted"] += 1
                    continue
                try:
                    os.remove(file_path)
                    counts["zero_byte_deleted"] += 1
                    report(f"Deleted zero-byte: {file_path}")
                except OSError as e:
                    report(f"Failed to delete zero-byte file {file_path}: {e}")
                continue

            # (4) work out where the file belongs (and make that folder)
            try:
                target_folder = compute_nested_folder_path(file_path, dest_dir, active_criteria_keys)
                if not dry_run:
                    os.makedirs(target_folder, exist_ok=True)
            except OSError as e:
                report(f"Error creating target folder for {file_path} ({e})")
                continue

            target_path = choose_target_path(file_path, target_folder, rename_mode)
            if normalize(file_path) == normalize(target_path):    # already exactly where it should be
                counts["skipped"] += 1
                continue

            # (5) preview mode: say what would happen, change nothing
            if dry_run:
                log(f"[preview] {file_path}  ->  {target_path}")
                counts["moved"] += 1
                continue

            # (6) the real move (never overwrites; exact duplicates are purged)
            result_path, outcome = move_file_with_overwrite_check(file_path, target_path, error_log=report)
            if result_path is None:
                continue
            if outcome == "duplicate":
                counts["duplicates_removed"] += 1
                log(f"Duplicate purged: {os.path.basename(file_path)} (identical copy already in {target_folder})")
            else:
                counts["moved"] += 1
                log(f"Processed: {os.path.basename(file_path)} -> {result_path}")

            # (7) tidy: remove the source folder if the move left it empty
            if remove_emptied_dirs:
                remove_empty_parents(os.path.dirname(file_path), source_dir)

    return counts


# =====================================================================================
# STEP 8 - THE WINDOW (everything you see and click)
# =====================================================================================
# The helpers below (THEME, DPI awareness, theme, ScrollFrame, Section) are shared with the other
# SilentChuckle tools; ClarifyGUI is built out of them.
SIGNATURE = "SilentChuckle"

# The license text shown in the "About & License" section (the same text is in the file header).
MIT_LICENSE_TEXT = (
    "MIT License\n\n"
    "Copyright (c) 2026 SilentChuckle\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and "
    "associated documentation files (the \"Software\"), to deal in the Software without restriction, including "
    "without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
    "copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the "
    "following conditions:\n\n"
    "The above copyright notice and this permission notice shall be included in all copies or substantial "
    "portions of the Software.\n\n"
    "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT "
    "LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO "
    "EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER "
    "IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE "
    "USE OR OTHER DEALINGS IN THE SOFTWARE."
)

# The colours of the window in one place, so the whole look can be changed here.
THEME = {
    "bg": "#f3f5f9", "card": "#ffffff", "head": "#e4e9f4", "head_hover": "#d5ddef", "text": "#1d2433",
    "muted": "#6b7488", "accent": "#3563e9", "accent_hover": "#294fc0", "accent_off": "#a9b6e8",
    "border": "#d0d7e6", "log_bg": "#10151f", "log_fg": "#d7e0f2",
    "info": "#eef1fb", "info_text": "#2c3a66", "ok": "#e7f6ec", "ok_text": "#1f6f3d",
    "warn": "#fdecea", "warn_text": "#9c2b1f",
}


# Windows draws Tk windows blurry on high-resolution screens unless the program says it understands scaling.
# This must be called BEFORE the window is created.
def _enable_dpi_awareness():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # not Windows, or an old Windows: nothing to do
        pass


# Give every standard widget the same modern flat look (colours, fonts, padding).
def _apply_theme(root):
    T = THEME
    style = ttk.Style(root)
    try:
        style.theme_use("clam")  # 'clam' is the only built-in theme that lets us colour everything
    except tk.TclError:
        pass
    base = ("Segoe UI", 10)
    root.configure(bg=T["bg"])
    root.option_add("*Font", base)
    style.configure(".", background=T["bg"], foreground=T["text"], font=base, bordercolor=T["border"],
                    lightcolor=T["bg"], darkcolor=T["bg"], focuscolor=T["accent"])
    style.configure("TFrame", background=T["bg"])
    style.configure("Card.TFrame", background=T["card"])
    style.configure("TLabel", background=T["bg"], foreground=T["text"])
    style.configure("Card.TLabel", background=T["card"], foreground=T["text"])
    style.configure("Muted.TLabel", background=T["bg"], foreground=T["muted"])
    style.configure("CardMuted.TLabel", background=T["card"], foreground=T["muted"], font=("Segoe UI", 9))
    style.configure("Title.TLabel", background=T["bg"], font=("Segoe UI", 17, "bold"))
    style.configure("Head.TLabel", background=T["head"], font=("Segoe UI", 10, "bold"), padding=(12, 8))
    style.configure("TButton", background=T["card"], padding=(14, 6), relief="flat", borderwidth=1)
    style.map("TButton", background=[("active", T["head_hover"]), ("disabled", T["bg"])],
              foreground=[("disabled", T["muted"])])
    style.configure("Accent.TButton", background=T["accent"], foreground="#ffffff", borderwidth=0)
    style.map("Accent.TButton", background=[("active", T["accent_hover"]), ("disabled", T["accent_off"])],
              foreground=[("disabled", "#ffffff")])
    style.configure("TCheckbutton", background=T["bg"])
    style.configure("Card.TCheckbutton", background=T["card"])
    style.configure("TEntry", fieldbackground="#ffffff", padding=4)
    style.configure("TCombobox", fieldbackground="#ffffff", padding=4)
    style.configure("Horizontal.TProgressbar", troughcolor=T["head"], background=T["accent"], thickness=10,
                    borderwidth=0)


# A scrollable page. Everything is placed on `.inner`; scrollbars appear whenever the content is bigger than
# the window, in either direction, and the mouse wheel scrolls it (Shift + wheel scrolls sideways).
class ScrollFrame(ttk.Frame):
    def __init__(self, parent, on_resize=None):
        super().__init__(parent)
        self._on_resize = on_resize
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=THEME["bg"], borderwidth=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.hbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vbar.set, xscrollcommand=self.hbar.set)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")  # the vertical bar is always there (keeps the layout stable)
        self.hbar.grid(row=1, column=0, sticky="ew")
        self.inner = ttk.Frame(self.canvas, padding=(16, 12, 16, 12))
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda _e: self.refresh())
        self.canvas.bind("<Configure>", lambda _e: self.refresh())
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._wheel_sideways)

    # Recalculate how big the page is and whether the horizontal scrollbar is needed.
    def refresh(self):
        need_w, need_h = self.inner.winfo_reqwidth(), self.inner.winfo_reqheight()
        view_w, view_h = self.canvas.winfo_width(), self.canvas.winfo_height()
        width = max(view_w, need_w)  # the page is at least as wide as the window, wider if its content needs it
        self.canvas.itemconfigure(self._window, width=width)
        self.canvas.configure(scrollregion=(0, 0, width, max(view_h, need_h)))
        if need_w > view_w + 1:
            self.hbar.grid()
        else:
            self.hbar.grid_remove()
        if self._on_resize:
            self._on_resize(view_w)

    # Mouse wheel over the page scrolls the page - except over the log (or any list), which scrolls itself.
    def _wheel(self, event):
        w = event.widget
        if isinstance(w, (tk.Text, tk.Listbox, ttk.Treeview)) or not str(w).startswith(str(self)):
            return
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _wheel_sideways(self, event):
        if str(event.widget).startswith(str(self)):
            self.canvas.xview_scroll(-1 if event.delta > 0 else 1, "units")


# A collapsible section: a clickable title bar (> when closed, v when open) above a body that can be hidden.
class Section(ttk.Frame):
    def __init__(self, parent, title, opened=True, on_toggle=None):
        super().__init__(parent)
        self.title, self.opened, self._on_toggle = title, opened, on_toggle
        self.head = ttk.Label(self, style="Head.TLabel", cursor="hand2", takefocus=True)
        self.head.pack(fill="x")
        self.body = ttk.Frame(self, style="Card.TFrame", padding=(14, 10))
        self.head.bind("<Button-1>", lambda _e: self.toggle())
        self.head.bind("<Return>", lambda _e: self.toggle())
        self.head.bind("<space>", lambda _e: self.toggle())
        self.head.bind("<Enter>", lambda _e: self.head.configure(background=THEME["head_hover"]))
        self.head.bind("<Leave>", lambda _e: self.head.configure(background=THEME["head"]))
        self._apply()

    def toggle(self):
        self.opened = not self.opened
        self._apply()
        if self._on_toggle:
            self._on_toggle()

    # Show or hide the body and update the arrow in the title.
    def _apply(self):
        self.head.configure(text=("v   " if self.opened else ">   ") + self.title)
        if self.opened:
            self.body.pack(fill="x")
        else:
            self.body.pack_forget()


def flash_taskbar(window):
    """Flash this window's taskbar button to draw attention, but only if it is not the one in focus
    right now (no point flashing something you're already looking at). Windows stops the flashing on
    its own as soon as the window is brought to the front - nothing else has to call it off."""
    try:
        import ctypes
        if window.focus_displayof() is not None:          # some widget in this window already has focus
            return
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())

        class FLASHWINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("hwnd", ctypes.c_void_p), ("dwFlags", ctypes.c_uint),
                        ("uCount", ctypes.c_uint), ("dwTimeout", ctypes.c_uint)]
        FLASHW_TRAY, FLASHW_TIMERNOFG = 0x00000002, 0x0000000C
        info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, FLASHW_TRAY | FLASHW_TIMERNOFG, 0, 0)
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
    except Exception:
        pass                                               # not on Windows, or no window handle yet - skip quietly


class Banner(ttk.Frame):
    """A message bar built into the window itself, in place of a separate pop-up dialog. show() displays
    text in the right color for its kind and an optional Yes/No pair of buttons for a question that would
    otherwise have been a messagebox.askyesno; ok() is the plain case with just a Dismiss button."""
    KIND_STYLE = {"info": ("info", "info_text"), "ok": ("ok", "ok_text"), "warn": ("warn", "warn_text")}

    def __init__(self, parent):
        super().__init__(parent)
        self._bg_key = None
        self._anchor = None                                  # set via attach(): keeps the banner pinned at top
        self.label = tk.Label(self, text="", anchor="w", justify="left", wraplength=1000, padx=12, pady=8)
        self.label.pack(side="left", fill="x", expand=True)
        self.btns = ttk.Frame(self)
        self.btns.pack(side="right", padx=8)
        self.pack_forget()                                  # hidden until there is something to say

    def attach(self, before_widget):
        """Remember which widget the banner should stay above, so repeated show()/ask() calls always
        land in the same place (the top of the window) instead of drifting to wherever was packed last."""
        self._anchor = before_widget

    def _set_kind(self, kind):
        bg_key, fg_key = self.KIND_STYLE.get(kind, self.KIND_STYLE["info"])
        self.label.configure(background=THEME[bg_key], foreground=THEME[fg_key])
        self.configure(style="TFrame")

    def _clear_buttons(self):
        for w in self.btns.winfo_children():
            w.destroy()

    def show(self, text, kind="info"):
        """A plain message with just a Dismiss button (replaces messagebox.showinfo/showerror)."""
        self._set_kind("warn" if kind == "error" else kind)
        self.label.configure(text=text)
        self._clear_buttons()
        ttk.Button(self.btns, text="Dismiss", command=self.hide).pack(side="left")
        self.pack_forget()
        self.pack(fill="x", side="top", before=self._anchor)
        flash_taskbar(self.winfo_toplevel())

    def ask(self, text, on_yes, on_no=None, yes_text="Continue", no_text="Cancel"):
        """A question with its own Yes/No buttons, built into the window (replaces messagebox.askyesno)."""
        self._set_kind("info")
        self.label.configure(text=text)
        self._clear_buttons()

        def _choose(fn):
            self.hide()
            if fn:
                fn()
        ttk.Button(self.btns, text=no_text, command=lambda: _choose(on_no)).pack(side="right", padx=(6, 0))
        ttk.Button(self.btns, text=yes_text, style="Accent.TButton",
                   command=lambda: _choose(on_yes)).pack(side="right")
        self.pack_forget()
        self.pack(fill="x", side="top", before=self._anchor)
        flash_taskbar(self.winfo_toplevel())

    def hide(self):
        self.pack_forget()


class ClarifyGUI:
    def __init__(self, root, source="", dest=""):
        self.root = root
        self.root.title("CLARIFY - File Organization Tool")
        self.root.resizable(True, True)

        # tk.*Var objects are "boxes" that stay linked to a widget: change the box, the widget updates.
        self.source_dir = tk.StringVar()
        self.dest_dir = tk.StringVar()
        self.delete_zero_byte = tk.BooleanVar(value=False)
        self.delete_empty_dirs = tk.BooleanVar(value=True)
        self.grant_access = tk.BooleanVar(value=False)
        self.verbose = tk.BooleanVar(value=True)
        self.enable_error_log = tk.BooleanVar(value=False)
        self.dry_run = tk.BooleanVar(value=False)
        self.enable_rename = tk.BooleanVar(value=False)
        self.rename_mode = tk.StringVar(value="Full")
        self.protected_folders = []
        self.exempt_paths = []                                    # folders/files that are never touched
        self.exempt_keywords = []                                 # any file/folder name containing one is never touched
        self.error_log_path = str(DEFAULT_ERROR_LOG)

        self.criteria_vars = {name: tk.BooleanVar(value=False) for name in SORT_CRITERIA_MAP}
        self.active_criteria_order = []                           # the order the user wants folders nested in

        self._stop_event = threading.Event()                      # flipped by the Stop button
        self._ui_queue = queue.Queue()                            # worker thread -> window messages
        self._error_log_lock = threading.Lock()                   # one writer to the error log at a time

        self.create_widgets()
        self._poll_ui_queue()
        self.load_config()
        if source:                                                # --source/--dest from the command line win
            self.source_dir.set(source)
        if dest:
            self.dest_dir.set(dest)

    # ---- building the window ------------------------------------------------------------------
    def create_widgets(self):
        """Build the page: a scrollable area holding one collapsible Section per segment."""
        _apply_theme(self.root)
        # Radio buttons inside a section need the white "card" background too.
        ttk.Style(self.root).configure("Card.TRadiobutton", background=THEME["card"])
        self.banner = Banner(self.root)
        self.scroller = ScrollFrame(self.root, on_resize=self._rewrap)
        self.scroller.pack(fill=tk.BOTH, expand=True)
        self.banner.attach(self.scroller)
        page = self.scroller.inner
        ttk.Label(page, text="CLARIFY - File Organization Tool", style="Title.TLabel").pack(anchor="w")
        self.desc = ttk.Label(page, text="Organize files with dynamic multi-level folder grouping",
                              style="Muted.TLabel", justify="left", wraplength=700)
        self.desc.pack(anchor="w", pady=(2, 10))

        def section(title, opened=True):
            sec = Section(page, title, opened, self._grow_if_needed)
            sec.pack(fill="x", pady=4)
            return sec.body

        # -- source / destination / protected folders
        dir_frame = section("Directories")
        dir_frame.columnconfigure(1, weight=1)
        ttk.Label(dir_frame, text="Source Directory:", style="Card.TLabel").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(dir_frame, textvariable=self.source_dir, width=60).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(dir_frame, text="Browse", command=self.browse_source).grid(row=0, column=2, pady=5)
        ttk.Label(dir_frame, text="Destination Directory:", style="Card.TLabel").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(dir_frame, textvariable=self.dest_dir, width=60).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(dir_frame, text="Browse", command=self.browse_dest).grid(row=1, column=2, pady=5)
        ttk.Label(dir_frame, text="(Leave blank to use source)", style="CardMuted.TLabel").grid(
            row=2, column=1, sticky=tk.W)
        ttk.Label(dir_frame, text="Protected Folders:", style="Card.TLabel").grid(row=3, column=0, sticky=tk.W, pady=5)
        protected_btn_frame = ttk.Frame(dir_frame, style="Card.TFrame")
        protected_btn_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(protected_btn_frame, text="Add Folder", command=self.add_protected_folder).pack(side=tk.LEFT)
        ttk.Button(protected_btn_frame, text="View/Remove", command=self.manage_protected_folders).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(dir_frame, text="Exempt from Sorting:", style="Card.TLabel").grid(row=4, column=0, sticky=tk.W, pady=5)
        exempt_btn_frame = ttk.Frame(dir_frame, style="Card.TFrame")
        exempt_btn_frame.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(exempt_btn_frame, text="Add Folder", command=self.add_exempt_folder).pack(side=tk.LEFT)
        ttk.Button(exempt_btn_frame, text="Add File(s)", command=self.add_exempt_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(exempt_btn_frame, text="Add Keyword", command=self.add_exempt_keyword).pack(side=tk.LEFT)
        ttk.Button(exempt_btn_frame, text="View/Remove", command=self.manage_exemptions).pack(side=tk.LEFT, padx=5)
        ttk.Label(dir_frame, text="(Keyword, e.g. SilentChuckle: any file or folder with it in its name is left "
                                  "alone, together with everything inside it)",
                  style="CardMuted.TLabel").grid(row=5, column=1, sticky=tk.W)

        # -- always-visible list of everything that is exempt (keywords, folders, files)
        exempt_frame = section("Currently Exempt (will not be touched)")
        exempt_scroll = ttk.Scrollbar(exempt_frame)
        exempt_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.exempt_listbox = tk.Listbox(exempt_frame, height=4, yscrollcommand=exempt_scroll.set, relief="flat",
                                         highlightthickness=1, highlightbackground=THEME["border"])
        self.exempt_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        exempt_scroll.config(command=self.exempt_listbox.yview)
        ttk.Button(exempt_frame, text="Remove Selected", command=self.remove_selected_exemption).pack(
            side=tk.LEFT, padx=5, anchor=tk.N)
        self.refresh_exempt_listbox()

        # -- the nesting criteria (tick boxes on the left, their order on the right)
        sorting_frame = section("Nested Folder Hierarchy")
        chk_container = ttk.Frame(sorting_frame, style="Card.TFrame")
        chk_container.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        ttk.Label(chk_container, text="Select Criteria:", style="Card.TLabel",
                  font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        for name in SORT_CRITERIA_MAP:
            ttk.Checkbutton(chk_container, text=name, variable=self.criteria_vars[name], style="Card.TCheckbutton",
                            command=lambda n=name: self.on_criteria_toggle(n)).pack(anchor=tk.W, pady=1)
        order_container = ttk.Frame(sorting_frame, style="Card.TFrame")
        order_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(order_container, text="Active Nesting Sequence (Top = Outer Folder):", style="Card.TLabel",
                  font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        list_btn_frame = ttk.Frame(order_container, style="Card.TFrame")
        list_btn_frame.pack(fill=tk.BOTH, expand=True)
        self.order_listbox = tk.Listbox(list_btn_frame, height=7, selectmode=tk.SINGLE, relief="flat",
                                        highlightthickness=1, highlightbackground=THEME["border"])
        self.order_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        btn_box = ttk.Frame(list_btn_frame, style="Card.TFrame")
        btn_box.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(btn_box, text="\u25b2 Move Up", command=lambda: self.move_criterion(-1)).pack(fill=tk.X, pady=2)
        ttk.Button(btn_box, text="\u25bc Move Down", command=lambda: self.move_criterion(1)).pack(fill=tk.X, pady=2)
        self.preview_label = ttk.Label(order_container, style="CardMuted.TLabel")
        self.preview_label.pack(anchor=tk.W, pady=(8, 0))
        self.update_preview()

        # -- cleanup / safety options
        options_frame = section("Options")
        ttk.Checkbutton(options_frame, text="PREVIEW ONLY - show what would happen, change nothing",
                        variable=self.dry_run, style="Card.TCheckbutton").pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Delete zero-byte files", variable=self.delete_zero_byte,
                        style="Card.TCheckbutton").pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Delete empty directories", variable=self.delete_empty_dirs,
                        style="Card.TCheckbutton").pack(anchor=tk.W, pady=2)
        access_frame = ttk.Frame(options_frame, style="Card.TFrame")
        access_frame.pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(access_frame, text="Grant MY account full access to all files/folders",
                        variable=self.grant_access, style="Card.TCheckbutton").pack(side=tk.LEFT)
        ttk.Label(access_frame, text="(Requires Admin)", style="CardMuted.TLabel", foreground="#c0392b").pack(
            side=tk.LEFT, padx=5)
        ttk.Checkbutton(options_frame, text="Verbose output (show detailed progress)", variable=self.verbose,
                        style="Card.TCheckbutton").pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Enable Error Log", variable=self.enable_error_log,
                        style="Card.TCheckbutton").pack(anchor=tk.W, pady=2)

        # -- timestamp renaming (its own section)
        rename_frame = section("Timestamp Renaming")
        ttk.Checkbutton(rename_frame, text="Rename files with their creation date/time (Day-Month-Year--Hour-Min-Sec)",
                        variable=self.enable_rename, style="Card.TCheckbutton").pack(anchor=tk.W)
        mode_frame = ttk.Frame(rename_frame, style="Card.TFrame")
        mode_frame.pack(anchor=tk.W, pady=2)
        for mode in RENAME_MODES:
            ttk.Radiobutton(mode_frame, text={"Full": "Full Rename", "Prefix": "Prefix", "Suffix": "Suffix"}[mode],
                            variable=self.rename_mode, value=mode, style="Card.TRadiobutton").pack(side=tk.LEFT, padx=5)
        ttk.Label(rename_frame, text="Note: renamed files always get unique names, so duplicate detection by "
                                     "name is skipped.", style="CardMuted.TLabel").pack(anchor=tk.W)

        # -- buttons, progress log, status line
        progress_frame = section("Progress")
        button_frame = ttk.Frame(progress_frame, style="Card.TFrame")
        button_frame.pack(fill=tk.X, pady=(0, 8))
        self.start_button = ttk.Button(button_frame, text="Start Organization", style="Accent.TButton",
                                       command=self.start_operation)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_operation, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Config", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Check Dependencies", command=self.check_dependencies_ui).pack(
            side=tk.RIGHT, padx=5)
        self.progress_text = scrolledtext.ScrolledText(progress_frame, height=12, width=80, state=tk.DISABLED,
                                                       wrap=tk.WORD, bg=THEME["log_bg"], fg=THEME["log_fg"],
                                                       insertbackground=THEME["log_fg"], relief="flat",
                                                       font=("Consolas", 10), padx=8, pady=6)
        self.progress_text.pack(fill=tk.BOTH, expand=True)
        self.status_label = ttk.Label(progress_frame, text="Ready", style="CardMuted.TLabel")
        self.status_label.pack(anchor=tk.W, pady=(6, 0))

        # -- about & license
        about = section("About & License", opened=False)
        ttk.Label(about, text=f"Written by {SIGNATURE}", style="Card.TLabel",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(about, text=MIT_LICENSE_TEXT, style="CardMuted.TLabel", justify="left",
                  wraplength=680).pack(anchor="w", pady=(6, 0))
        ttk.Label(page, text=f"{SIGNATURE}  |  MIT License", style="Muted.TLabel").pack(anchor="e", pady=(8, 0))
        self.root.after(10, self._fit_window)

    # ---- window size --------------------------------------------------------------------------
    def _fit_window(self):
        """Size the window to its content, never bigger than ~94% x 90% of the screen, and centre it.
        The page scrolls if the content is bigger than the window."""
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w = min(max(self.scroller.inner.winfo_reqwidth() + 40, 760), int(sw * 0.94))
        h = min(max(self.scroller.inner.winfo_reqheight() + 20, 520), int(sh * 0.90))
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{max((sh - h) // 3, 0)}")
        self.root.minsize(min(420, sw), min(320, sh))

    def _grow_if_needed(self):
        """After a section opens or closes: widen the window (never narrow it) if the content needs it."""
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        need = self.scroller.inner.winfo_reqwidth() + 40
        if need > self.root.winfo_width() and need <= int(sw * 0.96):
            self.root.geometry(f"{need}x{self.root.winfo_height()}")

    def _rewrap(self, view_w):
        """Keep the subtitle wrapped to the window width."""
        self.desc.configure(wraplength=max(view_w - 60, 280))

    # ---- the "nesting order" list -------------------------------------------------------------
    def on_criteria_toggle(self, name):
        """A criterion was ticked/unticked: add it to (or remove it from) the ordered list."""
        if self.criteria_vars[name].get():
            if name not in self.active_criteria_order:
                self.active_criteria_order.append(name)
        elif name in self.active_criteria_order:
            self.active_criteria_order.remove(name)
        self.refresh_criteria_listbox()

    def move_criterion(self, offset):
        """Swap the selected criterion with its neighbour (offset -1 = up, +1 = down)."""
        sel = self.order_listbox.curselection()
        if not sel:
            return
        idx, new_idx = sel[0], sel[0] + offset
        if 0 <= new_idx < len(self.active_criteria_order):
            order = self.active_criteria_order
            order[idx], order[new_idx] = order[new_idx], order[idx]
            self.refresh_criteria_listbox()
            self.order_listbox.selection_set(new_idx)

    def refresh_criteria_listbox(self):
        self.order_listbox.delete(0, tk.END)
        for item in self.active_criteria_order:
            self.order_listbox.insert(tk.END, item)
        self.update_preview()

    def update_preview(self):
        """Show an example of the folder path your choices will create."""
        if not self.active_criteria_order:
            self.preview_label.config(text="Folder Structure Preview: / (Root Directory Only)")
        else:
            preview_path = " / ".join(f"[{c}]" for c in self.active_criteria_order)
            self.preview_label.config(text=f"Folder Structure Preview: / {preview_path} / [filename]")

    # ---- thread-safe messaging ----------------------------------------------------------------
    # Tkinter windows may only be touched from the main thread, but the work runs in a background
    # thread. So the worker drops messages into a queue and the window empties it every 100 ms.
    def _poll_ui_queue(self):
        while True:
            try:
                func, args = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            func(*args)
        self.root.after(UI_POLL_MS, self._poll_ui_queue)

    def _on_ui(self, func, *args):
        if threading.current_thread() is threading.main_thread():
            func(*args)
        else:
            self._ui_queue.put((func, args))

    def log_message(self, message):
        self._on_ui(self._append_progress, f"{message}\n")

    def _append_progress(self, text):
        self.progress_text.config(state=tk.NORMAL)
        self.progress_text.insert(tk.END, text)
        self.progress_text.see(tk.END)
        self.progress_text.config(state=tk.DISABLED)

    def update_status(self, message):
        self._on_ui(lambda: self.status_label.config(text=message))

    def make_error_logger(self, enabled, path):
        """Return a function that appends a timestamped line to the error log (or does nothing)."""
        if not enabled:
            return _noop

        def write(message):
            try:
                with self._error_log_lock, open(path, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().isoformat()} {message}\n")
            except OSError as e:
                self.log_message(f"Failed to write to error log: {e}")
        return write

    # ---- folder pickers -----------------------------------------------------------------------
    def browse_source(self):
        directory = filedialog.askdirectory(title="Select Source Directory")
        if directory:
            self.source_dir.set(directory)

    def browse_dest(self):
        directory = filedialog.askdirectory(title="Select Destination Directory")
        if directory:
            self.dest_dir.set(directory)

    def add_protected_folder(self):
        directory = filedialog.askdirectory(title="Select Protected Folder")
        if not directory:
            return
        abs_path = os.path.abspath(directory)
        if abs_path in self.protected_folders:
            self.banner.show("This folder is already in the protected list.", "info")
        else:
            self.protected_folders.append(abs_path)
            self.banner.show(f"Protected folder added:\n{abs_path}", "ok")

    def manage_protected_folders(self):
        if not self.protected_folders:
            self.banner.show("No protected folders have been added.", "info")
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Manage Protected Folders")
        dialog.geometry("600x400")
        ttk.Label(dialog, text="Protected Folders:", font=("Arial", 10, "bold")).pack(pady=10)
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, height=15)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        for folder in self.protected_folders:
            listbox.insert(tk.END, folder)
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        def remove_selected():
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                folder = self.protected_folders.pop(idx)
                listbox.delete(idx)
                self.banner.show(f"Removed:\n{folder}", "ok")

        ttk.Button(btn_frame, text="Remove Selected", command=remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    # ---- exemptions: files, folders and keywords that are never touched -------------------------
    def _exempt_entries(self):
        """Everything exempt, as (kind, value) pairs - keywords first, then folders/files."""
        return ([("Keyword", k) for k in self.exempt_keywords]
                + [("Folder" if os.path.isdir(p) else "File", p) for p in self.exempt_paths])

    def refresh_exempt_listbox(self):
        self.exempt_listbox.delete(0, tk.END)
        for kind, value in self._exempt_entries():
            self.exempt_listbox.insert(tk.END, f"[{kind}] {value}")

    def remove_selected_exemption(self):
        selection = self.exempt_listbox.curselection()
        if selection:
            kind, value = self._exempt_entries()[selection[0]]
            (self.exempt_keywords if kind == "Keyword" else self.exempt_paths).remove(value)
            self.refresh_exempt_listbox()

    def add_exempt_folder(self):
        directory = filedialog.askdirectory(title="Select Folder to Exempt")
        if directory:
            self._add_exempt_paths([directory])

    def add_exempt_files(self):
        files = filedialog.askopenfilenames(title="Select File(s) to Exempt")
        if files:
            self._add_exempt_paths(files)

    def _add_exempt_paths(self, paths):
        added = 0
        for p in paths:
            abs_path = os.path.abspath(p)
            if abs_path not in self.exempt_paths:
                self.exempt_paths.append(abs_path)
                added += 1
        self.refresh_exempt_listbox()
        self.banner.show(f"Added {added} exempt item(s); {len(paths) - added} already listed.", "ok")

    def add_exempt_keyword(self):
        text = simpledialog.askstring(
            "Exempt Keyword",
            "Any file or folder whose name contains this word is left alone (not case-sensitive).\n"
            "Separate several keywords with commas.", parent=self.root)
        if not text:
            return
        for word in (w.strip() for w in text.split(",")):
            if word and word.lower() not in [k.lower() for k in self.exempt_keywords]:
                self.exempt_keywords.append(word)
        self.refresh_exempt_listbox()

    def manage_exemptions(self):
        if not self.exempt_paths and not self.exempt_keywords:
            self.banner.show("Nothing has been exempted yet.", "info")
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Manage Exemptions")
        dialog.geometry("600x400")
        ttk.Label(dialog, text="Exempt from sorting:", font=("Arial", 10, "bold")).pack(pady=10)
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, height=15)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        entries = [("Keyword", k) for k in self.exempt_keywords] + [("Path", p) for p in self.exempt_paths]
        for kind, value in entries:
            listbox.insert(tk.END, f"[{kind}] {value}")

        def remove_selected():
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                kind, value = entries.pop(idx)
                (self.exempt_keywords if kind == "Keyword" else self.exempt_paths).remove(value)
                listbox.delete(idx)
                self.refresh_exempt_listbox()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Remove Selected", command=remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    # ---- saving / loading your choices --------------------------------------------------------
    def load_config(self):
        """Restore the choices saved last time (silently ignores a missing or damaged file)."""
        if not CONFIG_FILE.exists():
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(data, dict):                            # a damaged file that is not a settings object
            return

        def text_list(key):                                       # only keep real text entries (ignore junk/blanks)
            value = data.get(key, [])
            return [x for x in value if isinstance(x, str) and x.strip()] if isinstance(value, list) else []

        self.protected_folders = text_list("protected")
        self.exempt_paths = text_list("exempt_paths")
        self.exempt_keywords = text_list("exempt_keywords")
        self.source_dir.set(str(data.get("source", "")))
        self.dest_dir.set(str(data.get("dest", "")))
        self.refresh_exempt_listbox()
        self.delete_zero_byte.set(data.get("delete_zero_byte", False))
        self.delete_empty_dirs.set(data.get("delete_empty_dirs", True))
        # "grant_universal" was the old name of this setting - still understood.
        self.grant_access.set(data.get("grant_my_access", data.get("grant_universal", False)))
        self.verbose.set(data.get("verbose", True))
        self.enable_error_log.set(data.get("enable_error_log", False))
        self.dry_run.set(data.get("dry_run", False))
        self.enable_rename.set(data.get("enable_rename", False))
        self.rename_mode.set(data.get("rename_mode", "Full") if data.get("rename_mode") in RENAME_MODES else "Full")
        labels = [l for l in data.get("criteria_labels", []) if l in SORT_CRITERIA_MAP]
        for label in labels:
            self.criteria_vars[label].set(True)
        self.active_criteria_order = labels
        self.refresh_criteria_listbox()

    def save_config(self):
        data = {
            "source": self.source_dir.get(),
            "dest": self.dest_dir.get(),
            "protected": self.protected_folders,
            "exempt_paths": self.exempt_paths,
            "exempt_keywords": self.exempt_keywords,
            "delete_zero_byte": self.delete_zero_byte.get(),
            "delete_empty_dirs": self.delete_empty_dirs.get(),
            "grant_my_access": self.grant_access.get(),
            "verbose": self.verbose.get(),
            "enable_error_log": self.enable_error_log.get(),
            "dry_run": self.dry_run.get(),
            "enable_rename": self.enable_rename.get(),
            "rename_mode": self.rename_mode.get(),
            "criteria_labels": self.active_criteria_order,
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self.banner.show("Configuration saved successfully.", "ok")
        except OSError as e:
            self.banner.show(f"Failed to save config:\n{e}", "error")

    def check_dependencies_ui(self):
        """The 'Check Dependencies' button: look again, and offer to install anything missing."""
        missing_packages, missing_tools = find_missing_dependencies(REQUIRED_PACKAGES, REQUIRED_TOOLS)
        if missing_packages or missing_tools:
            ensure_dependencies(REQUIRED_PACKAGES, REQUIRED_TOOLS)
        else:
            self.banner.show("All required dependencies are satisfied.", "ok")

    # ---- starting, stopping and running the work ----------------------------------------------
    def validate_inputs(self, on_ok):
        """Check the form before doing anything. Calls on_ok() only once it is safe to continue
        (any confirmation banners are asked along the way, so this may return before on_ok runs)."""
        source = self.source_dir.get().strip()
        if not source:
            self.banner.show("Please select a source directory.", "error")
            return
        if not os.path.isdir(source):
            self.banner.show(f"Source directory does not exist:\n{source}", "error")
            return
        protected = [normalize(p) for p in self.protected_folders]
        if should_skip_system_paths(source, protected):
            self.banner.show("The source directory is a system or protected folder.", "error")
            return
        dest = self.dest_dir.get().strip()
        if dest and not os.path.exists(dest) and not self.dry_run.get():
            def _create_dest():
                try:
                    os.makedirs(dest, exist_ok=True)
                except OSError as e:
                    self.banner.show(f"Failed to create directory:\n{e}", "error")
                    return
                self._check_admin(on_ok)
            self.banner.ask(f"Destination directory does not exist:\n{dest}\n\nCreate it?", on_yes=_create_dest)
            return
        self._check_admin(on_ok)

    def _check_admin(self, on_ok):
        """Second step of validate_inputs: ask before continuing without admin access, if needed."""
        if self.grant_access.get() and not self.dry_run.get() and not check_admin_privileges():
            def _continue_without_admin():
                self.grant_access.set(False)
                on_ok()
            self.banner.ask(
                "Changing access needs administrator privileges.\n"
                "You are not running as administrator.\n\n"
                "Continue without changing access?", on_yes=_continue_without_admin)
            return
        on_ok()

    def start_operation(self):
        self.validate_inputs(self._confirm_operation)

    def _confirm_operation(self):
        preview = self.dry_run.get()
        if not preview:
            self.banner.ask(
                "This will MOVE files into the chosen subfolder hierarchy, delete exact duplicate copies, "
                "and perform the selected cleanup operations.\n\n"
                "Tip: tick 'PREVIEW ONLY' first to see what would happen.\n\n"
                "Are you sure you want to continue?", on_yes=lambda: self._launch_operation(preview))
            return
        self._launch_operation(preview)

    def _launch_operation(self, preview):
        source = self.source_dir.get().strip()
        settings = {                                              # a snapshot, so changing the window mid-run is harmless
            "source": source,
            "dest": self.dest_dir.get().strip() or source,
            "criteria_labels": list(self.active_criteria_order),
            "protected": [normalize(p) for p in self.protected_folders + self.exempt_paths],
            "keywords": [k.lower() for k in self.exempt_keywords if k.strip()],   # a blank keyword would exclude everything
            "delete_zero_byte": self.delete_zero_byte.get(),
            "delete_empty_dirs": self.delete_empty_dirs.get(),
            "grant_access": self.grant_access.get(),
            "verbose": self.verbose.get(),
            "dry_run": preview,
            "rename_mode": self.rename_mode.get() if self.enable_rename.get() else None,
            "error_log": self.make_error_logger(self.enable_error_log.get(), self.error_log_path),
        }

        self.progress_text.config(state=tk.NORMAL)
        self.progress_text.delete(1.0, tk.END)
        self.progress_text.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self._stop_event.clear()
        threading.Thread(target=self.run_operation, args=(settings,), daemon=True).start()

    def stop_operation(self):
        self._stop_event.set()
        self.log_message("Stopping operation...")
        self.update_status("Stopping...")

    def run_operation(self, s):
        """Runs in the background thread: access -> organize -> clean up -> summary."""
        log = self.log_message
        detail = log if s["verbose"] else _noop
        should_stop = self._stop_event.is_set
        source, dest, protected, dry = s["source"], s["dest"], s["protected"], s["dry_run"]
        keywords = s["keywords"]
        criteria_keys = [SORT_CRITERIA_MAP[lbl] for lbl in s["criteria_labels"] if lbl in SORT_CRITERIA_MAP]
        access_changed = empty_removed = 0
        try:
            log("=" * 60)
            log("CLARIFY File Organization " + ("PREVIEW (nothing will be changed)" if dry else "Started"))
            log("=" * 60)
            log(f"Source: {source}")
            log(f"Destination: {dest}")
            log(f"Active Nesting Order: {s['criteria_labels'] or 'None (Root Folder Only)'}")
            if s["rename_mode"]:
                log(f"Timestamp renaming: {s['rename_mode']}")
            if protected:
                log(f"Protected/exempt paths: {len(protected)}")
            if keywords:
                log(f"Exempt keywords: {', '.join(keywords)}")
            log("")

            if s["grant_access"]:
                self.update_status("Granting access...")
                log("Granting your account full access to files and folders...")
                access_changed, errors = set_access_recursive(source, protected, detail, should_stop, dry, keywords)
                log(f"Access granted to {access_changed} items")
                if errors:
                    log(f"Failed to modify access for {errors} items")
                log("")

            self.update_status("Organizing files...")
            counts = organize_files_with_dedup(
                source, dest, criteria_keys, protected=protected,
                delete_zero_byte=s["delete_zero_byte"],
                remove_emptied_dirs=s["delete_empty_dirs"] and not dry,
                rename_mode=s["rename_mode"], dry_run=dry,
                log=detail, error_log=s["error_log"], should_stop=should_stop, keywords=keywords
            )

            if s["delete_empty_dirs"]:
                self.update_status("Cleaning empty directories...")
                log("Cleaning empty directories...")
                empty_removed = remove_empty_dirs(source, protected, detail, dry, keywords)
                log(f"{'Would remove' if dry else 'Removed'} {empty_removed} empty directories")
                log("")

            log("=" * 60)
            log("Preview Complete" if dry else "Operation Complete")
            log("=" * 60)
            log(f"Files {'That Would Move' if dry else 'Moved'}: {counts['moved']}")
            log(f"Files Skipped (Already in Place): {counts['skipped']}")
            log(f"Duplicates Purged on Contact: {counts['duplicates_removed']}")
            log(f"Zero-Byte Files {'That Would Be ' if dry else ''}Deleted: {counts['zero_byte_deleted']}")
            log(f"Empty Directories {'That Would Be ' if dry else ''}Removed: {empty_removed}")
            if access_changed:
                log(f"Access Modified: {access_changed} items")
            log("")
            self.update_status("Preview complete" if dry else "Complete")
        except OperationCancelled:
            log("")
            log("Operation cancelled by user.")
            self.update_status("Cancelled")
        except Exception as e:                                    # last safety net: show the problem, do not crash silently
            log(f"Fatal error during operation: {e}")
            s["error_log"](f"Fatal error: {e}")
            self.update_status("Error")
        finally:                                                  # always re-enable the buttons
            self._on_ui(lambda: self.start_button.config(state=tk.NORMAL))
            self._on_ui(lambda: self.stop_button.config(state=tk.DISABLED))
            self._on_ui(lambda: flash_taskbar(self.root))


# =====================================================================================
# STEP 9 - START THE PROGRAM
# =====================================================================================
def main():
    """Read command-line options, then open the window."""
    parser = argparse.ArgumentParser(description="CLARIFY File Organization Tool")
    parser.add_argument("--source", default="", help="Source directory")
    parser.add_argument("--dest", default="", help="Destination directory")
    args = parser.parse_args()

    _enable_dpi_awareness()                                       # must happen BEFORE the window exists
    root = tk.Tk()
    ClarifyGUI(root, source=args.source, dest=args.dest)
    root.mainloop()                                               # hand control to the window until it is closed


if __name__ == "__main__":                                        # True only when run directly (not imported)
    main()
