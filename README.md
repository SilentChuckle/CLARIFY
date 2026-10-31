# CLARIFY - File Organizer

Clarify tidies a messy folder. Point it at a source folder, tick how you want files grouped, and it moves every file into a tidy tree of subfolders, for example `Sorted / Images / 2026 / 10-October / photo.jpg`.

It has a desktop window (Tkinter) and a small command-line entry point. It uses only Python's standard library, so there is nothing to install.

## Features

- **Flexible sorting**: choose any combination, in the order you want: File Extension, Year, Month, Day, Hour, File Category, Day of Week, Quarter, Size Range, File Age.
- **Duplicate purge**: when a file with the same name already exists at the destination and has the same SHA-256 fingerprint, the extra copy is deleted. A different file with the same name gets a number (`name_1.jpg`). Nothing is ever overwritten.
- **Preview mode**: tick "Preview only" to see what would happen without moving, renaming or deleting anything.
- **Timestamp renaming**: rename files by their date/time.
- **Cleanup**: optionally delete zero-byte files and empty folders.
- **Access repair**: optionally give your own account full access to files Windows locked you out of.
- **Protected and exempt items**: system folders, your Protected Folders, and anything matching an exempt keyword or path are never touched, including everything below a matching folder.

## Requirements

- Windows 10 / 11
- Python 3.8 or newer (Tkinter is included with standard installs)

## Usage

```bash
git clone https://github.com/Merely-Human/CLARIFY.git
cd CLARIFY
python Clarify_File_Organizer.py
```

Double-clicking `Clarify_File_Organizer.py` also works. To pre-fill the folders from the command line:

```bash
python Clarify_File_Organizer.py --source D:\Downloads --dest D:\Sorted
```

Run with **Preview only** ticked first.

## Safety

- Windows system folders (`Windows`, `Program Files`, `$Recycle.Bin`, `System Volume Information` and similar) and your Protected Folders are never touched.
- Duplicates are purged only when the name and SHA-256 fingerprint match exactly.
- Settings are saved next to the script in `clarify_config.json`. The optional error log (`clarify_error.log`) lists file paths only, never file contents.
- The program writes nothing to disk unless you ask it to.

## License

MIT. See [LICENSE](LICENSE).
