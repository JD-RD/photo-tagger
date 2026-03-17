# Photo Tagger

Hybrid face recognition CLI tool for bulk-tagging people in photos.

## Features

- **Supervised**: Tag known people by name using a reference folder
- **Unsupervised**: Cluster unknown faces (optional)
- **Hybrid**: Mix of both — known people get names, unknowns get clustered or skipped
- **Fast**: Uses HOG model by default (CPU-friendly), optional CNN for GPU acceleration
- **Flexible output**: JSON, CSV, or both
- **Visual**: Optionally generate images with labeled bounding boxes

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### 1. Set up known faces (optional, for supervised tagging)

```
known_faces/
├── Alice/
│   ├── alice_01.jpg
│   └── alice_02.jpg
├── Bob/
│   ├── bob_01.jpg
│   └── bob_02.jpg
└── Mom/
    └── mom_photo.jpg
```

### 2. Run the tagger

```bash
# Basic: just tag known people, ignore unknowns
python photo_tagger.py --input ~/Photos/2024 --output ./results --known ./known_faces

# Cluster unknowns too
python photo_tagger.py --input ~/Photos/2024 --output ./results --known ./known_faces --cluster-unknowns

# Full: cluster unknowns + draw boxes on images
python photo_tagger.py --input ~/Photos/2024 --output ./results \
    --known ./known_faces --cluster-unknowns --draw-boxes --format both
```

## Usage

```
python photo_tagger.py --input DIR --output DIR [options]

Options:
  --input, -i           Directory containing photos to tag (required)
  --output, -o          Output directory for results (required)
  --known, -k           Directory of known faces (subfolders = person names)
  --model               Face detection: 'hog' (CPU, default) or 'cnn' (GPU)
  --tolerance, -t       Matching strictness (default: 0.6, lower = stricter)
  --cluster-unknowns    Group unknown faces into clusters
  --min-cluster-size    Minimum faces to form a cluster (default: 2)
  --draw-boxes          Create images with labeled bounding boxes
  --format              Output: 'json', 'csv', or 'both' (default: json)
  --save-encodings      Save face encodings to pickle file for reuse
```

## Output

### JSON format (`tags.json`)
```json
[
  {
    "image_path": "/home/user/Photos/2024/party_01.jpg",
    "person": "Alice",
    "type": "known",
    "confidence": 0.89,
    "face_location": [120, 450, 280, 290]
  },
  {
    "image_path": "/home/user/Photos/2024/party_01.jpg",
    "person": "unknown_1",
    "type": "clustered",
    "confidence": null,
    "face_location": [340, 620, 500, 460]
  }
]
```

### CSV format (`tags.csv`)
Same data as JSON, in tabular form.

### Tagged images (`tagged_images/`)
Copies of original images with colored bounding boxes and labels:
- **Green**: Known person
- **Blue**: Clustered unknown
- **Orange**: Unclustered unknown

## Tips

- **Start small**: Test on a few photos first to tune `--tolerance`
- **CNN model**: Use `--model cnn` if you have a GPU for better accuracy
- **Clustering**: HDBSCAN is used if available (better than DBSCAN), falls back to DBSCAN
- **Performance**: First run is slow (encoding faces). Use `--save-encodings` to cache.

## Troubleshooting

**"No faces found"**: Try lowering tolerance or using CNN model

**"Poor clustering"**: Adjust `--min-cluster-size` — higher values = fewer, tighter clusters

**Slow performance**: Use `--model hog` (default) and ensure dlib is compiled with optimizations
