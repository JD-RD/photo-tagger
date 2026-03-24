#!/usr/bin/env python3
"""
Dropbox Photo Downloader - Download photos from a specific year from Dropbox.

Basic usage (searches Camera Uploads):
    python photo-dl.py --token YOUR_TOKEN --year 2021

Dry run (list files without downloading):
    python photo-dl.py --token YOUR_TOKEN --year 2021 --dry-run

Custom output directory:
    python photo-dl.py --token YOUR_TOKEN --year 2021 --output ~/Downloads/Photos2021

Resume an interrupted run (skips scan, uses saved index):
    python photo-dl.py --token YOUR_TOKEN --year 2021 --resume

Re-download only previously failed files:
    python photo-dl.py --token YOUR_TOKEN --year 2021 --resume --retry-failed
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

PHOTO_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".heic", ".heif",
    ".bmp", ".tiff", ".tif", ".webp", ".raw", ".cr2",
    ".nef", ".arw", ".dng", ".orf", ".rw2"
}

def get_dropbox_client(token: str):
    try:
        import dropbox
    except ImportError:
        print("❌ dropbox package not found. Run: pip install dropbox tqdm")
        sys.exit(1)

    dbx = dropbox.Dropbox(token)
    try:
        account = dbx.users_get_current_account()
        print(f"✅ Connected as: {account.name.display_name} ({account.email})\n")
    except dropbox.exceptions.AuthError:
        print("❌ Invalid Dropbox token. Check your credentials.")
        sys.exit(1)
    return dbx

def search_photos(dbx, folder: str, year: int):
    """
    Use Dropbox's server-side search to find only image files, then
    filter locally by year. Much faster than listing every file.
    """
    import dropbox

    seen_ids = set()
    total_hits = 0

    search_opts = dropbox.files.SearchOptions(
        path=folder or None,
        file_categories=[dropbox.files.FileCategory.image],
        max_results=1000,
    )

    print(f"🔎 Searching Dropbox for images in '{folder or '/'}' ...")

    # Sort extensions so the progress indicator is predictable
    for i, ext in enumerate(sorted(PHOTO_EXTENSIONS), 1):
        # Print progress in-place to keep output clean but informative
        print(f"\r  ... querying {ext} ({i}/{len(PHOTO_EXTENSIONS)}) - found {total_hits} total hits so far ...", end="", flush=True)
        try:
            query_result = dbx.files_search_v2(ext, options=search_opts)
            while True:
                for match in query_result.matches:
                    md = match.metadata.get_metadata()
                    if not isinstance(md, dropbox.files.FileMetadata):
                        continue
                    total_hits += 1
                    if md.id in seen_ids:
                        continue
                    seen_ids.add(md.id)

                    if is_photo(md.path_lower) and photo_year(md) == year:
                        yield md

                if not query_result.has_more:
                    break
                query_result = dbx.files_search_continue_v2(query_result.cursor)
        except dropbox.exceptions.ApiError as e:
            print(f"\n  ⚠️ API error for '{ext}': {e}")

    print(f"\n  ... search returned {total_hits} image hit(s) from Dropbox.")

# -- Index helpers -------------------------------------------------------------

INDEX_VERSION = 1

def index_path(output_dir: Path, year: int) -> Path:
    return output_dir / f".dropbox_index_{year}.json"

def load_index(path: Path) -> dict:
    """Load existing index or return a fresh one."""
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
            print(f"📋 Loaded existing index: {len(data['files'])} file(s) tracked.\n")
            return data
        except (json.JSONDecodeError, KeyError):
            print("⚠️ Index file corrupt — starting fresh.\n")
    return {"version": INDEX_VERSION, "created_at": _now(), "files": {}}

def save_index(path: Path, index: dict):
    index["updated_at"] = _now()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(index, f, indent=2)
    tmp.replace(path)   # atomic on POSIX

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def entry_to_record(entry, local_path: Path) -> dict:
    """Serialize a Dropbox FileMetadata entry into an index record."""
    return {
        "dropbox_path": entry.path_display,
        "dropbox_id":   entry.id,
        "local_path":   str(local_path),
        "size":         entry.size,
        "client_modified": entry.client_modified.isoformat() if entry.client_modified else None,
        "server_modified": entry.server_modified.isoformat() if entry.server_modified else None,
        "content_hash": entry.content_hash,
        "status":       "pending",   # pending | done | failed
        "downloaded_at": None,
        "error": None,
    }

def is_photo(path: str) -> bool:
    return Path(path).suffix.lower() in PHOTO_EXTENSIONS

def photo_year(entry) -> int | None:
    """Return the year of a photo, preferring client_modified over server_modified."""
    dt = entry.client_modified or entry.server_modified
    return dt.year if dt else None

def download_file(dbx, dropbox_path: str, local_path: Path, retries: int = 3):
    """Download a single file with retry logic."""
    import dropbox

    local_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, retries + 1):
        try:
            _, response = dbx.files_download(dropbox_path)
            with open(local_path, "wb") as f:
                f.write(response.content)
            return True
        except dropbox.exceptions.ApiError as e:
            print(f"\n  ⚠️ API error (attempt {attempt}/{retries}): {e}")
        except Exception as e:
            print(f"\n  ⚠️ Error (attempt {attempt}/{retries}): {e}")
        if attempt < retries:
            time.sleep(2 ** attempt)  # exponential back-off

    return False

def human_size(n_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} TB"

def _build_local_path(entry, output_dir: Path, folder: str, flat: bool) -> Path:
    if flat:
        return output_dir / Path(entry.path_display).name
    rel = entry.path_display.lstrip("/")
    if folder:
        prefix = folder.strip("/") + "/"
        if rel.lower().startswith(prefix.lower()):
            rel = rel[len(prefix):]
    return output_dir / rel

def main():
    parser = argparse.ArgumentParser(
        description="Download photos from a specific year from Dropbox.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--token",        help="Dropbox access token (or set DROPBOX_TOKEN env var)")
    parser.add_argument("--year",         type=int, required=True, help="4-digit year, e.g. 2021")
    parser.add_argument("--folder",       default="/Camera Uploads",   help="Dropbox folder to search (default: /Camera Uploads)")
    parser.add_argument("--output",       default=None, help="Local output directory (default: ./dropbox_photos_YEAR)")
    parser.add_argument("--dry-run",      action="store_true", help="List matching files without downloading")
    parser.add_argument("--flat",         action="store_true", help="Save all files in one flat directory (no subdirs)")
    parser.add_argument("--resume",       action="store_true", help="Skip scan and reuse the saved index")
    parser.add_argument("--retry-failed", action="store_true", help="With --resume, re-attempt previously failed files only")
    args = parser.parse_args()

    # -- Token resolution ------------------------------------------------------
    token = args.token or os.environ.get("DROPBOX_TOKEN")
    if not token:
        print("❌ No token provided. Use --token or set DROPBOX_TOKEN env var.")
        sys.exit(1)

    # -- Output directory ------------------------------------------------------
    output_dir = Path(args.output) if args.output else Path(f"dropbox_photos_{args.year}")
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"💾 Saving to: {output_dir.resolve()}\n")

    idx_path = index_path(output_dir, args.year)

    # -- Connect ---------------------------------------------------------------
    dbx = get_dropbox_client(token)

    # -- Scan or resume --------------------------------------------------------
    index = load_index(idx_path)

    if args.resume and index["files"]:
        print(f"⏩ Resuming from saved index ({len(index['files'])} file(s)).\n")
    else:
        if args.resume:
            print("⚠️ --resume requested but no index found — running full scan.\n")

        new_count = 0
        try:
            for entry in search_photos(dbx, args.folder.rstrip("/"), args.year):
                local_path = _build_local_path(entry, output_dir, args.folder, args.flat)
                key = entry.id  # stable Dropbox file ID
                if key not in index["files"]:
                    index["files"][key] = entry_to_record(entry, local_path)
                    new_count += 1
        except Exception as e:
            print(f"\n❌ Scan interrupted: {e}")
            print(f"💾 Saving partial index ({len(index['files'])} file(s)) ...")
            save_index(idx_path, index)
            sys.exit(1)

        save_index(idx_path, index)
        print(f"\n📸 Found {len(index['files'])} photo(s) from {args.year} "
              f"({new_count} new).\n")

    if not index["files"]:
        print("Nothing to download. Exiting.")
        return

    # -- Dry run ---------------------------------------------------------------
    if args.dry_run:
        pending = [r for r in index["files"].values() if r["status"] != "done"]
        print(f"DRY RUN — {len(pending)} file(s) pending download:")
        for r in pending:
            print(f"  {r['dropbox_path']}  ({human_size(r['size'])})")
        print(f"\nIndex saved to: {idx_path}")
        return

    # -- Determine what to download --------------------------------------------
    if args.retry_failed:
        to_download = [r for r in index["files"].values() if r["status"] == "failed"]
        print(f"🔁 Retrying {len(to_download)} failed file(s).\n")
    else:
        to_download = [r for r in index["files"].values() if r["status"] != "done"]

    if not to_download:
        print("✅ All files already downloaded. Nothing to do.")
        return

    # -- Download --------------------------------------------------------------
    try:
        from tqdm import tqdm
        use_tqdm = True
    except ImportError:
        use_tqdm = False

    import concurrent.futures

    ok = skipped = failed = 0
    total_bytes = 0

    def process_record(record):
        local_path = Path(record["local_path"])

        # Check if file exists and size matches
        if local_path.exists() and record["status"] != "failed":
            if local_path.stat().st_size == record["size"]:
                return record, "skipped", 0

        success = download_file(dbx, record["dropbox_path"], local_path)
        if success:
            return record, "ok", record["size"]
        else:
            return record, "failed", 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_record, r): r for r in to_download}
        
        iterator = tqdm(concurrent.futures.as_completed(futures), total=len(futures), unit="file") if use_tqdm else concurrent.futures.as_completed(futures)

        for future in iterator:
            record, status, bytes_downloaded = future.result()
            
            if status == "skipped":
                record["status"] = "done"
                skipped += 1
            elif status == "ok":
                record["status"] = "done"
                record["downloaded_at"] = _now()
                record["error"] = None
                ok += 1
                total_bytes += bytes_downloaded
            elif status == "failed":
                record["status"] = "failed"
                record["error"] = "download failed after retries"
                failed += 1
                msg = f"  ❌ Failed: {record['dropbox_path']}"
                if use_tqdm:
                    tqdm.write(msg)
                else:
                    print(msg)

            if use_tqdm:
                iterator.set_postfix(ok=ok, skip=skipped, fail=failed)

            # Save index every 25 files so progress survives a crash
            if (ok + failed) % 25 == 0:
                save_index(idx_path, index)

    save_index(idx_path, index)

    # -- Summary ---------------------------------------------------------------
    done_total  = sum(1 for r in index["files"].values() if r["status"] == "done")
    fail_total  = sum(1 for r in index["files"].values() if r["status"] == "failed")

    print(f"\n{'─'*50}")
    print(f"✅ Downloaded : {ok} file(s)  ({human_size(total_bytes)})")
    if skipped:
        print(f"⏭️  Skipped    : {skipped} (already existed)")
    if failed:
        print(f"❌ Failed     : {failed}  (run with --resume --retry-failed to retry)")
    print(f"\n📋 Index total : {done_total} done, {fail_total} failed  →  {idx_path}")
    print(f"📁 Location   : {output_dir.resolve()}")

if __name__ == "__main__":
    main()
