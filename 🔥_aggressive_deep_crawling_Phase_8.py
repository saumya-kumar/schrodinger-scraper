#!/usr/bin/env python3
"""
Phase 7: Aggressive Deep Crawling - Process ALL remaining URLs
Comprehensive crawling of all discovered URLs with maximum link extraction
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
        logging.FileHandler('phase7_aggressive_deep_crawling.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class AggressiveCrawlConfig:
    """Configuration for aggressive deep crawling"""
    base_url: str
    max_pages: int = 20000
    max_concurrent: int = 100
    delay_between_requests: float = 0.05  # Faster crawling
    timeout: int = 20
    include_pdfs: bool = False  # PDFs excluded per requirement
    include_images: bool = False
    
    # Aggressive crawling settings
    max_retries: int = 3
    retry_delay: float = 1.0
    extract_all_links: bool = True
    follow_redirects: bool = True
    
    # PROXY CONFIGURATION
    proxy_enabled: bool = True
    brightdata_proxy: str = 'http://brd-customer-hl_c4d84340-zone-testingdc:l1yptwrxrmbr@brd.superproxy.io:33335'
    
    # STEALTH CONFIGURATION
    stealth_mode: bool = True
    rotate_user_agents: bool = True

class AggressiveDeepCrawler:
    """Phase 7: Aggressive Deep Crawling - Process ALL remaining URLs"""
    
    def __init__(self, config: AggressiveCrawlConfig):
        self.config = config
        self.discovered_urls: Set[str] = set()
        self.input_urls: Set[str] = set()  # URLs to crawl aggressively
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.retry_queue: Dict[str, int] = {}  # URL -> retry count
        self.domain = urlparse(config.base_url).netloc
        
        # Discovery statistics
        self.discovery_stats = {
            "aggressive_crawl_urls": 0,
            "pages_crawled": 0,
            "pages_failed": 0,
            "pages_retried": 0,
            "total_links_extracted": 0,
            "unique_links_found": 0
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
    
    def _get_aggressive_popup_bypass_js(self) -> str:
        """Enhanced JavaScript code for aggressive popup bypass"""
        return """
        // Aggressive overlay removal
        const overlaySelectors = [
            '[class*="overlay"]', '[class*="modal"]', '[class*="popup"]', 
            '[id*="overlay"]', '[id*="modal"]', '[id*="popup"]',
            '[class*="lightbox"]', '[class*="dialog"]', '[class*="banner"]',
            '[class*="cookie"]', '[class*="consent"]', '[class*="notice"]'
        ];
        
        overlaySelectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => el.remove());
        });
        
        // Remove high z-index elements (aggressive)
        const allElements = document.querySelectorAll('*');
        allElements.forEach(el => {
            const style = window.getComputedStyle(el);
            const zIndex = parseInt(style.zIndex);
            
            if (zIndex > 500) {  // Lower threshold for aggressive removal
                el.remove();
            }
            
            // Remove fixed/sticky positioned overlays
            if ((style.position === 'fixed' || style.position === 'sticky')) {
                const rect = el.getBoundingClientRect();
                if (rect.width > window.innerWidth * 0.3 && rect.height > window.innerHeight * 0.3) {
                    el.remove();
                }
            }
        });
        
        // Force enable scrolling
        document.body.style.overflow = 'auto';
        document.documentElement.style.overflow = 'auto';
        document.body.style.position = 'static';
        
        // Remove any event listeners that might block navigation
        window.onbeforeunload = null;
        window.addEventListener = function() {};
        
        // Wait for content to load, then scroll to trigger lazy loading
        setTimeout(() => {
            window.scrollTo(0, document.body.scrollHeight / 2);
            setTimeout(() => {
                window.scrollTo(0, document.body.scrollHeight);
            }, 500);
        }, 1000);
        """
    
    async def run_aggressive_deep_crawling(self, input_urls: Set[str], already_crawled: Set[str] = None) -> Dict[str, Any]:
        """Main aggressive deep crawling method"""
        print("\n🔥 PHASE 7: AGGRESSIVE DEEP CRAWLING")
        print("-" * 50)
        
        start_time = time.time()
        
        # Store input URLs and filter out already crawled ones
        self.input_urls = input_urls.copy()
        if already_crawled:
            self.input_urls -= already_crawled
            print(f"📂 Filtered out {len(already_crawled)} already crawled URLs")
        
        print(f"📂 Starting aggressive crawling of {len(self.input_urls)} URLs")
        
        # Progressive enhancement aggressive crawling
        await self._aggressive_crawling_progressive()
        
        # Handle retry queue
        await self._process_retry_queue()
        
        end_time = time.time()
        self.discovery_stats["aggressive_crawl_urls"] = len(self.discovered_urls)
        
        print(f"\n✅ Aggressive Deep Crawling Complete!")
        print(f"📊 URLs discovered: {len(self.discovered_urls)}")
        print(f"📊 Pages crawled: {self.discovery_stats['pages_crawled']}")
        print(f"📊 Pages failed: {self.discovery_stats['pages_failed']}")
        print(f"📊 Total links extracted: {self.discovery_stats['total_links_extracted']}")
        print(f"⏱️  Total time: {end_time - start_time:.1f}s")
        
        return self._generate_results()
    
    async def _aggressive_crawling_progressive(self):
        """Progressive enhancement aggressive crawling"""
        
        # 🧱 BRICK 1: Basic Aggressive Crawl4AI
        print("\n  🧱 BRICK 1: Basic Aggressive Crawl4AI")
        if await self._try_basic_aggressive_crawling():
            print("    🎉 SUCCESS with Basic Aggressive Crawl4AI!")
            return
        
        # 🧱 BRICK 2: Stealth Aggressive Crawling
        print("\n  🧱 BRICK 2: Stealth Aggressive Crawling")
        if await self._try_stealth_aggressive_crawling():
            print("    🎉 SUCCESS with Stealth Aggressive Crawling!")
            return
        
        # 🧱 BRICK 3: Undetected Aggressive Crawling
        print("\n  🧱 BRICK 3: Undetected Aggressive Crawling")
        if await self._try_undetected_aggressive_crawling():
            print("    🎉 SUCCESS with Undetected Aggressive Crawling!")
            return
        
        # 🧱 BRICK 4: HTTP Aggressive Fallback
        print("\n  🧱 BRICK 4: HTTP Aggressive Fallback")
        await self._try_http_aggressive_fallback()
        
        print("\n  ✅ Progressive aggressive crawling complete")
    
    async def _try_basic_aggressive_crawling(self) -> bool:
        """Try basic aggressive crawling with Crawl4AI"""
        try:
            async with AsyncWebCrawler(config=self.browser_configs['basic']) as crawler:
                return await self._aggressive_crawl_with_config(crawler, "BASIC_AGGRESSIVE")
        except Exception as e:
            print(f"      ❌ Basic aggressive crawling failed: {str(e)[:100]}")
            logger.error(f"Basic aggressive crawling failed: {e}")
            return False
    
    async def _try_stealth_aggressive_crawling(self) -> bool:
        """Try stealth aggressive crawling"""
        if 'stealth' not in self.browser_configs:
            return False
        
        try:
            async with AsyncWebCrawler(config=self.browser_configs['stealth']) as crawler:
                return await self._aggressive_crawl_with_config(crawler, "STEALTH_AGGRESSIVE")
        except Exception as e:
            print(f"      ❌ Stealth aggressive crawling failed: {str(e)[:100]}")
            logger.error(f"Stealth aggressive crawling failed: {e}")
            return False
    
    async def _try_undetected_aggressive_crawling(self) -> bool:
        """Try undetected aggressive crawling"""
        try:
            browser_config = self.browser_configs['undetected']
            crawler_strategy = AsyncPlaywrightCrawlerStrategy(
                adapter=UndetectedAdapter(),
                browser_config=browser_config
            )
            
            async with AsyncWebCrawler(crawler_strategy=crawler_strategy) as crawler:
                return await self._aggressive_crawl_with_config(crawler, "UNDETECTED_AGGRESSIVE")
        except Exception as e:
            print(f"      ❌ Undetected aggressive crawling failed: {str(e)[:100]}")
            logger.error(f"Undetected aggressive crawling failed: {e}")
            return False
    
    async def _aggressive_crawl_with_config(self, crawler, mode: str) -> bool:
        """Aggressive crawling with specific configuration"""
        print(f"      🚀 Starting {mode} crawling...")
        
        try:
            # Aggressive crawler config
            crawler_config = CrawlerRunConfig(
                page_timeout=25000,  # Longer timeout for aggressive crawling
                verbose=False,
                js_code=self._get_aggressive_popup_bypass_js(),
                wait_for_images=False,
                delay_before_return_html=3000,  # Wait for dynamic content
                remove_overlay_elements=True,
                simulate_user=True,
                override_navigator=True,
                extract_links=True,  # Enable comprehensive link extraction
                js_only=False,  # Get both JS and non-JS content
                process_iframes=True,  # Process iframe content
                exclude_external_links=False  # Include external links for validation
            )
            
            urls_to_crawl = list(self.input_urls - self.crawled_urls - self.failed_urls)
            total_new_links = 0
            
            # Use aggressive batch processing
            batch_size = min(self.config.max_concurrent, 50)
            
            for i in range(0, len(urls_to_crawl), batch_size):
                batch = urls_to_crawl[i:i + batch_size]
                
                # Stop if we've reached max pages
                if len(self.crawled_urls) >= self.config.max_pages:
                    print(f"      ⚠️  Reached max pages limit ({self.config.max_pages})")
                    break
                
                print(f"        📊 Aggressive batch {i//batch_size + 1}/{(len(urls_to_crawl) + batch_size - 1)//batch_size} ({len(batch)} URLs)")
                
                # Process batch with aggressive settings
                batch_results = await self._process_aggressive_batch(crawler, batch, crawler_config)
                
                new_links = batch_results['new_links']
                successful_count = batch_results['successful_count']
                failed_count = batch_results['failed_count']
                
                total_new_links += len(new_links)
                
                # Add new URLs to discovered set
                for new_url in new_links:
                    if (new_url not in self.discovered_urls and
                        self._should_include_url(new_url)):
                        self.discovered_urls.add(new_url)
                
                print(f"        ✅ Aggressive batch complete: {successful_count} success, {failed_count} failed, {len(new_links)} new links")
                
                # Very short delay for aggressive crawling
                await asyncio.sleep(self.config.delay_between_requests)
            
            print(f"      ✅ {mode} complete: {total_new_links} total links extracted")
            self.discovery_stats["total_links_extracted"] += total_new_links
            self.discovery_stats["unique_links_found"] = len(self.discovered_urls)
            return total_new_links > 0
            
        except Exception as e:
            print(f"      ❌ {mode} failed: {str(e)[:100]}")
            logger.error(f"{mode} failed: {e}")
            return False
    
    async def _process_aggressive_batch(self, crawler, urls: List[str], crawler_config) -> Dict[str, Any]:
        """Process a batch of URLs with aggressive settings"""
        all_new_links = set()
        successful_count = 0
        failed_count = 0
        
        try:
            # Create tasks for concurrent processing
            tasks = []
            for url in urls:
                task = self._crawl_single_url_aggressive(crawler, url, crawler_config)
                tasks.append(task)
            
            # Process all URLs concurrently with return_exceptions=True
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                url = urls[i]
                
                if isinstance(result, Exception):
                    print(f"          ❌ {url}: {str(result)[:50]}")
                    failed_count += 1
                    # Add to retry queue if not exceeded max retries
                    if url not in self.retry_queue:
                        self.retry_queue[url] = 0
                    if self.retry_queue[url] < self.config.max_retries:
                        self.retry_queue[url] += 1
                    else:
                        self.failed_urls.add(url)
                else:
                    successful_count += 1
                    self.crawled_urls.add(url)
                    # Remove from retry queue if it was there
                    if url in self.retry_queue:
                        del self.retry_queue[url]
                    
                    if result:  # Set of extracted links
                        all_new_links.update(result)
                        print(f"          ✅ {url}: {len(result)} links extracted")
                    else:
                        print(f"          ⚠️  {url}: No links extracted")
        
        except Exception as e:
            print(f"        ❌ Aggressive batch processing failed: {str(e)}")
            logger.error(f"Aggressive batch processing failed: {e}")
            failed_count = len(urls)
        
        self.discovery_stats["pages_crawled"] += successful_count
        self.discovery_stats["pages_failed"] += failed_count
        
        return {
            'new_links': all_new_links,
            'successful_count': successful_count,
            'failed_count': failed_count
        }
    
    async def _crawl_single_url_aggressive(self, crawler, url: str, crawler_config) -> Set[str]:
        """Crawl a single URL with aggressive settings"""
        try:
            result_container = await asyncio.wait_for(
                crawler.arun(url=url, config=crawler_config),
                timeout=self.config.timeout
            )
            
            if result_container and len(result_container._results) > 0:
                result = result_container._results[0]
                
                if result.success and result.html:
                    # Aggressive link extraction using all available methods
                    extracted_links = await self._extract_links_aggressive(result, url)
                    return extracted_links
            
            return set()
            
        except asyncio.TimeoutError:
            logger.debug(f"Timeout in aggressive crawling {url}")
            return set()
        except Exception as e:
            logger.debug(f"Error in aggressive crawling {url}: {e}")
            return set()
    
    async def _extract_links_aggressive(self, result, base_url: str) -> Set[str]:
        """Aggressive link extraction using all available methods"""
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
                
                # Include external links that might redirect to internal
                if hasattr(result.links, 'external'):
                    for link in result.links.external:
                        if hasattr(link, 'href') and self.domain in link.href:
                            if self._should_include_url(link.href):
                                links.add(link.href)
            
            # Method 2: Aggressive HTML parsing
            if hasattr(result, 'html') and result.html:
                html_links = await self._extract_links_from_html_aggressive(result.html, base_url)
                links.update(html_links)
            
            # Method 3: Extract from cleaned HTML
            if hasattr(result, 'cleaned_html') and result.cleaned_html:
                cleaned_links = await self._extract_links_from_html_aggressive(result.cleaned_html, base_url)
                links.update(cleaned_links)
            
            # Method 4: Extract from markdown if available
            if hasattr(result, 'markdown') and result.markdown:
                markdown_links = self._extract_links_from_markdown(result.markdown, base_url)
                links.update(markdown_links)
        
        except Exception as e:
            logger.debug(f"Aggressive link extraction failed for {base_url}: {e}")
        
        return links
    
    async def _extract_links_from_html_aggressive(self, html_content: str, base_url: str) -> Set[str]:
        """Aggressive HTML link extraction"""
        links = set()
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Method 1: All href attributes
            for element in soup.find_all(attrs={'href': True}):
                href = element['href']
                full_url = urljoin(base_url, href)
                if self._should_include_url(full_url):
                    links.add(full_url)
            
            # Method 2: All src attributes (for iframes, etc.)
            for element in soup.find_all(attrs={'src': True}):
                src = element['src']
                if src.startswith(('http', '/')):  # Valid URL
                    full_url = urljoin(base_url, src)
                    if self._should_include_url(full_url):
                        links.add(full_url)
            
            # Method 3: Form actions
            for form in soup.find_all('form', action=True):
                action = form['action']
                if action and not action.startswith(('javascript:', 'mailto:')):
                    full_url = urljoin(base_url, action)
                    if self._should_include_url(full_url):
                        links.add(full_url)
            
            # Method 4: JavaScript-referenced URLs (aggressive regex)
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Multiple regex patterns for different URL formats
                    url_patterns = [
                        r'["\']([^"\']*\.html?[^"\']*)["\']',
                        r'["\']([^"\']*\.php[^"\']*)["\']',
                        r'["\']([^"\']*\.jsp[^"\']*)["\']',
                        r'["\']([^"\']*\.asp[^"\']*)["\']',
                        r'["\']([^"\']*\.aspx[^"\']*)["\']',
                        r'url\s*:\s*["\']([^"\']+)["\']',
                        r'location\s*=\s*["\']([^"\']+)["\']',
                        r'href\s*=\s*["\']([^"\']+)["\']'
                    ]
                    
                    for pattern in url_patterns:
                        js_urls = re.findall(pattern, script.string)
                        for js_url in js_urls:
                            full_url = urljoin(base_url, js_url)
                            if self._should_include_url(full_url):
                                links.add(full_url)
            
            # Method 5: Meta refresh URLs
            meta_refresh = soup.find_all('meta', attrs={'http-equiv': 'refresh'})
            for meta in meta_refresh:
                content = meta.get('content', '')
                if 'url=' in content.lower():
                    url_part = content.lower().split('url=')[1]
                    full_url = urljoin(base_url, url_part)
                    if self._should_include_url(full_url):
                        links.add(full_url)
            
            # Method 6: Data attributes that might contain URLs
            for element in soup.find_all(attrs=lambda x: x and any(attr.startswith('data-') for attr in x.keys())):
                for attr_name, attr_value in element.attrs.items():
                    if (attr_name.startswith('data-') and 
                        isinstance(attr_value, str) and 
                        ('/' in attr_value or '.html' in attr_value)):
                        full_url = urljoin(base_url, attr_value)
                        if self._should_include_url(full_url):
                            links.add(full_url)
        
        except Exception as e:
            logger.debug(f"Aggressive HTML parsing failed: {e}")
        
        return links
    
    def _extract_links_from_markdown(self, markdown_content: str, base_url: str) -> Set[str]:
        """Extract links from markdown content"""
        links = set()
        
        try:
            # Regex for markdown links [text](url)
            markdown_links = re.findall(r'\[([^\]]*)\]\(([^)]+)\)', markdown_content)
            for text, url in markdown_links:
                full_url = urljoin(base_url, url)
                if self._should_include_url(full_url):
                    links.add(full_url)
        
        except Exception as e:
            logger.debug(f"Markdown link extraction failed: {e}")
        
        return links
    
    async def _process_retry_queue(self):
        """Process URLs in the retry queue"""
        if not self.retry_queue:
            return
        
        print(f"\n  🔄 Processing {len(self.retry_queue)} URLs in retry queue...")
        
        retry_urls = list(self.retry_queue.keys())
        
        try:
            async with AsyncWebCrawler(config=self.browser_configs['basic']) as crawler:
                
                crawler_config = CrawlerRunConfig(
                    page_timeout=30000,  # Longer timeout for retries
                    verbose=False,
                    js_code=self._get_aggressive_popup_bypass_js(),
                    wait_for_images=False,
                    delay_before_return_html=2000,
                    extract_links=True
                )
                
                for url in retry_urls:
                    try:
                        await asyncio.sleep(self.config.retry_delay)  # Delay between retries
                        
                        result_container = await asyncio.wait_for(
                            crawler.arun(url=url, config=crawler_config),
                            timeout=self.config.timeout
                        )
                        
                        if result_container and len(result_container._results) > 0:
                            result = result_container._results[0]
                            
                            if result.success and result.html:
                                # Extract links on successful retry
                                links = await self._extract_links_aggressive(result, url)
                                
                                # Add new URLs
                                for link in links:
                                    if (link not in self.discovered_urls and
                                        self._should_include_url(link)):
                                        self.discovered_urls.add(link)
                                
                                self.crawled_urls.add(url)
                                self.discovery_stats["pages_retried"] += 1
                                print(f"    ✅ Retry success: {url} ({len(links)} links)")
                            else:
                                self.failed_urls.add(url)
                                print(f"    ❌ Retry failed: {url}")
                        else:
                            self.failed_urls.add(url)
                            print(f"    ❌ Retry failed: {url}")
                    
                    except Exception as e:
                        self.failed_urls.add(url)
                        print(f"    ❌ Retry error: {url}: {str(e)[:50]}")
        
        except Exception as e:
            print(f"  ❌ Retry queue processing failed: {str(e)}")
            logger.error(f"Retry queue processing failed: {e}")
        
        # Clear retry queue
        self.retry_queue.clear()
    
    async def _try_http_aggressive_fallback(self):
        """HTTP fallback for aggressive crawling"""
        print("      🌐 Trying HTTP aggressive fallback...")
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; AggressiveCrawler)'}
            
            # Configure proxy if enabled
            connector = None
            if self.config.proxy_enabled:
                connector = aiohttp.TCPConnector()
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=connector
            ) as session:
                
                urls_to_crawl = list(self.input_urls - self.crawled_urls - self.failed_urls)
                total_new_links = 0
                
                for url in urls_to_crawl:
                    if len(self.crawled_urls) >= self.config.max_pages:
                        break
                    
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
                                        self._should_include_url(link)):
                                        self.discovered_urls.add(link)
                                
                                total_new_links += len(links)
                                self.crawled_urls.add(url)
                                self.discovery_stats["pages_crawled"] += 1
                                
                                print(f"        ✅ {url}: {len(links)} links extracted")
                            else:
                                print(f"        ❌ {url}: Status {response.status}")
                                self.failed_urls.add(url)
                                self.discovery_stats["pages_failed"] += 1
                    
                    except Exception as e:
                        print(f"        ❌ {url}: {str(e)[:50]}")
                        self.failed_urls.add(url)
                        self.discovery_stats["pages_failed"] += 1
                    
                    await asyncio.sleep(self.config.delay_between_requests)
                
                print(f"      ✅ HTTP aggressive fallback complete: {total_new_links} links extracted")
                self.discovery_stats["total_links_extracted"] += total_new_links
        
        except Exception as e:
            print(f"      ❌ HTTP aggressive fallback failed: {str(e)}")
            logger.error(f"HTTP aggressive fallback failed: {e}")
    
    async def _extract_links_from_html_basic(self, html_content: str, base_url: str) -> Set[str]:
        """Basic HTML link extraction for HTTP fallback"""
        links = set()
        
        try:
            # Multiple regex patterns for comprehensive extraction
            patterns = [
                r'href=["\']([^"\']+)["\']',
                r'src=["\']([^"\']+)["\']',
                r'action=["\']([^"\']+)["\']'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html_content)
                for match in matches:
                    full_url = urljoin(base_url, match)
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
            "phase": "aggressive_deep_crawling",
            "total_discovered_urls": len(self.discovered_urls),
            "input_urls_processed": len(self.input_urls),
            "pages_crawled": self.discovery_stats["pages_crawled"],
            "pages_failed": self.discovery_stats["pages_failed"],
            "pages_retried": self.discovery_stats["pages_retried"],
            "total_links_extracted": self.discovery_stats["total_links_extracted"],
            "unique_links_found": self.discovery_stats["unique_links_found"],
            "discovered_urls": sorted(list(self.discovered_urls)),
            "failed_urls": sorted(list(self.failed_urls)),
            "discovery_stats": self.discovery_stats,
            "config": {
                "base_url": self.config.base_url,
                "max_pages": self.config.max_pages,
                "max_concurrent": self.config.max_concurrent,
                "max_retries": self.config.max_retries,
                "extract_all_links": self.config.extract_all_links,
                "proxy_enabled": self.config.proxy_enabled,
                "stealth_mode": self.config.stealth_mode
            }
        }
    
    def save_results(self, filename: str = None) -> str:
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"phase7_aggressive_deep_crawling_results_{timestamp}.json"
        
        results = self._generate_results()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")
        return filename

# Example usage
async def main():
    """Example usage of Phase 7: Aggressive Deep Crawling"""
    
    # Configuration
    config = AggressiveCrawlConfig(
        base_url="https://www.city.chiyoda.lg.jp",
        max_pages=15000,
        max_concurrent=75,
        delay_between_requests=0.05,
        max_retries=3,
        extract_all_links=True,
        proxy_enabled=True,
        stealth_mode=True
    )
    
    # Sample input URLs (would normally come from previous phases)
    sample_input_urls = {
        "https://www.city.chiyoda.lg.jp/koho/kurashi/index.html",
        "https://www.city.chiyoda.lg.jp/koho/bunka/index.html",
        "https://www.city.chiyoda.lg.jp/koho/kenko/index.html",
    }
    
    # Create crawler
    crawler = AggressiveDeepCrawler(config)
    
    # Run aggressive deep crawling
    results = await crawler.run_aggressive_deep_crawling(sample_input_urls)
    
    # Save results
    filename = crawler.save_results()
    
    print(f"\n📊 Phase 7 Complete!")
    print(f"📂 URLs discovered: {results['total_discovered_urls']}")
    print(f"📄 Pages crawled: {results['pages_crawled']}")
    print(f"❌ Pages failed: {results['pages_failed']}")
    print(f"🔄 Pages retried: {results['pages_retried']}")
    print(f"🔗 Total links extracted: {results['total_links_extracted']}")
    print(f"📁 Results saved: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
