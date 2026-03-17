#!/usr/bin/env python3
"""
Photo Tagger - Hybrid face recognition CLI tool.
Tags known people by name, clusters unknowns (or skips them).
"""

import os
import sys
import json
import csv
import pickle
import argparse
from pathlib import Path
from collections import defaultdict

import cv2
import face_recognition
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm
import numpy as np

try:
    from hdbscan import HDBSCAN
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False
    from sklearn.cluster import DBSCAN


def load_known_faces(known_dir):
    """Load known faces from directory structure: known_dir/PersonName/image.jpg"""
    known_encodings = []
    known_names = []
    
    if not known_dir or not os.path.exists(known_dir):
        return known_encodings, known_names
    
    print(f"Loading known faces from: {known_dir}")
    
    for person_name in tqdm(os.listdir(known_dir), desc="Loading known people"):
        person_path = os.path.join(known_dir, person_name)
        if not os.path.isdir(person_path):
            continue
            
        for img_name in os.listdir(person_path):
            img_path = os.path.join(person_path, img_name)
            if not img_name.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                continue
                
            try:
                image = face_recognition.load_image_file(img_path)
                encodings = face_recognition.face_encodings(image)
                
                if encodings:
                    known_encodings.append(encodings[0])
                    known_names.append(person_name)
            except Exception as e:
                print(f"  Warning: Could not process {img_path}: {e}")
    
    print(f"Loaded {len(known_encodings)} face(s) for {len(set(known_names))} person(s)")
    return known_encodings, known_names


def process_images(input_dir, known_encodings, known_names, model="hog", tolerance=0.6):
    """Process all images and extract face data."""
    results = []
    unknown_encodings = []
    unknown_locations = []  # (image_path, face_location)
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    image_files = [
        f for f in Path(input_dir).rglob('*')
        if f.suffix.lower() in image_extensions
    ]
    
    print(f"\nProcessing {len(image_files)} images...")
    
    for img_path in tqdm(image_files, desc="Scanning photos"):
        try:
            image = face_recognition.load_image_file(img_path)
            face_locations = face_recognition.face_locations(image, model=model)
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            image_faces = []
            
            for face_encoding, face_location in zip(face_encodings, face_locations):
                # Check against known faces first
                if known_encodings:
                    matches = face_recognition.compare_faces(
                        known_encodings, face_encoding, tolerance=tolerance
                    )
                    face_distances = face_recognition.face_distance(
                        known_encodings, face_encoding
                    )
                    
                    if True in matches:
                        best_match_index = np.argmin(face_distances)
                        name = known_names[best_match_index]
                        confidence = 1 - face_distances[best_match_index]
                    else:
                        name = None
                        confidence = None
                else:
                    name = None
                    confidence = None
                
                if name:
                    image_faces.append({
                        'name': name,
                        'confidence': float(confidence),
                        'location': face_location,
                        'type': 'known'
                    })
                else:
                    # Unknown face - store for potential clustering
                    unknown_encodings.append(face_encoding)
                    unknown_locations.append((str(img_path), face_location, len(image_faces)))
                    image_faces.append({
                        'name': None,
                        'confidence': None,
                        'location': face_location,
                        'type': 'unknown'
                    })
            
            results.append({
                'image_path': str(img_path),
                'faces': image_faces
            })
            
        except Exception as e:
            print(f"  Error processing {img_path}: {e}")
    
    return results, unknown_encodings, unknown_locations


def cluster_unknowns(unknown_encodings, unknown_locations, results, min_cluster_size=2):
    """Cluster unknown faces and assign labels like 'unknown_1', 'unknown_2', etc."""
    if len(unknown_encodings) < min_cluster_size:
        print(f"\nNot enough unknown faces ({len(unknown_encodings)}) for clustering")
        return results
    
    print(f"\nClustering {len(unknown_encodings)} unknown faces...")
    
    # Use HDBSCAN if available, otherwise DBSCAN
    if HDBSCAN_AVAILABLE:
        clusterer = HDBSCAN(min_cluster_size=min_cluster_size, metric='euclidean')
    else:
        # DBSCAN with eps tuned for 128D face embeddings
        clusterer = DBSCAN(eps=0.5, min_samples=min_cluster_size, metric='euclidean')
    
    labels = clusterer.fit_predict(unknown_encodings)
    
    # Assign cluster labels to results
    cluster_names = {}
    next_cluster = 1
    
    for (img_path, face_location, face_idx), label in zip(unknown_locations, labels):
        if label == -1:  # Noise point - unclustered
            name = f"unknown_unclustered"
        else:
            if label not in cluster_names:
                cluster_names[label] = f"unknown_{next_cluster}"
                next_cluster += 1
            name = cluster_names[label]
        
        # Find and update the corresponding result
        for result in results:
            if result['image_path'] == img_path:
                if face_idx < len(result['faces']):
                    result['faces'][face_idx]['name'] = name
                    result['faces'][face_idx]['type'] = 'clustered'
                break
    
    clustered_count = sum(1 for l in labels if l != -1)
    print(f"  Created {len(cluster_names)} cluster(s) with {clustered_count} face(s)")
    print(f"  {len(labels) - clustered_count} face(s) remain unclustered")
    
    return results


