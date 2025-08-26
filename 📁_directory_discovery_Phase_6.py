#!/usr/bin/env python3
"""
Phase 5: Directory Discovery - 150+ common directory patterns
Test common directory patterns and structures to find hidden content
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
        logging.FileHandler('phase5_directory_discovery.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class DirectoryDiscoveryConfig:
    """Configuration for directory discovery"""
    base_url: str
    max_directories: int = 5000
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

class DirectoryDiscoverer:
    """Phase 5: Directory Discovery - 150+ common directory patterns"""
    
    def __init__(self, config: DirectoryDiscoveryConfig):
        self.config = config
        self.discovered_urls: Set[str] = set()
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.directory_patterns: List[str] = []
        self.domain = urlparse(config.base_url).netloc
        
        # Discovery statistics
        self.discovery_stats = {
            "directory_discovery_urls": 0,
            "directories_tested": 0,
            "directories_found": 0,
            "crawled_pages": 0,
            "failed_pages": 0
        }
        
        # Browser configurations for different enhancement levels
        self.browser_configs = self._create_browser_configs()
        
        # Initialize comprehensive directory patterns
        self._initialize_directory_patterns()
        
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
    
    def _initialize_directory_patterns(self):
        """Initialize comprehensive list of 150+ directory patterns"""
        
        # Administrative & Management (20 patterns)
        admin_patterns = [
            '/admin/', '/administration/', '/manage/', '/management/', '/control/',
            '/console/', '/dashboard/', '/panel/', '/backend/', '/cp/',
            '/controlpanel/', '/admincp/', '/sysadmin/', '/system/', '/config/',
            '/configuration/', '/settings/', '/options/', '/preferences/', '/tools/'
        ]
        
        # Information & About (25 patterns)
        info_patterns = [
            '/about/', '/info/', '/information/', '/overview/', '/profile/',
            '/company/', '/organization/', '/corporate/', '/history/', '/mission/',
            '/vision/', '/values/', '/culture/', '/team/', '/staff/',
            '/leadership/', '/management/', '/board/', '/executives/', '/officers/',
            '/background/', '/introduction/', '/summary/', '/details/', '/description/'
        ]
        
        # Services & Products (20 patterns)
        service_patterns = [
            '/services/', '/service/', '/products/', '/product/', '/solutions/',
            '/solution/', '/offerings/', '/offering/', '/programs/', '/program/',
            '/packages/', '/package/', '/plans/', '/plan/', '/options/',
            '/features/', '/benefits/', '/advantages/', '/capabilities/', '/expertise/'
        ]
        
        # Resources & Documentation (25 patterns)
        resource_patterns = [
            '/resources/', '/resource/', '/documents/', '/document/', '/files/',
            '/downloads/', '/download/', '/library/', '/archive/', '/repository/',
            '/database/', '/catalog/', '/collection/', '/gallery/', '/portfolio/',
            '/samples/', '/examples/', '/templates/', '/forms/', '/guides/',
            '/manuals/', '/handbook/', '/documentation/', '/docs/', '/help/'
        ]
        
        # News & Communication (20 patterns)
        news_patterns = [
            '/news/', '/press/', '/media/', '/blog/', '/articles/',
            '/article/', '/posts/', '/post/', '/updates/', '/update/',
            '/announcements/', '/announcement/', '/releases/', '/release/', '/alerts/',
            '/notifications/', '/bulletin/', '/newsletter/', '/magazine/', '/journal/'
        ]
        
        # Support & Contact (15 patterns)
        support_patterns = [
            '/support/', '/help/', '/contact/', '/feedback/', '/customer/',
            '/client/', '/service/', '/assistance/', '/faq/', '/questions/',
            '/answers/', '/support-center/', '/helpdesk/', '/tickets/', '/issues/'
        ]
        
        # Content & Pages (15 patterns)
        content_patterns = [
            '/content/', '/pages/', '/page/', '/sections/', '/section/',
            '/categories/', '/category/', '/topics/', '/topic/', '/areas/',
            '/area/', '/departments/', '/department/', '/divisions/', '/division/'
        ]
        
        # Portal & Navigation (10 patterns)
        portal_patterns = [
            '/portal/', '/gateway/', '/entrance/', '/main/', '/home/',
            '/index/', '/start/', '/welcome/', '/landing/', '/sitemap/'
        ]
        
        # Data & Analytics (10 patterns)
        data_patterns = [
            '/data/', '/statistics/', '/stats/', '/metrics/', '/analytics/',
            '/reports/', '/report/', '/research/', '/studies/', '/surveys/'
        ]
        
        # Search & Browse (5 patterns)
        search_patterns = [
            '/search/', '/find/', '/browse/', '/explore/', '/directory/'
        ]
        
        # Combine all patterns
        self.directory_patterns = (
            admin_patterns + info_patterns + service_patterns + resource_patterns +
            news_patterns + support_patterns + content_patterns + portal_patterns +
            data_patterns + search_patterns
        )
        
        print(f"📁 Initialized {len(self.directory_patterns)} directory patterns for testing")
    
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
    
    async def run_directory_discovery(self, seed_urls: Set[str] = None) -> Dict[str, Any]:
        """Main directory discovery method"""
        print("\n📁 PHASE 5: DIRECTORY DISCOVERY")
        print("-" * 50)
        
        start_time = time.time()
        
        # Initialize with seed URLs if provided
        if seed_urls:
            self.discovered_urls.update(seed_urls)
            print(f"📂 Starting with {len(seed_urls)} seed URLs")
        
        # Generate directory URLs from patterns
        directory_urls = self._generate_directory_urls()
        
        # Progressive enhancement directory testing
        await self._directory_discovery_progressive(directory_urls)
        
        end_time = time.time()
        self.discovery_stats["directory_discovery_urls"] = len(self.discovered_urls)
        
        print(f"\n✅ Directory Discovery Complete!")
        print(f"📊 URLs discovered: {len(self.discovered_urls)}")
        print(f"📊 Directories tested: {self.discovery_stats['directories_tested']}")
        print(f"📊 Directories found: {self.discovery_stats['directories_found']}")
        print(f"⏱️  Total time: {end_time - start_time:.1f}s")
        
        return self._generate_results()
    
    def _generate_directory_urls(self) -> List[str]:
        """Generate directory URLs from patterns"""
        directory_urls = []
        
        for pattern in self.directory_patterns:
            directory_url = urljoin(self.config.base_url, pattern)
            if self._should_include_url(directory_url):
                directory_urls.append(directory_url)
        
        self.discovery_stats["directories_tested"] = len(directory_urls)
        print(f"  📊 Generated {len(directory_urls)} directory URLs to test")
        
        return directory_urls
    
    async def _directory_discovery_progressive(self, directory_urls: List[str]):
        """Progressive enhancement directory discovery"""
        
        # 🧱 BRICK 1: Basic Crawl4AI
        print("\n  🧱 BRICK 1: Basic Crawl4AI Directory Testing")
        if await self._try_basic_directory_discovery(directory_urls):
            print("    🎉 SUCCESS with Basic Crawl4AI!")
            return
        
        # 🧱 BRICK 2: Crawl4AI + Stealth Mode  
        print("\n  🧱 BRICK 2: Crawl4AI + Stealth Mode Directory Testing")
        if await self._try_stealth_directory_discovery(directory_urls):
            print("    🎉 SUCCESS with Stealth Mode!")
            return
        
        # 🧱 BRICK 3: Crawl4AI + Stealth + Undetected Browser
        print("\n  🧱 BRICK 3: Crawl4AI + Stealth + Undetected Browser Directory Testing")
        if await self._try_undetected_directory_discovery(directory_urls):
            print("    🎉 SUCCESS with Undetected Browser!")
            return
        
        # 🧱 BRICK 4: HTTP Fallback (final resort)
        print("\n  🧱 BRICK 4: HTTP Fallback (Final Resort)")
        await self._try_http_directory_fallback(directory_urls)
        
        print("\n  ✅ Progressive directory discovery complete")
    
    async def _try_basic_directory_discovery(self, directory_urls: List[str]) -> bool:
        """Try basic directory discovery with Crawl4AI"""
        try:
            async with AsyncWebCrawler(config=self.browser_configs['basic']) as crawler:
                return await self._directory_discovery_with_config(crawler, directory_urls, "BASIC")
        except Exception as e:
            print(f"      ❌ Basic directory discovery failed: {str(e)[:100]}")
            logger.error(f"Basic directory discovery failed: {e}")
            return False
    
    async def _try_stealth_directory_discovery(self, directory_urls: List[str]) -> bool:
        """Try stealth directory discovery"""
        if 'stealth' not in self.browser_configs:
            return False
        
        try:
            async with AsyncWebCrawler(config=self.browser_configs['stealth']) as crawler:
                return await self._directory_discovery_with_config(crawler, directory_urls, "STEALTH")
        except Exception as e:
            print(f"      ❌ Stealth directory discovery failed: {str(e)[:100]}")
            logger.error(f"Stealth directory discovery failed: {e}")
            return False
    
    async def _try_undetected_directory_discovery(self, directory_urls: List[str]) -> bool:
        """Try undetected directory discovery"""
        try:
            browser_config = self.browser_configs['undetected']
            crawler_strategy = AsyncPlaywrightCrawlerStrategy(
                adapter=UndetectedAdapter(),
                browser_config=browser_config
            )
            
            async with AsyncWebCrawler(crawler_strategy=crawler_strategy) as crawler:
                return await self._directory_discovery_with_config(crawler, directory_urls, "UNDETECTED")
        except Exception as e:
            print(f"      ❌ Undetected directory discovery failed: {str(e)[:100]}")
            logger.error(f"Undetected directory discovery failed: {e}")
            return False
    
    async def _directory_discovery_with_config(self, crawler, directory_urls: List[str], mode: str) -> bool:
        """Directory discovery with specific configuration"""
        print(f"      🚀 Starting {mode} directory discovery...")
        
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
            
            batch_size = min(self.config.max_concurrent, 25)  # Smaller batches for directory testing
            total_new_links = 0
            directories_found = 0
            
            # Process directory URLs in batches
            for i in range(0, len(directory_urls), batch_size):
                batch = directory_urls[i:i + batch_size]
                print(f"        📊 Testing directory batch {i//batch_size + 1}/{(len(directory_urls) + batch_size - 1)//batch_size} ({len(batch)} directories)")
                
                # Process batch concurrently
                batch_results = await self._process_directory_batch(crawler, batch, crawler_config)
                new_links = batch_results['new_links']
                found_dirs = batch_results['found_directories']
                
                total_new_links += len(new_links)
                directories_found += found_dirs
                
                # Add new URLs to discovered set
                for new_url in new_links:
                    if (new_url not in self.discovered_urls and
                        self._should_include_url(new_url)):
                        self.discovered_urls.add(new_url)
                
                print(f"        ✅ Directory batch complete. Found dirs: {found_dirs}, New links: {len(new_links)}")
                
                # Add small delay between batches
                await asyncio.sleep(self.config.delay_between_requests)
            
            print(f"      ✅ {mode} directory discovery complete: {directories_found} directories found, {total_new_links} links extracted")
            self.discovery_stats["directories_found"] += directories_found
            return directories_found > 0
            
        except Exception as e:
            print(f"      ❌ {mode} directory discovery failed: {str(e)[:100]}")
            logger.error(f"{mode} directory discovery failed: {e}")
            return False
    
    async def _process_directory_batch(self, crawler, urls: List[str], crawler_config) -> Dict[str, Any]:
        """Process a batch of directory URLs concurrently"""
        all_new_links = set()
        found_directories = 0
        
        try:
            # Create tasks for concurrent processing
            tasks = []
            for url in urls:
                task = self._test_single_directory(crawler, url, crawler_config)
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
                    
                    if result and result['exists']:
                        found_directories += 1
                        links = result['links']
                        all_new_links.update(links)
                        print(f"          ✅ {url}: Directory found! {len(links)} links extracted")
                    else:
                        print(f"          ⚠️  {url}: Directory not found or empty")
        
        except Exception as e:
            print(f"        ❌ Directory batch processing failed: {str(e)}")
            logger.error(f"Directory batch processing failed: {e}")
        
        return {
            'new_links': all_new_links,
            'found_directories': found_directories
        }
    
    async def _test_single_directory(self, crawler, url: str, crawler_config) -> Dict[str, Any]:
        """Test a single directory URL"""
        try:
            result_container = await asyncio.wait_for(
                crawler.arun(url=url, config=crawler_config),
                timeout=self.config.timeout
            )
            
            if result_container and len(result_container._results) > 0:
                result = result_container._results[0]
                
                if result.success and result.html:
                    # Check if this is a valid directory page
                    if self._is_valid_directory_page(result.html, url):
                        # Extract links from directory page
                        extracted_links = await self._extract_directory_links(result, url)
                        return {
                            'exists': True,
                            'links': extracted_links
                        }
            
            return {'exists': False, 'links': set()}
            
        except asyncio.TimeoutError:
            logger.debug(f"Timeout testing directory {url}")
            return {'exists': False, 'links': set()}
        except Exception as e:
            logger.debug(f"Error testing directory {url}: {e}")
            return {'exists': False, 'links': set()}
    
    def _is_valid_directory_page(self, html_content: str, url: str) -> bool:
        """Check if HTML content represents a valid directory page"""
        try:
            # Check content length (very short pages are likely errors)
            if len(html_content) < 200:
                return False
            
            # Check for common error indicators
            error_indicators = ['404', 'not found', 'page not found', 'error', 'forbidden', '403']
            content_lower = html_content.lower()
            
            if any(indicator in content_lower for indicator in error_indicators):
                return False
            
            # Check for directory-like content
            directory_indicators = [
                '<a href=', 'index of', 'directory listing', 'parent directory',
                'file list', 'folder', 'directory', '<ul>', '<li>', '<table>'
            ]
            
            if any(indicator in content_lower for indicator in directory_indicators):
                return True
            
            # Check title for directory-like content
            soup = BeautifulSoup(html_content, 'html.parser')
            title = soup.find('title')
            if title and title.text:
                title_lower = title.text.lower()
                if any(indicator in title_lower for indicator in ['index', 'directory', 'listing', 'contents']):
                    return True
            
            # If we have substantial content and no error indicators, consider it valid
            return len(html_content) > 1000
            
        except Exception:
            return False
    
    async def _extract_directory_links(self, result, directory_url: str) -> Set[str]:
        """Extract links from a directory page"""
        links = set()
        
        try:
            # Method 1: Use Crawl4AI's built-in link extraction
            if hasattr(result, 'links') and result.links:
                if hasattr(result.links, 'internal'):
                    for link in result.links.internal:
                        if hasattr(link, 'href'):
                            full_url = urljoin(directory_url, link.href)
                            if self._should_include_url(full_url):
                                links.add(full_url)
            
            # Method 2: Enhanced HTML parsing for directory listings
            if hasattr(result, 'html') and result.html:
                additional_links = await self._extract_directory_links_from_html(result.html, directory_url)
                links.update(additional_links)
        
        except Exception as e:
            logger.debug(f"Directory link extraction failed for {directory_url}: {e}")
        
        return links
    
    async def _extract_directory_links_from_html(self, html_content: str, directory_url: str) -> Set[str]:
        """Extract directory listing links from HTML"""
        links = set()
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Method 1: Standard directory listing links
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(directory_url, href)
                if self._should_include_url(full_url):
                    links.add(full_url)
            
            # Method 2: Table-based directory listings
            tables = soup.find_all('table')
            for table in tables:
                table_links = table.find_all('a', href=True)
                for link in table_links:
                    href = link['href']
                    full_url = urljoin(directory_url, href)
                    if self._should_include_url(full_url):
                        links.add(full_url)
            
            # Method 3: List-based directory structures
            lists = soup.find_all(['ul', 'ol'])
            for list_elem in lists:
                list_links = list_elem.find_all('a', href=True)
                for link in list_links:
                    href = link['href']
                    full_url = urljoin(directory_url, href)
                    if self._should_include_url(full_url):
                        links.add(full_url)
            
            # Method 4: Navigation and menu links
            nav_elements = soup.find_all(['nav', 'div'], class_=re.compile(r'nav|menu|sidebar', re.I))
            for nav in nav_elements:
                nav_links = nav.find_all('a', href=True)
                for link in nav_links:
                    href = link['href']
                    full_url = urljoin(directory_url, href)
                    if self._should_include_url(full_url):
                        links.add(full_url)
        
        except Exception as e:
            logger.debug(f"Directory HTML link extraction failed: {e}")
        
        return links
    
    async def _try_http_directory_fallback(self, directory_urls: List[str]):
        """HTTP fallback for directory discovery"""
        print("      🌐 Trying HTTP fallback for directory discovery...")
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; DirectoryDiscoverer)'}
            
            # Configure proxy if enabled
            connector = None
            if self.config.proxy_enabled:
                connector = aiohttp.TCPConnector()
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=connector
            ) as session:
                
                total_new_links = 0
                directories_found = 0
                
                for url in directory_urls:
                    try:
                        kwargs = {}
                        if self.config.proxy_enabled:
                            kwargs['proxy'] = self.config.brightdata_proxy
                        
                        async with session.get(url, **kwargs) as response:
                            if response.status == 200:
                                html = await response.text()
                                
                                if self._is_valid_directory_page(html, url):
                                    directories_found += 1
                                    links = await self._extract_directory_links_basic(html, url)
                                    
                                    # Add new URLs
                                    for link in links:
                                        if (link not in self.discovered_urls and
                                            self._should_include_url(link)):
                                            self.discovered_urls.add(link)
                                    
                                    total_new_links += len(links)
                                    print(f"        ✅ {url}: Directory found! {len(links)} links extracted")
                                else:
                                    print(f"        ⚠️  {url}: Not a valid directory")
                                
                                self.crawled_urls.add(url)
                                self.discovery_stats["crawled_pages"] += 1
                            else:
                                print(f"        ❌ {url}: Status {response.status}")
                                self.failed_urls.add(url)
                                self.discovery_stats["failed_pages"] += 1
                    
                    except Exception as e:
                        print(f"        ❌ {url}: {str(e)[:50]}")
                        self.failed_urls.add(url)
                        self.discovery_stats["failed_pages"] += 1
                    
                    await asyncio.sleep(self.config.delay_between_requests)
                
                print(f"      ✅ HTTP directory fallback complete: {directories_found} directories found, {total_new_links} links extracted")
                self.discovery_stats["directories_found"] += directories_found
        
        except Exception as e:
            print(f"      ❌ HTTP directory fallback failed: {str(e)}")
            logger.error(f"HTTP directory fallback failed: {e}")
    
    async def _extract_directory_links_basic(self, html_content: str, directory_url: str) -> Set[str]:
        """Basic directory link extraction for HTTP fallback"""
        links = set()
        
        try:
            # Simple regex-based extraction
            href_pattern = r'href=["\']([^"\']+)["\']'
            matches = re.findall(href_pattern, html_content)
            
            for href in matches:
                full_url = urljoin(directory_url, href)
                if self._should_include_url(full_url):
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
            "phase": "directory_discovery",
            "total_discovered_urls": len(self.discovered_urls),
            "directories_tested": self.discovery_stats["directories_tested"],
            "directories_found": self.discovery_stats["directories_found"],
            "crawled_pages": self.discovery_stats["crawled_pages"],
            "failed_pages": self.discovery_stats["failed_pages"],
            "discovered_urls": sorted(list(self.discovered_urls)),
            "directory_patterns": self.directory_patterns,
            "discovery_stats": self.discovery_stats,
            "config": {
                "base_url": self.config.base_url,
                "max_directories": self.config.max_directories,
                "max_concurrent": self.config.max_concurrent,
                "proxy_enabled": self.config.proxy_enabled,
                "stealth_mode": self.config.stealth_mode
            }
        }
    
    def save_results(self, filename: str = None) -> str:
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"phase5_directory_discovery_results_{timestamp}.json"
        
        results = self._generate_results()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")
        return filename

# Example usage
async def main():
    """Example usage of Phase 5: Directory Discovery"""
    
    # Configuration
    config = DirectoryDiscoveryConfig(
        base_url="https://www.city.chiyoda.lg.jp",
        max_directories=5000,
        max_concurrent=25,
        proxy_enabled=True,
        stealth_mode=True
    )
    
    # Create discoverer
    discoverer = DirectoryDiscoverer(config)
    
    # Run directory discovery
    results = await discoverer.run_directory_discovery()
    
    # Save results
    filename = discoverer.save_results()
    
    print(f"\n📊 Phase 5 Complete!")
    print(f"📂 URLs discovered: {results['total_discovered_urls']}")
    print(f"📁 Directories tested: {results['directories_tested']}")
    print(f"✅ Directories found: {results['directories_found']}")
    print(f"📁 Results saved: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
