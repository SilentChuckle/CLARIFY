import os
import sys
import shutil
import hashlib
import subprocess
import platform
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
from pathlib import Path
import threading
import json

CONFIG_FILE = "clarify_config.json"
PROTECTED_FOLDERS = set()
REQUIRED_PACKAGES = []

def check_platform():
    if platform.system().lower() != 'windows':
        messagebox.showerror(
            "Platform Error",
            "This script is designed for Windows only.\n"
            f"Current platform: {platform.system()}"
        )
        sys.exit(1)

def check_dependencies():
    missing_packages = []
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    return missing_packages

def install_package(package_name):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return True
    except Exception as e:
        messagebox.showerror("Installation Failed", f"Failed to install {package_name}:\n{e}")
        return False

def offer_install_dependencies(missing):
    if not missing:
        return True
    msg = f"Missing dependencies:\n{', '.join(missing)}\n\nWould you like to install them now?"
    if messagebox.askyesno("Missing Dependencies", msg):
        for package in missing:
            if not install_package(package):
                return False
        messagebox.showinfo("Success", "All dependencies installed successfully!")
        return True
    else:
        messagebox.showwarning("Cannot Continue", "Cannot run without required dependencies.")
        return False

def is_windows():
    return platform.system().lower() == 'windows'

def should_skip_system_paths(path):
    path_lower = path.lower()
    folder_name = os.path.basename(path_lower)
    skip_folders = {
        '$recycle.bin','recycle.bin','system volume information','pagefile.sys',
        'hiberfil.sys','swapfile.sys','windows','program files',
        'program files (x86)','programdata','boot','efi','recovery'
    }
    if folder_name in skip_folders:
        return True
    if 'system volume information' in path_lower or \
       '$recycle.bin' in path_lower or 'recycle.bin' in path_lower:
        return True
    for protected in PROTECTED_FOLDERS:
        try:
            if os.path.commonpath([os.path.abspath(path), os.path.abspath(protected)]) == os.path.abspath(protected):
                return True
        except Exception:
            continue
    return False

