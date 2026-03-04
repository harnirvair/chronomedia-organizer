import subprocess
import json
import shutil
from pathlib import Path
from datetime import datetime
import hashlib
import logging
from openpyxl import Workbook
from tqdm import tqdm

# -------- CONFIG --------

SOURCE = Path(r"C:\iphone_dump")
DEST = Path(r"C:\organized_media")

VIDEO_EXTS = {".mov", ".mp4", ".m4v", ".avi", ".mkv"}
IMAGE_EXTS = {".heic", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff"}

# ------------------------

DEST.mkdir(parents=True, exist_ok=True)

run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

log_file = DEST / f"organize_log_{run_timestamp}.log"
excel_file = DEST / f"media_index_{run_timestamp}.xlsx"

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

def log(msg):
    print(msg)
    logging.info(msg)

# -------- Metadata --------

def get_metadata():

    log("Scanning files with ExifTool...")

    cmd = ["exiftool", "-json", "-r", str(SOURCE)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )

    if result.stderr:
        log("Exiftool stderr: " + result.stderr)

    if not result.stdout.strip():
        log("No files found in source folder.")
        exit()

    return json.loads(result.stdout)

# -------- Date Parsing --------

def parse_date(meta, path):

    for tag in ["DateTimeOriginal", "CreateDate", "MediaCreateDate"]:
        if tag in meta:
            try:
                return datetime.strptime(meta[tag], "%Y:%m:%d %H:%M:%S")
            except:
                pass

    return datetime.fromtimestamp(path.stat().st_mtime)

# -------- Hashing --------

def sha1(file):

    h = hashlib.sha1()

    with open(file, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()

# -------- Filename Safety --------

def sanitize_filename(name):

    bad = ['<','>',':','"','/','\\','|','?','*']

    for c in bad:
        name = name.replace(c,"_")

    return name

# -------- Start --------


print("\n-----------------------------------------")
print("Photo Organizer Starting")
print("-----------------------------------------")

print(f"Source Folder      : {SOURCE}")
print(f"Destination Folder : {DEST}")

print("\nScanning source folder...")

all_files = [f for f in SOURCE.rglob("*") if f.is_file()]
file_count = len(all_files)

print(f"Files detected     : {file_count}")

print("-----------------------------------------\n")

metadata = get_metadata()

log(f"Total files detected: {len(metadata)}")

# build grouping for live photos
by_stem = {}

for item in metadata:
    p = Path(item["SourceFile"])
    by_stem.setdefault(p.stem, []).append(p)

seen_hash = {}

records = []

# -------- Processing Loop --------

for item in tqdm(metadata, desc="Organizing files"):

    src = Path(item["SourceFile"])

    if not src.exists():
        continue

    date = parse_date(item, src)

    year = date.strftime("%Y")
    month = date.strftime("%Y-%m")

    folder = DEST / year / month
    folder.mkdir(parents=True, exist_ok=True)

    timestamp_name = date.strftime("%Y-%m-%d_%H-%M-%S")

    ext = src.suffix.lower()

    # detect media type

    group = by_stem.get(src.stem, [])

    has_image = any(p.suffix.lower() in IMAGE_EXTS for p in group)
    has_video = any(p.suffix.lower() in VIDEO_EXTS for p in group)

    if has_image and has_video:
        typetag = "live"

    elif ext in VIDEO_EXTS:
        typetag = "video"

    elif ext in IMAGE_EXTS:

        if "screenshot" in src.name.lower():
            typetag = "screenshot"
        else:
            typetag = "photo"

    else:
        typetag = "unknown"

    base_name = f"{timestamp_name}_{typetag}"
    base_name = sanitize_filename(base_name)

    target = folder / f"{base_name}{ext}"

    if target.exists():
        log(f"Already exists, skipping: {target}")
        records.append([str(src), str(target), "Already exists"])
        continue

    counter = 1

    while target.exists():
        target = folder / f"{base_name}_{counter}{ext}"
        counter += 1

    filehash = sha1(src)

    if filehash in seen_hash:
        log(f"Duplicate detected: {src}")
        records.append([str(src), "", "Duplicate skipped"])
        continue

    seen_hash[filehash] = True

    shutil.copy2(src, target)

    log(f"Copied → {target}")

    records.append([str(src), str(target), "Copied"])

# -------- Excel Report --------

log("Creating Excel report...")

wb = Workbook()
ws = wb.active

ws.append(["Original Path","New Path","Action"])

for r in records:
    ws.append(r)

wb.save(excel_file)

log(f"Excel report created: {excel_file}")

log("Finished successfully")

print("\nFinished")
print("Excel report:", excel_file)
print("Log file:", log_file)