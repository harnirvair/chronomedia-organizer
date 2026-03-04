# Photo Organizer

Python script to organize iPhone photo dumps into a clean timeline structure.

## Features

- Copies files (does not move originals)
- Organizes by year and month
- Renames files using capture timestamp
- Detects duplicates
- Generates Excel report
- Creates timestamped log files
- Shows live progress bar

## Requirements

Python 3.9+

Install dependencies:

pip install -r requirements.txt

Also install ExifTool:
https://exiftool.org/

## Usage

Edit source and destination paths in:

organize_media.py

Run:

python organize_media.py

Output will be written to the organized_media folder.