def grant_universal_access(path, verbose=False):
    try:
        result = subprocess.run(
            ['icacls', path, '/grant', 'Everyone:F', '/C'],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False

def set_universal_access_recursive(directory, progress_callback=None):
    access_changed = 0
    errors = 0
    try:
        for root, dirs, files in os.walk(directory):
            if should_skip_system_paths(root):
                dirs.clear()
                continue
            dirs[:] = [d for d in dirs if not should_skip_system_paths(os.path.join(root, d))]
            if grant_universal_access(root):
                access_changed += 1
            else:
                errors += 1
            for file in files:
                file_path = os.path.join(root, file)
                if should_skip_system_paths(file_path):
                    continue
                if grant_universal_access(file_path):
                    access_changed += 1
                else:
                    errors += 1
                if progress_callback:
                    progress_callback(f"Access: {file_path}")
        return access_changed, errors
    except Exception as e:
        return 0, 0

def get_file_hash(file_path, block_size=65536):
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except Exception:
        return None

def get_file_extension(filename):
    ext = Path(filename).suffix[1:].lower()
    return ext if ext else 'no-extension'

def get_date_folder(file_path):
    try:
        ts = os.path.getmtime(file_path)
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except Exception:
        return 'unknown_date'

def get_timestamp_name(file_path, mode, original_name, extension, counter=0):
    try:
        ts = os.path.getctime(file_path)
    except Exception:
        try:
            ts = os.path.getmtime(file_path)
        except Exception:
            ts = datetime.now().timestamp()
    
    dt = datetime.fromtimestamp(ts)
    time_str = dt.strftime('%d-%m-%Y--%H-%M-%S')
    
    if counter > 0:
        time_str = f"{time_str}-({counter})"
        
    stem = Path(original_name).stem
    if mode == "Full":
        new_stem = time_str
    elif mode == "Prefix":
        new_stem = f"{time_str}_{stem}"
    elif mode == "Suffix":
        new_stem = f"{stem}_{time_str}"
    else:
        new_stem = time_str
        
    return f"{new_stem}{extension}"

def ensure_dir_exists(path):
    os.makedirs(path, exist_ok=True)

def remove_empty_dirs(path, progress_callback=None):
    removed_count = 0
    for root, dirs, files in os.walk(path, topdown=False):
        for d in dirs:
            dir_path = os.path.join(root, d)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    removed_count += 1
                    if progress_callback:
                        progress_callback(f"Removed empty: {dir_path}")
            except Exception:
                pass
    return removed_count

def delete_zero_byte_file_if_needed(file_path, progress_callback=None, error_log_callback=None):
    try:
        if os.path.exists(file_path) and os.path.getsize(file_path) == 0:
            os.remove(file_path)
            if progress_callback:
                progress_callback(f"Deleted zero-byte: {file_path}")
            if error_log_callback:
                error_log_callback(f"Deleted zero-byte: {file_path}")
            return True
    except Exception as e:
        if error_log_callback:
            error_log_callback(f"Failed to delete zero-byte file {file_path}: {e}")
    return False

def move_file_with_overwrite_check(src, dst, error_log_callback=None):
    if not os.path.exists(dst):
        shutil.move(src, dst)
        return dst
    else:
        try:
            src_hash = get_file_hash(src)
            dst_hash = get_file_hash(dst)
            src_size = os.path.getsize(src)
            dst_size = os.path.getsize(dst)
            if src_hash is None or dst_hash is None:
                msg = f"Could not hash during move: {src} or {dst}, not deleted or moved."
                if error_log_callback:
                    error_log_callback(msg)
                return src
            if src_hash == dst_hash and src_size == dst_size:
                os.remove(src)
                return dst
            else:
                base, ext = os.path.splitext(dst)
                counter = 1
                new_dst = f"{base}_({counter}){ext}"
                while os.path.exists(new_dst):
                    counter += 1
                    new_dst = f"{base}_({counter}){ext}"
                shutil.move(src, new_dst)
                return new_dst
        except Exception as e:
            msg = f"Error moving file '{src}' -> '{dst}': {e}"
            if error_log_callback:
                error_log_callback(msg)
            return src

def organize_files_with_dedup(source_dir, dest_dir, use_date_folders=False, delete_zero_byte=False, enable_date_rename=False, rename_mode="Full", progress_callback=None, error_log_callback=None):
    hash_latest = {}
    files = []
    zero_byte_deleted = 0
    for root, dirs, fs in os.walk(source_dir):
        if should_skip_system_paths(root):
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if not should_skip_system_paths(os.path.join(root, d))]
        for f in fs:
            file_path = os.path.join(root, f)
            if not should_skip_system_paths(file_path):
                if delete_zero_byte and delete_zero_byte_file_if_needed(file_path, progress_callback, error_log_callback):
                    zero_byte_deleted += 1
                else:
                    files.append(file_path)
    if progress_callback:
        progress_callback(f"Found {len(files)} files to process")
        if delete_zero_byte and zero_byte_deleted > 0:
            progress_callback(f"Deleted {zero_byte_deleted} zero-byte files on contact")
    for idx, file_path in enumerate(files):
        try:
            if not os.path.isfile(file_path):
                continue
            f_hash = get_file_hash(file_path)
            f_size = os.path.getsize(file_path)
            if f_hash is None:
                msg = f"Could not hash: {file_path}, skipped"
                if progress_callback:
                    progress_callback(msg)
                if error_log_callback:
                    error_log_callback(msg)
                continue
            last_mod = os.path.getmtime(file_path)
            if (f_hash, f_size) in hash_latest:
                stored_path, stored_mod = hash_latest[(f_hash, f_size)]
                if last_mod > stored_mod:
                    try:
                        if os.path.exists(stored_path):
                            os.remove(stored_path)
                        if progress_callback:
                            progress_callback(f"Removed duplicate: {stored_path}")
                        if error_log_callback:
                            error_log_callback(f"Removed duplicate: {stored_path}")
                    except Exception as e:
                        msg = f"Error removing (duplicate): {stored_path} ({e})"
                        if error_log_callback:
                            error_log_callback(msg)
                    hash_latest[(f_hash, f_size)] = (file_path, last_mod)
                else:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        if progress_callback:
                            progress_callback(f"Removed duplicate: {file_path}")
                        if error_log_callback:
                            error_log_callback(f"Removed duplicate: {file_path}")
                    except Exception as e:
                        msg = f"Error removing (duplicate): {file_path} ({e})"
                        if error_log_callback:
                            error_log_callback(msg)
            else:
                hash_latest[(f_hash, f_size)] = (file_path, last_mod)
            if progress_callback and idx % 10 == 0:
                progress_callback(f"Processing: {idx}/{len(files)} files")
        except Exception as e:
            msg = f"Error during dedup: {file_path} ({e})"
            if progress_callback:
                progress_callback(msg)
            if error_log_callback:
                error_log_callback(msg)
    moved_count = 0
    skipped_count = 0
    for (fhash, fsize), (file_path, _) in hash_latest.items():
        try:
            if not os.path.exists(file_path):
                continue
            ext = get_file_extension(file_path)
            ext_folder = os.path.join(dest_dir, ext)
            ensure_dir_exists(ext_folder)
            if use_date_folders:
                date_folder = get_date_folder(file_path)
                target_folder = os.path.join(ext_folder, date_folder)
                ensure_dir_exists(target_folder)
            else:
                target_folder = ext_folder
            
            original_basename = os.path.basename(file_path)
            ext_with_dot = Path(file_path).suffix
            
            if enable_date_rename:
                counter = 0
                while True:
                    new_filename = get_timestamp_name(file_path, rename_mode, original_basename, ext_with_dot, counter)
                    target_path = os.path.join(target_folder, new_filename)
                    if not os.path.exists(target_path):
                        break
                    counter += 1
            else:
                target_path = os.path.join(target_folder, original_basename)

            if os.path.abspath(file_path) == os.path.abspath(target_path):
                skipped_count += 1
                continue
            moved_to = move_file_with_overwrite_check(file_path, target_path, error_log_callback=error_log_callback)
            if progress_callback:
                progress_callback(f"Moved: {os.path.basename(file_path)} -> {os.path.basename(moved_to)}")
            moved_count += 1
            src_parent = os.path.dirname(file_path)
            while src_parent != source_dir and src_parent != os.path.dirname(src_parent):
                try:
                    if not os.listdir(src_parent):
                        os.rmdir(src_parent)
                    else:
                        break
                except Exception:
                    break
                src_parent = os.path.dirname(src_parent)
        except Exception as e:
            msg = f"Error during move: {file_path} ({e})"
            if progress_callback:
                progress_callback(msg)
            if error_log_callback:
                error_log_callback(msg)
    return moved_count, skipped_count, zero_byte_deleted

