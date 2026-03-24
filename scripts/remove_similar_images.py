import argparse
import shutil
from pathlib import Path
from typing import Dict, Optional

import cv2
import numpy as np
from astropy.io import fits

ASTROPY_AVAILABLE = True


def dhash(image: np.ndarray, hash_size: int = 8) -> int:
    """
    Compute the difference hash (dHash) of an image.
    1. Resize to (hash_size + 1, hash_size).
    2. Convert to grayscale.
    3. Compute differences between adjacent pixels.
    4. Build the hash.
    """
    # Resize the image. aspect ratio is ignored.
    # cv2.resize expects (width, height)
    resized = cv2.resize(image, (hash_size + 1, hash_size))

    # Convert to grayscale if needed
    if len(resized.shape) == 3 and resized.shape[2] == 3:
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    else:
        gray = resized

    # Compute differences between adjacent columns
    diff = gray[:, 1:] > gray[:, :-1]

    # Convert binary array to integer hash
    return sum([2**i for (i, v) in enumerate(diff.flatten()) if v])


def load_image_data(file_path: Path) -> Optional[np.ndarray]:
    """
    Load image data from file path.
    Handles FITS files by normalizing and converting to 8-bit.
    Handles standard image files using cv2.
    """
    suffix = file_path.suffix.lower()

    if suffix in [".fits", ".fit"]:
        if not ASTROPY_AVAILABLE:
            return None

        try:
            with fits.open(file_path) as hdul:
                # Usually the image data is in the primary HDU (index 0)
                data = hdul[0].data

                # If primary HDU is empty, check extension 1 (common in compressed FITS)
                if data is None and len(hdul) > 1:
                    data = hdul[1].data

                if data is None:
                    return None

                # Cast to float for normalization
                img_data = data.astype(float)

                # Normalize to 0-1 range
                min_val = np.min(img_data)
                max_val = np.max(img_data)

                # Avoid division by zero
                if max_val - min_val != 0:
                    img_data = (img_data - min_val) / (max_val - min_val)
                else:
                    img_data = np.zeros_like(img_data)

                # Convert to 8-bit (0-255) for consistent hashing with PNGs
                img_data = (img_data * 255).astype(np.uint8)
                return img_data

        except Exception as e:
            print(f"Error loading FITS file {file_path}: {e}")
            return None

    elif suffix in [".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"]:
        try:
            # Load as grayscale directly
            # Check if file exists to avoid open errors
            if not file_path.exists():
                return None
            img = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
            return img
        except Exception as e:
            print(f"Error loading image file {file_path}: {e}")
            return None

    return None


def hamming_distance(hash1: int, hash2: int) -> int:
    """Calculate the Hamming distance between two hashes."""
    # XOR the two hashes and count the number of set bits (population count)
    return bin(hash1 ^ hash2).count("1")


def find_and_remove_duplicates(
    data_dir: Path, threshold: int, action: str, move_dir: Path, recursive: bool = False
):
    """
    Find and remove duplicate/similar images in the data directory.
    """
    if not data_dir.exists():
        print(f"Data directory '{data_dir}' does not exist.")
        return

    if action == "move":
        move_dir.mkdir(parents=True, exist_ok=True)

    # Gather files
    pattern = "**/*" if recursive else "*"
    # Handle files recursively or flat
    files = sorted([f for f in data_dir.glob(pattern) if f.is_file()])

    print(f"Found {len(files)} files in {data_dir}. Computing hashes...")

    hashes: Dict[int, Path] = {}
    duplicates_found = 0

    for file_path in files:
        # Load image data
        image_data = load_image_data(file_path)

        if image_data is None:
            continue

        # Compute hash
        try:
            img_hash = dhash(image_data)
        except Exception as e:
            print(f"Error computing hash for {file_path}: {e}")
            continue

        # Check for similarity with existing hashes
        is_duplicate = False
        original_file = None
        min_dist = float("inf")

        # Check against all known hashes
        # Note: Depending on threshold, this can be slow if there are many images
        # For dHash, checking all is the simplest way.
        for h, existing_path in hashes.items():
            dist = hamming_distance(img_hash, h)
            if dist <= threshold:
                # If multiple existing images are similar,
                # picking the one with smallest dist is reasonable,
                # but "first match" logic is simpler and
                # sufficient for duplicate removal.
                # However, iterating all to find best match
                # might prevent false positives near threshold?
                if dist < min_dist:
                    min_dist = dist
                    original_file = existing_path
                    is_duplicate = True

        if is_duplicate:
            duplicates_found += 1
            print(f"Duplicate found: {file_path.name} \
                is similar to {original_file.name} (Distance: {min_dist})")

            # Handle duplicate
            if action == "delete":
                try:
                    file_path.unlink()
                    print(f"  -> Deleted {file_path.name}")
                except Exception as e:
                    print(f"  -> Error deleting {file_path.name}: {e}")
            elif action == "move":
                try:
                    dest = move_dir / file_path.name
                    # Handle name collision in destination
                    if dest.exists():
                        base = dest.stem
                        ext = dest.suffix
                        counter = 1
                        while dest.exists():
                            dest = move_dir / f"{base}_{counter}{ext}"
                            counter += 1

                    shutil.move(str(file_path), str(dest))
                    print(f"  -> Moved {file_path.name} to {dest}")
                except Exception as e:
                    print(f"  -> Error moving {file_path.name}: {e}")
        else:
            hashes[img_hash] = file_path

    print(
        f"Summary: Processed {len(files)} files. Found {duplicates_found} duplicates."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clean up similar images from a directory."
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Directory containing images to check.",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=5,
        help="Hamm. dist. thresh for similarity \
            (0-64, lower means more strict). Default 5.",
    )
    parser.add_argument(
        "--action",
        type=str,
        choices=["delete", "move"],
        default="move",
        help="Action to take on duplicates.",
    )
    parser.add_argument(
        "--move-dir",
        type=str,
        default="duplicates",
        help="Directory to move duplicates to (if action is move).",
    )
    parser.add_argument(
        "--recursive", action="store_true", help="Search recursively in subdirectories."
    )

    args = parser.parse_args()

    find_and_remove_duplicates(
        Path(args.data_dir),
        args.threshold,
        args.action,
        Path(args.move_dir),
        args.recursive,
    )
