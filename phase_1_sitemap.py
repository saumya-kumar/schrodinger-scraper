#!/usr/bin/env python3
"""
Phase 1: Sitemap Discovery - Complete URL Discovery & Performance Testing
"""

import asyncio
import aiohttp
import time
import json
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Set, List

# Target website for testing
TARGET_URL = "https://www.city.chiyoda.lg.jp/"

async def discover_sitemap_urls(base_url: str) -> Set[str]:
    """Discover URLs from sitemap.html"""
    discovered_urls = set()
    
    # Common sitemap locations to try
    sitemap_locations = [
        "sitemap.html",
        "sitemap.xml", 
        "sitemap_index.xml",
        "sitemaps.xml"
    ]
    
    async with aiohttp.ClientSession() as session:
        for location in sitemap_locations:
            try:
                sitemap_url = urljoin(base_url, location)
                print(f"🔍 Trying: {sitemap_url}")
                
                async with session.get(sitemap_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        print(f"✅ Found {location} with {len(content)} characters")
                        
                        # Parse HTML sitemap
                        if location.endswith('.html'):
                            urls = parse_html_sitemap(content, base_url)
                            discovered_urls.update(urls)
                            print(f"📊 Extracted {len(urls)} URLs from HTML sitemap")
                        
                        # Parse XML sitemap  
                        elif location.endswith('.xml'):
                            urls = parse_xml_sitemap(content, base_url)
                            discovered_urls.update(urls)
                            print(f"📊 Extracted {len(urls)} URLs from XML sitemap")
                    else:
                        print(f"❌ {location}: HTTP {response.status}")
                        
            except Exception as e:
                print(f"⚠️ Error with {location}: {e}")
    
    return discovered_urls

def parse_html_sitemap(content: str, base_url: str) -> Set[str]:
    """Parse HTML sitemap and extract URLs"""
    urls = set()
    
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Convert relative URLs to absolute
            if href.startswith('/'):
                full_url = urljoin(base_url, href)
            elif href.startswith('http'):
                full_url = href
            else:
                continue
                
            # Filter for same domain and .html files
            if is_valid_url(full_url, base_url):
                urls.add(full_url)
                
    except Exception as e:
        print(f"⚠️ HTML parsing error: {e}")
    
    return urls

def parse_xml_sitemap(content: str, base_url: str) -> Set[str]:
    """Parse XML sitemap and extract URLs"""
    urls = set()
    
    try:
        # Try to find URLs using regex (more reliable than XML parsing for this case)
        url_pattern = r'<loc>(.*?)</loc>'
        found_urls = re.findall(url_pattern, content)
        
        for url in found_urls:
            if is_valid_url(url, base_url):
                urls.add(url)
                
    except Exception as e:
        print(f"⚠️ XML parsing error: {e}")
    
    return urls

def is_valid_url(url: str, base_url: str) -> bool:
    """Check if URL is valid for our criteria"""
    try:
        parsed_base = urlparse(base_url)
        parsed_url = urlparse(url)
        
        # Must be same domain
        if parsed_url.netloc != parsed_base.netloc:
            return False
            
        # Skip certain file types
        skip_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', 
                          '.css', '.js', '.xml', '.json', '.csv', '.zip', '.rar', 
                          '.mp3', '.mp4', '.avi', '.png', '.jpg', '.jpeg', '.gif']
        
        path = parsed_url.path.lower()
        for ext in skip_extensions:
            if path.endswith(ext):
                return False
                
        return True
        
    except Exception:
        return False
async def main():
    """Main function to test Phase 1: Sitemap Discovery"""
    print("=" * 80)
    print("🗺️ PHASE 1: SITEMAP DISCOVERY")
    print("=" * 80)
    print(f"🎯 Target: {TARGET_URL}")
    print(f"📅 Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    try:
        # Discover URLs from sitemaps
        discovered_urls = await discover_sitemap_urls(TARGET_URL)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Filter for HTML pages specifically
        html_urls = {url for url in discovered_urls if url.endswith('.html') or '/' in url.split('/')[-1]}
        
        # Display results
        print("\n" + "=" * 80)
        print("📊 PHASE 1 RESULTS")
        print("=" * 80)
        print(f"⏱️ Execution Time: {execution_time:.2f} seconds")
        print(f"🔢 Total URLs Found: {len(discovered_urls)}")
        print(f"📄 HTML Pages: {len(html_urls)}")
        print(f"🔗 Other URLs: {len(discovered_urls) - len(html_urls)}")
        
        # Save results
        results = {
            "phase": "1_sitemap_discovery",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "execution_time_seconds": execution_time,
            "total_urls": len(discovered_urls),
            "html_urls": len(html_urls),
            "other_urls": len(discovered_urls) - len(html_urls),
            "urls": list(discovered_urls)
        }
        
        with open("phase_1_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: phase_1_results.json")
        
        # Display sample URLs
        print(f"\n� Sample URLs (first 10):")
        for i, url in enumerate(list(discovered_urls)[:10]):
            print(f"   {i+1:2d}. {url}")
        
        if len(discovered_urls) > 10:
            print(f"   ... and {len(discovered_urls) - 10} more URLs")
            
        return discovered_urls
        
    except Exception as e:
        print(f"❌ Phase 1 failed: {e}")
        return set()

if __name__ == "__main__":
    asyncio.run(main())