def check_admin_privileges():
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

class ClarifyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CLARIFY - File Organization Tool")
        self.root.geometry("800x780")
        self.root.resizable(True, True)

        self.source_dir = tk.StringVar()
        self.dest_dir = tk.StringVar()
        self.use_date_folders = tk.BooleanVar(value=False)
        self.delete_zero_byte = tk.BooleanVar(value=False)
        self.delete_empty_dirs = tk.BooleanVar(value=True)
        self.grant_universal = tk.BooleanVar(value=False)
        self.verbose = tk.BooleanVar(value=True)
        
        # New Renaming Options (Disabled by Default)
        self.enable_date_rename = tk.BooleanVar(value=False)
        self.rename_mode = tk.StringVar(value="Full")

        self.protected_folders = []
        self.enable_error_log = tk.BooleanVar(value=False)
        self.error_log_path = "clarify_error.log"

        self.running = False

        self.load_config()
        self.create_widgets()

    def create_widgets(self):
        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.pack(fill=tk.X)
        title_label = ttk.Label(
            title_frame,
            text="CLARIFY - File Organization Tool",
            font=("Arial", 16, "bold")
        )
        title_label.pack()
        subtitle_label = ttk.Label(
            title_frame,
            text="Organize files by extension, remove duplicates, clean up directories",
            font=("Arial", 9)
        )
        subtitle_label.pack()
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        dir_frame = ttk.LabelFrame(main_frame, text="Directories", padding="10")
        dir_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(dir_frame, text="Source Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(dir_frame, textvariable=self.source_dir, width=60).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(dir_frame, text="Browse", command=self.browse_source).grid(row=0, column=2, pady=5)
        ttk.Label(dir_frame, text="Destination Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(dir_frame, textvariable=self.dest_dir, width=60).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(dir_frame, text="Browse", command=self.browse_dest).grid(row=1, column=2, pady=5)
        ttk.Label(dir_frame, text="(Leave blank to use source)", font=("Arial", 8)).grid(row=2, column=1, sticky=tk.W)

        ttk.Label(dir_frame, text="Protected Folders:").grid(row=3, column=0, sticky=tk.W, pady=5)
        protected_btn_frame = ttk.Frame(dir_frame)
        protected_btn_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(protected_btn_frame, text="Add Folder", command=self.add_protected_folder).pack(side=tk.LEFT)
        ttk.Button(protected_btn_frame, text="View/Remove", command=self.manage_protected_folders).pack(side=tk.LEFT, padx=5)

        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Checkbutton(
            options_frame,
            text="Organize into date subfolders (YYYY-MM-DD)",
            variable=self.use_date_folders
        ).pack(anchor=tk.W, pady=2)
        
        # Timestamp Renaming Section
        rename_frame = ttk.LabelFrame(options_frame, text="Timestamp Renaming", padding="5")
        rename_frame.pack(fill=tk.X, pady=4)
        ttk.Checkbutton(
            rename_frame,
            text="Enable timestamp renaming (Day-Month-Year--Hour-Minutes-Seconds)",
            variable=self.enable_date_rename
        ).pack(anchor=tk.W, pady=2)
        
        mode_frame = ttk.Frame(rename_frame)
        mode_frame.pack(anchor=tk.W, padx=20, pady=2)
        ttk.Label(mode_frame, text="Mode:").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Full Rename", variable=self.rename_mode, value="Full").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Prefix", variable=self.rename_mode, value="Prefix").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Suffix", variable=self.rename_mode, value="Suffix").pack(side=tk.LEFT, padx=5)

        ttk.Checkbutton(
            options_frame,
            text="Delete zero-byte files",
            variable=self.delete_zero_byte
        ).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(
            options_frame,
            text="Delete empty directories",
            variable=self.delete_empty_dirs
        ).pack(anchor=tk.W, pady=2)
        access_frame = ttk.Frame(options_frame)
        access_frame.pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(
            access_frame,
            text="Grant universal access to all files/folders",
            variable=self.grant_universal
        ).pack(side=tk.LEFT)
        ttk.Label(
            access_frame,
            text="(Requires Admin)",
            font=("Arial", 8),
            foreground="red"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(
            options_frame,
            text="Verbose output (show detailed progress)",
            variable=self.verbose
        ).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(
            options_frame,
            text="Enable Error Log",
            variable=self.enable_error_log
        ).pack(anchor=tk.W, pady=2)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_button = ttk.Button(
            button_frame,
            text="Start Organization",
            command=self.start_operation,
            style="Accent.TButton"
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(
            button_frame,
            text="Stop",
            command=self.stop_operation,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(
            button_frame,
            text="Save Config",
            command=self.save_config
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            button_frame,
            text="Check Dependencies",
            command=self.check_dependencies_ui
        ).pack(side=tk.RIGHT, padx=5)

        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.pack(fill=tk.BOTH, expand=True)

        self.progress_text = scrolledtext.ScrolledText(
            progress_frame,
            height=12,
            width=80,
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        self.progress_text.pack(fill=tk.BOTH, expand=True)
        self.status_label = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def log_message(self, message):
        self.progress_text.config(state=tk.NORMAL)
        self.progress_text.insert(tk.END, f"{message}\n")
        self.progress_text.see(tk.END)
        self.progress_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def log_error(self, message):
        if self.enable_error_log.get():
            try:
                with open(self.error_log_path, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().isoformat()} {message}\n")
            except Exception as e:
                self.log_message(f"Failed to write to error log: {e}")

    def update_status(self, message):
        self.status_label.config(text=message)
        self.root.update_idletasks()

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
        if directory:
            abs_path = os.path.abspath(directory)
            if abs_path not in self.protected_folders:
                self.protected_folders.append(abs_path)
                messagebox.showinfo("Added", f"Protected folder added:\n{abs_path}")
            else:
                messagebox.showinfo("Already Protected", "This folder is already in the protected list.")

    def manage_protected_folders(self):
        if not self.protected_folders:
            messagebox.showinfo("No Protected Folders", "No protected folders have been added.")
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
                messagebox.showinfo("Removed", f"Removed:\n{folder}")

        ttk.Button(btn_frame, text="Remove Selected", command=remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def validate_inputs(self):
        source = self.source_dir.get().strip()
        if not source:
            messagebox.showerror("Error", "Please select a source directory.")
            return False
        if not os.path.exists(source):
            messagebox.showerror("Error", f"Source directory does not exist:\n{source}")
            return False
        dest = self.dest_dir.get().strip()
        if dest and not os.path.exists(dest):
            if messagebox.askyesno("Create Directory", f"Destination directory does not exist:\n{dest}\n\nCreate it?"):
                try:
                    os.makedirs(dest, exist_ok=True)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to create directory:\n{e}")
                    return False
            else:
                return False
        if self.grant_universal.get() and not check_admin_privileges():
            if not messagebox.askyesno(
                "Admin Required",
                "Universal access changes require administrator privileges.\n"
                "You are not running as administrator.\n\n"
                "Continue without universal access?"
            ):
                return False
            self.grant_universal.set(False)
        return True

    def start_operation(self):
        if not self.validate_inputs():
            return
        if not messagebox.askyesno(
            "Confirm Operation",
            "This will organize files, remove duplicates, and perform selected cleanup operations.\n\n"
            "Are you sure you want to continue?"
        ):
            return
        self.progress_text.config(state=tk.NORMAL)
        self.progress_text.delete(1.0, tk.END)
        self.progress_text.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.running = True
        thread = threading.Thread(target=self.run_operation, daemon=True)
        thread.start()

    def stop_operation(self):
        self.running = False
        self.log_message("Stopping operation...")
        self.update_status("Stopping...")

    def run_operation(self):
        try:
            source = self.source_dir.get().strip()
            dest = self.dest_dir.get().strip() or source
            global PROTECTED_FOLDERS
            PROTECTED_FOLDERS = set(self.protected_folders)
            self.log_message("=" * 60)
            self.log_message("CLARIFY File Organization Started")
            self.log_message("=" * 60)
            self.log_message(f"Source: {source}")
            self.log_message(f"Destination: {dest}")
            if self.protected_folders:
                self.log_message(f"Protected folders: {len(self.protected_folders)}")
            self.log_message("")
            results = {
                'access_changed': 0,
                'zero_byte_deleted': 0,
                'files_moved': 0,
                'files_skipped': 0,
                'empty_dirs_removed': 0
            }
            if self.grant_universal.get() and self.running:
                self.update_status("Granting universal access...")
                self.log_message("Granting universal access to files and folders...")
                access_changed, errors = set_universal_access_recursive(
                    source,
                    self.log_message if self.verbose.get() else None
                )
                results['access_changed'] = access_changed
                self.log_message(f"Universal access granted to {access_changed} items")
                if errors > 0:
                    self.log_message(f"Failed to modify access for {errors} items")
                self.log_message("")
            
            if self.running:
                self.update_status("Organizing files and removing duplicates...")
                self.log_message("Organizing files and removing duplicates...")
                if self.delete_zero_byte.get():
                    self.log_message("(Zero-byte files will be deleted on contact)")
                if self.enable_date_rename.get():
                    self.log_message(f"(Timestamp renaming enabled: Mode = {self.rename_mode.get()})")
                
                moved, skipped, zero_deleted = organize_files_with_dedup(
                    source,
                    dest,
                    self.use_date_folders.get(),
                    self.delete_zero_byte.get(),
                    enable_date_rename=self.enable_date_rename.get(),
                    rename_mode=self.rename_mode.get(),
                    progress_callback=self.log_message if self.verbose.get() else None,
                    error_log_callback=self.log_error if self.enable_error_log.get() else None
                )
                results['files_moved'] = moved
                results['files_skipped'] = skipped
                results['zero_byte_deleted'] = zero_deleted
                self.log_message(f"Files organized: {moved}")
                self.log_message(f"Files already in place: {skipped}")
                if self.delete_zero_byte.get():
                    self.log_message(f"Zero-byte files deleted: {zero_deleted}")
                self.log_message("")

            if self.grant_universal.get() and source != dest and results['files_moved'] > 0 and self.running:
                self.update_status("Granting universal access to organized files...")
                self.log_message("Granting universal access to newly organized files...")
                access_changed, errors = set_universal_access_recursive(
                    dest,
                    self.log_message if self.verbose.get() else None
                )
                results['access_changed'] += access_changed
                self.log_message(f"Additional access granted to {access_changed} items")
                self.log_message("")

            if self.delete_empty_dirs.get() and self.running:
                self.update_status("Removing empty directories...")
                self.log_message("Removing empty directories...")
                removed = remove_empty_dirs(
                    source,
                    self.log_message if self.verbose.get() else None
                )
                if source != dest:
                    removed += remove_empty_dirs(
                        dest,
                        self.log_message if self.verbose.get() else None
                    )
                results['empty_dirs_removed'] += removed
                self.log_message(f"Empty directories removed: {removed}")
                self.log_message("")

            self.log_message("=" * 60)
            self.log_message("OPERATION COMPLETED!")
            self.log_message("=" * 60)
            self.log_message("SUMMARY:")
            if self.grant_universal.get() and results['access_changed'] > 0:
                self.log_message(f"  Universal access granted: {results['access_changed']} items")
            if self.delete_zero_byte.get():
                self.log_message(f"  Zero-byte files deleted: {results['zero_byte_deleted']}")
            self.log_message(f"  Files organized: {results['files_moved']}")
            self.log_message(f"  Already in place: {results['files_skipped']}")
            if self.delete_empty_dirs.get():
                self.log_message(f"  Empty directories removed: {results['empty_dirs_removed']}")
            self.log_message("=" * 60)
            self.update_status("Operation completed successfully")
            messagebox.showinfo("Success", "File organization completed successfully!")
        except Exception as e:
            self.log_message(f"\nERROR: {e}")
            self.log_error(f"ERROR: {e}")
            self.update_status("Operation failed")
            messagebox.showerror("Error", f"An error occurred:\n{e}")
        finally:
            self.running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def check_dependencies_ui(self):
        missing = check_dependencies()
        if not missing:
            messagebox.showinfo("Dependencies OK", "All required dependencies are installed!")
        else:
            offer_install_dependencies(missing)

    def save_config(self):
        config = {
            'source_dir': self.source_dir.get(),
            'dest_dir': self.dest_dir.get(),
            'use_date_folders': self.use_date_folders.get(),
            'delete_zero_byte': self.delete_zero_byte.get(),
            'delete_empty_dirs': self.delete_empty_dirs.get(),
            'grant_universal': self.grant_universal.get(),
            'verbose': self.verbose.get(),
            'enable_date_rename': self.enable_date_rename.get(),
            'rename_mode': self.rename_mode.get(),
            'protected_folders': self.protected_folders,
            'enable_error_log': self.enable_error_log.get(),
            'error_log_path': self.error_log_path
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("Saved", "Configuration saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration:\n{e}")

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                self.source_dir.set(config.get('source_dir', ''))
                self.dest_dir.set(config.get('dest_dir', ''))
                self.use_date_folders.set(config.get('use_date_folders', False))
                self.delete_zero_byte.set(config.get('delete_zero_byte', False))
                self.delete_empty_dirs.set(config.get('delete_empty_dirs', True))
                self.grant_universal.set(config.get('grant_universal', False))
                self.verbose.set(config.get('verbose', True))
                self.enable_date_rename.set(config.get('enable_date_rename', False))
                self.rename_mode.set(config.get('rename_mode', 'Full'))
                self.protected_folders = config.get('protected_folders', [])
                self.enable_error_log.set(config.get('enable_error_log', False))
                self.error_log_path = config.get('error_log_path', "clarify_error.log")
        except Exception:
            pass

def main():
    check_platform()
    missing = check_dependencies()
    if missing:
        temp_root = tk.Tk()
        temp_root.withdraw()
        if not offer_install_dependencies(missing):
            sys.exit(1)
        temp_root.destroy()
    root = tk.Tk()
    app = ClarifyGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()