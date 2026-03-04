# ChronoMedia Organizer

ChronoMedia Organizer is a Python tool that organizes large media dumps into a clean chronological timeline structure.

It is especially useful for organizing media exported from smartphones such as iPhone.

The tool reads metadata using ExifTool and copies files into a structured timeline folder system.

Original files remain untouched.

---

## Features

- Timeline based organization (Year / Month folders)
- Works with photos and videos
- Handles iPhone Live Photos
- Detects duplicate files
- Generates Excel report
- Creates timestamped log file
- Progress bar for large collections
- Safe: copies files instead of moving originals

---

## Example Output

organized_media/

2023/
2023-08/

2023-08-21_14-33-02_photo.heic
2023-08-21_14-33-02_live.mov
2023-08-21_15-10-55_video.mp4

---

## Installation

Install Python dependencies

pip install -r requirements.txt

Install ExifTool

https://exiftool.org/

Ensure `exiftool` is available in your system PATH.

---

## Usage

Run the script using:

python chronomedia_organizer.py --source <media_dump> --dest <organized_folder>

Example

python chronomedia_organizer.py --source C:\iphone_dump --dest D:\organized_media

---

## Typical Use Cases

### Organizing iPhone media dumps

When exporting photos from iPhone you often get files like

IMG_0001.HEIC  
IMG_0001.MOV  
IMG_0002.HEIC  

ChronoMedia Organizer groups them into chronological folders while keeping Live Photos together.

### Cleaning large photo archives

Useful for organizing

- phone backups
- SD card dumps
- Google Takeout exports
- WhatsApp media archives

### Building a long term media archive

Creates a scalable timeline based media library that works well even with very large collections.

---

## Requirements

Python 3.9+

Dependencies

- tqdm
- openpyxl

External tool

- ExifTool

---

## License

MIT License