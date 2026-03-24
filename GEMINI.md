# Photo Tagger & Downloader Toolkit

## Project Overview
This is a Python-based toolkit designed to download photos from Dropbox and perform hybrid face recognition to tag people within those photos. 

The project consists of two primary CLI tools:
1. **`photo-dl.py`**: A high-performance Dropbox photo downloader that fetches images by year. It features server-side search optimization, concurrent multi-threaded downloads, and an indexing system (`.dropbox_index_*.json`) to resume interrupted runs and skip already-downloaded files.
2. **`photo_tagger.py`**: A hybrid face recognition tool that tags known people by name using a reference directory, and optionally clusters unknown faces using HDBSCAN or DBSCAN. It can output metadata to JSON and CSV formats, and optionally generate copies of images with labeled bounding boxes.

## Building and Running

### Environment Setup
The project uses a Python virtual environment (`.venv`) to manage dependencies due to externally-managed-environment restrictions on the host system.
```bash
# Create and activate the virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### Configuration
The tools require a `.env` file in the root directory for secrets and default configurations. Make sure this file exists before running the scripts:
```env
DROPBOX_TOKEN=your_dropbox_access_token_here
PHOTO_INPUT_DIR=/path/to/your/photos
```

### Running the Tools

**1. Downloading Photos:**
```bash
# Download photos from 2021 to the 'photos' directory
.venv/bin/python photo-dl.py --year 2021 --output photos

# Resume an interrupted download and re-try any failed files
.venv/bin/python photo-dl.py --year 2021 --output photos --resume --retry-failed
```

**2. Tagging Photos:**
```bash
# Tag known faces and output results
.venv/bin/python photo_tagger.py --input photos --output ./results --known ./known_faces

# Tag known faces, cluster unknown faces, and generate images with bounding boxes
.venv/bin/python photo_tagger.py --input photos --output ./results --known ./known_faces --cluster-unknowns --draw-boxes
```

## Development Conventions
- **Dependency Management:** Keep `requirements.txt` unified for both scripts. If a new library is needed, add it there.
- **Secrets & Configuration:** Never hardcode sensitive tokens or local paths. Always use `os.environ` or `python-dotenv` to retrieve them from the `.env` file.
- **Performance Optimization:** 
  - Network-bound tasks (like downloading) should leverage concurrency, such as `concurrent.futures.ThreadPoolExecutor`.
  - CPU-bound tasks (like face encoding) should offer configurable models (e.g., `--model hog` vs `cnn`) and provide mechanisms to cache results (e.g., `--save-encodings`).
- **Data Privacy & Git:** Ensure that `.env` files, downloaded photo directories, temporary indexes (`.dropbox_index_*.json`), and the `.venv/` folder remain in `.gitignore` to prevent leaking private photos or credentials to version control.
- **Documentation:**
  - **Mandatory:** ALWAYS update `CHANGELOG.md` with a summary of any code modifications, new features, or security improvements made during a session.
  - Follow the existing formatting in `CHANGELOG.md` (e.g., categorizing changes under `Added`, `Changed`, `Fixed`, or `Security`).