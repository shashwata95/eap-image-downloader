# EAP Image Downloader

A Python script to download images from the British Library's Endangered Archives Programme (EAP) website. The script uses the IIIF (International Image Interoperability Framework) API to efficiently download full-resolution images from archive files.

## Features

- **IIIF Manifest Support**: Automatically fetches and parses IIIF manifests for efficient batch downloading
- **Playwright Fallback**: Falls back to browser automation if manifest is not accessible
- **Progress Tracking**: Visual progress bar using `tqdm`
- **Rate Limiting**: Respectful delays between requests (default 1.5 seconds)
- **Resume Support**: Skips already downloaded images
- **Page Range Selection**: Download specific page ranges
- **Organized Output**: Creates separate directories for each archive file

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository:

```bash
cd eap-image-downloader
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install Playwright browsers (only needed if IIIF manifest is not accessible):

```bash
playwright install chromium
```

## Usage

### Basic Usage

Download all images from an EAP archive file:

```bash
python download_eap_images.py "https://eap.bl.uk/archive-file/EAP262-1-2-1-1"
```

### Advanced Options

**Specify output directory:**

```bash
python download_eap_images.py "https://eap.bl.uk/archive-file/EAP262-1-2-1-1" --output ./my_downloads
```

**Download specific page range:**

```bash
python download_eap_images.py "https://eap.bl.uk/archive-file/EAP262-1-2-1-1" --start 1 --end 10
```

**Adjust rate limiting (delay between requests):**

```bash
python download_eap_images.py "https://eap.bl.uk/archive-file/EAP262-1-2-1-1" --delay 2.0
```

**Specify image quality/size:**

```bash
# Full resolution (default)
python download_eap_images.py "https://eap.bl.uk/archive-file/EAP262-1-2-1-1" --quality full

# Maximum available size
python download_eap_images.py "https://eap.bl.uk/archive-file/EAP262-1-2-1-1" --quality max

# Specific width (maintains aspect ratio)
python download_eap_images.py "https://eap.bl.uk/archive-file/EAP262-1-2-1-1" --quality "2000,"
```

### Command-Line Options

```
positional arguments:
  url                   EAP archive file URL

optional arguments:
  -h, --help            Show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Output directory for downloaded images (default: ./downloads)
  --delay DELAY, -d DELAY
                        Delay between requests in seconds (default: 1.5)
  --quality QUALITY, -q QUALITY
                        Image quality/size: "full", "max", or specific dimensions (default: full)
  --start START, -s START
                        Start page number (optional)
  --end END, -e END     End page number (optional)
```

## How It Works

The script uses a two-tier approach to download images:

### Primary Method: IIIF Manifest

1. Extracts the archive identifier from the URL (e.g., `EAP262-1-2-1-1`)
2. Constructs and fetches the IIIF manifest JSON
3. Parses the manifest to extract all image identifiers and metadata
4. Downloads images using the IIIF Image API

### Fallback Method: Playwright

If the manifest is not accessible:

1. Launches a headless browser using Playwright
2. Loads the Universal Viewer on the archive page
3. Monitors network requests to capture IIIF image URLs
4. Extracts the URL pattern for batch downloading

## Output Structure

Downloaded images are organized in directories by archive identifier:

```
downloads/
└── EAP262-1-2-1-1/
    ├── 001.jpg
    ├── 002.jpg
    ├── 003.jpg
    └── ...
```

## Examples

### Example 1: Download a complete archive

```bash
python download_eap_images.py "https://eap.bl.uk/archive-file/EAP262-1-2-1-1"
```

Output:
```
Initialized downloader for: EAP262-1-2-1-1
Output directory: downloads/EAP262-1-2-1-1
Attempting to fetch manifest: https://eap.bl.uk/iiif/EAP262-1-2-1-1/manifest
✓ Successfully fetched manifest
✓ Extracted 24 images from manifest

Downloading 24 images...
100%|████████████████████████████| 24/24 [01:30<00:00,  3.77s/image]

============================================================
Download complete!
✓ Successful: 24
Output directory: downloads/EAP262-1-2-1-1
============================================================
```

### Example 2: Download pages 5-15 only

```bash
python download_eap_images.py "https://eap.bl.uk/archive-file/EAP262-1-2-1-1" --start 5 --end 15
```

### Example 3: Download with custom settings

```bash
python download_eap_images.py \
  "https://eap.bl.uk/archive-file/EAP262-1-2-1-1" \
  --output ~/Documents/eap_archives \
  --delay 2.0 \
  --quality "2000,"
```

## Best Practices

1. **Respect Rate Limits**: Keep the default delay or increase it. The British Library servers deserve respect.
2. **Check Terms of Service**: Ensure you have the right to download and use these images.
3. **Storage Space**: Full-resolution images can be large. Check available disk space first.
4. **Resume Capability**: If interrupted, simply run the same command again. Already downloaded images will be skipped.

## Troubleshooting

### "Could not extract identifier from URL"

Make sure the URL follows the pattern: `https://eap.bl.uk/archive-file/EAP###-#-#-#-#`

### "Manifest not available"

The script will automatically fall back to Playwright. Ensure you have run `playwright install chromium`.

### "Playwright not installed"

Run:
```bash
pip install playwright
playwright install chromium
```

### Network/timeout errors

Try increasing the delay:
```bash
python download_eap_images.py "URL" --delay 3.0
```

## Technical Details

### IIIF Image API

The script uses the IIIF Image API 2.0/3.0 specification:

```
https://eap.bl.uk/iiif/2/{identifier}/{region}/{size}/{rotation}/{quality}.{format}
```

Where:
- `{identifier}`: Archive file identifier
- `{region}`: `full` (entire image)
- `{size}`: `full`, `max`, or specific dimensions
- `{rotation}`: `0` (no rotation)
- `{quality}`: `default`, `color`, `gray`, or `bitonal`
- `{format}`: `jpg`, `png`, etc.

### Dependencies

- **requests**: HTTP library for downloading images
- **playwright**: Browser automation for fallback method
- **beautifulsoup4**: HTML parsing (for potential future enhancements)
- **tqdm**: Progress bar visualization

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This script is provided as-is for educational and research purposes. Please respect the British Library's terms of service and copyright policies when using downloaded images.

## Acknowledgments

- British Library's Endangered Archives Programme for preserving cultural heritage
- IIIF Consortium for the interoperability framework

## Author

Created for downloading EAP archive images efficiently and respectfully.

