#!/usr/bin/env python3
"""
Phase 4: Hierarchical Parent Crawling - Discover parent directories
Systematically crawl parent pages to discover child pages that might not be in sitemaps
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
    print("✅ Crawl4AI imported successfully with advanced features")
except ImportError:
    print("❌ Crawl4AI not installed. Install with: pip install crawl4ai")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('phase4_hierarchical_parent_crawling.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class HierarchicalCrawlConfig:
    """Configuration for hierarchical parent crawling"""
    base_url: str
    max_parent_levels: int = 8
    max_pages: int = 5000
    max_concurrent: int = 50
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

class HierarchicalParentCrawler:
    """Phase 4: Hierarchical Parent Crawling - Discover parent directories"""
    
    def __init__(self, config: HierarchicalCrawlConfig):
        self.config = config
        self.discovered_urls: Set[str] = set()
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.parent_paths: Set[str] = set()
        self.domain = urlparse(config.base_url).netloc
        
        # Discovery statistics
        self.discovery_stats = {
            "hierarchical_crawl_urls": 0,
            "parent_pages_discovered": 0,
            "child_pages_discovered": 0,
            "crawled_pages": 0,
            "failed_pages": 0
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
        """
    
    async def run_hierarchical_crawling(self, seed_urls: Set[str] = None) -> Dict[str, Any]:
        """Main hierarchical parent crawling method"""
        print("\n🌳 PHASE 4: HIERARCHICAL PARENT CRAWLING")
        print("-" * 50)
        
        start_time = time.time()
        
        # Initialize with seed URLs or base URL
        if seed_urls:
            self.discovered_urls.update(seed_urls)
            print(f"📂 Starting with {len(seed_urls)} seed URLs")
        else:
            self.discovered_urls.add(self.config.base_url)
            print(f"📂 Starting with base URL: {self.config.base_url}")
        
        # Step 1: Generate parent paths from discovered URLs
        await self._generate_parent_paths()
        
        # Step 2: Progressive enhancement crawling of parent paths
        await self._hierarchical_crawl_progressive()
        
        end_time = time.time()
        self.discovery_stats["hierarchical_crawl_urls"] = len(self.discovered_urls)
        
        print(f"\n✅ Hierarchical Parent Crawling Complete!")
        print(f"📊 URLs discovered: {len(self.discovered_urls)}")
        print(f"📊 Parent paths found: {len(self.parent_paths)}")
        print(f"📊 Pages crawled: {self.discovery_stats['crawled_pages']}")
        print(f"⏱️  Total time: {end_time - start_time:.1f}s")
        
        return self._generate_results()
    
    async def _generate_parent_paths(self):
        """Generate all unique parent paths from discovered URLs"""
        print("  📁 Generating parent paths from discovered URLs...")
        
        # Extract parent paths from all discovered URLs
        for url in list(self.discovered_urls):
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            # Generate all parent paths
            for i in range(len(path_parts)):
                parent_path = '/' + '/'.join(path_parts[:i+1]) + '/'
                if parent_path not in ['/', '//']:
                    parent_url = urljoin(self.config.base_url, parent_path)
                    if self._should_include_url(parent_url):
                        self.parent_paths.add(parent_url)
        
        # Generate smart parent directories using LLM + fallbacks
        common_parents = await self._generate_smart_parent_directories()
        
        # Add basic fallback patterns
        basic_parents = [
            '/admin/', '/administration/', '/management/',
            '/info/', '/about/', '/contact/', '/services/',
            '/news/', '/support/', '/documents/', '/resources/',
            '/content/', '/search/', '/sitemap/', '/api/'
        ]
        common_parents.extend(basic_parents)
        
        for parent in common_parents:
            parent_url = urljoin(self.config.base_url, parent)
            if self._should_include_url(parent_url):
                self.parent_paths.add(parent_url)
        
        print(f"    📊 Generated {len(self.parent_paths)} unique parent paths")
        self.discovery_stats["parent_pages_discovered"] = len(self.parent_paths)
    
    async def _generate_smart_parent_directories(self) -> List[str]:
        """Generate smart parent directories using cost-effective LLM"""
        try:
            # Import LLM integration
            from llm_integration import generate_phase_patterns
            
            domain = self.domain
            sample_urls = list(self.discovered_urls)[:5] if self.discovered_urls else []
            
            # Get LLM suggestions with budget controls
            llm_patterns = await generate_phase_patterns(
                domain=domain,
                discovered_urls=sample_urls,
                phase="directory_discovery"
            )
            
            print(f"    🤖 LLM suggested {len(llm_patterns)} parent directories")
            return llm_patterns
            
        except Exception as e:
            print(f"    ⚠️  LLM parent generation failed: {e}")
            # Fallback to generic patterns
            return [
                '/admin/', '/api/', '/docs/', '/resources/', '/services/',
                '/support/', '/content/', '/media/', '/downloads/', '/archive/'
            ]
    
    async def _hierarchical_crawl_progressive(self):
        """Progressive enhancement hierarchical crawling"""
        
        # 🧱 BRICK 1: Basic Crawl4AI
        print("\n  🧱 BRICK 1: Basic Crawl4AI Parent Crawling")
        if await self._try_basic_parent_crawling():
            print("    🎉 SUCCESS with Basic Crawl4AI!")
            return
        
        # 🧱 BRICK 2: Crawl4AI + Stealth Mode  
        print("\n  🧱 BRICK 2: Crawl4AI + Stealth Mode Parent Crawling")
        if await self._try_stealth_parent_crawling():
            print("    🎉 SUCCESS with Stealth Mode!")
            return
        
        # 🧱 BRICK 3: Crawl4AI + Stealth + Undetected Browser
        print("\n  🧱 BRICK 3: Crawl4AI + Stealth + Undetected Browser Parent Crawling")
        if await self._try_undetected_parent_crawling():
            print("    🎉 SUCCESS with Undetected Browser!")
            return
        
        # 🧱 BRICK 4: HTTP Fallback (final resort)
        print("\n  🧱 BRICK 4: HTTP Fallback (Final Resort)")
        await self._try_http_parent_fallback()
        
        print("\n  ✅ Progressive hierarchical parent crawling complete")
    
    async def _try_basic_parent_crawling(self) -> bool:
        """Try basic parent crawling with Crawl4AI"""
        try:
            async with AsyncWebCrawler(config=self.browser_configs['basic']) as crawler:
                return await self._parent_crawl_with_config(crawler, "BASIC")
        except Exception as e:
            print(f"      ❌ Basic parent crawling failed: {str(e)[:100]}")
            logger.error(f"Basic parent crawling failed: {e}")
            return False
    
    async def _try_stealth_parent_crawling(self) -> bool:
        """Try stealth parent crawling"""
        if 'stealth' not in self.browser_configs:
            return False
        
        try:
            async with AsyncWebCrawler(config=self.browser_configs['stealth']) as crawler:
                return await self._parent_crawl_with_config(crawler, "STEALTH")
        except Exception as e:
            print(f"      ❌ Stealth parent crawling failed: {str(e)[:100]}")
            logger.error(f"Stealth parent crawling failed: {e}")
            return False
    
    async def _try_undetected_parent_crawling(self) -> bool:
        """Try undetected parent crawling"""
        try:
            browser_config = self.browser_configs['undetected']
            crawler_strategy = AsyncPlaywrightCrawlerStrategy(
                adapter=UndetectedAdapter(),
                browser_config=browser_config
            )
            
            async with AsyncWebCrawler(crawler_strategy=crawler_strategy) as crawler:
                return await self._parent_crawl_with_config(crawler, "UNDETECTED")
        except Exception as e:
            print(f"      ❌ Undetected parent crawling failed: {str(e)[:100]}")
            logger.error(f"Undetected parent crawling failed: {e}")
            return False
    
    async def _parent_crawl_with_config(self, crawler, mode: str) -> bool:
        """Parent crawling with specific configuration"""
        print(f"      🚀 Starting {mode} parent crawling...")
        
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
            
            parent_urls = list(self.parent_paths)
            batch_size = min(self.config.max_concurrent, 30)  # Smaller batches for parent crawling
            total_new_links = 0
            
            # Process parent URLs in batches
            for i in range(0, len(parent_urls), batch_size):
                batch = parent_urls[i:i + batch_size]
                print(f"        📊 Processing parent batch {i//batch_size + 1}/{(len(parent_urls) + batch_size - 1)//batch_size} ({len(batch)} URLs)")
                
                # Process batch concurrently
                new_links = await self._process_parent_batch(crawler, batch, crawler_config)
                total_new_links += len(new_links)
                
                # Add new URLs to discovered set
                for new_url in new_links:
                    if (new_url not in self.discovered_urls and
                        self._should_include_url(new_url)):
                        self.discovered_urls.add(new_url)
                
                print(f"        ✅ Parent batch complete. New links: {len(new_links)}, Total discovered: {len(self.discovered_urls)}")
                
                # Add small delay between batches
                await asyncio.sleep(self.config.delay_between_requests)
            
            print(f"      ✅ {mode} parent crawling complete: {total_new_links} total links extracted")
            self.discovery_stats["child_pages_discovered"] += total_new_links
            return total_new_links > 0
            
        except Exception as e:
            print(f"      ❌ {mode} parent crawling failed: {str(e)[:100]}")
            logger.error(f"{mode} parent crawling failed: {e}")
            return False
    
    async def _process_parent_batch(self, crawler, urls: List[str], crawler_config) -> Set[str]:
        """Process a batch of parent URLs concurrently"""
        all_new_links = set()
        
        try:
            # Create tasks for concurrent processing
            tasks = []
            for url in urls:
                task = self._crawl_single_parent_url(crawler, url, crawler_config)
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
                        print(f"          ✅ {url}: {len(result)} child links extracted")
                    else:
                        print(f"          ⚠️  {url}: No child links found")
        
        except Exception as e:
            print(f"        ❌ Parent batch processing failed: {str(e)}")
            logger.error(f"Parent batch processing failed: {e}")
        
        return all_new_links
    
    async def _crawl_single_parent_url(self, crawler, url: str, crawler_config) -> Set[str]:
        """Crawl a single parent URL and extract child links"""
        try:
            result_container = await asyncio.wait_for(
                crawler.arun(url=url, config=crawler_config),
                timeout=self.config.timeout
            )
            
            if result_container and len(result_container._results) > 0:
                result = result_container._results[0]
                
                if result.success and result.html:
                    # Extract child links from parent page
                    extracted_links = await self._extract_child_links_from_parent(result, url)
                    return extracted_links
            
            return set()
            
        except asyncio.TimeoutError:
            logger.debug(f"Timeout crawling parent {url}")
            return set()
        except Exception as e:
            logger.debug(f"Error crawling parent {url}: {e}")
            return set()
    
    async def _extract_child_links_from_parent(self, result, parent_url: str) -> Set[str]:
        """Extract child links from a parent page"""
        child_links = set()
        
        try:
            # Method 1: Use Crawl4AI's built-in link extraction
            if hasattr(result, 'links') and result.links:
                if hasattr(result.links, 'internal'):
                    for link in result.links.internal:
                        if hasattr(link, 'href'):
                            full_url = urljoin(parent_url, link.href)
                            if self._should_include_url(full_url) and self._is_child_of_parent(full_url, parent_url):
                                child_links.add(full_url)
            
            # Method 2: Enhanced HTML parsing for directory listings
            if hasattr(result, 'html') and result.html:
                additional_links = await self._extract_directory_links(result.html, parent_url)
                child_links.update(additional_links)
        
        except Exception as e:
            logger.debug(f"Child link extraction failed for parent {parent_url}: {e}")
        
        return child_links
    
    async def _extract_directory_links(self, html_content: str, parent_url: str) -> Set[str]:
        """Extract directory listing links from HTML"""
        links = set()
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Method 1: Standard directory listing links
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(parent_url, href)
                if self._should_include_url(full_url) and self._is_child_of_parent(full_url, parent_url):
                    links.add(full_url)
            
            # Method 2: Look for table-based directory listings
            tables = soup.find_all('table')
            for table in tables:
                table_links = table.find_all('a', href=True)
                for link in table_links:
                    href = link['href']
                    full_url = urljoin(parent_url, href)
                    if self._should_include_url(full_url) and self._is_child_of_parent(full_url, parent_url):
                        links.add(full_url)
            
            # Method 3: Look for list-based directory structures
            lists = soup.find_all(['ul', 'ol'])
            for list_elem in lists:
                list_links = list_elem.find_all('a', href=True)
                for link in list_links:
                    href = link['href']
                    full_url = urljoin(parent_url, href)
                    if self._should_include_url(full_url) and self._is_child_of_parent(full_url, parent_url):
                        links.add(full_url)
        
        except Exception as e:
            logger.debug(f"Directory link extraction failed: {e}")
        
        return links
    
    def _is_child_of_parent(self, child_url: str, parent_url: str) -> bool:
        """Check if a URL is a child of a parent URL"""
        try:
            parent_parsed = urlparse(parent_url)
            child_parsed = urlparse(child_url)
            
            # Must be same domain
            if parent_parsed.netloc != child_parsed.netloc:
                return False
            
            parent_path = parent_parsed.path.rstrip('/')
            child_path = child_parsed.path.rstrip('/')
            
            # Child path should start with parent path and be longer
            return (child_path.startswith(parent_path) and 
                    len(child_path) > len(parent_path) and
                    child_path != parent_path)
        
        except Exception:
            return False
    
    async def _try_http_parent_fallback(self):
        """HTTP fallback for parent crawling"""
        print("      🌐 Trying HTTP fallback for parent crawling...")
        
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
                
                parent_urls = list(self.parent_paths)
                total_new_links = 0
                
                for url in parent_urls:
                    try:
                        kwargs = {}
                        if self.config.proxy_enabled:
                            kwargs['proxy'] = self.config.brightdata_proxy
                        
                        async with session.get(url, **kwargs) as response:
                            if response.status == 200:
                                html = await response.text()
                                links = await self._extract_directory_links_basic(html, url)
                                
                                # Add new child URLs
                                for link in links:
                                    if (link not in self.discovered_urls and
                                        self._should_include_url(link) and
                                        self._is_child_of_parent(link, url)):
                                        
                                        self.discovered_urls.add(link)
                                
                                total_new_links += len(links)
                                self.crawled_urls.add(url)
                                self.discovery_stats["crawled_pages"] += 1
                                
                                print(f"        ✅ {url}: {len(links)} child links extracted")
                            else:
                                print(f"        ❌ {url}: Status {response.status}")
                                self.failed_urls.add(url)
                                self.discovery_stats["failed_pages"] += 1
                    
                    except Exception as e:
                        print(f"        ❌ {url}: {str(e)[:50]}")
                        self.failed_urls.add(url)
                        self.discovery_stats["failed_pages"] += 1
                    
                    await asyncio.sleep(self.config.delay_between_requests)
                
                print(f"      ✅ HTTP parent fallback complete: {total_new_links} child links extracted")
                self.discovery_stats["child_pages_discovered"] += total_new_links
        
        except Exception as e:
            print(f"      ❌ HTTP parent fallback failed: {str(e)}")
            logger.error(f"HTTP parent fallback failed: {e}")
    
    async def _extract_directory_links_basic(self, html_content: str, parent_url: str) -> Set[str]:
        """Basic directory link extraction for HTTP fallback"""
        links = set()
        
        try:
            # Simple regex-based extraction
            href_pattern = r'href=["\']([^"\']+)["\']'
            matches = re.findall(href_pattern, html_content)
            
            for href in matches:
                full_url = urljoin(parent_url, href)
                if (self._should_include_url(full_url) and 
                    self._is_child_of_parent(full_url, parent_url)):
                    links.add(full_url)
        
        except Exception as e:
            logger.debug(f"Basic directory link extraction failed: {e}")
        
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
            "phase": "hierarchical_parent_crawling",
            "total_discovered_urls": len(self.discovered_urls),
            "parent_pages_discovered": self.discovery_stats["parent_pages_discovered"],
            "child_pages_discovered": self.discovery_stats["child_pages_discovered"],
            "crawled_pages": self.discovery_stats["crawled_pages"],
            "failed_pages": self.discovery_stats["failed_pages"],
            "discovered_urls": sorted(list(self.discovered_urls)),
            "parent_paths": sorted(list(self.parent_paths)),
            "discovery_stats": self.discovery_stats,
            "config": {
                "base_url": self.config.base_url,
                "max_parent_levels": self.config.max_parent_levels,
                "max_pages": self.config.max_pages,
                "max_concurrent": self.config.max_concurrent,
                "proxy_enabled": self.config.proxy_enabled,
                "stealth_mode": self.config.stealth_mode
            }
        }
    
    def save_results(self, filename: str = None) -> str:
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"phase4_hierarchical_parent_crawling_results_{timestamp}.json"
        
        results = self._generate_results()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")
        return filename

# Example usage
async def main():
    """Example usage of Phase 4: Hierarchical Parent Crawling"""
    
    # Configuration
    config = HierarchicalCrawlConfig(
        base_url="https://www.city.chiyoda.lg.jp",
        max_parent_levels=8,
        max_pages=3000,
        max_concurrent=30,
        proxy_enabled=True,
        stealth_mode=True
    )
    
    # Create crawler
    crawler = HierarchicalParentCrawler(config)
    
    # Run hierarchical parent crawling
    results = await crawler.run_hierarchical_crawling()
    
    # Save results
    filename = crawler.save_results()
    
    print(f"\n📊 Phase 4 Complete!")
    print(f"📂 URLs discovered: {results['total_discovered_urls']}")
    print(f"📁 Parent paths: {results['parent_pages_discovered']}")
    print(f"👶 Child pages: {results['child_pages_discovered']}")
    print(f"📁 Results saved: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
