import argparse
import subprocess
import json
import shutil
import csv
import os
import hashlib
import logging
import time
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

# Constants
VIDEO_EXTS = {".mov", ".mp4", ".m4v", ".avi", ".mkv"}
IMAGE_EXTS = {".heic", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff"}

def sha1(file):
    h = hashlib.sha1()
    try:
        with open(file, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk: break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def sanitize(name):
    bad = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for c in bad:
        name = name.replace(c, "_")
    return name

def parse_date(meta, path):
    for tag in ["DateTimeOriginal", "CreateDate", "MediaCreateDate"]:
        if tag in meta:
            try:
                return datetime.strptime(meta[tag][:19], "%Y:%m:%d %H:%M:%S")
            except Exception: pass
    return datetime.fromtimestamp(path.stat().st_mtime)

def process_metadata_chunk(file_paths):
    if not file_paths: return []
    cmd = ["exiftool", "-json", "-fast"] + [str(f) for f in file_paths]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    try:
        return json.loads(result.stdout) if result.stdout.strip() else []
    except Exception: return []

def get_metadata_parallel(file_list, workers=None):
    if not file_list: return []
    workers = workers or (os.cpu_count() or 4)
    all_metadata = []
    chunk_size = 50
    chunks = [file_list[i:i + chunk_size] for i in range(0, len(file_list), chunk_size)]
    
    print(f"\n--- Extracting metadata using {workers} parallel workers ---")
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(process_metadata_chunk, chunk) for chunk in chunks]
        with tqdm(total=len(file_list), desc="Reading Metadata", unit="file") as pbar:
            for future in as_completed(futures):
                batch_result = future.result()
                all_metadata.extend(batch_result)
                pbar.update(len(batch_result) if batch_result else chunk_size)
    return all_metadata

def process_single_file(item, by_stem, dest, dry_run):
    src_path_str = item.get("SourceFile", "Unknown")
    try:
        src = Path(src_path_str)
        if not src.exists():
            return "skipped", src_path_str, "File not found", None

        date = parse_date(item, src)
        year, month = date.strftime("%Y"), date.strftime("%Y-%m")
        target_folder = dest / year / month
        target_folder.mkdir(parents=True, exist_ok=True)

        ext = src.suffix.lower()
        group = by_stem.get(src.stem, [])
        has_image = any(p.suffix.lower() in IMAGE_EXTS for p in group)
        has_video = any(p.suffix.lower() in VIDEO_EXTS for p in group)

        tag = "live" if (has_image and has_video) else \
              "video" if ext in VIDEO_EXTS else \
              ("screenshot" if "screenshot" in src.name.lower() else "photo") if ext in IMAGE_EXTS else "misc"

        filename = sanitize(f"{date.strftime('%Y-%m-%d_%H-%M-%S')}_{tag}")
        target = target_folder / f"{filename}{ext}"

        # Collision & Duplicate handling
        counter = 1
        while target.exists():
            if src.stat().st_size == target.stat().st_size:
                if sha1(src) == sha1(target):
                    return "duplicate", src_path_str, f"Existing: {target}", None
            target = target_folder / f"{filename}_{counter}{ext}"
            counter += 1
        
        if not dry_run:
            retries = 3
            for i in range(retries):
                try:
                    shutil.copy2(src, target)
                    break 
                except PermissionError:
                    if i < retries - 1:
                        time.sleep(0.3)
                        continue
                    else: raise

        return "copied", src_path_str, "Success", str(target)
    except Exception as e:
        return "error", src_path_str, str(e), None

def main():
    parser = argparse.ArgumentParser(description="ChronoMedia Organizer Parallel")
    parser.add_argument("--source", required=True)
    parser.add_argument("--dest", required=True)
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=None)

    args = parser.parse_args()
    source, dest = Path(args.source), Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    run_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = dest / f"chronomedia_log_{run_time}.log"
    
    # Custom logger setup for immediate flushing
    logger = logging.getLogger("ChronoMedia")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)

    all_files = [f for f in source.rglob("*") if f.is_file()]
    if not all_files: return

    print(f"\nFiles detected: {len(all_files)}")
    if input("Proceed? (y/n): ").lower() != 'y': return

    metadata = get_metadata_parallel(all_files, workers=args.workers)

    by_stem = {}
    for item in metadata:
        p = Path(item["SourceFile"])
        by_stem.setdefault(p.stem, []).append(p)

    stats = {"copied": 0, "duplicate": 0, "skipped": 0, "error": 0}
    report_rows = []
    
    print(f"\n--- Organizing and Copying (Parallel) ---")
    
    max_threads = args.workers or 12
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_to_file = {executor.submit(process_single_file, item, by_stem, dest, args.dry_run): item for item in metadata}
        
        with tqdm(total=len(metadata), desc="Copying Files") as pbar:
            for future in as_completed(future_to_file):
                status, src_name, msg, target_path = future.result()
                stats[status] += 1
                
                # Format log entry
                if status == "error":
                    logger.error(f"FAILED: {src_name} | Reason: {msg}")
                elif status == "duplicate":
                    logger.warning(f"DUPLICATE: {src_name} | {msg}")
                elif status == "copied":
                    logger.info(f"SUCCESS: {src_name} -> {target_path}")
                    report_rows.append([src_name, target_path])
                
                pbar.update(1)

    if args.report and report_rows:
        report_path = dest / f"report_{run_time}.csv"
        with open(report_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Original", "New"])
            writer.writerows(report_rows)

    print(f"\nDone! Copied: {stats['copied']} | Duplicates: {stats['duplicate']} | Errors: {stats['error']}")
    print(f"Full log: {log_file}")

if __name__ == "__main__":
    main()
