# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **`organize_photos.py`**: A new standalone utility script that reads the `tags.json` output from `photo_tagger.py` and copies the tagged photos into separate subdirectories named after each person. If a photo contains multiple people, it is copied into each person's respective directory.
- **`prep_references.py`**: An interactive GUI helper tool to quickly build a high-quality `known_faces/` directory. It auto-detects faces in downloaded photos, crops them, displays them, and asks the user to name them via the terminal.

## [1.0.0] - 2026-03-23

### Added
- **`photo-dl.py`**: A new high-performance CLI tool to download photos from Dropbox by year.
  - **Server-side Search**: Optimized to use Dropbox's `files_search_v2` API, drastically reducing the time spent scanning large accounts.
  - **Concurrent Downloads**: Implemented multi-threading (via `ThreadPoolExecutor`) to download up to 5 files simultaneously, bypassing sequential network bottlenecks.
  - **Indexing & Resume**: Created a JSON-based tracking system (`.dropbox_index_{year}.json`) that allows the script to resume interrupted runs and skip already-downloaded files.
  - **Integrity Checks**: Added automatic file-size validation to detect and re-download corrupted or partial files.
  - **Live Progress**: Added real-time in-place status indicators for both the searching and downloading phases.
- **`.gitignore`**: Implemented a comprehensive ignore file to prevent sensitive `.env` files, photos, virtual environments, and caches from being committed to the repository.

### Changed
- **`photo_tagger.py`**: Integrated `python-dotenv` to automatically load local configuration (like `PHOTO_INPUT_DIR`) from a `.env` file.
- **`requirements.txt`**: Unified dependencies for both scripts, adding `python-dotenv` and `dropbox`.
- **Documentation**: Updated `README.md` and `GEMINI.md` to use `.venv/bin/python` or `python3` for better compatibility with Linux distributions (like Linux Mint) where the `python` command is unmapped.

### Fixed
- **Face Recognition Models Error**: Resolved the `ModuleNotFoundError: No module named 'pkg_resources'` by pinning `setuptools==69.5.1` in `requirements.txt`. This ensures the models used by `face_recognition` can be correctly loaded.
- **Linux Compatibility**: Resolved "command 'python' not found" errors by explicitly documenting the use of `python3` and virtual environment paths.

### Security
- **Credential Protection**: Migrated hardcoded tokens and paths to environment variables.
- **Privacy**: Configured Git to strictly ignore the `photos/` directory and `.env` secrets.
