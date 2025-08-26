#!/usr/bin/env python3
"""Test all phases sequentially with set-based deduplication"""

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
        self.base_url = bdef run_all_phases(base_url):
    """Run all phases with set-based tracking"""
    print("📋 TESTING ALL PHASES WITH SET-BASED DEDUPLICATION")
    print("=" * 80)
    print(f"📋 Target: {base_url}")
    print(f"💾 Results stored in: all_urls.json")
    
    # Initialize tracker
    tracker = PhaseURLTracker(base_url)
    
    # Run phases
    phase_results = {}
    
    # Phase 1
    phase_results['phase_1'] = test_phase_1(tracker)
    
    # Phase 2
    phase_results['phase_2'] = test_phase_2(tracker)
    
    # Phase 3
    phase_results['phase_3'] = test_phase_3(tracker)
    
    # Phase 4
    phase_results['phase_4'] = test_phase_4(tracker)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"🔢 Total Unique URLs in Set: {len(tracker.all_urls)}")
    
    for phase, result in phase_results.items():
        print(f"{phase:15} | {result['total_found']:3d} found | {result['new_unique']:3d} new | {result['execution_time']:.2f}s")
    
    print(f"\n✅ All results stored in: all_urls.json")
    print(f"🎯 Master URL set contains: {len(tracker.all_urls)} unique URLs")
    
    return phase_resultself.all_urls = set()  # Master set for deduplication
        self.results_file = Path("all_urls.json")
        
        # Load existing data
        self.load_existing_data()
    
    def load_existing_data(self):
        """Load existing URLs from all_urls.json"""
        if self.results_file.exists() and self.results_file.stat().st_size > 0:
            try:
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Extract all existing URLs into our set
                    if 'phases' in data:
                        for phase_data in data['phases'].values():
                            if 'urls' in phase_data:
                                self.all_urls.update(phase_data['urls'])
                    print(f"📋 Loaded {len(self.all_urls)} existing URLs from all_urls.json")
            except Exception as e:
                print(f"⚠️ Could not load existing data: {e}")
                print("🔄 Starting fresh with empty URL set")
        else:
            print("📋 Starting with fresh URL set (no existing data)")
    
    def comprehensive_url_filter(self, url):
        """Enhanced URL filtering with strict exclusion"""
        if not url or not isinstance(url, str):
            return False
        
        url = url.strip().lower()
        
        # File extension exclusions
        excluded_extensions = {
            'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
            'zip', 'rar', '7z', 'tar', 'gz',
            'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'ico',
            'mp3', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'wav',
            'css', 'js', 'xml', 'json', 'txt', 'csv',
            'rss', 'atom'
        }
        
        # Check for file extensions
        for ext in excluded_extensions:
            if f'.{ext}' in url:
                return False
        
        # Additional exclusions
        excluded_patterns = [
            'mailto:', 'tel:', 'ftp:', 'javascript:', '#',
            'download', 'file', 'attachment', 'document', 'asset'
        ]
        
        for pattern in excluded_patterns:
            if pattern in url:
                return False
        
        return True
    
    def add_phase_urls(self, phase_name, urls, execution_time):
        """Add URLs from a phase, tracking unique counts"""
        # Filter and convert to set
        filtered_urls = [url for url in urls if self.comprehensive_url_filter(url)]
        phase_url_set = set(filtered_urls)
        
        # Calculate new unique URLs
        new_urls = phase_url_set - self.all_urls
        
        # Update master set
        self.all_urls.update(phase_url_set)
        
        # Update all_urls.json
        self.update_json_file(phase_name, phase_url_set, execution_time)
        
        return {
            'total_found': len(phase_url_set),
            'new_unique': len(new_urls),
            'execution_time': execution_time
        }
    
    def update_json_file(self, phase_name, phase_urls, execution_time):
        """Update the all_urls.json file"""
        # Load current data
        data = {}
        if self.results_file.exists() and self.results_file.stat().st_size > 0:
            try:
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                print("⚠️ JSON file corrupted, creating new structure")
                data = {}
        
        # Initialize structure if empty
        if not data:
            data = {
                "schema_version": "2.0",
                "base_domain": self.base_url.replace('https://', '').replace('http://', '').rstrip('/'),
                "description": "Unified store of all discovered URLs with set-based deduplication",
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
        
        # Update metadata
        data['updated_at_utc'] = datetime.now().isoformat()
        data['total_unique_urls'] = len(self.all_urls)
        
        # Save
        with open(self.results_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def test_phase_1(tracker):
    """Phase 1: Sitemap Discovery"""
    print("🗺️ PHASE 1: SITEMAP DISCOVERY")
    print("=" * 50)
    
    start_time = time.time()
    discovered_urls = set()
    
    base_url = tracker.base_url
    
    # Try sitemap.html
    try:
        sitemap_url = urljoin(base_url, "sitemap.html")
        print(f"🔍 Checking: {sitemap_url}")
        
        response = requests.get(sitemap_url, timeout=10)
        if response.status_code == 200:
            content = response.text
            print(f"✅ Found sitemap.html with {len(content)} characters")
            
            # Extract URLs
            url_pattern = r'href=["\']([^"\']+)["\']'
            matches = re.findall(url_pattern, content)
            
            for match in matches:
                full_url = urljoin(base_url, match)
                if full_url.startswith(('http://', 'https://')):
                    discovered_urls.add(full_url)
        else:
            print(f"❌ sitemap.html: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    execution_time = time.time() - start_time
    result = tracker.add_phase_urls("1_sitemap", list(discovered_urls), execution_time)
    
    print(f"⏱️ Time: {execution_time:.2f}s | URLs: {result['total_found']} | New: {result['new_unique']}")
    return result

def test_phase_2(tracker):
    """Phase 2: Robots.txt Analysis"""
    print("\n🤖 PHASE 2: ROBOTS.TXT ANALYSIS")
    print("=" * 50)
    
    start_time = time.time()
    discovered_urls = set()
    
    try:
        robots_url = f"{tracker.base_url.rstrip('/')}/robots.txt"
        print(f"🔍 Checking: {robots_url}")
        
        response = requests.get(robots_url, timeout=10)
        if response.status_code == 200:
            content = response.text
            print(f"✅ Found robots.txt with {len(content)} characters")
            
            # Extract patterns
            allow_patterns = re.findall(r'Allow:\s*(/[^\s]*)', content, re.IGNORECASE)
            disallow_patterns = re.findall(r'Disallow:\s*(/[^\s]*)', content, re.IGNORECASE)
            
            # Generate URLs from patterns
            for pattern in allow_patterns + disallow_patterns:
                if pattern and pattern != '/' and 'admin' not in pattern.lower():
                    url = f"{tracker.base_url.rstrip('/')}{pattern}".replace('*', '')
                    discovered_urls.add(url)
        else:
            print(f"❌ robots.txt: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    execution_time = time.time() - start_time
    result = tracker.add_phase_urls("2_robots", list(discovered_urls), execution_time)
    
    print(f"⏱️ Time: {execution_time:.2f}s | URLs: {result['total_found']} | New: {result['new_unique']}")
    return result

def test_phase_3(tracker):
    """Phase 3: Ultra-Maximum URL Discovery using comprehensive seeding system"""
    print("\n🌐 PHASE 3: ULTRA-MAXIMUM URL DISCOVERY (COMPREHENSIVE SEEDING)")
    print("=" * 50)
    
    start_time = time.time()
    discovered_urls = set()
    
    try:
        # Import the comprehensive URL seeding system from the enhanced phase 3 file
        import sys
        import os
        
        # Add current directory to path for imports
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)
        
        # Import the comprehensive seeding system
        from importlib import import_module
        enhanced_phase3 = import_module('🌐_url_seeding_Phase_3')
        
        async def run_ultra_maximum_url_discovery():
            print(f"� Using ultra-comprehensive URL discovery system for maximum results...")
            
            # Extract domain from base URL
            domain = tracker.base_url.replace('https://', '').replace('http://', '').rstrip('/')
            
            # Configure the enhanced URL seeding system for maximum discovery
            config = enhanced_phase3.URLSeedingConfig(
                base_url=tracker.base_url,
                use_sitemap=True,
                use_common_crawl=True,
                use_enhanced_sitemaps=True,
                max_urls_per_domain=50000,  # Very high limit
                concurrency=50,  # High concurrency
                hits_per_sec=25,  # Fast processing
                extract_head=False,  # Skip for speed, focus on quantity
                live_check=False,  # Skip for speed
                verbose=True,
                force_refresh=True,  # Get fresh data
                smart_filtering=True,
                recursive_sitemap_discovery=True,
                cross_domain_analysis=False,  # Skip to focus on main domain
                use_llm_analysis=False,  # Skip LLM to focus on discovery speed
                query="municipal government services information pages"  # Broad query
            )
            
            # Use the comprehensive seeder
            async with enhanced_phase3.EnhancedURLSeeder(config) as seeder:
                print("🔄 Running comprehensive URL discovery with all methods...")
                
                # Discover URLs using all available methods
                results = await seeder.discover_urls([domain])
                
                # Extract all URLs from results
                all_discovered = set()
                if 'discovered_urls' in results:
                    for domain_name, urls in results['discovered_urls'].items():
                        if isinstance(urls, list):
                            for url in urls:
                                if isinstance(url, dict):
                                    if 'url' in url:
                                        all_discovered.add(url['url'])
                                elif isinstance(url, str):
                                    all_discovered.add(url)
                
                print(f"✅ Comprehensive discovery completed: {len(all_discovered)} URLs")
                return list(all_discovered)
        
        # Try to use the comprehensive system
        try:
            import asyncio
            urls = asyncio.run(run_ultra_maximum_url_discovery())
            discovered_urls.update(urls)
            print(f"🎯 Enhanced seeding system found: {len(urls)} URLs")
            
        except Exception as enhanced_error:
            print(f"⚠️ Enhanced system failed ({enhanced_error}), falling back to advanced AsyncUrlSeeder...")
            
            # Fallback to advanced AsyncUrlSeeder
            from crawl4ai import AsyncUrlSeeder, SeedingConfig
            
            async def run_fallback_advanced_seeding():
                domain = tracker.base_url.replace('https://', '').replace('http://', '').rstrip('/')
                
                async with AsyncUrlSeeder() as seeder:
                    all_configs = [
                        # Maximum coverage configuration
                        SeedingConfig(
                            source="sitemap+cc",
                            pattern="*",
                            extract_head=False,
                            max_urls=-1,  # Unlimited
                            concurrency=50,
                            hits_per_sec=25,
                            verbose=True,
                            force=True,
                            filter_nonsense_urls=False  # Include everything
                        ),
                        # CC-only with high limits
                        SeedingConfig(
                            source="cc",
                            pattern="*",
                            max_urls=100000,  # Very high limit
                            concurrency=50,
                            hits_per_sec=30,
                            verbose=True,
                            force=True,
                            filter_nonsense_urls=False
                        ),
                        # Sitemap-only with metadata
                        SeedingConfig(
                            source="sitemap",
                            pattern="*",
                            extract_head=True,
                            max_urls=-1,
                            concurrency=30,
                            verbose=True,
                            force=True,
                            filter_nonsense_urls=False
                        ),
                        # Pattern-based discoveries
                        SeedingConfig(
                            source="sitemap+cc",
                            pattern="*.html",
                            max_urls=25000,
                            concurrency=40,
                            verbose=False,
                            filter_nonsense_urls=False
                        ),
                        SeedingConfig(
                            source="sitemap+cc",
                            pattern="*.htm",
                            max_urls=25000,
                            concurrency=40,
                            verbose=False,
                            filter_nonsense_urls=False
                        ),
                        SeedingConfig(
                            source="sitemap+cc",
                            pattern="*.php",
                            max_urls=25000,
                            concurrency=40,
                            verbose=False,
                            filter_nonsense_urls=False
                        )
                    ]
                    
                    fallback_urls = set()
                    
                    for i, config in enumerate(all_configs, 1):
                        try:
                            print(f"🔄 Fallback method {i}/6...")
                            urls = await seeder.urls(domain, config)
                            step_urls = [url["url"] if isinstance(url, dict) else url for url in urls]
                            before_count = len(fallback_urls)
                            fallback_urls.update(step_urls)
                            new_count = len(fallback_urls) - before_count
                            print(f"  ✅ Method {i}: {len(step_urls)} URLs ({new_count} new)")
                        except Exception as e:
                            print(f"  ⚠️ Method {i} failed: {e}")
                    
                    print(f"🎯 Fallback methods total: {len(fallback_urls)} URLs")
                    return list(fallback_urls)
            
            urls = asyncio.run(run_fallback_advanced_seeding())
            discovered_urls.update(urls)
        
    except ImportError as import_error:
        print(f"❌ Crawl4AI not available ({import_error}), using basic fallback")
        # Basic fallback
        fallback_paths = ['/sitemap.xml', '/sitemap.html', '/robots.txt']
        for path in fallback_paths:
            url = f"{tracker.base_url.rstrip('/')}{path}"
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    discovered_urls.add(url)
            except:
                pass
                
    except Exception as e:
        print(f"❌ Error in ultra-maximum URL discovery: {e}")
        import traceback
        traceback.print_exc()
    
    execution_time = time.time() - start_time
    result = tracker.add_phase_urls("3_url_seeding", list(discovered_urls), execution_time)
    
    print(f"⏱️ Time: {execution_time:.2f}s | URLs: {result['total_found']} | New: {result['new_unique']}")
    return result

def run_all_phases(base_url):
    """Run all phases with set-based tracking"""
    print("� TESTING ALL PHASES WITH SET-BASED DEDUPLICATION")
    print("=" * 80)
    print(f"📋 Target: {base_url}")
    print(f"💾 Results stored in: all_urls.json")
    
    # Initialize tracker
    tracker = PhaseURLTracker(base_url)
    
    # Run phases
    phase_results = {}
    
    # Phase 1
    phase_results['phase_1'] = test_phase_1(tracker)
    
    # Phase 2
    phase_results['phase_2'] = test_phase_2(tracker)
    
def test_phase_4(tracker):
    """Phase 4: Ultra-Fast Recursive Link Crawling (Comprehensive Discovery)"""
    print("\n🔄 PHASE 4: ULTRA-FAST RECURSIVE LINK CRAWLING")
    print("=" * 50)
    
    start_time = time.time()
    discovered_urls = set()
    
    try:
        # Import Crawl4AI components
        import asyncio
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        from collections import deque
        
        async def run_ultra_fast_recursive_crawling():
            print(f"� Starting ultra-fast recursive link crawling with queue-based processing...")
            
            # Configuration for ultra-fast recursive crawling
            base_url = tracker.base_url
            domain = urlparse(base_url).netloc
            
            # Initialize queue-based system (inspired by comprehensive crawler)
            url_queue = deque([base_url])
            if tracker.all_urls:
                # Add existing discovered URLs as additional seeds
                seed_urls = list(tracker.all_urls)[:100]  # Use first 100 as seeds
                url_queue.extend(seed_urls)
                print(f"🌱 Added {len(seed_urls)} existing URLs as additional seeds")
            
            crawled_urls = set()
            all_discovered = set(url_queue)
            max_pages = 3000  # Increased limit for comprehensive discovery
            batch_size = 100  # Large batches for ultra-fast processing
            total_processed = 0
            
            # Ultra-fast browser configuration (optimized for speed)
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
                java_script_enabled=True,
                ignore_https_errors=True,
                extra_args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-images",  # Speed optimization
                    "--disable-css",     # Speed optimization
                    "--disable-plugins",
                    "--disable-extensions"
                ]
            )
            
            # Popup bypass JavaScript (enhanced)
            popup_bypass_js = """
            // Ultra-fast popup removal
            document.querySelectorAll('[class*="overlay"], [class*="modal"], [class*="popup"], [id*="popup"]').forEach(el => el.remove());
            document.querySelectorAll('*').forEach(el => {
                const style = window.getComputedStyle(el);
                if (style.zIndex && parseInt(style.zIndex) > 999) el.remove();
            });
            document.body.style.overflow = 'auto';
            document.documentElement.style.overflow = 'auto';
            """
            
            print(f"🔧 Queue initialized with {len(url_queue)} URLs")
            
            try:
                async with AsyncWebCrawler(config=browser_config) as crawler:
                    
                    # Ultra-fast crawler configuration
                    crawler_config = CrawlerRunConfig(
                        page_timeout=10000,  # Faster timeout
                        verbose=False,
                        js_code=popup_bypass_js,
                        wait_for_images=False,
                        delay_before_return_html=500,  # Reduced delay
                        remove_overlay_elements=True,
                        simulate_user=False  # Disable for speed
                    )
                    
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
                        new_urls_found = await process_batch_ultra_fast(crawler, crawler_config, current_batch, domain)
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
                print(f"❌ Ultra-fast crawler failed: {str(e)[:80]}")
                return []
            
            return list(all_discovered)
        
        async def process_batch_ultra_fast(crawler, config, urls, domain):
            """Process a batch of URLs ultra-fast and extract all links"""
            all_new_links = set()
            
            # Process URLs with controlled concurrency
            semaphore = asyncio.Semaphore(50)  # High concurrency
            
            async def process_single_url_ultra_fast(url):
                async with semaphore:
                    try:
                        result = await crawler.arun(url, config=config)
                        if result.success:
                            links = await extract_links_ultra_fast(result, url, domain)
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
        
        async def extract_links_ultra_fast(result, base_url, domain):
            """Ultra-fast link extraction using multiple methods"""
            links = set()
            
            try:
                # Method 1: Extract from Crawl4AI links metadata
                if hasattr(result, 'links') and result.links:
                    for link_dict in result.links:
                        if isinstance(link_dict, dict) and 'url' in link_dict:
                            url = link_dict['url']
                            if domain in url:
                                links.add(url)
                
                # Method 2: Extract from HTML using regex (fastest)
                if hasattr(result, 'html') and result.html:
                    import re
                    # Ultra-fast regex for href links
                    href_pattern = r'href=["\']([^"\']+)["\']'
                    matches = re.findall(href_pattern, result.html, re.IGNORECASE)
                    
                    for href in matches:
                        if href and not href.startswith('#'):
                            full_url = urljoin(base_url, href)
                            if domain in full_url and should_include_url_ultra_fast(full_url, domain):
                                links.add(full_url)
                
                # Method 3: Extract from cleaned HTML if available
                if hasattr(result, 'cleaned_html') and result.cleaned_html:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(result.cleaned_html, 'html.parser')
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if href and not href.startswith('#'):
                            full_url = urljoin(base_url, href)
                            if domain in full_url and should_include_url_ultra_fast(full_url, domain):
                                links.add(full_url)
            
            except Exception as e:
                print(f"        ⚠️ Link extraction error: {str(e)[:50]}")
            
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
                if any(ext in path for ext in ['.css', '.js', '.zip', '.exe', '.png', '.jpg', '.gif']):
                    return False
                
                # Skip malformed URLs
                if '#tmp_header' in url or '/tmp/' in path:
                    return False
                
                return True
                
            except Exception:
                return False
        
        # Run the ultra-fast async function
        import asyncio
        urls = asyncio.run(run_ultra_fast_recursive_crawling())
        discovered_urls.update(urls)
        
    except ImportError:
        print("❌ Crawl4AI not available, using fallback method")
        # Simple fallback using requests
        fallback_urls = set()
        try:
            # Use some existing URLs to extract more links
            import requests
            from bs4 import BeautifulSoup
            
            seed_urls = list(tracker.all_urls)[:10]  # Use first 10 as seeds
            
            for seed_url in seed_urls:
                try:
                    response = requests.get(seed_url, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        for link in soup.find_all('a', href=True):
                            full_url = urljoin(seed_url, link['href'])
                            if tracker.base_url.replace('https://', '').replace('http://', '') in full_url:
                                fallback_urls.add(full_url)
                except:
                    continue
            
            discovered_urls.update(fallback_urls)
            print(f"✅ Fallback method discovered {len(fallback_urls)} URLs")
            
        except Exception as e:
            print(f"❌ Fallback method failed: {e}")
                
    except Exception as e:
        print(f"❌ Error in recursive crawling: {e}")
    
    execution_time = time.time() - start_time
    result = tracker.add_phase_urls("4_recursive_crawling", list(discovered_urls), execution_time)
    
    print(f"⏱️ Time: {execution_time:.2f}s | URLs: {result['total_found']} | New: {result['new_unique']}")
    return result
    """Run all phases sequentially"""
    print("📋 TESTING ALL PHASES WITH SET-BASED DEDUPLICATION")
    print("=" * 80)
    print(f"📋 Target: {base_url}")
    print("💾 Results stored in: all_urls.json")
    
    # Initialize tracker
    tracker = PhaseURLTracker(base_url)
    
    # Phase results storage
    phase_results = {}
    
    # Phase 1
    phase_results['phase_1'] = test_phase_1(tracker)
    
    # Phase 2
    phase_results['phase_2'] = test_phase_2(tracker)
    
    # Phase 3
    phase_results['phase_3'] = test_phase_3(tracker)
    
    # Phase 4
    phase_results['phase_4'] = test_phase_4(tracker)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"🔢 Total Unique URLs in Set: {len(tracker.all_urls)}")
    
    for phase, result in phase_results.items():
        print(f"{phase:15} | {result['total_found']:3d} found | {result['new_unique']:3d} new | {result['execution_time']:.2f}s")
    
    print(f"\n✅ All results stored in: all_urls.json")
    print(f"🎯 Master URL set contains: {len(tracker.all_urls)} unique URLs")
    
    return phase_results

if __name__ == "__main__":
    test_url = "https://www.city.chiyoda.lg.jp/"
    results = run_all_phases(test_url)
