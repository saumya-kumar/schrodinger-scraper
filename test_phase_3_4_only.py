#!/usr/bin/env python3
"""Test Phase 3 and 4 only - simplified version"""

import sys
import json
import time
import requests
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

class PhaseURLTracker:
    """Tracks URLs using sets for proper deduplication"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.all_urls = set()
        self.results_file = Path("all_urls.json")
        self.load_existing_data()
    
    def load_existing_data(self):
        """Load existing URLs from all_urls.json"""
        if self.results_file.exists() and self.results_file.stat().st_size > 0:
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
        phase_urls_set = set(phase_urls)
        new_urls = phase_urls_set - self.all_urls
        self.all_urls.update(new_urls)
        
        # Save to JSON file
        self.save_to_json(phase_name, phase_urls, execution_time)
        
        return {
            'total_found': len(phase_urls),
            'new_unique': len(new_urls),
            'execution_time': execution_time
        }
    
    def save_to_json(self, phase_name, phase_urls, execution_time):
        """Save phase results to JSON file"""
        data = {}
        if self.results_file.exists() and self.results_file.stat().st_size > 0:
            try:
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = {}
        
        if not data:
            data = {
                "schema_version": "2.0",
                "base_domain": self.base_url.replace('https://', '').replace('http://', '').rstrip('/'),
                "description": "Unified store of all discovered URLs with set-based deduplication",
                "created_at_utc": datetime.now().isoformat(),
                "phases": {}
            }
        
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

def test_phase_3(tracker):
    """Phase 3: Enhanced URL Seeding with Crawl4AI"""
    print("\n🌐 PHASE 3: ENHANCED URL SEEDING")
    print("=" * 50)
    
    start_time = time.time()
    discovered_urls = set()
    
    try:
        from crawl4ai import AsyncUrlSeeder, SeedingConfig
        import asyncio
        
        async def run_enhanced_seeding():
            domain = tracker.base_url.replace('https://', '').replace('http://', '').rstrip('/')
            
            async with AsyncUrlSeeder() as seeder:
                # Comprehensive seeding with multiple strategies
                configs = [
                    SeedingConfig(
                        source="sitemap+cc",
                        pattern="*",
                        max_urls=10000,
                        concurrency=30,
                        hits_per_sec=20,
                        verbose=True,
                        force=True
                    ),
                    SeedingConfig(
                        source="cc",
                        pattern="*.html",
                        max_urls=5000,
                        concurrency=25,
                        verbose=False
                    )
                ]
                
                all_urls = set()
                for i, config in enumerate(configs, 1):
                    try:
                        print(f"🔄 Strategy {i}/{len(configs)}...")
                        urls = await seeder.urls(domain, config)
                        step_urls = [url["url"] if isinstance(url, dict) else url for url in urls]
                        before = len(all_urls)
                        all_urls.update(step_urls)
                        new_count = len(all_urls) - before
                        print(f"  ✅ Found {len(step_urls)} URLs ({new_count} new)")
                    except Exception as e:
                        print(f"  ⚠️ Strategy {i} failed: {e}")
                
                return list(all_urls)
        
        urls = asyncio.run(run_enhanced_seeding())
        discovered_urls.update(urls)
        
    except ImportError:
        print("❌ Crawl4AI not available, using basic fallback")
        # Basic requests fallback
        sitemap_url = f"{tracker.base_url}/sitemap.html"
        try:
            response = requests.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                for link in soup.find_all('a', href=True):
                    full_url = urljoin(sitemap_url, link['href'])
                    if tracker.base_url.replace('https://', '').replace('http://', '') in full_url:
                        discovered_urls.add(full_url)
        except Exception as e:
            print(f"❌ Fallback failed: {e}")
    
    execution_time = time.time() - start_time
    result = tracker.add_phase_urls("3_url_seeding", list(discovered_urls), execution_time)
    
    print(f"⏱️ Time: {execution_time:.2f}s | URLs: {result['total_found']} | New: {result['new_unique']}")
    return result

def test_phase_4(tracker):
    """Phase 4: Recursive Link Crawling"""
    print("\n🔄 PHASE 4: RECURSIVE LINK CRAWLING")
    print("=" * 50)
    
    start_time = time.time()
    discovered_urls = set()
    
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        import asyncio
        
        async def run_recursive_crawling():
            base_url = tracker.base_url
            domain = urlparse(base_url).netloc
            
            # Use existing URLs as seeds
            seed_urls = list(tracker.all_urls)[:50]  # First 50 URLs
            print(f"🌱 Using {len(seed_urls)} seed URLs")
            
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
                java_script_enabled=True,
                ignore_https_errors=True
            )
            
            all_discovered = set(seed_urls)
            max_pages = 1000  # Reasonable limit
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                crawler_config = CrawlerRunConfig(
                    page_timeout=15000,
                    verbose=False,
                    wait_for_images=False,
                    delay_before_return_html=1000
                )
                
                # Process seed URLs to find more links
                for i, url in enumerate(seed_urls[:20]):  # Process first 20 seeds
                    try:
                        print(f"  🔍 Processing {i+1}/20: {url[:60]}...")
                        result = await crawler.arun(url, config=crawler_config)
                        
                        if result.success and result.html:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(result.html, 'html.parser')
                            
                            for link in soup.find_all('a', href=True):
                                href = link['href']
                                if href and not href.startswith('#'):
                                    full_url = urljoin(url, href)
                                    if domain in full_url:
                                        all_discovered.add(full_url)
                        
                        if len(all_discovered) >= max_pages:
                            break
                            
                    except Exception as e:
                        print(f"    ⚠️ Error: {str(e)[:50]}")
                        continue
            
            return list(all_discovered)
        
        urls = asyncio.run(run_recursive_crawling())
        discovered_urls.update(urls)
        
    except ImportError:
        print("❌ Crawl4AI not available, using requests fallback")
        # Simple fallback
        seed_urls = list(tracker.all_urls)[:5]
        for seed_url in seed_urls:
            try:
                response = requests.get(seed_url, timeout=10)
                if response.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.content, 'html.parser')
                    for link in soup.find_all('a', href=True):
                        full_url = urljoin(seed_url, link['href'])
                        if tracker.base_url.replace('https://', '').replace('http://', '') in full_url:
                            discovered_urls.add(full_url)
            except:
                continue
    
    execution_time = time.time() - start_time
    result = tracker.add_phase_urls("4_recursive_crawling", list(discovered_urls), execution_time)
    
    print(f"⏱️ Time: {execution_time:.2f}s | URLs: {result['total_found']} | New: {result['new_unique']}")
    return result

def run_phases_3_4(base_url):
    """Run Phase 3 and 4 only"""
    print("📋 TESTING PHASE 3 AND 4")
    print("=" * 50)
    print(f"📋 Target: {base_url}")
    
    tracker = PhaseURLTracker(base_url)
    
    # Phase 3
    result_3 = test_phase_3(tracker)
    
    # Phase 4
    result_4 = test_phase_4(tracker)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Phase 3: {result_3['total_found']:3d} found | {result_3['new_unique']:3d} new | {result_3['execution_time']:.2f}s")
    print(f"Phase 4: {result_4['total_found']:3d} found | {result_4['new_unique']:3d} new | {result_4['execution_time']:.2f}s")
    print(f"Total URLs: {len(tracker.all_urls)}")
    
    return {'phase_3': result_3, 'phase_4': result_4}

if __name__ == "__main__":
    test_url = "https://www.city.chiyoda.lg.jp/"
    results = run_phases_3_4(test_url)
