#!/usr/bin/env python3
"""Test Phase 4 - Depth-Based Recursive Link Crawling starting from homepage"""

import time
import json
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path
from datetime import datetime

class PhaseURLTracker:
    """Simple tracker for Phase 4 testing"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.all_urls = set()
        self.results_file = Path("all_urls.json")
        
        # Load existing URLs
        self.load_existing_data()
    
    def load_existing_data(self):
        """Load existing URLs from all_urls.json"""
        if self.results_file.exists():
            try:
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'phases' in data:
                        for phase_data in data['phases'].values():
                            if 'urls' in phase_data:
                                self.all_urls.update(phase_data['urls'])
                    print(f"📋 Loaded {len(self.all_urls)} existing URLs from all_urls.json")
            except Exception as e:
                print(f"⚠️ Could not load existing data: {e}")
        else:
            print("📋 Starting with fresh URL set")
    
    def add_phase_urls(self, phase_name, phase_urls, execution_time):
        """Add URLs from a phase and return statistics"""
        # Filter URLs and update master set
        filtered_urls = [url for url in phase_urls if url and isinstance(url, str)]
        new_urls = set(filtered_urls) - self.all_urls
        self.all_urls.update(new_urls)
        
        # Save to JSON
        self.save_to_json(phase_name, filtered_urls, execution_time)
        
        return {
            'total_found': len(filtered_urls),
            'new_unique': len(new_urls),
            'execution_time': execution_time
        }
    
    def save_to_json(self, phase_name, phase_urls, execution_time):
        """Save results to all_urls.json"""
        data = {}
        if self.results_file.exists():
            try:
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = {}
        
        if not data:
            data = {
                "schema_version": "2.0",
                "base_domain": self.base_url.replace('https://', '').replace('http://', '').rstrip('/'),
                "description": "Depth-based recursive crawling results",
                "created_at_utc": datetime.now().isoformat(),
                "phases": {}
            }
        
        # Update phase data
        html_urls = [url for url in phase_urls if url.endswith('.html') or not any(f'.{ext}' in url for ext in ['pdf', 'doc', 'zip', 'jpg', 'css', 'js', 'xml'])]
        
        data['phases'][phase_name] = {
            "execution_time": execution_time,
            "raw_count": len(phase_urls),
            "stats": {
                "html_pages": len(html_urls),
                "other_urls": len(phase_urls) - len(html_urls)
            },
            "timestamp": datetime.now().isoformat(),
            "urls": list(phase_urls)
        }
        
        data['updated_at_utc'] = datetime.now().isoformat()
        data['total_unique_urls'] = len(self.all_urls)
        
        with open(self.results_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

async def test_phase_4_depth_based(tracker):
    """Phase 4: Depth-Based Recursive Link Crawling"""
    print("🔄 PHASE 4: DEPTH-BASED RECURSIVE LINK CRAWLING")
    print("=" * 60)
    
    start_time = time.time()
    discovered_urls = set()
    
    try:
        # Start from ONLY the homepage
        base_url = tracker.base_url
        domain = urlparse(base_url).netloc
        
        print(f"🏠 Starting from homepage: {base_url}")
        print(f"🎯 Target domain: {domain}")
        print(f"📏 Target depth: 9 levels")
        
        # Initialize with ONLY the homepage
        current_depth_urls = {base_url}
        all_discovered = {base_url}
        max_depth = 9
        max_pages_per_depth = 100  # Reasonable limit per depth
        
        # Create aiohttp session with proper encoding handling
        connector = aiohttp.TCPConnector(
            ssl=False,
            limit=30,
            limit_per_host=5,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=20)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',  # Japanese + English
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        async with aiohttp.ClientSession(
            headers=headers,
            connector=connector,
            timeout=timeout
        ) as session:
            
            # Process each depth level systematically
            for depth in range(max_depth + 1):
                if not current_depth_urls:
                    print(f"    🏁 No URLs at depth {depth}, stopping")
                    break
                
                # Limit URLs per depth
                if len(current_depth_urls) > max_pages_per_depth:
                    current_depth_urls = set(list(current_depth_urls)[:max_pages_per_depth])
                
                print(f"\n  📏 DEPTH {depth}: Processing {len(current_depth_urls)} URLs")
                
                # Process current depth and find next depth URLs
                next_depth_urls = await process_depth_level(
                    session, current_depth_urls, domain, depth
                )
                
                # Add new URLs for next depth
                new_urls = next_depth_urls - all_discovered
                all_discovered.update(new_urls)
                
                print(f"  ✅ Depth {depth} complete: {len(new_urls)} new URLs found")
                print(f"  📊 Total discovered: {len(all_discovered)}")
                
                # Set up for next depth
                current_depth_urls = new_urls
                
                # Stop if no new URLs or too many total URLs
                if not new_urls:
                    print(f"    🏁 No new URLs found at depth {depth}, stopping")
                    break
                
                if len(all_discovered) > 3000:
                    print(f"    🛑 Reached 3000 URLs limit, stopping at depth {depth}")
                    break
        
        discovered_urls = all_discovered
        print(f"\n🎯 Depth-based crawling discovered {len(discovered_urls)} total URLs")
        
    except Exception as e:
        print(f"❌ Error in depth-based crawling: {e}")
        import traceback
        traceback.print_exc()
    
    execution_time = time.time() - start_time
    result = tracker.add_phase_urls("4_depth_recursive_crawling", list(discovered_urls), execution_time)
    
    print(f"\n✅ PHASE 4 COMPLETED")
    print(f"⏱️ Time: {execution_time:.2f}s")
    print(f"📊 URLs Found: {result['total_found']}")
    print(f"🆕 New URLs: {result['new_unique']}")
    print(f"💾 Results saved to: all_urls.json")
    
    return result

async def process_depth_level(session, urls, domain, depth):
    """Process all URLs at a specific depth level"""
    all_next_depth_urls = set()
    semaphore = asyncio.Semaphore(3)  # Very conservative concurrency
    
    async def crawl_url_for_depth(url):
        async with semaphore:
            try:
                # Rate limiting
                await asyncio.sleep(0.3)
                
                async with session.get(url) as response:
                    if response.status == 200:
                        # Handle encoding properly
                        try:
                            content = await response.read()
                            
                            # Try different encodings for Japanese content
                            for encoding in ['utf-8', 'shift_jis', 'euc-jp', 'iso-2022-jp']:
                                try:
                                    text = content.decode(encoding)
                                    break
                                except UnicodeDecodeError:
                                    continue
                            else:
                                # If all encodings fail, use utf-8 with error handling
                                text = content.decode('utf-8', errors='ignore')
                        
                        except Exception as e:
                            print(f"      ⚠️ Encoding error: {url[:50]}...")
                            return set()
                        
                        # Extract links for next depth
                        links = extract_links_for_depth(text, url, domain)
                        
                        if links:
                            print(f"    📎 Depth {depth}: {url[:50]}... → {len(links)} links")
                        
                        return links
                    else:
                        if response.status != 404:  # Don't spam 404 errors
                            print(f"      ❌ HTTP {response.status}: {url[:50]}...")
                        return set()
                        
            except asyncio.TimeoutError:
                print(f"      ⏰ Timeout: {url[:50]}...")
                return set()
            except Exception as e:
                print(f"      ⚠️ Error: {url[:50]}... - {str(e)[:30]}")
                return set()
    
    # Process all URLs at this depth
    tasks = [crawl_url_for_depth(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect all links for next depth
    for result in results:
        if isinstance(result, set):
            all_next_depth_urls.update(result)
    
    return all_next_depth_urls

def extract_links_for_depth(html_content, base_url, domain):
    """Extract links from HTML for next depth level"""
    links = set()
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all anchor tags
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            
            # Skip obvious non-links
            if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:') or href.startswith('tel:'):
                continue
            
            # Convert to absolute URL
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            
            # Only include same domain URLs
            if parsed.netloc == domain:
                if should_crawl_url(full_url):
                    links.add(full_url)
    
    except Exception as e:
        print(f"        ⚠️ HTML parsing error: {str(e)[:30]}")
    
    return links

def should_crawl_url(url):
    """Determine if URL should be crawled for depth-based exploration"""
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Exclude file downloads
        excluded_extensions = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.tar', '.gz', '.7z',
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.webp', '.bmp',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.wav',
            '.css', '.js', '.xml', '.json', '.txt', '.csv'
        ]
        
        for ext in excluded_extensions:
            if path.endswith(ext):
                return False
        
        # Exclude non-content paths
        excluded_patterns = [
            '/print.asp', '/feedback.asp', '/download/', '/file/', '/attachment/',
            '/admin/', '/login/', '/logout/', '/api/', '/ajax/', '/cgi-bin/',
            '?print=', '?download=', '?action=print', '?format=pdf',
            '/search?', '/searchresult', '#print', '#download'
        ]
        
        url_lower = url.lower()
        for pattern in excluded_patterns:
            if pattern in url_lower:
                return False
        
        # Include HTML pages and directory-like URLs
        return True
        
    except Exception:
        return False

async def main():
    """Main function to run Phase 4 depth-based crawling"""
    base_url = "https://www.city.chiyoda.lg.jp/"
    tracker = PhaseURLTracker(base_url)
    
    result = await test_phase_4_depth_based(tracker)
    return result

if __name__ == "__main__":
    asyncio.run(main())
