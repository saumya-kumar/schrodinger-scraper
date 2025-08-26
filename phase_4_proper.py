#!/usr/bin/env python3
"""
Phase 4: Proper Recursive Link Crawling Implementation
Based on comprehensive_site_crawler.py logic
"""

import asyncio
import aiohttp
import time
import json
from collections import deque
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

class ProperPhase4Crawler:
    """Proper recursive link crawling implementation"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.discovered_urls = set()
        self.crawled_urls = set()
        self.failed_urls = set()
        self.url_metadata = {}
        self._consecutive_empty_batches = 0  # Track empty batches for intelligent stopping
        
        # Configuration
        self.max_pages = 50000  # ULTRA HIGH: 50k for maximum discovery
        self.max_concurrent = 100  # High concurrency
        self.delay_between_requests = 0.01  # 10ms delay - ultra fast
        self.timeout = 15
        self.max_depth = 9  # Maximum crawling depth
        self.batch_size = 500  # Large batches for ultra-fast processing
        
        # Headers for requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    def _create_session(self) -> aiohttp.ClientSession:
        """Create a properly configured HTTP session"""
        connector = aiohttp.TCPConnector(
            ssl=False,
            limit=200,  # Connection pool limit
            limit_per_host=50,  # Per-host limit
            keepalive_timeout=60,
            enable_cleanup_closed=True,
            force_close=False,
            ttl_dns_cache=600
        )
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        return aiohttp.ClientSession(
            headers=self.headers,
            connector=connector,
            timeout=timeout
        )
    
    async def recursive_link_crawling(self) -> set:
        """Main recursive crawling function - ULTRA-FAST BATCH PROCESSING"""
        print("[RECURSIVE] Starting ULTRA-FAST recursive link crawling...")
        start_time = time.time()
        
        # Initialize using QUEUE approach with depth tracking
        url_queue = deque([(self.base_url, 0)])  # (url, depth) tuples
        self.discovered_urls.add(self.base_url)
        batch_size = self.batch_size  # Use configured batch size (500)
        total_processed = 0
        depth_stats = {}  # Track URLs per depth
        batch_number = 0
        
        print(f"🔧 Starting with batch size: {batch_size}, max pages: {self.max_pages}")
        
        while url_queue and len(self.discovered_urls) < self.max_pages:
            batch_number += 1
            
            # Process URLs in batches
            current_batch = []
            batch_count = min(batch_size, len(url_queue))
            current_depth_batch = None
            skipped_deep_urls = 0
            
            for _ in range(batch_count):
                if url_queue:
                    url_depth_tuple = url_queue.popleft()
                    url, depth = url_depth_tuple
                    
                    # Skip if depth exceeds maximum but track it
                    if depth > self.max_depth:
                        skipped_deep_urls += 1
                        continue
                        
                    current_batch.append(url)
                    
                    # Track depth for this batch
                    if current_depth_batch is None:
                        current_depth_batch = depth
                    
                    # Track depth statistics
                    if depth not in depth_stats:
                        depth_stats[depth] = 0
                    depth_stats[depth] += 1
            
            if not current_batch:
                # No URLs left to process at valid depths
                print(f"⚠️ No more URLs to process (skipped {skipped_deep_urls} deep URLs)")
                break
            
            print(f"📦 Batch {batch_number}: Processing {len(current_batch)} URLs at depth {current_depth_batch}")
            print(f"   Queue remaining: {len(url_queue)}, Total discovered: {len(self.discovered_urls)}")
            
            # Process this batch and get NEW URLs
            batch_start = time.time()
            new_urls_found = await self._process_url_batch_ultra_fast(current_batch)
            batch_time = time.time() - batch_start
            
            # Add NEW URLs to both discovered set and queue for next processing with depth tracking
            truly_new_urls = new_urls_found - self.discovered_urls
            self.discovered_urls.update(truly_new_urls)
            
            # Add new URLs to queue for further crawling with incremented depth
            next_depth = current_depth_batch + 1 if current_depth_batch is not None else 1
            new_urls_added = 0
            for new_url in truly_new_urls:
                if next_depth <= self.max_depth and len(self.discovered_urls) < self.max_pages:
                    url_queue.append((new_url, next_depth))
                    new_urls_added += 1
            
            print(f"   ✅ Found {len(new_urls_found)} links, {len(truly_new_urls)} new URLs, added {new_urls_added} to queue")
            total_processed += len(current_batch)
            
            # Progress reporting every 5 batches
            if batch_number % 5 == 0:
                print(f"🔄 Progress: {total_processed} processed, {len(self.discovered_urls)} discovered, {len(url_queue)} queued")
                print(f"   Depth distribution: {dict(sorted(depth_stats.items()))}")
            
            # Intelligent stopping conditions
            if len(truly_new_urls) == 0 and len(url_queue) < batch_size:
                print(f"   🏁 Low discovery rate at depth {current_depth_batch}, minimal queue remaining")
                break
            
            # Prevent infinite loops - but be more careful
            consecutive_empty_batches = getattr(self, '_consecutive_empty_batches', 0)
            if len(truly_new_urls) == 0:
                consecutive_empty_batches += 1
                self._consecutive_empty_batches = consecutive_empty_batches
                if consecutive_empty_batches >= 3:  # Allow a few empty batches before stopping
                    print("   🏁 Multiple empty batches - stopping to prevent infinite loop")
                    break
            else:
                self._consecutive_empty_batches = 0
        
        # Final comprehensive reporting
        crawl_time = time.time() - start_time
        print(f"\n🎯 PHASE 4 COMPLETE - Recursive Link Crawling")
        print(f"⏱️ Execution time: {crawl_time:.1f}s")
        print(f"📊 Total URLs discovered: {len(self.discovered_urls)}")
        print(f"📊 Total URLs processed: {total_processed}")
        print(f"📊 Total batches processed: {batch_number}")
        print(f"📊 Pages crawled successfully: {len(self.crawled_urls)}")
        print(f"📊 Queue remaining: {len(url_queue)}")
        print(f"📊 Depth distribution: {dict(sorted(depth_stats.items()))}")
        
        if len(url_queue) > 0:
            print(f"⚠️ Stopped due to max_pages limit ({self.max_pages}), {len(url_queue)} URLs remain queued")
        if skipped_deep_urls > 0:
            print(f"⚠️ Skipped {skipped_deep_urls} URLs that exceeded max depth ({self.max_depth})")
        
        return sorted(list(self.discovered_urls))
        print(f"❌ Failed {len(self.failed_urls)} pages")
        
        # Print depth statistics
        print("📊 DEPTH STATISTICS:")
        for depth in sorted(depth_stats.keys()):
            print(f"    Depth {depth}: {depth_stats[depth]} URLs processed")
        
        return self.discovered_urls
    
    async def _process_url_batch_ultra_fast(self, urls) -> set:
        """Process a batch of URLs ultra-fast"""
        all_new_links = set()
        
        # Use semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_single_url_ultra_fast(url: str) -> set:
            async with semaphore:
                try:
                    # Minimal delay for maximum speed
                    await asyncio.sleep(self.delay_between_requests)
                    return await self._extract_links_ultra_fast(url)
                except Exception as e:
                    print(f"      ⚠️ Error: {url[:40]}... - {str(e)[:50]}")
                    return set()
        
        # Process all URLs in batch concurrently
        tasks = [process_single_url_ultra_fast(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all discovered links
        for result in results:
            if isinstance(result, set):
                all_new_links.update(result)
        
        return all_new_links
    
    async def _extract_links_ultra_fast(self, url: str) -> set:
        """ULTRA-FAST link extraction - MAXIMUM SPEED, MINIMAL FILTERING"""
        links = set()
        
        try:
            async with self._create_session() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # Handle different encodings properly
                        try:
                            content = await response.text(encoding='utf-8')
                        except UnicodeDecodeError:
                            try:
                                content = await response.text(encoding='shift_jis')
                            except UnicodeDecodeError:
                                content = await response.text(encoding='latin1', errors='ignore')
                        
                        # ULTRA-FAST: Use faster parsing
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Extract ALL href attributes - NO FILTERING for speed
                        for element in soup.find_all(href=True):
                            href = element['href']
                            full_url = urljoin(url, href)
                            if self._should_include_url_fast(full_url):
                                links.add(full_url)
                        
                        # Extract form actions
                        for form in soup.find_all('form', action=True):
                            action = form['action']
                            full_url = urljoin(url, action)
                            if self._should_include_url_fast(full_url):
                                links.add(full_url)
                        
                        # Store minimal metadata for speed
                        page_title = self._extract_title_fast(content)
                        self.url_metadata[url] = {
                            "status": response.status,
                            "content_type": response.headers.get("content-type", ""),
                            "title": page_title
                        }
                        
                        # Mark as crawled
                        self.crawled_urls.add(url)
                        
                    else:
                        self.failed_urls.add(url)
                    
        except Exception as e:
            self.failed_urls.add(url)
        
        return links
    
    def _should_include_url_fast(self, url: str) -> bool:
        """ULTRA-FAST URL filtering - minimal checks for maximum speed"""
        try:
            parsed = urlparse(url)
            
            # Must be same domain
            if parsed.netloc != self.domain:
                return False
            
            # MINIMAL filtering for maximum speed
            path = parsed.path.lower()
            
            # Skip only the most obvious non-content URLs
            if any(ext in path for ext in ['.css', '.js', '.zip', '.exe']):
                return False
            
            # Skip malformed URLs
            if '#tmp_header' in url or '/tmp/' in path:
                return False
            
            return True
        except:
            return False
    
    def _extract_title_fast(self, content: str) -> str:
        """ULTRA-FAST title extraction"""
        try:
            # Find title tag with minimal processing
            title_start = content.find('<title>')
            if title_start != -1:
                title_end = content.find('</title>', title_start)
                if title_end != -1:
                    return content[title_start + 7:title_end].strip()
        except:
            pass
        return ""

# Test function for Phase 4
async def test_phase_4_proper(base_url, existing_urls=None):
    """Test the proper Phase 4 implementation"""
    print("🔄 PHASE 4: PROPER RECURSIVE LINK CRAWLING (aiohttp)")
    print("=" * 60)
    
    start_time = time.time()
    
    # Load existing URLs
    if existing_urls:
        print(f"📋 Loaded {len(existing_urls)} existing URLs")
    
    # Create crawler
    crawler = ProperPhase4Crawler(base_url)
    
    # Run recursive crawling
    discovered_urls = await crawler.recursive_link_crawling()
    
    execution_time = time.time() - start_time
    
    # Convert discovered_urls to set for proper set operations
    discovered_urls_set = set(discovered_urls)
    
    # Calculate new URLs
    if existing_urls:
        new_urls = discovered_urls_set - existing_urls
    else:
        new_urls = discovered_urls_set
    
    print(f"\n✅ PHASE 4 COMPLETED")
    print(f"⏱️ Time: {execution_time:.2f}s")
    print(f"📊 URLs Found: {len(discovered_urls_set)}")
    print(f"🆕 New URLs: {len(new_urls)}")
    print(f"🔄 Pages Crawled: {len(crawler.crawled_urls)}")
    print(f"❌ Failed URLs: {len(crawler.failed_urls)}")
    
    return {
        'total_found': len(discovered_urls_set),
        'new_unique': len(new_urls),
        'execution_time': execution_time,
        'urls': list(discovered_urls_set),
        'crawled_count': len(crawler.crawled_urls),
        'failed_count': len(crawler.failed_urls)
    }

# Main execution
if __name__ == "__main__":
    async def main():
        base_url = "https://www.city.chiyoda.lg.jp/"
        
        # Load existing URLs
        existing_urls = set()
        try:
            with open('all_urls.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for phase_data in data.get('phases', {}).values():
                    if 'urls' in phase_data:
                        existing_urls.update(phase_data['urls'])
        except:
            pass
        
        # Run Phase 4
        result = await test_phase_4_proper(base_url, existing_urls)
        
        # Save results
        if result['urls']:
            try:
                # Load existing data
                try:
                    with open('all_urls.json', 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except:
                    data = {
                        "schema_version": "2.0",
                        "base_domain": "www.city.chiyoda.lg.jp",
                        "description": "Unified store of all discovered URLs with set-based deduplication",
                        "created_at_utc": datetime.now().isoformat(),
                        "phases": {}
                    }
                
                # Add Phase 4 results
                data['phases']['4_recursive_crawling'] = {
                    "execution_time": result['execution_time'],
                    "raw_count": result['total_found'],
                    "stats": {
                        "html_pages": len([url for url in result['urls'] if url.endswith('.html') or not any(f'.{ext}' in url for ext in ['pdf', 'doc', 'zip', 'jpg', 'css', 'js', 'xml'])]),
                        "other_urls": result['total_found'] - len([url for url in result['urls'] if url.endswith('.html') or not any(f'.{ext}' in url for ext in ['pdf', 'doc', 'zip', 'jpg', 'css', 'js', 'xml'])])
                    },
                    "timestamp": datetime.now().isoformat(),
                    "urls": result['urls'],
                    "crawled_count": result['crawled_count'],
                    "failed_count": result['failed_count']
                }
                
                # Update metadata
                data['updated_at_utc'] = datetime.now().isoformat()
                all_unique_urls = set()
                for phase_data in data['phases'].values():
                    if 'urls' in phase_data:
                        all_unique_urls.update(phase_data['urls'])
                data['total_unique_urls'] = len(all_unique_urls)
                
                # Save
                with open('all_urls.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"💾 Results saved to: all_urls.json")
                print(f"📊 Total unique URLs now: {data['total_unique_urls']}")
                
            except Exception as e:
                print(f"⚠️ Could not save results: {e}")
    
    # Run the async main function
    asyncio.run(main())
