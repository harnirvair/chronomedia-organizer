import argparse
import subprocess
import json
import shutil
import csv
from pathlib import Path
from datetime import datetime
import hashlib
import logging
from tqdm import tqdm

VIDEO_EXTS = {".mov",".mp4",".m4v",".avi",".mkv"}
IMAGE_EXTS = {".heic",".jpg",".jpeg",".png",".gif",".tif",".tiff"}

def sha1(file):

    h = hashlib.sha1()

    with open(file,"rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def sanitize(name):

    bad = ['<','>',':','"','/','\\','|','?','*']

    for c in bad:
        name = name.replace(c,"_")

    return name


def parse_date(meta,path):

    for tag in ["DateTimeOriginal","CreateDate","MediaCreateDate"]:

        if tag in meta:

            try:
                return datetime.strptime(meta[tag],"%Y:%m:%d %H:%M:%S")
            except:
                pass

    return datetime.fromtimestamp(path.stat().st_mtime)


def get_metadata(source):

    print("\nReading metadata using ExifTool...\n")

    cmd = ["exiftool","-json","-r",str(source)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )

    if not result.stdout.strip():
        print("No files found.")
        exit()

    return json.loads(result.stdout)


def main():

    parser = argparse.ArgumentParser(
        description="ChronoMedia Organizer — organize media files into chronological folders"
    )

    parser.add_argument("--source",required=True,help="Source media folder")
    parser.add_argument("--dest",required=True,help="Destination organized folder")

    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate CSV report"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without copying files"
    )

    args = parser.parse_args()

    source = Path(args.source)
    dest = Path(args.dest)

    dest.mkdir(parents=True,exist_ok=True)

    run_time = datetime.now().strftime("%Y%m%d_%H%M%S")

    log_file = dest / f"chronomedia_log_{run_time}.log"

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s %(message)s"
    )

    all_files = [f for f in source.rglob("*") if f.is_file()]

    print("\n--------------------------------------")
    print("ChronoMedia Organizer")
    print("--------------------------------------")
    print("Source folder      :",source)
    print("Destination folder :",dest)
    print("Files detected     :",len(all_files))
    print("--------------------------------------\n")

    confirm = input("Proceed with organization? (y/n): ")

    if confirm.lower() != "y":
        print("Cancelled.")
        return

    metadata = get_metadata(source)

    by_stem = {}

    for item in metadata:

        p = Path(item["SourceFile"])

        by_stem.setdefault(p.stem,[]).append(p)

    seen_hash = set()

    stats = {
        "copied":0,
        "duplicates":0,
        "skipped":0
    }

    report_rows = []

    for item in tqdm(metadata,desc="Processing media"):

        src = Path(item["SourceFile"])

        if not src.exists():
            continue

        date = parse_date(item,src)

        year = date.strftime("%Y")
        month = date.strftime("%Y-%m")

        folder = dest / year / month
        folder.mkdir(parents=True,exist_ok=True)

        timestamp = date.strftime("%Y-%m-%d_%H-%M-%S")

        ext = src.suffix.lower()

        group = by_stem.get(src.stem,[])

        has_image = any(p.suffix.lower() in IMAGE_EXTS for p in group)
        has_video = any(p.suffix.lower() in VIDEO_EXTS for p in group)

        if has_image and has_video:
            typetag="live"

        elif ext in VIDEO_EXTS:
            typetag="video"

        elif ext in IMAGE_EXTS:

            if "screenshot" in src.name.lower():
                typetag="screenshot"
            else:
                typetag="photo"

        else:
            typetag="unknown"

        base = sanitize(f"{timestamp}_{typetag}")

        target = folder / f"{base}{ext}"

        if target.exists():

            stats["skipped"]+=1

            continue

        filehash = sha1(src)

        if filehash in seen_hash:

            stats["duplicates"]+=1

            continue

        seen_hash.add(filehash)

        if not args.dry_run:

            shutil.copy2(src,target)

        logging.info(f"{src} -> {target}")

        stats["copied"]+=1

        report_rows.append([str(src),str(target)])

    print("\nProcessing complete\n")

    print("Files copied     :",stats["copied"])
    print("Duplicates found :",stats["duplicates"])
    print("Skipped existing :",stats["skipped"])

    if args.report:

        report_file = dest / f"chronomedia_report_{run_time}.csv"

        with open(report_file,"w",newline="",encoding="utf-8") as f:

            writer = csv.writer(f)

            writer.writerow(["Original Path","New Path"])

            writer.writerows(report_rows)

        print("Report saved :",report_file)

    print("Log file :",log_file)
    print("\nDone\n")


if __name__=="__main__":
    main()