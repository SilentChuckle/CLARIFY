import os
import shutil
import hashlib
import subprocess
import platform
import getpass
from datetime import datetime
from pathlib import Path

def is_windows():
    return platform.system().lower() == 'windows'

def should_skip_system_paths(path):
    """Skip system paths that shouldn't be modified"""
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
    return False

def grant_universal_access(path, verbose=False):
    """Grant full access to Everyone group for universal access"""
    if not is_windows():
        try:
            # On Unix-like systems, set 755 for directories, 644 for files
            if os.path.isdir(path):
                os.chmod(path, 0o755)
            else:
                os.chmod(path, 0o644)
            if verbose:
                print(f"Set universal permissions: {path}")
            return True
        except Exception as e:
            if verbose:
                print(f"Error setting permissions on {path}: {e}")
            return False
    
    try:
        # Windows: Grant full control to Everyone group
        result = subprocess.run(
            ['icacls', path, '/grant', 'Everyone:F', '/C'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            if verbose:
                print(f"Granted universal access: {path}")
            return True
        else:
            if verbose:
                print(f"Failed to grant universal access: {path} - {result.stderr.strip()}")
            return False
    except Exception as e:
        if verbose:
            print(f"Error granting universal access to {path}: {e}")
        return False

def set_universal_access_recursive(directory, verbose=False):
    """Grant universal access to all files and folders in directory"""
    if is_windows():
        print(f"Granting universal access to files in: {directory}")
    else:
        print(f"Setting universal permissions for files in: {directory}")
    print("This may take a while for large directories...")
    
    access_changed = 0
    errors = 0
    
    try:
        for root, dirs, files in os.walk(directory):
            # Skip system directories
            if should_skip_system_paths(root):
                if verbose:
                    print(f"Skipping system directory: {root}")
                dirs.clear()
                continue
            
            # Filter out system directories from dirs list
            dirs[:] = [d for d in dirs if not should_skip_system_paths(os.path.join(root, d))]
            
            # Set universal access for current directory
            success = grant_universal_access(root, verbose)
            if success: 
                access_changed += 1
            else: 
                errors += 1
            
            # Set universal access for all files in directory
            for file in files:
                file_path = os.path.join(root, file)
                if should_skip_system_paths(file_path):
                    continue
                
                success = grant_universal_access(file_path, verbose)
                if success: 
                    access_changed += 1
                else: 
                    errors += 1
        
        print(f"Universal access granted to {access_changed} items")
        if errors > 0:
            print(f"Failed to modify access for {errors} items")
        return access_changed
        
    except Exception as e:
        print(f"Error during access modification: {e}")
        return 0

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

def ensure_dir_exists(path):
    os.makedirs(path, exist_ok=True)

def remove_empty_dirs(path, verbose=False):
    removed_count = 0
    for root, dirs, files in os.walk(path, topdown=False):
        for d in dirs:
            dir_path = os.path.join(root, d)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    if verbose:
                        print(f"Removed empty directory: {dir_path}")
                    removed_count += 1
            except Exception:
                pass
    return removed_count

def delete_zero_byte_files(directory, verbose=False):
    deleted_count = 0
    for root, dirs, files in os.walk(directory):
        # Skip system directories
        dirs[:] = [d for d in dirs if not should_skip_system_paths(os.path.join(root, d))]
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if os.path.exists(file_path) and os.path.getsize(file_path) == 0:
                    os.remove(file_path)
                    if verbose:
                        print(f"Deleted zero-byte file: {file_path}")
                    deleted_count += 1
            except Exception as e:
                if verbose:
                    print(f"Error deleting zero-byte file {file_path}: {e}")
    return deleted_count

def move_file_with_overwrite_check(src, dst):
    if not os.path.exists(dst):
        shutil.move(src, dst)
        return dst
    else:
        try:
            src_hash = get_file_hash(src)
            dst_hash = get_file_hash(dst)
            if src_hash is None or dst_hash is None:
                # Fall back to modification time comparison
                src_mtime = os.path.getmtime(src)
                dst_mtime = os.path.getmtime(dst)
                if src_mtime > dst_mtime:
                    os.remove(dst)
                    shutil.move(src, dst)
                    return dst
                else:
                    os.remove(src)
                    return dst
            else:
                if src_hash == dst_hash:
                    # Files are identical, remove source
                    os.remove(src)
                    return dst
                else:
                    # Files are different, keep the newer one
                    src_mtime = os.path.getmtime(src)
                    dst_mtime = os.path.getmtime(dst)
                    if src_mtime > dst_mtime:
                        os.remove(dst)
                        shutil.move(src, dst)
                        return dst
                    else:
                        os.remove(src)
                        return dst
        except Exception:
            # If there's any error, create a new filename with counter
            base, ext = os.path.splitext(dst)
            counter = 1
            new_dst = f"{base}_{counter}{ext}"
            while os.path.exists(new_dst):
                counter += 1
                new_dst = f"{base}_{counter}{ext}"
            shutil.move(src, new_dst)
            return new_dst

def organize_files_with_dedup(source_dir, dest_dir, use_date_folders=False, verbose=False):
    hash_latest = {}
    files = []
    
    # Collect all files first
    for root, dirs, fs in os.walk(source_dir):
        # Skip system directories
        dirs[:] = [d for d in dirs if not should_skip_system_paths(os.path.join(root, d))]
        for f in fs:
            file_path = os.path.join(root, f)
            if not should_skip_system_paths(file_path):
                files.append(file_path)
    
    if verbose:
        print(f"Found {len(files)} files to process.")

    # First pass: find duplicates and keep only the newest version
    for file_path in files:
        try:
            if not os.path.isfile(file_path):
                continue
            f_hash = get_file_hash(file_path)
            if f_hash is None:
                if verbose: 
                    print(f"Skipping file (hash error): {file_path}")
                continue
            
            last_mod = os.path.getmtime(file_path)
            if f_hash in hash_latest:
                stored_path, stored_mod = hash_latest[f_hash]
                if last_mod > stored_mod:
                    # Current file is newer, delete the stored one
                    try:
                        os.remove(stored_path)
                        if verbose: 
                            print(f"Deleted older duplicate: {stored_path}")
                    except Exception: 
                        pass
                    hash_latest[f_hash] = (file_path, last_mod)
                else:
                    # Stored file is newer, delete current one
                    try:
                        os.remove(file_path)
                        if verbose: 
                            print(f"Deleted older duplicate: {file_path}")
                    except Exception: 
                        pass
            else:
                hash_latest[f_hash] = (file_path, last_mod)
        except Exception as e:
            if verbose: 
                print(f"Error processing file {file_path}: {e}")

    # Second pass: organize remaining files
    moved_count = 0
    skipped_count = 0
    for fhash, (file_path, _) in hash_latest.items():
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
            
            target_path = os.path.join(target_folder, os.path.basename(file_path))
            
            # Skip if file is already in the target location
            if os.path.abspath(file_path) == os.path.abspath(target_path):
                skipped_count += 1
                continue
            
            moved_to = move_file_with_overwrite_check(file_path, target_path)
            if verbose: 
                print(f"Moved: {file_path} -> {moved_to}")
            moved_count += 1
            
            # Clean up empty source directories
            src_parent = os.path.dirname(file_path)
            while src_parent != source_dir and src_parent != os.path.dirname(src_parent):
                try:
                    if not os.listdir(src_parent):
                        os.rmdir(src_parent)
                        if verbose: 
                            print(f"Removed empty directory: {src_parent}")
                    else:
                        break
                except Exception:
                    break
                src_parent = os.path.dirname(src_parent)
                
        except Exception as e:
            if verbose: 
                print(f"Failed to move {file_path}: {e}")
    
    # Clean up empty directories
    removed_src = remove_empty_dirs(source_dir, verbose)
    removed_dest = remove_empty_dirs(dest_dir, verbose)
    
    if verbose:
        print(f"Removed {removed_src} empty dirs from source")
        print(f"Removed {removed_dest} empty dirs from dest")
    
    return moved_count, skipped_count

def get_user_input():
    while True:
        source = input("Enter source directory: ").strip()
        if not source:
            print("Source directory cannot be empty.")
            continue
        if not os.path.exists(source):
            print(f"Source directory '{source}' does not exist.")
            continue
        break
    
    dest = input("Enter destination directory (press Enter to use source): ").strip()
    if not dest:
        dest = source
    elif not os.path.exists(dest):
        try:
            os.makedirs(dest, exist_ok=True)
            print(f"Created destination directory: {dest}")
        except Exception as e:
            print(f"Could not create destination directory: {e}")
            return None, None
    
    return source, dest

def get_cleanup_options():
    print("\nCleanup Options:")
    print("-" * 20)
    delete_zero_byte = input("Delete zero-byte files permanently? (y/N): ").strip().lower() in ['y','yes']
    delete_empty_dirs = input("Delete empty directories? (y/N): ").strip().lower() in ['y','yes']
    grant_universal = input("Grant universal access to all files/folders? (y/N): ").strip().lower() in ['y','yes']
    return delete_zero_byte, delete_empty_dirs, grant_universal

def check_admin_privileges():
    if not is_windows():
        return True  # Unix systems handle permissions differently
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def main():
    print("File Organization Script with Universal Access")
    print("=" * 70)
    print("Organizes files by extension with optional date subfolders.")
    print("Removes duplicates automatically, keeping the newest version.")
    print("Can grant universal access so all users can access files.")
    print("System folders are protected and untouched!")
    print("=" * 70)

    source, dest = get_user_input()
    if not source or not dest:
        print("Exiting due to invalid directories.")
        return

    delete_zero_byte, delete_empty_dirs, grant_universal = get_cleanup_options()
    use_date_folders = input("Also organize into date subfolders? (y/N): ").strip().lower() in ['y','yes']
    verbose = input("Enable verbose output? (y/N): ").strip().lower() in ['y','yes']

    print(f"\nStarting operations on: {source}")
    if source != dest:
        print(f"Organizing to: {dest}")
    print("-" * 50)
    
    universal_access_changed = 0
    zero_byte_deleted = 0
    files_moved = 0
    files_skipped = 0
    removed_dirs = 0
    
    try:
        # Grant universal access first if requested
        if grant_universal:
            if is_windows() and not check_admin_privileges():
                print("WARNING: Administrator privileges recommended for universal access changes.")
                proceed = input("Continue anyway? (y/N): ").strip().lower() in ['y','yes']
                if not proceed:
                    print("Skipping universal access changes.")
                    grant_universal = False
            
            if grant_universal:
                print("Granting universal access to files and folders...")
                universal_access_changed = set_universal_access_recursive(source, verbose)
        
        # Delete zero-byte files if requested
        if delete_zero_byte:
            print("Deleting zero-byte files...")
            zero_byte_deleted = delete_zero_byte_files(source, verbose)
        
        # Organize files with deduplication
        print("Organizing files and removing duplicates...")
        files_moved, files_skipped = organize_files_with_dedup(source, dest, use_date_folders, verbose)
        
        # Grant universal access to newly organized files
        if grant_universal and source != dest and files_moved > 0:
            print("Granting universal access to newly organized files...")
            additional_access = set_universal_access_recursive(dest, verbose)
            universal_access_changed += additional_access
        
        # Clean up empty directories if requested
        if delete_empty_dirs:
            print("Removing empty directories...")
            removed_dirs = remove_empty_dirs(source, verbose)
            if source != dest:
                removed_dirs += remove_empty_dirs(dest, verbose)
        
        # Summary
        print("="*50)
        print("OPERATION COMPLETED!")
        print("="*50)
        print("SUMMARY:")
        if grant_universal and universal_access_changed > 0:
            print(f"Universal access granted: {universal_access_changed} items")
        if delete_zero_byte: 
            print(f"Zero-byte files deleted: {zero_byte_deleted}")
        print(f"Files organized: {files_moved}")
        print(f"Already in place: {files_skipped}")
        if delete_empty_dirs: 
            print(f"Empty directories removed: {removed_dirs}")
        print("="*50)
        if grant_universal and universal_access_changed > 0:
            print("All files now have universal access for all users!")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()