def save_results(results, output_dir, format='json'):
    """Save results to JSON or CSV."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Flatten results for output
    flat_results = []
    for result in results:
        for face in result['faces']:
            flat_results.append({
                'image_path': result['image_path'],
                'person': face['name'],
                'type': face['type'],
                'confidence': face.get('confidence'),
                'face_location': face['location']
            })
    
    if format == 'json':
        output_file = output_path / 'tags.json'
        with open(output_file, 'w') as f:
            json.dump(flat_results, f, indent=2)
        print(f"\nSaved JSON: {output_file}")
    
    elif format == 'csv':
        output_file = output_path / 'tags.csv'
        with open(output_file, 'w', newline='') as f:
            if flat_results:
                writer = csv.DictWriter(f, fieldnames=flat_results[0].keys())
                writer.writeheader()
                writer.writerows(flat_results)
        print(f"\nSaved CSV: {output_file}")
    
    return output_file


def draw_boxes_on_images(results, output_dir):
    """Create copies of images with labeled bounding boxes."""
    output_path = Path(output_dir) / 'tagged_images'
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\nCreating tagged images in: {output_path}")
    
    # Color scheme
    colors = {
        'known': (0, 255, 0),      # Green
        'unknown': (255, 165, 0),  # Orange
        'clustered': (0, 191, 255) # Deep sky blue
    }
    
    for result in tqdm(results, desc="Drawing boxes"):
        try:
            # Load image
            image = Image.open(result['image_path'])
            draw = ImageDraw.Draw(image)
            
            # Try to load a font, fall back to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            # Draw boxes and labels
            for face in result['faces']:
                top, right, bottom, left = face['location']
                name = face['name']
                face_type = face['type']
                
                color = colors.get(face_type, (128, 128, 128))
                
                # Draw rectangle
                draw.rectangle([left, top, right, bottom], outline=color, width=3)
                
                # Draw label background
                label = name if name else "unknown"
                bbox = draw.textbbox((0, 0), label, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                draw.rectangle(
                    [left, top - text_height - 4, left + text_width + 4, top],
                    fill=color
                )
                
                # Draw label text
                draw.text((left + 2, top - text_height - 2), label, fill=(0, 0, 0), font=font)
            
            # Save tagged image
            rel_path = Path(result['image_path']).relative_to(Path(result['image_path']).anchor.lstrip('/'))
            out_file = output_path / rel_path.name
            counter = 1
            while out_file.exists():
                stem = out_file.stem
                if '_' in stem and stem.rsplit('_', 1)[1].isdigit():
                    stem = stem.rsplit('_', 1)[0]
                out_file = output_path / f"{stem}_{counter}{out_file.suffix}"
                counter += 1
            
            image.save(out_file)
            
        except Exception as e:
            print(f"  Error drawing on {result['image_path']}: {e}")
    
    print(f"  Saved {len(results)} tagged image(s)")


def main():
    parser = argparse.ArgumentParser(
        description='Tag photos with face recognition. Known people by name, unknowns clustered or skipped.'
    )
    parser.add_argument('--input', '-i', required=True, help='Directory containing photos to tag')
    parser.add_argument('--output', '-o', required=True, help='Output directory for results')
    parser.add_argument('--known', '-k', help='Directory of known faces (subfolders named after people)')
    parser.add_argument('--model', choices=['hog', 'cnn'], default='hog',
                        help='Face detection model: hog (CPU, faster) or cnn (GPU, more accurate)')
    parser.add_argument('--tolerance', '-t', type=float, default=0.6,
                        help='Face matching tolerance (lower = stricter, default: 0.6)')
    parser.add_argument('--cluster-unknowns', action='store_true',
                        help='Cluster unknown faces into groups')
    parser.add_argument('--min-cluster-size', type=int, default=2,
                        help='Minimum faces to form a cluster (default: 2)')
    parser.add_argument('--draw-boxes', action='store_true',
                        help='Create copies of images with labeled bounding boxes')
    parser.add_argument('--format', choices=['json', 'csv', 'both'], default='json',
                        help='Output format')
    parser.add_argument('--save-encodings', action='store_true',
                        help='Save face encodings to pickle file for reuse')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.input):
        print(f"Error: Input directory not found: {args.input}")
        sys.exit(1)
    
    if args.known and not os.path.exists(args.known):
        print(f"Warning: Known faces directory not found: {args.known}")
        args.known = None
    
    # Load known faces
    known_encodings, known_names = load_known_faces(args.known)
    
    # Process images
    results, unknown_encodings, unknown_locations = process_images(
        args.input, known_encodings, known_names, model=args.model, tolerance=args.tolerance
    )
    
    # Cluster unknowns if requested
    if args.cluster_unknowns and unknown_encodings:
        results = cluster_unknowns(results, unknown_encodings, unknown_locations, args.min_cluster_size)
    
    # Save results
    if args.format in ('json', 'both'):
        save_results(results, args.output, 'json')
    if args.format in ('csv', 'both'):
        save_results(results, args.output, 'csv')
    
    # Save encodings if requested
    if args.save_encodings:
        encodings_file = Path(args.output) / 'encodings.pkl'
        with open(encodings_file, 'wb') as f:
            pickle.dump({
                'known_encodings': known_encodings,
                'known_names': known_names,
                'unknown_encodings': unknown_encodings if args.cluster_unknowns else []
            }, f)
        print(f"Saved encodings: {encodings_file}")
    
    # Draw boxes if requested
    if args.draw_boxes:
        draw_boxes_on_images(results, args.output)
    
    # Print summary
    total_faces = sum(len(r['faces']) for r in results)
    known_count = sum(1 for r in results for f in r['faces'] if f['type'] == 'known')
    unknown_count = sum(1 for r in results for f in r['faces'] if f['type'] == 'unknown')
    clustered_count = sum(1 for r in results for f in r['faces'] if f['type'] == 'clustered')
    
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"Images processed: {len(results)}")
    print(f"Total faces found: {total_faces}")
    print(f"  Known: {known_count}")
    if args.cluster_unknowns:
        print(f"  Clustered unknowns: {clustered_count}")
        print(f"  Unclustered: {unknown_count}")
    else:
        print(f"  Unknown (not clustered): {unknown_count}")
    print(f"\nOutput saved to: {args.output}")


if __name__ == '__main__':
    main()
