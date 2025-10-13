CLARIFY – Clean, Locate, Arrange, Remove, Index Files for You

I also updated the title and first description to reflect the name change.

markdown
Copy code
# CLARIFY - Clean, Locate, Arrange, Remove, Index Files for You

**CLARIFY** is a cross-platform script that deduplicates files by hash, organizes them by extension/date, manages access permissions, and cleans up zero-byte files and empty folders. It skips system-critical directories and offers verbose output—ideal for admins, hoarders, and backup users.

# 🗂️ File Organizer with Universal Access and Deduplication

A powerful Python script to organize files by extension (and optionally by date), automatically remove duplicates (retaining the newest version), clean up zero-byte files, and optionally grant universal access permissions to all files and folders.

---

## 🚀 Features

- ✅ Organize files by extension into destination directories  
- 📅 Optional organization by modification date (e.g., `2025-10-13`)  
- 🧹 Remove duplicate files (based on content hash + last modified time)  
- ⚖️ Automatically resolves file conflicts with smart overwrite logic  
- 🔓 Optionally grants **universal access** to all files/folders  
- 🧺 Delete empty folders and zero-byte files  
- 🛡️ Skips critical system directories and files to prevent corruption  
- 🖥️ Cross-platform: supports **Windows**, **Linux**, and **macOS**

---

## 📂 Example Use Cases

- Cleaning up downloaded files or exported data  
- Merging and deduplicating folders from backups  
- Preparing shared folders with universal access  
- Organizing camera or media exports by date/type

---

## 🛠️ Requirements

- Python 3.6+  
- Works out-of-the-box with standard libraries  
- On **Windows**, admin rights are recommended if changing file permissions

---

## ⚙️ How It Works

1. **Prompts for source and destination directory**  
2. **Optionally:**
   - Grants universal access  
   - Deletes zero-byte files  
   - Organizes files into dated folders  
3. **Identifies and removes duplicates**  
4. **Moves files into destination folders grouped by extension**  
5. **Cleans up empty directories**  
6. **Prints a detailed summary**

---

## 🧾 Usage

Run the script directly in shell:

```bash
python file_organizer.py
```

You will be prompted to:

Enter the source directory

Enter a destination directory (defaults to source if empty)

Choose cleanup options:

Delete zero-byte files?

Delete empty directories?

Grant universal access?

Organize into date subfolders?

Enable verbose output?

🔐 Universal Access Explanation

Windows: Grants full control to the Everyone group using icacls

Linux/macOS: Sets directory permissions to 755 and file permissions to 644

📌 Note: You may need admin/root privileges depending on file ownership

⚠️ Safety Warnings

❗ System directories like Windows, Program Files, and System Volume Information are automatically skipped

⚠️ Always back up your data before organizing large or important folders

🧪 Use the script in a test directory before applying it to sensitive locations

📦 Output Structure

Organized files will be moved to:

swift
Copy code
/destination_folder/
    ├── jpg/
    │   ├── 2025-10-13/
    │   └── ...
    ├── pdf/
    ├── txt/
    └── no-extension/

🧪 Sample Output
bash
Copy code
Enter source directory: /Users/you/Downloads
Enter destination directory (press Enter to use source): /Users/you/Organized

Cleanup Options:
Delete zero-byte files permanently? (y/N): y
Delete empty directories? (y/N): y
Grant universal access to all files/folders? (y/N): y
Also organize into date subfolders? (y/N): y
Enable verbose output? (y/N): y

Starting operations on: /Users/you/Downloads
Organizing to: /Users/you/Organized
--------------------------------------------------
Organizing files and removing duplicates...
Moved: /Downloads/photo1.jpg -> /Organized/jpg/2025-10-13/photo1.jpg
Deleted older duplicate: /Downloads/old_photo1.jpg
...
OPERATION COMPLETED!
SUMMARY:
Universal access granted: 215 items  
Zero-byte files deleted: 5  
Files organized: 173  
Already in place: 2  
Empty directories removed: 23

📄 License

This script is provided as-is, with no warranty or guarantee. Use at your own risk.

🧠 Author Notes

Designed for safe and effective cleanup of large and messy folders.
Feedback or contributions welcome!

Happy organizing with CLARIFY!
