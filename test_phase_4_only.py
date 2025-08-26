#!/usr/bin/env python3
"""Test Phase 4 Only - Ultra-Fast Recursive Link Crawling using aiohttp"""

import time
import json
import asyncio
import aiohttp
from collections import deque
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
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
        """Save phase results to JSON"""
        data = {}
        if self.results_file.exists():
            try:
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = {}
        
        # Initialize structure if empty
        if not data:
            data = {
                "schema_version": "2.0",
                "base_domain": self.base_url.replace('https://', '').replace('http://', '').rstrip('/'),
                "description": "Unified store of all discovered URLs",
                "created_at_utc": datetime.now().isoformat(),
                "phases": {}
            }
        
        # Update phase data
        data['phases'][phase_name] = {
            "execution_time": execution_time,
            "raw_count": len(phase_urls),
            "timestamp": datetime.now().isoformat(),
            "urls": list(phase_urls)
        }
        
        # Update metadata
        data['updated_at_utc'] = datetime.now().isoformat()
        data['total_unique_urls'] = len(self.all_urls)
        
        # Save
        with open(self.results_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

async def run_ultra_fast_recursive_crawling(tracker):
    """Ultra-fast recursive link crawling with aiohttp"""
    print(f"🚀 Starting ultra-fast recursive link crawling with aiohttp...")
    
    # Configuration for ultra-fast recursive crawling
    base_url = tracker.base_url
    domain = urlparse(base_url).netloc
    
    # Initialize queue-based system
    url_queue = deque([base_url])
    if tracker.all_urls:
        # Add existing discovered URLs as additional seeds
        seed_urls = list(tracker.all_urls)[:50]  # Use first 50 as seeds
        url_queue.extend(seed_urls)
        print(f"🌱 Added {len(seed_urls)} existing URLs as additional seeds")
    
    crawled_urls = set()
    all_discovered = set(url_queue)
    max_pages = 1000  # Reasonable limit for Phase 4
    batch_size = 50   # Batch size for processing
    total_processed = 0
    
    print(f"🔧 Queue initialized with {len(url_queue)} URLs")
    
    # Create aiohttp session with proper configuration
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    connector = aiohttp.TCPConnector(
        ssl=False,
        limit=100,        # Connection pool limit
        limit_per_host=20, # Per-host limit
        keepalive_timeout=60,
        enable_cleanup_closed=True,
        force_close=False
    )
    
    timeout = aiohttp.ClientTimeout(total=15)
    
    try:
        async with aiohttp.ClientSession(
            headers=headers,
            connector=connector,
            timeout=timeout
        ) as session:
            
            # Ultra-fast queue-based processing
            while url_queue and len(crawled_urls) < max_pages:
                # Process URLs in large batches
                current_batch = []
                batch_count = min(batch_size, len(url_queue))
                
                for _ in range(batch_count):
                    if url_queue:
                        current_batch.append(url_queue.popleft())
                
                if not current_batch:
                    break
                
                total_processed += len(current_batch)
                print(f"    📊 Processing batch of {len(current_batch)} URLs (Total: {total_processed})")
                
                # Process batch and find NEW URLs
                batch_start = time.time()
                new_urls_found = await process_batch_ultra_fast(session, current_batch, domain)
                batch_time = time.time() - batch_start
                
                # Add NEW URLs to both discovered set and queue
                truly_new_urls = new_urls_found - all_discovered
                all_discovered.update(truly_new_urls)
                crawled_urls.update(current_batch)
                
                # Add new URLs to queue for further crawling
                for new_url in truly_new_urls:
                    url_queue.append(new_url)
                
                print(f"    ✅ Batch complete: {len(truly_new_urls)} new URLs found in {batch_time:.1f}s")
                print(f"    📈 Total discovered: {len(all_discovered)} | Queue: {len(url_queue)}")
                
                # Prevent infinite loops and respect limits
                if len(truly_new_urls) == 0 and len(url_queue) == 0:
                    print("    🏁 No new URLs found and queue empty - stopping")
                    break
                    
                if len(all_discovered) >= max_pages:
                    print(f"    🛑 Reached max pages limit ({max_pages})")
                    break
                
                # Small delay between batches for server courtesy
                await asyncio.sleep(0.1)
            
            print(f"🎯 Ultra-fast recursive crawling discovered {len(all_discovered)} total URLs")
            
    except Exception as e:
        print(f"❌ Session error: {str(e)[:80]}")
        return []
    
    return list(all_discovered)

async def process_batch_ultra_fast(session, urls, domain):
    """Process a batch of URLs ultra-fast and extract all links using aiohttp"""
    all_new_links = set()
    
    # Process URLs with controlled concurrency
    semaphore = asyncio.Semaphore(20)  # Control concurrency
    
    async def process_single_url_ultra_fast(url):
        async with semaphore:
            try:
                await asyncio.sleep(0.05)  # Small delay for politeness
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        links = extract_links_from_html(content, url, domain)
                        return links
            except Exception as e:
                print(f"      ⚠️ Error: {url[:40]}... - {str(e)[:30]}")
            return set()
    
    # Process all URLs in batch concurrently
    tasks = [process_single_url_ultra_fast(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect all discovered links
    for result in results:
        if isinstance(result, set):
            all_new_links.update(result)
    
    return all_new_links

def extract_links_from_html(html_content, base_url, domain):
    """Extract links from HTML content using BeautifulSoup"""
    links = set()
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract all href links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href and not href.startswith('#'):
                full_url = urljoin(base_url, href)
                if should_include_url_ultra_fast(full_url, domain):
                    links.add(full_url)
        
        # Extract navigation links specifically
        nav_elements = soup.find_all(['nav', 'ul', 'div'], class_=re.compile(r'nav|menu|breadcrumb', re.I))
        for nav in nav_elements:
            nav_links = nav.find_all('a', href=True)
            for link in nav_links:
                href = link['href']
                if href and not href.startswith('#'):
                    full_url = urljoin(base_url, href)
                    if should_include_url_ultra_fast(full_url, domain):
                        links.add(full_url)
        
        # Extract footer links
        footer = soup.find('footer') or soup.find('div', class_=re.compile(r'footer', re.I))
        if footer:
            footer_links = footer.find_all('a', href=True)
            for link in footer_links:
                href = link['href']
                if href and not href.startswith('#'):
                    full_url = urljoin(base_url, href)
                    if should_include_url_ultra_fast(full_url, domain):
                        links.add(full_url)
                        
    except Exception as e:
        print(f"        ⚠️ HTML parsing error: {str(e)[:50]}")
    
    return links

def should_include_url_ultra_fast(url, domain):
    """Ultra-fast URL filtering for maximum speed"""
    try:
        parsed = urlparse(url)
        
        # Must be same domain
        if parsed.netloc != domain:
            return False
        
        # Ultra-fast filtering - only exclude obvious non-content
        path = parsed.path.lower()
        
        # Skip only the most obvious non-content URLs
        if any(ext in path for ext in ['.css', '.js', '.zip', '.exe', '.png', '.jpg', '.gif', '.pdf', '.doc']):
            return False
        
        # Skip malformed URLs and admin paths
        if any(pattern in url.lower() for pattern in ['#tmp_header', '/tmp/', '/admin/', '/api/', 'mailto:', 'tel:']):
            return False
        
        return True
        
    except Exception:
        return False

async def test_phase_4_only():
    """Test Phase 4 only with proper aiohttp implementation"""
    print("🔄 PHASE 4: ULTRA-FAST RECURSIVE LINK CRAWLING (aiohttp)")
    print("=" * 60)
    
    # Initialize tracker
    tracker = PhaseURLTracker("https://www.city.chiyoda.lg.jp/")
    
    start_time = time.time()
    
    try:
        # Run the ultra-fast async function
        urls = await run_ultra_fast_recursive_crawling(tracker)
        
        execution_time = time.time() - start_time
        result = tracker.add_phase_urls("4_recursive_crawling", urls, execution_time)
        
        print(f"\n✅ PHASE 4 COMPLETED")
        print(f"⏱️ Time: {execution_time:.2f}s")
        print(f"📊 URLs Found: {result['total_found']}")
        print(f"🆕 New URLs: {result['new_unique']}")
        print(f"💾 Results saved to: all_urls.json")
        
        return result
        
    except Exception as e:
        print(f"❌ Error in Phase 4: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    # Run Phase 4 test
    result = asyncio.run(test_phase_4_only())
