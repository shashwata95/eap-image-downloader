#!/usr/bin/env python3
"""
EAP Image Downloader
Downloads images from British Library's Endangered Archives Programme (EAP) website.
Uses IIIF (International Image Interoperability Framework) API.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


class EAPImageDownloader:
    """Main class for downloading images from EAP archive files."""
    
    def __init__(self, url: str, output_dir: str = "./downloads", 
                 delay: float = 1.5, quality: str = "full"):
        """
        Initialize the downloader.
        
        Args:
            url: The EAP archive file URL
            output_dir: Directory to save downloaded images
            delay: Delay between requests in seconds
            quality: Image quality/size (full, max, or specific dimensions)
        """
        self.url = url
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.quality = quality
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; EAP-Image-Downloader/1.0)'
        })
        
        # Extract identifier from URL
        self.identifier = self._extract_identifier(url)
        if not self.identifier:
            raise ValueError(f"Could not extract identifier from URL: {url}")
        
        # Create output directory
        self.image_dir = self.output_dir / self.identifier
        self.image_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Initialized downloader for: {self.identifier}")
        print(f"Output directory: {self.image_dir}")
    
    def _extract_identifier(self, url: str) -> Optional[str]:
        """Extract the archive file identifier from the URL."""
        # Pattern: https://eap.bl.uk/archive-file/EAP262-1-2-1-1
        match = re.search(r'/archive-file/([A-Z0-9\-]+)', url)
        if match:
            return match.group(1)
        return None
    
    def _construct_manifest_url(self) -> str:
        """Construct the IIIF manifest URL."""
        # EAP uses archive-file path for manifests
        return f"https://eap.bl.uk/archive-file/{self.identifier}/manifest"
    
    def fetch_manifest(self) -> Optional[Dict]:
        """
        Fetch and parse the IIIF manifest.
        
        Returns:
            Parsed manifest as dictionary, or None if not available
        """
        manifest_url = self._construct_manifest_url()
        print(f"Attempting to fetch manifest: {manifest_url}")
        
        try:
            response = self.session.get(manifest_url, timeout=10)
            if response.status_code == 200:
                manifest = response.json()
                print("✓ Successfully fetched manifest")
                return manifest
            else:
                print(f"✗ Manifest not available (status: {response.status_code})")
                return None
        except Exception as e:
            print(f"✗ Error fetching manifest: {e}")
            return None
    
    def extract_image_ids_from_manifest(self, manifest: Dict) -> List[Dict[str, any]]:
        """
        Extract image identifiers and metadata from IIIF manifest.
        
        Args:
            manifest: Parsed IIIF manifest
            
        Returns:
            List of dictionaries with image info
        """
        images = []
        
        # IIIF Presentation API 2.x format
        if 'sequences' in manifest:
            for sequence in manifest['sequences']:
                if 'canvases' in sequence:
                    for idx, canvas in enumerate(sequence['canvases']):
                        image_info = {
                            'index': idx + 1,
                            'label': canvas.get('label', f"Image {idx + 1}")
                        }
                        
                        # Extract image identifier from canvas
                        if 'images' in canvas:
                            for image in canvas['images']:
                                if 'resource' in image:
                                    resource = image['resource']
                                    if '@id' in resource:
                                        image_info['url'] = resource['@id']
                                    elif 'service' in resource and '@id' in resource['service']:
                                        service_id = resource['service']['@id']
                                        image_info['service_id'] = service_id
                        
                        images.append(image_info)
        
        # IIIF Presentation API 3.x format
        elif 'items' in manifest:
            for idx, canvas in enumerate(manifest['items']):
                image_info = {
                    'index': idx + 1,
                    'label': canvas.get('label', {}).get('en', [f"Image {idx + 1}"])[0]
                }
                
                if 'items' in canvas:
                    for annotation_page in canvas['items']:
                        if 'items' in annotation_page:
                            for annotation in annotation_page['items']:
                                if 'body' in annotation:
                                    body = annotation['body']
                                    if 'id' in body:
                                        image_info['url'] = body['id']
                                    elif 'service' in body:
                                        services = body['service'] if isinstance(body['service'], list) else [body['service']]
                                        for service in services:
                                            if 'id' in service or '@id' in service:
                                                image_info['service_id'] = service.get('id') or service.get('@id')
                
                images.append(image_info)
        
        print(f"✓ Extracted {len(images)} images from manifest")
        return images
    
    def discover_images_with_playwright(self) -> List[Dict[str, any]]:
        """
        Use Playwright to load the viewer and discover image URLs.
        This is a fallback method when manifest is not accessible.
        
        Returns:
            List of dictionaries with image info
        """
        print("Using Playwright to discover images...")
        
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("✗ Playwright not installed. Run: playwright install")
            return []
        
        images = []
        captured_urls = set()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Capture network requests
            def handle_response(response):
                url = response.url
                if 'iiif' in url and ('/full/' in url or '/info.json' in url):
                    captured_urls.add(url)
            
            page.on('response', handle_response)
            
            print(f"Loading page: {self.url}")
            page.goto(self.url, wait_until='networkidle', timeout=30000)
            
            # Wait a bit for all images to load
            page.wait_for_timeout(3000)
            
            # Try to find pagination or image count
            try:
                # Look for page navigation elements
                page_info = page.eval_on_selector('.pageArea', 'el => el.textContent') or ''
                print(f"Page info: {page_info}")
            except:
                pass
            
            browser.close()
        
        # Process captured URLs
        print(f"✓ Captured {len(captured_urls)} unique image URLs")
        
        # Parse and organize URLs
        for idx, url in enumerate(sorted(captured_urls), 1):
            images.append({
                'index': idx,
                'url': url,
                'label': f"Image {idx}"
            })
        
        return images
    
    def construct_iiif_image_url(self, service_id: str, size: str = "full", 
                                 quality: str = "default", format: str = "jpg") -> str:
        """
        Construct IIIF Image API URL.
        
        Args:
            service_id: Base service identifier
            size: Image size (full, max, or w,h)
            quality: Image quality (default, color, gray, bitonal)
            format: Image format (jpg, png, etc.)
            
        Returns:
            Full IIIF image URL
        """
        # Ensure service_id doesn't end with slash
        service_id = service_id.rstrip('/')
        
        # IIIF Image API URL format: {scheme}://{server}{/prefix}/{identifier}/{region}/{size}/{rotation}/{quality}.{format}
        # region=full, rotation=0
        return f"{service_id}/full/{size}/0/{quality}.{format}"
    
    def download_image(self, image_info: Dict[str, any], start_page: Optional[int] = None,
                      end_page: Optional[int] = None) -> bool:
        """
        Download a single image.
        
        Args:
            image_info: Dictionary with image information
            start_page: Optional start page number filter
            end_page: Optional end page number filter
            
        Returns:
            True if successful, False otherwise
        """
        index = image_info['index']
        
        # Check if within page range
        if start_page and index < start_page:
            return False
        if end_page and index > end_page:
            return False
        
        # Determine image URL
        if 'url' in image_info:
            image_url = image_info['url']
        elif 'service_id' in image_info:
            image_url = self.construct_iiif_image_url(
                image_info['service_id'], 
                size=self.quality
            )
        else:
            print(f"✗ No URL found for image {index}")
            return False
        
        # Generate filename
        filename = f"{index:03d}.jpg"
        filepath = self.image_dir / filename
        
        # Skip if already exists
        if filepath.exists():
            return True
        
        # Download
        try:
            response = self.session.get(image_url, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                print(f"\n✗ Failed to download image {index} (status: {response.status_code})")
                return False
        except Exception as e:
            print(f"\n✗ Error downloading image {index}: {e}")
            return False
    
    def download_all(self, start_page: Optional[int] = None, 
                     end_page: Optional[int] = None) -> None:
        """
        Download all images from the archive file.
        
        Args:
            start_page: Optional start page number
            end_page: Optional end page number
        """
        print("\n" + "="*60)
        print("Starting download process...")
        print("="*60 + "\n")
        
        # Try manifest first
        images = []
        manifest = self.fetch_manifest()
        
        if manifest:
            images = self.extract_image_ids_from_manifest(manifest)
        
        # Fallback to Playwright if needed
        if not images:
            print("\nManifest method failed. Trying Playwright fallback...")
            images = self.discover_images_with_playwright()
        
        if not images:
            print("\n✗ Could not discover any images. Please check the URL.")
            return
        
        # Filter by page range if specified
        if start_page or end_page:
            original_count = len(images)
            images = [img for img in images 
                     if (not start_page or img['index'] >= start_page) and
                        (not end_page or img['index'] <= end_page)]
            print(f"\nFiltered to {len(images)} images (from {original_count} total)")
        
        print(f"\nDownloading {len(images)} images...\n")
        
        # Download with progress bar
        successful = 0
        failed = 0
        
        with tqdm(total=len(images), unit='image') as pbar:
            for image_info in images:
                if self.download_image(image_info, start_page, end_page):
                    successful += 1
                else:
                    failed += 1
                
                pbar.update(1)
                
                # Rate limiting
                time.sleep(self.delay)
        
        # Summary
        print("\n" + "="*60)
        print("Download complete!")
        print(f"✓ Successful: {successful}")
        if failed > 0:
            print(f"✗ Failed: {failed}")
        print(f"Output directory: {self.image_dir}")
        print("="*60)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Download images from British Library EAP archive files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "https://eap.bl.uk/archive-file/EAP262-1-2-1-1"
  %(prog)s "https://eap.bl.uk/archive-file/EAP262-1-2-1-1" --output ./my_images
  %(prog)s "https://eap.bl.uk/archive-file/EAP262-1-2-1-1" --start 1 --end 10
  %(prog)s "https://eap.bl.uk/archive-file/EAP262-1-2-1-1" --delay 2.0
        """
    )
    
    parser.add_argument(
        'url',
        help='EAP archive file URL (e.g., https://eap.bl.uk/archive-file/EAP262-1-2-1-1)'
    )
    parser.add_argument(
        '--output', '-o',
        default='./downloads',
        help='Output directory for downloaded images (default: ./downloads)'
    )
    parser.add_argument(
        '--delay', '-d',
        type=float,
        default=1.5,
        help='Delay between requests in seconds (default: 1.5)'
    )
    parser.add_argument(
        '--quality', '-q',
        default='full',
        help='Image quality/size: "full", "max", or specific dimensions like "2000," (default: full)'
    )
    parser.add_argument(
        '--start', '-s',
        type=int,
        help='Start page number (optional)'
    )
    parser.add_argument(
        '--end', '-e',
        type=int,
        help='End page number (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        downloader = EAPImageDownloader(
            url=args.url,
            output_dir=args.output,
            delay=args.delay,
            quality=args.quality
        )
        downloader.download_all(start_page=args.start, end_page=args.end)
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

