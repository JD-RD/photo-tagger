# Photo Tagger & Downloader Toolkit

A complete hybrid face recognition and cloud photo downloading CLI toolkit. This project provides tools to efficiently download photos from Dropbox and perform bulk face-tagging, either by recognizing known people or clustering unknown faces.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Downloading Photos (`photo-dl.py`)](#downloading-photos-photo-dlpy)
  - [Tagging Photos (`photo_tagger.py`)](#tagging-photos-photo_taggerpy)
- [Output](#output)
- [Tips](#tips)
- [Troubleshooting](#troubleshooting)

## Features

### Downloader (`photo-dl.py`)
- **Server-Side Search**: Uses Dropbox's `files_search_v2` API to quickly filter image files before downloading.
- **Concurrent Downloads**: Multi-threaded downloading (via `ThreadPoolExecutor`) bypasses sequential network bottlenecks.
- **Resume & Indexing**: Saves progress to a `.dropbox_index_{year}.json` file so interrupted runs can resume instantly.
- **Integrity Checks**: Validates local file sizes against Dropbox metadata to automatically detect and fix partial downloads.

### Tagger (`photo_tagger.py`)
- **Supervised Tagging**: Identifies known people by name using a reference directory of faces.
- **Unsupervised Clustering**: Groups unknown faces together automatically (optional).
- **Hybrid Approach**: Tags known people and clusters/skips the rest.
- **Visual Output**: Can generate copies of your photos with colored bounding boxes and labels drawn over faces.
- **Performance**: Uses HOG model by default (CPU-friendly) with optional CNN support for GPU acceleration.

## Installation

Because this project uses several data science and image processing libraries, it is recommended to run it inside a Python virtual environment.

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

## Configuration

Both scripts support loading secrets and configurations from a `.env` file to prevent hardcoding sensitive information.

Create a `.env` file in the root directory:

```env
# Required for photo-dl.py
DROPBOX_TOKEN=your_dropbox_access_token_here

# Optional defaults for photo_tagger.py
PHOTO_INPUT_DIR=/path/to/your/photos
```

## Usage

### Downloading Photos (`photo-dl.py`)

Download all photos from a specific year from your Dropbox `Camera Uploads` folder.

```bash
# Basic usage (downloads 2021 photos to a 'photos' directory)
.venv/bin/python photo-dl.py --year 2021 --output photos

# Dry run (list files without downloading)
.venv/bin/python photo-dl.py --year 2021 --dry-run

# Resume an interrupted run
.venv/bin/python photo-dl.py --year 2021 --output photos --resume

# Re-download only previously failed files
.venv/bin/python photo-dl.py --year 2021 --output photos --resume --retry-failed
```

### Tagging Photos (`photo_tagger.py`)

Before supervised tagging, set up a directory of known faces like this:
```text
known_faces/
├── Alice/
│   ├── alice_01.jpg
│   └── alice_02.jpg
└── Bob/
    └── bob_01.jpg
```

Run the tagger:

```bash
# Basic: just tag known people, ignore unknowns
.venv/bin/python photo_tagger.py --input photos --output ./results --known ./known_faces

# Cluster unknowns too
.venv/bin/python photo_tagger.py --input photos --output ./results --known ./known_faces --cluster-unknowns

# Full: cluster unknowns + draw colored bounding boxes on images
.venv/bin/python photo_tagger.py --input photos --output ./results \
    --known ./known_faces --cluster-unknowns --draw-boxes --format both
```

## Output

### JSON format (`tags.json`)
```json
[
  {
    "image_path": "photos/party_01.jpg",
    "person": "Alice",
    "type": "known",
    "confidence": 0.89,
    "face_location": [120, 450, 280, 290]
  },
  {
    "image_path": "photos/party_01.jpg",
    "person": "unknown_1",
    "type": "clustered",
    "confidence": null,
    "face_location": [340, 620, 500, 460]
  }
]
```

### CSV format (`tags.csv`)
The same data as JSON, but in tabular form.

### Tagged images (`tagged_images/`)
If ran with `--draw-boxes`, copies of original images are saved here with colored bounding boxes and labels:
- **Green**: Known person
- **Blue**: Clustered unknown
- **Orange**: Unclustered unknown

## Tips

- **Start small**: Test the tagger on a few photos first to tune `--tolerance`.
- **CNN model**: Use `--model cnn` if you have a GPU for much better accuracy.
- **Clustering**: HDBSCAN is used if available (better than DBSCAN) and falls back to DBSCAN if missing.
- **Performance**: The first run is slow as it encodes faces. Use `--save-encodings` to cache them.

## Troubleshooting

- **"No faces found"**: Try lowering tolerance or using the CNN model.
- **"Poor clustering"**: Adjust `--min-cluster-size` — higher values = fewer, tighter clusters.
- **Slow performance**: Ensure you are using the default `--model hog`. If it's still slow, ensure `dlib` is compiled with optimizations.
