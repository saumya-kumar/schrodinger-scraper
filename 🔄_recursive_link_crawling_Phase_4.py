#!/usr/bin/env python3
"""
Phase 3: Recursive Link Crawling - Main discovery engine
Comprehensive recursive crawling using Crawl4AI with enhanced link extraction
"""

import asyncio
import json
import os
import sys
import time
import logging
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Set, List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import deque
import aiohttp
import psutil
from bs4 import BeautifulSoup

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")

# Crawl4AI imports
try:
    from crawl4ai import (
        AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, UndetectedAdapter,
        ProxyConfig, RoundRobinProxyStrategy, CacheMode, PlaywrightAdapter,
        BrowserProfiler, GeolocationConfig
    )
    from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    from crawl4ai import AsyncUrlSeeder, SeedingConfig
    print("✅ Crawl4AI imported successfully with advanced features")
except ImportError:
    print("❌ Crawl4AI not installed. Install with: pip install crawl4ai")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('phase3_recursive_crawling.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class RecursiveCrawlConfig:
    """Configuration for recursive crawling"""
    base_url: str
    max_pages: int = 10000
    max_depth: int = 5
    max_concurrent: int = 100
    delay_between_requests: float = 0.1
    timeout: int = 15
    include_pdfs: bool = False  # PDFs excluded per requirement
    include_images: bool = False
    
    # PROXY CONFIGURATION
    proxy_enabled: bool = True
    brightdata_proxy: str = 'http://brd-customer-hl_c4d84340-zone-testingdc:l1yptwrxrmbr@brd.superproxy.io:33335'
    
    # STEALTH CONFIGURATION
    stealth_mode: bool = True
    rotate_user_agents: bool = True

class RecursiveLinkCrawler:
    """Phase 3: Recursive Link Crawling - Main discovery engine"""
    
    def __init__(self, config: RecursiveCrawlConfig):
        self.config = config
        self.discovered_urls: Set[str] = set()
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.url_metadata: Dict[str, Dict] = {}
        self.domain = urlparse(config.base_url).netloc
        
        # Discovery statistics
        self.discovery_stats = {
            "recursive_crawl_urls": 0,
            "crawled_pages": 0,
            "failed_pages": 0,
            "total_links_extracted": 0
        }
        
        # Browser configurations for different enhancement levels
        self.browser_configs = self._create_browser_configs()
        
    def _create_browser_configs(self) -> Dict[str, BrowserConfig]:
        """Create browser configurations for different enhancement levels"""
        configs = {}
        
        # Basic config
        configs['basic'] = BrowserConfig(
            headless=True,
            verbose=False,
            java_script_enabled=True,
            ignore_https_errors=True,
            viewport_width=1920,
            viewport_height=1080
        )
        
        # Stealth config
        if self.config.stealth_mode:
            proxy_param = self.config.brightdata_proxy if self.config.proxy_enabled else None
            configs['stealth'] = BrowserConfig(
                headless=False,
                verbose=False,
                java_script_enabled=True,
                ignore_https_errors=True,
                viewport_width=1920,
                viewport_height=1080,
                proxy=proxy_param,
                enable_stealth=True,
                browser_mode="dedicated",
                extra_args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-extensions",
                    "--no-first-run",
                    "--disable-default-apps"
                ]
            )
        
        # Undetected config
        proxy_param = self.config.brightdata_proxy if self.config.proxy_enabled else None
        configs['undetected'] = BrowserConfig(
            headless=False,
            verbose=False,
            java_script_enabled=True,
            ignore_https_errors=True,
            viewport_width=1920,
            viewport_height=1080,
            proxy=proxy_param,
            enable_stealth=True,
            browser_mode="dedicated",
            extra_args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-extensions",
                "--no-first-run"
            ]
        )
        
        return configs
    
    def _get_popup_bypass_js(self) -> str:
        """JavaScript code to bypass popups, overlays, and modals"""
        return """
        // Remove all overlay elements
        const overlays = document.querySelectorAll('[class*="overlay"], [class*="modal"], [class*="popup"], [id*="overlay"], [id*="modal"], [id*="popup"]');
        overlays.forEach(el => el.remove());
        
        // Remove elements with high z-index (likely overlays)
        const allElements = document.querySelectorAll('*');
        allElements.forEach(el => {
            const zIndex = window.getComputedStyle(el).zIndex;
            if (zIndex && parseInt(zIndex) > 999) {
                el.remove();
            }
        });
        
        // Enable scrolling
        document.body.style.overflow = 'auto';
        document.documentElement.style.overflow = 'auto';
        
        // Remove fixed/sticky positioned elements that might be overlays
        allElements.forEach(el => {
            const position = window.getComputedStyle(el).position;
            if (position === 'fixed' || position === 'sticky') {
                const rect = el.getBoundingClientRect();
                // If element covers significant portion of screen, remove it
                if (rect.width > window.innerWidth * 0.5 && rect.height > window.innerHeight * 0.5) {
                    el.remove();
                }
            }
        });
        """
    
    async def run_recursive_crawling(self, seed_urls: Set[str] = None) -> Dict[str, Any]:
        """Main recursive crawling method"""
        print("\n🔄 PHASE 3: RECURSIVE LINK CRAWLING")
        print("-" * 50)
        
        start_time = time.time()
        
        # Initialize with seed URLs or base URL
        if seed_urls:
            self.discovered_urls.update(seed_urls)
            print(f"📂 Starting with {len(seed_urls)} seed URLs")
        else:
            self.discovered_urls.add(self.config.base_url)
            print(f"📂 Starting with base URL: {self.config.base_url}")
        
        # Progressive enhancement approach
        await self._recursive_crawl_progressive()
        
        end_time = time.time()
        self.discovery_stats["recursive_crawl_urls"] = len(self.discovered_urls)
        
        print(f"\n✅ Recursive Crawling Complete!")
        print(f"📊 URLs discovered: {len(self.discovered_urls)}")
        print(f"📊 Pages crawled: {self.discovery_stats['crawled_pages']}")
        print(f"📊 Pages failed: {self.discovery_stats['failed_pages']}")
        print(f"⏱️  Total time: {end_time - start_time:.1f}s")
        
        return self._generate_results()
    
    async def _recursive_crawl_progressive(self):
        """Progressive enhancement recursive crawling"""
        
        # 🧱 BRICK 1: Basic Crawl4AI
        print("\n  🧱 BRICK 1: Basic Crawl4AI")
        if await self._try_basic_recursive_crawling():
            print("    🎉 SUCCESS with Basic Crawl4AI!")
            return
        
        # 🧱 BRICK 2: Crawl4AI + Stealth Mode  
        print("\n  🧱 BRICK 2: Crawl4AI + Stealth Mode")
        if await self._try_stealth_recursive_crawling():
            print("    🎉 SUCCESS with Stealth Mode!")
            return
        
        # 🧱 BRICK 3: Crawl4AI + Stealth + Undetected Browser
        print("\n  🧱 BRICK 3: Crawl4AI + Stealth + Undetected Browser")
        if await self._try_undetected_recursive_crawling():
            print("    🎉 SUCCESS with Undetected Browser!")
            return
        
        # 🧱 BRICK 4: HTTP Fallback (final resort)
        print("\n  🧱 BRICK 4: HTTP Fallback (Final Resort)")
        await self._try_http_recursive_fallback()
        
        print("\n  ✅ Progressive recursive crawling complete")
    
    async def _try_basic_recursive_crawling(self) -> bool:
        """Try basic recursive crawling with Crawl4AI"""
        try:
            async with AsyncWebCrawler(config=self.browser_configs['basic']) as crawler:
                return await self._recursive_crawl_with_config(crawler, "BASIC")
        except Exception as e:
            print(f"      ❌ Basic crawling failed: {str(e)[:100]}")
            logger.error(f"Basic recursive crawling failed: {e}")
            return False
    
    async def _try_stealth_recursive_crawling(self) -> bool:
        """Try stealth recursive crawling"""
        if 'stealth' not in self.browser_configs:
            return False
        
        try:
            async with AsyncWebCrawler(config=self.browser_configs['stealth']) as crawler:
                return await self._recursive_crawl_with_config(crawler, "STEALTH")
        except Exception as e:
            print(f"      ❌ Stealth crawling failed: {str(e)[:100]}")
            logger.error(f"Stealth recursive crawling failed: {e}")
            return False
    
    async def _try_undetected_recursive_crawling(self) -> bool:
        """Try undetected recursive crawling"""
        try:
            browser_config = self.browser_configs['undetected']
            crawler_strategy = AsyncPlaywrightCrawlerStrategy(
                adapter=UndetectedAdapter(),
                browser_config=browser_config
            )
            
            async with AsyncWebCrawler(crawler_strategy=crawler_strategy) as crawler:
                return await self._recursive_crawl_with_config(crawler, "UNDETECTED")
        except Exception as e:
            print(f"      ❌ Undetected crawling failed: {str(e)[:100]}")
            logger.error(f"Undetected recursive crawling failed: {e}")
            return False
    
    async def _recursive_crawl_with_config(self, crawler, mode: str) -> bool:
        """Recursive crawling with specific configuration"""
        print(f"      🚀 Starting {mode} recursive crawling...")
        
        try:
            # Progressive crawler config
            crawler_config = CrawlerRunConfig(
                page_timeout=30000,
                verbose=False,
                js_code=self._get_popup_bypass_js(),
                wait_for_images=False,
                delay_before_return_html=2000,
                remove_overlay_elements=True,
                simulate_user=True,
                override_navigator=True,
                extract_links=True  # Enable link extraction
            )
            
            urls_to_crawl = deque(self.discovered_urls - self.crawled_urls)
            depth_tracker = {url: 0 for url in urls_to_crawl}
            
            batch_size = min(self.config.max_concurrent, 50)
            total_new_links = 0
            
            while urls_to_crawl and len(self.crawled_urls) < self.config.max_pages:
                # Process batch of URLs
                batch = []
                for _ in range(min(batch_size, len(urls_to_crawl))):
                    if not urls_to_crawl:
                        break
                    url = urls_to_crawl.popleft()
                    if depth_tracker.get(url, 0) <= self.config.max_depth:
                        batch.append(url)
                
                if not batch:
                    break
                
                print(f"        📊 Processing batch of {len(batch)} URLs (Queue: {len(urls_to_crawl)})")
                
                # Process batch concurrently
                new_links = await self._process_url_batch(crawler, batch, crawler_config, depth_tracker)
                total_new_links += len(new_links)
                
                # Add new URLs to queue
                for new_url in new_links:
                    if (new_url not in self.discovered_urls and 
                        new_url not in self.crawled_urls and
                        self._should_include_url(new_url)):
                        
                        self.discovered_urls.add(new_url)
                        parent_depth = min([depth_tracker.get(parent, 0) for parent in batch])
                        depth_tracker[new_url] = parent_depth + 1
                        
                        if depth_tracker[new_url] <= self.config.max_depth:
                            urls_to_crawl.append(new_url)
                
                print(f"        ✅ Batch complete. New links: {len(new_links)}, Total discovered: {len(self.discovered_urls)}")
                
                # Add small delay between batches
                await asyncio.sleep(self.config.delay_between_requests)
            
            print(f"      ✅ {mode} crawling complete: {total_new_links} total links extracted")
            self.discovery_stats["total_links_extracted"] += total_new_links
            return total_new_links > 0
            
        except Exception as e:
            print(f"      ❌ {mode} recursive crawling failed: {str(e)[:100]}")
            logger.error(f"{mode} recursive crawling failed: {e}")
            return False
    
    async def _process_url_batch(self, crawler, urls: List[str], crawler_config, depth_tracker) -> Set[str]:
        """Process a batch of URLs concurrently"""
        all_new_links = set()
        
        try:
            # Create tasks for concurrent processing
            tasks = []
            for url in urls:
                task = self._crawl_single_url(crawler, url, crawler_config)
                tasks.append(task)
            
            # Process all URLs concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                url = urls[i]
                
                if isinstance(result, Exception):
                    print(f"          ❌ {url}: {str(result)[:50]}")
                    self.failed_urls.add(url)
                    self.discovery_stats["failed_pages"] += 1
                else:
                    self.crawled_urls.add(url)
                    self.discovery_stats["crawled_pages"] += 1
                    
                    if result:  # Set of extracted links
                        all_new_links.update(result)
                        print(f"          ✅ {url}: {len(result)} links extracted")
                    else:
                        print(f"          ⚠️  {url}: No links extracted")
        
        except Exception as e:
            print(f"        ❌ Batch processing failed: {str(e)}")
            logger.error(f"Batch processing failed: {e}")
        
        return all_new_links
    
    async def _crawl_single_url(self, crawler, url: str, crawler_config) -> Set[str]:
        """Crawl a single URL and extract links"""
        try:
            result_container = await asyncio.wait_for(
                crawler.arun(url=url, config=crawler_config),
                timeout=self.config.timeout
            )
            
            if result_container and len(result_container._results) > 0:
                result = result_container._results[0]
                
                if result.success and result.html:
                    # Extract links using comprehensive method
                    extracted_links = await self._extract_links_comprehensive(result, url)
                    return extracted_links
            
            return set()
            
        except asyncio.TimeoutError:
            logger.debug(f"Timeout crawling {url}")
            return set()
        except Exception as e:
            logger.debug(f"Error crawling {url}: {e}")
            return set()
    
    async def _extract_links_comprehensive(self, result, base_url: str) -> Set[str]:
        """Comprehensive link extraction using multiple techniques"""
        links = set()
        
        try:
            # Method 1: Use Crawl4AI's built-in link extraction
            if hasattr(result, 'links') and result.links:
                if hasattr(result.links, 'internal'):
                    for link in result.links.internal:
                        if hasattr(link, 'href'):
                            full_url = urljoin(base_url, link.href)
                            if self._should_include_url(full_url):
                                links.add(full_url)
                
                # Also check external links that might be internal (redirects)
                if hasattr(result.links, 'external'):
                    for link in result.links.external:
                        if hasattr(link, 'href') and self.domain in link.href:
                            if self._should_include_url(link.href):
                                links.add(link.href)
            
            # Method 2: Enhanced HTML parsing
            if hasattr(result, 'html') and result.html:
                additional_links = await self._extract_links_from_html_advanced(result.html, base_url)
                links.update(additional_links)
            
            # Method 3: Extract from cleaned HTML if available
            if hasattr(result, 'cleaned_html') and result.cleaned_html:
                cleaned_links = await self._extract_links_from_html_advanced(result.cleaned_html, base_url)
                links.update(cleaned_links)
        
        except Exception as e:
            logger.debug(f"Comprehensive link extraction failed for {base_url}: {e}")
        
        return links
    
    async def _extract_links_from_html_advanced(self, html_content: str, base_url: str) -> Set[str]:
        """Advanced HTML link extraction"""
        links = set()
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Method 1: Standard href links
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)
                if self._should_include_url(full_url):
                    links.add(full_url)
            
            # Method 2: Navigation links
            nav_tags = soup.find_all(['nav', 'ul', 'div'], class_=re.compile(r'nav|menu|breadcrumb', re.I))
            for nav in nav_tags:
                nav_links = nav.find_all('a', href=True)
                for link in nav_links:
                    full_url = urljoin(base_url, link['href'])
                    if self._should_include_url(full_url):
                        links.add(full_url)
            
            # Method 3: Footer links
            footer = soup.find('footer') or soup.find('div', class_=re.compile(r'footer', re.I))
            if footer:
                footer_links = footer.find_all('a', href=True)
                for link in footer_links:
                    full_url = urljoin(base_url, link['href'])
                    if self._should_include_url(full_url):
                        links.add(full_url)
            
            # Method 4: Form actions
            for form in soup.find_all('form', action=True):
                action = form['action']
                if action and not action.startswith(('javascript:', 'mailto:')):
                    full_url = urljoin(base_url, action)
                    if self._should_include_url(full_url):
                        links.add(full_url)
            
            # Method 5: JavaScript-referenced URLs (basic extraction)
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Look for URL patterns in JavaScript
                    js_urls = re.findall(r'["\']([^"\']*\.html?)["\']', script.string)
                    for js_url in js_urls:
                        full_url = urljoin(base_url, js_url)
                        if self._should_include_url(full_url):
                            links.add(full_url)
        
        except Exception as e:
            logger.debug(f"Advanced HTML parsing failed: {e}")
        
        return links
    
    async def _try_http_recursive_fallback(self):
        """HTTP fallback for recursive crawling"""
        print("      🌐 Trying HTTP fallback for recursive crawling...")
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; Crawler)'}
            
            # Configure proxy if enabled
            connector = None
            if self.config.proxy_enabled:
                connector = aiohttp.TCPConnector()
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=connector
            ) as session:
                
                urls_to_crawl = deque(self.discovered_urls - self.crawled_urls)
                total_new_links = 0
                
                while urls_to_crawl and len(self.crawled_urls) < self.config.max_pages:
                    url = urls_to_crawl.popleft()
                    
                    try:
                        kwargs = {}
                        if self.config.proxy_enabled:
                            kwargs['proxy'] = self.config.brightdata_proxy
                        
                        async with session.get(url, **kwargs) as response:
                            if response.status == 200:
                                html = await response.text()
                                links = await self._extract_links_from_html_basic(html, url)
                                
                                # Add new URLs
                                for link in links:
                                    if (link not in self.discovered_urls and
                                        link not in self.crawled_urls and
                                        self._should_include_url(link)):
                                        
                                        self.discovered_urls.add(link)
                                        urls_to_crawl.append(link)
                                
                                total_new_links += len(links)
                                self.crawled_urls.add(url)
                                self.discovery_stats["crawled_pages"] += 1
                                
                                print(f"        ✅ {url}: {len(links)} links extracted")
                            else:
                                print(f"        ❌ {url}: Status {response.status}")
                                self.failed_urls.add(url)
                                self.discovery_stats["failed_pages"] += 1
                    
                    except Exception as e:
                        print(f"        ❌ {url}: {str(e)[:50]}")
                        self.failed_urls.add(url)
                        self.discovery_stats["failed_pages"] += 1
                    
                    await asyncio.sleep(self.config.delay_between_requests)
                
                print(f"      ✅ HTTP fallback complete: {total_new_links} links extracted")
        
        except Exception as e:
            print(f"      ❌ HTTP fallback failed: {str(e)}")
            logger.error(f"HTTP recursive fallback failed: {e}")
    
    async def _extract_links_from_html_basic(self, html_content: str, base_url: str) -> Set[str]:
        """Basic HTML link extraction for HTTP fallback"""
        links = set()
        
        try:
            # Simple regex-based extraction
            href_pattern = r'href=["\']([^"\']+)["\']'
            matches = re.findall(href_pattern, html_content)
            
            for href in matches:
                full_url = urljoin(base_url, href)
                if self._should_include_url(full_url):
                    links.add(full_url)
        
        except Exception as e:
            logger.debug(f"Basic HTML parsing failed: {e}")
        
        return links
    
    def _should_include_url(self, url: str) -> bool:
        """Determine if URL should be included in discovery"""
        try:
            parsed = urlparse(url)
            
            # Must be same domain
            if parsed.netloc != self.domain:
                return False
            
            path = parsed.path.lower()
            
            # Skip certain file types
            if not self.config.include_images and any(path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico']):
                return False
            
            if not self.config.include_pdfs and path.endswith('.pdf'):
                return False
            
            # Skip obvious non-content URLs
            skip_patterns = [
                '/css/', '/js/', '/images/', '/img/', '/assets/', '/static/',
                '.css', '.js', '.zip', '.exe', '#', 'javascript:', 'mailto:'
            ]
            
            if any(pattern in url.lower() for pattern in skip_patterns):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _generate_results(self) -> Dict[str, Any]:
        """Generate comprehensive results"""
        return {
            "phase": "recursive_link_crawling",
            "total_discovered_urls": len(self.discovered_urls),
            "crawled_pages": self.discovery_stats["crawled_pages"],
            "failed_pages": self.discovery_stats["failed_pages"],
            "total_links_extracted": self.discovery_stats["total_links_extracted"],
            "discovered_urls": sorted(list(self.discovered_urls)),
            "discovery_stats": self.discovery_stats,
            "config": {
                "base_url": self.config.base_url,
                "max_pages": self.config.max_pages,
                "max_depth": self.config.max_depth,
                "max_concurrent": self.config.max_concurrent,
                "proxy_enabled": self.config.proxy_enabled,
                "stealth_mode": self.config.stealth_mode
            }
        }
    
    def save_results(self, filename: str = None) -> str:
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"phase3_recursive_crawling_results_{timestamp}.json"
        
        results = self._generate_results()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")
        return filename

# Example usage
async def main():
    """Example usage of Phase 3: Recursive Link Crawling"""
    
    # Configuration
    config = RecursiveCrawlConfig(
        base_url="https://www.city.chiyoda.lg.jp",
        max_pages=5000,
        max_depth=5,
        max_concurrent=50,
        proxy_enabled=True,
        stealth_mode=True
    )
    
    # Create crawler
    crawler = RecursiveLinkCrawler(config)
    
    # Run recursive crawling
    results = await crawler.run_recursive_crawling()
    
    # Save results
    filename = crawler.save_results()
    
    print(f"\n📊 Phase 3 Complete!")
    print(f"📂 URLs discovered: {results['total_discovered_urls']}")
    print(f"📄 Pages crawled: {results['crawled_pages']}")
    print(f"📁 Results saved: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
