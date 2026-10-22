# CLARIFY (2026 Edition)

**Clarify** is a dedicated Windows file organization, deduplication, and directory maintenance tool. It cleans up unorganized directories by grouping files into extension- and date-based taxonomies, eliminating duplicate content safely using cryptographic verification, and enforcing file system permissions across user profiles.

The **2026 Edition** upgrades Clarify from a terminal-based script to a threaded desktop app featuring an asynchronous GUI, compound file validation, custom timestamp renaming, and user-defined directory protections.

---

## Technical Comparison: Original vs. 2026 Edition

| Feature / Subsystem | Clarify (Original) | Clarify (2026) |
| :--- | :--- | :--- |
| **User Interface** | Interactive Terminal (CLI) | Asynchronous Graphical Interface (Tkinter GUI) |
| **OS Compatibility** | Cross-platform (Windows / Unix) | Optimized for Windows System Administration |
| **Deduplication Strategy** | SHA-256 Hash | Compound Index: `(SHA-256 Hash, File Byte Size)` |
| **File Renaming Subsystem** | Passive (Retains original names) | Configurable Timestamp Engine (Full, Prefix, Suffix) |
| **Safety Restrictions** | Hardcoded OS System Directory Filters | OS System Directory Filters + User-Defined Protected Roots |
| **Configuration State** | Non-persistent (Prompt-driven) | Persistent JSON State (`clarify_config.json`) |
| **Execution Architecture** | Single-threaded (Blocking) | Multi-threaded Daemon (`threading.Thread`) |
| **Audit Logging** | Terminal output stream | Live UI Log Box + File Logging (`clarify_error.log`) |

---

## Key Features in Clarify (2026)

* **Asynchronous Multi-Threaded Engine**: Long-running scans and file transfers execute off the primary UI thread, keeping the interface responsive and allowing process interrupts at any stage.
* **Compound Hash & Size Deduplication**: Pairs 256-bit SHA-256 content hashing with strict byte-length comparisons to ensure duplicate identification is accurate before purging older variants.
* **Dynamic Timestamp Renaming Engine**: Formats file names according to their exact creation or modification date (`DD-MM-YYYY--HH-MM-SS`):
  * **Full**: Replaces original filename stem with the timestamp (`10-08-2026--14-30-00.png`).
  * **Prefix**: Prepends timestamp to existing filename (`10-08-2026--14-30-00_photo.png`).
  * **Suffix**: Appends timestamp to existing filename (`photo_10-08-2026--14-30-00.png`).
* **Custom Protected Folders**: Allows users to define custom directory trees that are protected from modification during batch processing, alongside default OS exclusions (`$Recycle.bin`, `System Volume Information`, `Windows`, `Program Files`).
* **Universal Access Enforcement (Windows ACL)**: Invokes native Windows Access Control Lists (`icacls`) to grant full access rights (`Everyone:F`) across targeted structures when run with administrator privileges.
* **Directory Sanitization**: Features automatic zero-byte file deletion and top-down empty folder cleanup.

---

## Installation & Requirements

* **Operating System**: Windows 10 / 11
* **Runtime Requirement**: Python 3.8+ (Tkinter included in standard installations)

### Installation
Clone or download the repository to your local environment:

```bash
git clone https://github.com/your-username/clarify.git
cd clarify
```

Run the application directly:

```bash
python "Clarify (20206).py"
```

---

## How It Works

1. **Path Selection**: Specify the target **Source** directory. Optionally set a separate **Destination** directory (if left blank, files are reorganized within the source directory).
2. **Configure Protections**: Add critical directories to the **Protected Folders** list to ensure they are excluded from file moves or deduplication passes.
3. **Select Execution Parameters**:
   * Toggle **Date Subfolders** (`YYYY-MM-DD`) to organize inside extension folders.
   * Toggle **Timestamp Renaming** and pick between *Full*, *Prefix*, or *Suffix* modes.
   * Toggle optional cleanup tasks (**Delete zero-byte files**, **Delete empty directories**, **Grant universal access**).
4. **Execution**: Click **Start Organization**. Progress is logged in real-time within the UI text window. Click **Stop** at any time to break execution safely.

---

## Configuration & Error Logging

* **JSON Configuration (`clarify_config.json`)**: Saved preferences (directory paths, protected folders, renaming modes) automatically persist across sessions.
* **Error Log (`clarify_error.log`)**: When **Enable Error Log** is enabled, permission denials, locked file exceptions, or read errors write directly to this file with ISO 8601 timestamps for auditing.

---

## Safety & System Protection

To protect system integrity, Clarify enforces hardcoded path skips on the following directories:
* `C:\Windows`
* `C:\Program Files` & `C:\Program Files (x86)`
* `C:\ProgramData`
* `$Recycle.Bin`
* `System Volume Information`
* Boot and Recovery partitions

Files matching these path prefixes will be skipped during directory traversals.
