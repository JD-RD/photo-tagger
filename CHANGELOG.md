# Changelog

All notable changes to this project will be documented in this file.

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
- **Linux Compatibility**: Resolved "command 'python' not found" errors by explicitly documenting the use of `python3` and virtual environment paths.

### Security
- **Credential Protection**: Migrated hardcoded tokens and paths to environment variables.
- **Privacy**: Configured Git to strictly ignore the `photos/` directory and `.env` secrets.
