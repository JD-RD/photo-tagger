#!/usr/bin/env python3
"""
Prep References - Interactive tool to build a known_faces/ directory.
Scans photos, detects faces, crops them with a margin, displays them, and asks for a name.
"""

import os
import sys
import argparse
import uuid
from pathlib import Path

import cv2
import face_recognition
import numpy as np
from PIL import Image, ImageOps

def load_image_exif_corrected(path):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return np.array(img)

def main():
    parser = argparse.ArgumentParser(description="Interactive tool to build a known_faces/ directory.")
    parser.add_argument("--input", "-i", default="photos", help="Directory containing photos to scan (default: photos)")
    parser.add_argument("--output", "-o", default="known_faces", help="Output directory for known faces (default: known_faces)")
    parser.add_argument("--margin", type=float, default=0.5, help="Margin ratio around the face (default: 0.5)")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists():
        print(f"❌ Error: Input directory '{input_dir}' not found.")
        print("Make sure you have downloaded some photos first!")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    image_files = [
        f for f in input_dir.rglob('*')
        if f.suffix.lower() in image_extensions
    ]

    print(f"📸 Found {len(image_files)} images in '{input_dir}'.")
    print("An image window will pop up. For each face:")
    print("  - Type the person's name and press Enter to save.")
    print("  - Just press Enter (empty name) to skip the face.")
    print("  - Type 'QUIT' to exit the script.")
    print("-" * 50)

    cv2.namedWindow("Face", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Face", 400, 400)

    try:
        for img_path in image_files:
            try:
                image = load_image_exif_corrected(img_path)
                # face_recognition uses RGB, opencv uses BGR for display
                image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                
                # Use HOG model (faster for scanning)
                face_locations = face_recognition.face_locations(image, model="hog")
                
                if not face_locations:
                    continue
                    
                for top, right, bottom, left in face_locations:
                    # Add margin
                    height = bottom - top
                    width = right - left
                    
                    margin_h = int(height * args.margin)
                    margin_w = int(width * args.margin)
                    
                    new_top = max(0, top - margin_h)
                    new_bottom = min(image.shape[0], bottom + margin_h)
                    new_left = max(0, left - margin_w)
                    new_right = min(image.shape[1], right + margin_w)
                    
                    face_crop = image_bgr[new_top:new_bottom, new_left:new_right]
                    
                    if face_crop.size == 0:
                        continue
                    
                    # Show the face in the GUI window
                    cv2.imshow("Face", face_crop)
                    cv2.waitKey(1)  # Required to refresh the OpenCV window
                    
                    print(f"\n👀 Showing face from {img_path.name}")
                    name = input("Who is this? (Enter to skip, 'QUIT' to exit): ").strip()
                    
                    if name.upper() == 'QUIT':
                        print("Exiting...")
                        cv2.destroyAllWindows()
                        return
                    
                    if not name:
                        continue
                    
                    # Save the face
                    person_dir = output_dir / name
                    person_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Generate unique filename
                    filename = f"{name.replace(' ', '_').lower()}_{uuid.uuid4().hex[:8]}.jpg"
                    save_path = person_dir / filename
                    
                    cv2.imwrite(str(save_path), face_crop)
                    print(f"✅ Saved to {save_path}")
                    
            except Exception as e:
                print(f"  ⚠️ Error processing {img_path.name}: {e}")

    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")
    finally:
        cv2.destroyAllWindows()
        print("\nDone scanning images.")

if __name__ == "__main__":
    main()