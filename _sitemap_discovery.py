#!/usr/bin/env python3
"""
Sitemap Discovery - Progressive Enhancement Implementation
Brick-by-brick approach: Basic → Stealth → Undetected → Proxy → HTTP Fallback

Strategy:
1. Basic Crawl4AI (baseline)
2. Crawl4AI + Stealth Mode  
3. Crawl4AI + Stealth + Undetected Browser
4. Crawl4AI + Stealth + Undetected + Proxy
5. HTTP Fallback (final resort)
"""

import asyncio
import aiohttp
import logging
import warnings
import xml.etree.ElementTree as ET
import re
import time
import atexit
import os
import signal
import sys
from urllib.parse import urljoin, urlparse

# Completely suppress all warnings
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'

# Set up proper event loop policy for Windows
if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from typing import Set, List, Dict, Any, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup

# Crawl4AI imports
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
    from crawl4ai.browser_adapter import UndetectedAdapter
    from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
    print("✅ Crawl4AI imported successfully")
except ImportError as e:
    print(f"❌ Crawl4AI import failed: {e}")
    exit(1)

# Set up logging to suppress most messages
logging.basicConfig(level=logging.ERROR)
logging.getLogger().setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

@dataclass
class SitemapConfig:
    """Configuration for sitemap discovery"""
    base_url: str
    proxy_url: Optional[str] = None  # Format: "http://username:password@host:port"
    timeout: int = 30
    max_retry_attempts: int = 3
    output_file: str = "discovered_sitemap_urls.txt"
    verbose: bool = True

class SitemapDiscovery:
    """Progressive Enhancement Sitemap Discovery"""
    
    def __init__(self, config: SitemapConfig):
        self.config = config
        self.discovered_urls: Set[str] = set()
        self.domain = urlparse(config.base_url).netloc
        self.successfully_processed_sitemaps: Set[str] = set()  # Track successful sitemaps
        self._shutdown_called = False
        self.test_only_chiyoda = "chiyoda" in self.config.base_url.lower()  # Auto-detect Chiyoda testing
        self.stats = {
            "basic_crawl4ai": {"attempted": 0, "successful": 0, "urls_found": 0},
            "stealth_mode": {"attempted": 0, "successful": 0, "urls_found": 0},
            "undetected_browser": {"attempted": 0, "successful": 0, "urls_found": 0},
            "proxy_enabled": {"attempted": 0, "successful": 0, "urls_found": 0},
            "http_fallback": {"attempted": 0, "successful": 0, "urls_found": 0}
        }
        
        # Sitemap locations to check
        self.sitemap_urls = self._generate_sitemap_urls()
        
        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self._cleanup_on_exit)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self._shutdown_called = True
        sys.exit(0)
        
    def _cleanup_on_exit(self):
        """Cleanup on exit"""
        self._shutdown_called = True
        
    def _generate_sitemap_urls(self) -> List[str]:
        """Generate common sitemap URLs"""
        base = self.config.base_url.rstrip('/')
        return [
            f"{base}/sitemap.xml",
            f"{base}/sitemap_index.xml", 
            f"{base}/sitemaps.xml",
            f"{base}/sitemap.html",
            f"{base}/sitemap/",
            f"{base}/wp-sitemap.xml",     # WordPress
            f"{base}/news-sitemap.xml",   # News sites
            f"{base}/video-sitemap.xml",  # Video sites
            f"{base}/product-sitemap.xml", # E-commerce
            f"{base}/page-sitemap.xml",   # General pages
            f"{base}/robots.txt"          # Check robots.txt for sitemap links
        ]
    
    def _cleanup_resources(self):
        """Clean up any remaining resources - simplified"""
        pass
    
    async def discover_all_sitemaps(self) -> Dict[str, Any]:
        """Main discovery method - progressive enhancement approach with early success detection"""
        print("🚀 Starting Progressive Sitemap Discovery")
        print("=" * 60)
        start_time = time.time()
        
        # 🧱 BRICK 1: Basic Crawl4AI
        print("\n🧱 BRICK 1: Basic Crawl4AI")
        self._basic_crawl4ai_initial_count = len(self.discovered_urls)
        await self._try_basic_crawl4ai()
        
        # Early termination check
        if len(self.successfully_processed_sitemaps) == len(self.sitemap_urls):
            print("🏆 ALL SITEMAPS SUCCESSFULLY PROCESSED! Stopping early.")
            return self._generate_results(time.time() - start_time)
        
        # 🧱 BRICK 2: Crawl4AI + Stealth Mode
        print("\n🧱 BRICK 2: Crawl4AI + Stealth Mode")
        self._stealth_mode_initial_count = len(self.discovered_urls)
        await self._try_stealth_mode()
        
        # Early termination check
        if len(self.successfully_processed_sitemaps) == len(self.sitemap_urls):
            print("🏆 ALL SITEMAPS SUCCESSFULLY PROCESSED! Stopping early.")
            return self._generate_results(time.time() - start_time)
        
        # 🧱 BRICK 3: Crawl4AI + Stealth + Undetected Browser
        print("\n🧱 BRICK 3: Crawl4AI + Stealth + Undetected Browser")
        self._undetected_browser_initial_count = len(self.discovered_urls)
        await self._try_undetected_browser()
        
        # Early termination check
        if len(self.successfully_processed_sitemaps) == len(self.sitemap_urls):
            print("🏆 ALL SITEMAPS SUCCESSFULLY PROCESSED! Stopping early.")
            return self._generate_results(time.time() - start_time)
        
        # 🧱 BRICK 4: Crawl4AI + Stealth + Undetected + Proxy
        if self.config.proxy_url:
            print("\n🧱 BRICK 4: Crawl4AI + Stealth + Undetected + Proxy")
            self._proxy_enabled_initial_count = len(self.discovered_urls)
            await self._try_proxy_enabled()
            
            # Early termination check
            if len(self.successfully_processed_sitemaps) == len(self.sitemap_urls):
                print("🏆 ALL SITEMAPS SUCCESSFULLY PROCESSED! Stopping early.")
                return self._generate_results(time.time() - start_time)
        else:
            print("\n⏭️ BRICK 4: Skipped (no proxy configured)")
        
        # 🧱 BRICK 5: HTTP Fallback
        remaining_count = len(self.sitemap_urls) - len(self.successfully_processed_sitemaps)
        if remaining_count > 0:
            print(f"\n🧱 BRICK 5: HTTP Fallback ({remaining_count} sitemaps remaining)")
            self._http_fallback_initial_count = len(self.discovered_urls)
            await self._try_http_fallback()
        else:
            print("\n⏭️ BRICK 5: Skipped (all sitemaps already successful)")
        
        # Generate results
        end_time = time.time()
        results = self._generate_results(end_time - start_time)
        
        # Save discovered URLs
        await self._save_urls()
        
        print(f"\n✅ Discovery Complete: {len(self.discovered_urls)} URLs found")
        print(f"📊 Successfully processed: {len(self.successfully_processed_sitemaps)}/{len(self.sitemap_urls)} sitemaps")
        return results
    
    # =================================================================
    # BRICK 1: Basic Crawl4AI
    # =================================================================
    
    async def _try_basic_crawl4ai(self):
        """BRICK 1: Basic Crawl4AI without any enhancements"""
        print("  📋 Trying basic Crawl4AI...")
        
        # Basic browser config
        browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
        
        # Basic crawler config
        crawler_config = CrawlerRunConfig(
            page_timeout=5000,  # Very fast - 5 seconds max
            verbose=False,
            wait_for_images=False,
            delay_before_return_html=2.0,  # Allow time for J-SERVER bypass
            remove_overlay_elements=True
        )
        
        await self._test_browser_config("basic_crawl4ai", browser_config, crawler_config)
    
    # =================================================================
    # BRICK 2: Stealth Mode
    # =================================================================
    
    async def _try_stealth_mode(self):
        """BRICK 2: Crawl4AI + Stealth Mode"""
        print("  🥷 Trying stealth mode...")
        
        # Stealth browser config
        stealth_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-extensions",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-web-security",
            "--allow-running-insecure-content",
            "--disable-popup-blocking",
            "--disable-notifications",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive"
        }
        
        browser_config = BrowserConfig(
            headless=False,  # Better for stealth
            verbose=False,
            headers=headers,
            extra_args=stealth_args,
            enable_stealth=True
        )
        
        crawler_config = CrawlerRunConfig(
            page_timeout=5000,  # Very fast - 5 seconds max
            verbose=False,
            wait_for_images=False,
            delay_before_return_html=2.0,  # Allow time for J-SERVER bypass
            remove_overlay_elements=True
        )
        
        await self._test_browser_config("stealth_mode", browser_config, crawler_config)
    
    # =================================================================
    # BRICK 3: Undetected Browser
    # =================================================================
    
    async def _try_undetected_browser(self):
        """BRICK 3: Crawl4AI + Stealth + Undetected Browser"""
        print("  🎭 Trying undetected browser...")
        
        try:
            # Create undetected adapter
            adapter = UndetectedAdapter()
            
            # Create strategy with undetected adapter
            strategy = AsyncPlaywrightCrawlerStrategy(browser_adapter=adapter)
            
            # Minimal config for undetected browser
            browser_config = BrowserConfig(
                headless=False,
                verbose=False,
                enable_stealth=False  # Let undetected adapter handle stealth
            )
            
            crawler_config = CrawlerRunConfig(
                page_timeout=5000,  # Very fast - 5 seconds max
                verbose=False,
                wait_for_images=False,
                delay_before_return_html=0,  # No delay to prevent hanging
                remove_overlay_elements=True
            )
            
            await self._test_with_strategy("undetected_browser", strategy, crawler_config)
            
        except Exception as e:
            print(f"    ❌ Undetected browser failed: {e}")
            logger.error(f"Undetected browser error: {e}")
    
    # =================================================================
    # BRICK 4: Proxy Integration
    # =================================================================
    
    async def _try_proxy_enabled(self):
        """BRICK 4: Crawl4AI + Stealth + Undetected + Proxy"""
        print(f"  🌐 Trying proxy enabled...")
        
        try:
            # Create undetected adapter
            adapter = UndetectedAdapter()
            strategy = AsyncPlaywrightCrawlerStrategy(browser_adapter=adapter)
            
            # Proxy-enabled browser config
            browser_config = BrowserConfig(
                headless=False,
                verbose=False,
                proxy=self.config.proxy_url,
                enable_stealth=True
            )
            
            crawler_config = CrawlerRunConfig(
                page_timeout=5000,  # Very fast - 5 seconds max
                verbose=False,
                wait_for_images=False,
                delay_before_return_html=2.0,  # Allow time for J-SERVER bypass
                remove_overlay_elements=True
            )
            
            await self._test_with_strategy("proxy_enabled", strategy, crawler_config, browser_config)
            
        except Exception as e:
            print(f"    ❌ Proxy enabled failed: {e}")
            logger.error(f"Proxy enabled error: {e}")
    
    # =================================================================
    # BRICK 5: HTTP Fallback
    # =================================================================
    
    async def _try_http_fallback(self):
        """BRICK 5: Direct HTTP requests as final fallback with early success detection"""
        print("  🌐 Trying HTTP fallback...")
        
        self.stats["http_fallback"]["attempted"] = 0
        successful_sitemaps = set()
        
        # Create HTTP session with proxy if configured  
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",  # Removed br to avoid compression issues
            "DNT": "1",
            "Connection": "keep-alive"
        }
        
        try:
            # Create session with proxy in session params, not connector
            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            ) as session:
                
                for i, sitemap_url in enumerate(self.sitemap_urls, 1):
                    # Skip if this sitemap was already successfully processed by a previous method
                    if sitemap_url in self.successfully_processed_sitemaps:
                        print(f"    ⏭️  [{i}/{len(self.sitemap_urls)}] Skipping {sitemap_url} (already successful)")
                        continue
                    
                    print(f"    🔍 [{i}/{len(self.sitemap_urls)}] Testing: {sitemap_url}")
                    self.stats["http_fallback"]["attempted"] += 1
                    
                    success = await self._test_http_sitemap(session, sitemap_url)
                    if success:
                        self.stats["http_fallback"]["successful"] += 1
                        successful_sitemaps.add(sitemap_url)
                        self.successfully_processed_sitemaps.add(sitemap_url)
                        print(f"      ✅ Success! ({len(self.successfully_processed_sitemaps)}/{len(self.sitemap_urls)} total completed)")
                    else:
                        print(f"      ❌ Failed")
                
                if successful_sitemaps:
                    print(f"    🎉 HTTP_FALLBACK: Successfully processed {len(successful_sitemaps)} new sitemaps!")
                        
        except Exception as e:
            print(f"    ❌ HTTP fallback error: {e}")
            logger.error(f"HTTP fallback error: {e}")
    
    async def _test_http_sitemap(self, session: aiohttp.ClientSession, url: str) -> bool:
        """Test a single sitemap URL via HTTP with proper error handling"""
        try:
            # Use proxy in the request if configured
            proxy = self.config.proxy_url if self.config.proxy_url else None
            
            async with session.get(url, proxy=proxy, timeout=aiohttp.ClientTimeout(total=10)) as response:
                print(f"        📊 HTTP {response.status}")
                
                # Check for successful response
                if response.status == 200:
                    content = await response.text()
                    
                    # Remove the 100 character limit - that was also blocking real content!
                    # Only skip truly empty content
                    if len(content) < 10:
                        print(f"        ⚠️  Content too small ({len(content)} chars), likely error page")
                        return False
                    
                    # Check for common 404/error indicators (be more specific)
                    error_indicators = ["見つかりませんでした", "404 not found", "page not found", "error 404"]
                    content_lower = content.lower()
                    if any(indicator in content_lower for indicator in error_indicators):
                        print(f"        ⚠️  Error page detected, skipping")
                        return False
                        
                    urls_found = await self._parse_sitemap_content(content, url)
                    if urls_found > 0:
                        self.stats["http_fallback"]["urls_found"] += urls_found
                        return True
                elif response.status == 404:
                    print(f"        ❌ Sitemap not found (404)")
                elif response.status == 403:
                    print(f"        🚫 Access forbidden (403)")
                else:
                    print(f"        ❌ HTTP error {response.status}")
                        
        except asyncio.TimeoutError:
            print(f"        ⏰ HTTP timeout after 10 seconds")
        except Exception as e:
            print(f"        ❌ HTTP error: {str(e)[:50]}...")
            logger.debug(f"HTTP test failed for {url}: {e}")
            
        return False
    
    # =================================================================
    # Browser Testing Methods
    # =================================================================
    
    async def _test_browser_config(self, method_name: str, browser_config: BrowserConfig, crawler_config: CrawlerRunConfig):
        """Test a browser configuration against sitemap URLs with proper cleanup"""
        self.stats[method_name]["attempted"] = 0
        successful_sitemaps = set()
        
        try:
            # Use context manager for proper cleanup
            async with AsyncWebCrawler(config=browser_config) as crawler:
                for i, sitemap_url in enumerate(self.sitemap_urls, 1):
                    if self._shutdown_called:
                        break
                        
                    # Skip if this sitemap was already successfully processed by a previous method
                    if sitemap_url in self.successfully_processed_sitemaps:
                        print(f"    ⏭️  [{i}/{len(self.sitemap_urls)}] Skipping {sitemap_url} (already successful)")
                        continue
                    
                    print(f"    🔍 [{i}/{len(self.sitemap_urls)}] Testing: {sitemap_url}")
                    self.stats[method_name]["attempted"] += 1
                    
                    success = await self._test_single_sitemap(crawler, sitemap_url, crawler_config, method_name)
                    if success:
                        self.stats[method_name]["successful"] += 1
                        successful_sitemaps.add(sitemap_url)
                        self.successfully_processed_sitemaps.add(sitemap_url)
                        print(f"      ✅ Success! ({len(self.successfully_processed_sitemaps)}/{len(self.sitemap_urls)} total completed)")
                    else:
                        print(f"      ❌ Failed")
                
                # Update stats with URLs found by this method
                initial_count = getattr(self, f'_{method_name}_initial_count', len(self.discovered_urls))
                current_count = len(self.discovered_urls)
                self.stats[method_name]["urls_found"] = current_count - initial_count
                
                if successful_sitemaps:
                    print(f"    🎉 {method_name.upper()}: Successfully processed {len(successful_sitemaps)} new sitemaps!")
                        
        except Exception as e:
            print(f"    ❌ Browser config failed: {e}")
        
        # Force cleanup delay
        await asyncio.sleep(0.2)
    
    async def _test_with_strategy(self, method_name: str, strategy: AsyncPlaywrightCrawlerStrategy, 
                                 crawler_config: CrawlerRunConfig, browser_config: BrowserConfig = None):
        """Test with a specific crawler strategy with proper cleanup"""
        self.stats[method_name]["attempted"] = 0
        successful_sitemaps = set()
        
        try:
            # Use browser config if provided, otherwise create basic one
            if browser_config is None:
                browser_config = BrowserConfig(headless=False, verbose=False)
                
            # Use context manager for proper cleanup
            async with AsyncWebCrawler(config=browser_config, crawler_strategy=strategy) as crawler:
                for i, sitemap_url in enumerate(self.sitemap_urls, 1):
                    if self._shutdown_called:
                        break
                        
                    # Skip if this sitemap was already successfully processed by a previous method
                    if sitemap_url in self.successfully_processed_sitemaps:
                        print(f"    ⏭️  [{i}/{len(self.sitemap_urls)}] Skipping {sitemap_url} (already successful)")
                        continue
                    
                    print(f"    🔍 [{i}/{len(self.sitemap_urls)}] Testing: {sitemap_url}")
                    self.stats[method_name]["attempted"] += 1
                    
                    success = await self._test_single_sitemap(crawler, sitemap_url, crawler_config, method_name)
                    if success:
                        self.stats[method_name]["successful"] += 1
                        successful_sitemaps.add(sitemap_url)
                        self.successfully_processed_sitemaps.add(sitemap_url)
                        print(f"      ✅ Success! ({len(self.successfully_processed_sitemaps)}/{len(self.sitemap_urls)} total completed)")
                    else:
                        print(f"      ❌ Failed")
                
                # Update stats with URLs found by this method
                initial_count = getattr(self, f'_{method_name}_initial_count', len(self.discovered_urls))
                current_count = len(self.discovered_urls)
                self.stats[method_name]["urls_found"] = current_count - initial_count
                
                if successful_sitemaps:
                    print(f"    🎉 {method_name.upper()}: Successfully processed {len(successful_sitemaps)} new sitemaps!")
                        
        except Exception as e:
            print(f"    ❌ Strategy test failed: {e}")
        
        # Force cleanup delay
        await asyncio.sleep(0.2)
    
    async def _test_single_sitemap(self, crawler: AsyncWebCrawler, url: str, 
                                  config: CrawlerRunConfig, method_name: str) -> bool:
        """Test a single sitemap URL with the crawler"""
        try:
            # For Chiyoda, try to bypass J-SERVER directly with HTTP requests first
            if "chiyoda.lg.jp" in url:
                print(f"        🔄 Trying direct HTTP bypass for J-SERVER...")
                success = await self._try_direct_http_bypass(url, method_name)
                if success:
                    return True
            
            # Add shorter timeout to prevent hanging
            result_container = await asyncio.wait_for(
                crawler.arun(url=url, config=config), 
                timeout=10  # Max 10 seconds per sitemap
            )
            
            if result_container and len(result_container._results) > 0:
                result = result_container._results[0]
                if result.success and result.markdown:
                    
                    # Special handling for J-SERVER warning pages
                    if self._is_jserver_warning_page(result.markdown):
                        print(f"        ⚠️  J-SERVER warning page detected, trying alternative access...")
                        
                        # Try to access the page with Japanese language parameters to bypass translation
                        if "chiyoda.lg.jp" in url and not "?SLANG=ja" in url:
                            bypass_url = f"{url}?SLANG=ja&TLANG=ja&XMODE=0"
                            try:
                                bypass_result = await asyncio.wait_for(
                                    crawler.arun(url=bypass_url, config=config),
                                    timeout=10
                                )
                                if bypass_result and len(bypass_result._results) > 0:
                                    bypass_content = bypass_result._results[0]
                                    if bypass_content.success and bypass_content.markdown:
                                        if not self._is_jserver_warning_page(bypass_content.markdown):
                                            print(f"        ✅ J-SERVER bypass successful!")
                                            result = bypass_content  # Use the bypassed content
                                        else:
                                            print(f"        ⚠️  J-SERVER bypass still showing warning")
                            except Exception as e:
                                print(f"        ⚠️  J-SERVER bypass failed: {e}")
                    
                    # Quick validation - if content is too small, it's probably a 404 page
                    if len(result.markdown) < 100:
                        print(f"        ⚠️  Content too small ({len(result.markdown)} chars), likely 404/error page")
                        return False
                    
                    # Check for common 404/error indicators
                    error_indicators = ["見つかりませんでした", "404", "not found", "error", "エラー"]
                    content_lower = result.markdown.lower()
                    if any(indicator in content_lower for indicator in error_indicators):
                        print(f"        ⚠️  Error page detected, skipping")
                        return False
                    
                    urls_found = await self._parse_sitemap_content(result.markdown, url)
                    if urls_found > 0:
                        self.stats[method_name]["urls_found"] += urls_found
                        return True
                        
        except asyncio.TimeoutError:
            print(f"        ⏰ Timeout after 10 seconds")
            logger.debug(f"Timeout for {url}")
        except Exception as e:
            print(f"        ❌ Error: {str(e)[:50]}...")
            logger.debug(f"Single sitemap test failed for {url}: {e}")
            
        return False
    
    async def _try_direct_http_bypass(self, url: str, method_name: str) -> bool:
        """Try direct HTTP access to bypass J-SERVER popup"""
        try:
            import aiohttp
            
            # Try multiple bypass approaches
            bypass_urls = [
                url,  # Original URL
                f"{url}?SLANG=ja&TLANG=ja",  # Japanese mode
                url.replace("www.city.chiyoda.lg.jp", "city.chiyoda.lg.jp"),  # Without www
            ]
            
            timeout = aiohttp.ClientTimeout(total=10)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ja-JP,ja;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate'
            }
            
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                for bypass_url in bypass_urls:
                    try:
                        print(f"        🌐 Trying direct HTTP: {bypass_url}")
                        async with session.get(bypass_url) as response:
                            if response.status == 200:
                                content = await response.text()
                                
                                # Check if we bypassed the J-SERVER warning
                                if not self._is_jserver_warning_page(content):
                                    print(f"        ✅ Direct HTTP bypass successful!")
                                    urls_found = await self._parse_sitemap_content(content, bypass_url)
                                    if urls_found > 0:
                                        self.stats[method_name]["urls_found"] += urls_found
                                        return True
                                else:
                                    print(f"        ⚠️  Still getting J-SERVER warning via HTTP")
                            else:
                                print(f"        ❌ HTTP {response.status}: {bypass_url}")
                                
                    except Exception as e:
                        print(f"        ⚠️  HTTP error for {bypass_url}: {e}")
                        continue
                        
        except Exception as e:
            print(f"        ❌ Direct HTTP bypass failed: {e}")
            
        return False
    
    # =================================================================
    # Content Parsing
    # =================================================================
    
    def _is_jserver_warning_page(self, content: str) -> bool:
        """Check if content is a J-SERVER translation warning page"""
        warning_indicators = [
            "KODENSHA_080201_144032_WARNING",
            "J-SERVER Professional",
            "machine translation system",
            "MESS0001", "MESS0003",
            "translated by J-SERVER"
        ]
        return any(indicator in content for indicator in warning_indicators)
    
    async def _parse_sitemap_content(self, content: str, source_url: str) -> int:
        """Parse sitemap content and extract URLs with enhanced detection and debug output"""
        urls_found = 0
        total_candidates = 0
        
        print(f"        🔍 Content length: {len(content)} chars")
        print(f"        🌐 Source URL: {source_url}")
        
        # Debug: Show first 200 chars of content
        preview = content[:200].replace('\n', '\\n')
        print(f"        📝 Content preview: {preview}...")
        
        # Remove the stupid character limit - only skip truly empty content
        if len(content) < 10:
            print(f"        ⚠️  Content too small, skipping")
            return 0
        
        # Check for error page indicators (be more specific)
        error_indicators = ["見つかりませんでした", "page not found", "404 not found", "error 404"]
        content_lower = content.lower()
        has_error = any(indicator in content_lower for indicator in error_indicators)
        if has_error:
            print(f"        ⚠️  Error page detected, skipping")
            return 0
        
        # Special handling for robots.txt
        if source_url.endswith('robots.txt'):
            return await self._parse_robots_txt(content, source_url)
        
        # Debug: Check if this looks like HTML
        is_html = '<html' in content_lower or '<body' in content_lower or '<a' in content_lower
        is_xml = content.strip().startswith('<?xml') or '<urlset' in content_lower or '<sitemapindex' in content_lower
        
        print(f"        🔍 Content type detection: HTML={is_html}, XML={is_xml}")
        
        # Try XML parsing first with better error handling
        try:
            # Clean the XML content first
            cleaned_content = content.strip()
            
            # Handle BOM and encoding issues
            if cleaned_content.startswith('\ufeff'):
                cleaned_content = cleaned_content[1:]
            
            # Try multiple parsing approaches
            try:
                root = ET.fromstring(cleaned_content)
                xml_parsed = True
            except ET.ParseError:
                # Try with XML declaration removed
                if cleaned_content.startswith('<?xml'):
                    xml_end = cleaned_content.find('?>') + 2
                    cleaned_content = cleaned_content[xml_end:].strip()
                    root = ET.fromstring(cleaned_content)
                    xml_parsed = True
                else:
                    xml_parsed = False
                    raise ET.ParseError("Could not parse XML")
            
            if xml_parsed:
                print(f"        ✅ Valid XML detected")
                
                # Handle sitemap index with multiple namespace possibilities
                namespaces = [
                    "{http://www.sitemaps.org/schemas/sitemap/0.9}",
                    "",  # No namespace
                ]
                
                for ns in namespaces:
                    # Handle sitemap index
                    sitemap_elements = root.findall(f".//{ns}sitemap")
                    print(f"        🔗 Found {len(sitemap_elements)} sitemap index entries with namespace '{ns}'")
                    
                    for sitemap in sitemap_elements:
                        loc = sitemap.find(f"{ns}loc")
                        if loc is not None and loc.text:
                            url = loc.text.strip()
                            total_candidates += 1
                            print(f"        🔗 Processing nested sitemap: {url}")
                            if self._should_include_url(url):
                                # This is a nested sitemap - fetch and parse it recursively
                                try:
                                    nested_urls = await self._fetch_and_parse_nested_sitemap(url)
                                    urls_found += nested_urls
                                    print(f"        📄 Nested sitemap yielded {nested_urls} URLs")
                                except Exception as e:
                                    print(f"        ⚠️  Error processing nested sitemap {url}: {e}")
                            else:
                                print(f"        ⚠️  Filtered out sitemap: {url}")
                    
                    # Handle individual URLs
                    url_elements = root.findall(f".//{ns}url")
                    print(f"        📄 Found {len(url_elements)} individual URL entries with namespace '{ns}'")
                    
                    for url_elem in url_elements:
                        loc = url_elem.find(f"{ns}loc")
                        if loc is not None and loc.text:
                            url = loc.text.strip()
                            total_candidates += 1
                            # Skip self-referencing URLs
                            if url == source_url or url.endswith('sitemap.xml') or url.endswith('sitemap.html'):
                                print(f"        ⚠️  Skipping self-reference: {url}")
                                continue
                            if self._should_include_url(url):
                                self.discovered_urls.add(url)
                                urls_found += 1
                                print(f"        ✅ Added URL: {url}")
                            else:
                                print(f"        ⚠️  Filtered out URL: {url}")
                            
        except ET.ParseError as e:
            print(f"        ⚠️  XML parsing failed ({e}), trying HTML parsing...")
            # Try HTML parsing as fallback
            if is_html:
                try:
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Find all links
                    links = soup.find_all('a', href=True)
                    print(f"        🔗 Found {len(links)} HTML links")
                    
                    for link in links:
                        url = link['href']
                        total_candidates += 1
                        
                        # Handle relative URLs
                        if url.startswith('/'):
                            parsed_base = urlparse(source_url)
                            url = f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
                        elif url.startswith('http'):
                            pass  # Absolute URL
                        else:
                            print(f"        ⚠️  Skipping non-HTTP URL: {url}")
                            continue  # Skip other formats
                        
                        # Skip self-referencing URLs and sitemap URLs
                        if (url == source_url or 
                            url.endswith('sitemap.xml') or 
                            url.endswith('sitemap.html') or
                            'sitemap' in url.lower()):
                            print(f"        ⚠️  Skipping sitemap/self-reference: {url}")
                            continue
                            
                        if self._should_include_url(url):
                            self.discovered_urls.add(url)
                            urls_found += 1
                            print(f"        ✅ Added HTML URL: {url}")
                        else:
                            print(f"        ⚠️  Filtered out HTML link: {url}")
                            
                except Exception as e:
                    print(f"        ⚠️  HTML parsing failed: {e}")
            
            # Try regex extraction as additional backup
            if urls_found == 0 and 'http' in content:
                print(f"        🔍 Trying regex extraction as fallback...")
                # Use more restrictive regex to avoid malformed URLs
                urls = re.findall(r'https?://[^\s<>"\'()]+[^\s<>"\'().,!?;]', content)
                print(f"        🔗 Regex found {len(urls)} potential URLs")
                
                for url in urls:
                    total_candidates += 1
                    # Skip self-referencing URLs and sitemap URLs
                    if (url == source_url or 
                        url.endswith('sitemap.xml') or 
                        url.endswith('sitemap.html') or
                        'sitemap' in url.lower()):
                        print(f"        ⚠️  Skipping sitemap/self-reference: {url}")
                        continue
                        
                    if self._should_include_url(url):
                        self.discovered_urls.add(url)
                        urls_found += 1
                        print(f"        ✅ Added regex URL: {url}")
                    else:
                        print(f"        ⚠️  Filtered out regex URL: {url}")
        
        print(f"        📊 Final count - Candidates: {total_candidates}, Accepted: {urls_found}")
        if urls_found > 0:
            print(f"      📄 Found {urls_found} content URLs in sitemap")
            
        return urls_found
    
    async def _fetch_and_parse_nested_sitemap(self, sitemap_url: str) -> int:
        """Fetch and parse a nested sitemap from a sitemap index"""
        try:
            # Use HTTP to fetch the nested sitemap (faster than browser)
            proxy = self.config.proxy_url if self.config.proxy_url else None
            
            async with aiohttp.ClientSession() as session:
                async with session.get(sitemap_url, proxy=proxy, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Basic validation
                        if len(content) < 10:
                            return 0
                            
                        # Parse the nested sitemap content
                        urls_found = 0
                        
                        try:
                            # Clean the XML content
                            cleaned_content = content.strip()
                            if cleaned_content.startswith('\ufeff'):
                                cleaned_content = cleaned_content[1:]
                                
                            # Try XML parsing
                            root = ET.fromstring(cleaned_content)
                            
                            # Extract URLs from the nested sitemap
                            namespaces = [
                                "{http://www.sitemaps.org/schemas/sitemap/0.9}",
                                "",  # No namespace
                            ]
                            
                            for ns in namespaces:
                                for url_elem in root.findall(f".//{ns}url"):
                                    loc = url_elem.find(f"{ns}loc")
                                    if loc is not None and loc.text:
                                        url = loc.text.strip()
                                        if self._should_include_url(url):
                                            self.discovered_urls.add(url)
                                            urls_found += 1
                                            
                        except ET.ParseError:
                            # Fallback to regex if XML parsing fails
                            urls = re.findall(r'<loc[^>]*>([^<]+)</loc>', content, re.IGNORECASE)
                            for url in urls:
                                url = url.strip()
                                if self._should_include_url(url):
                                    self.discovered_urls.add(url)
                                    urls_found += 1
                                    
                        return urls_found
                    else:
                        print(f"        ⚠️  Failed to fetch nested sitemap {sitemap_url}: HTTP {response.status}")
                        return 0
                        
        except Exception as e:
            print(f"        ⚠️  Error fetching nested sitemap {sitemap_url}: {e}")
            return 0
    
    async def _parse_robots_txt(self, content: str, source_url: str) -> int:
        """Parse robots.txt for sitemap links"""
        urls_found = 0
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.lower().startswith('sitemap:'):
                sitemap_url = line[8:].strip()  # Remove 'Sitemap:' prefix
                if self._should_include_url(sitemap_url):
                    self.discovered_urls.add(sitemap_url)
                    urls_found += 1
                    print(f"        🗺️  Found sitemap in robots.txt: {sitemap_url}")
        
        return urls_found
    
    def _should_include_url(self, url: str) -> bool:
        """Check if URL should be included - more permissive for Chiyoda with debug output"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()
            
            # Skip empty or malformed URLs
            if not url or not parsed.scheme or not parsed.netloc:
                print(f"        ❌ Malformed URL: {url}")
                return False
            
            # Skip non-HTTP(S) URLs
            if parsed.scheme not in ['http', 'https']:
                print(f"        ❌ Non-HTTP URL: {url}")
                return False
            
            # Skip image and media files
            media_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.css', '.js', '.ico']
            if any(path.endswith(ext) for ext in media_extensions):
                print(f"        ❌ Media file: {url}")
                return False
            
            # If testing only Chiyoda, accept all Chiyoda URLs
            if hasattr(self, 'test_only_chiyoda') and self.test_only_chiyoda:
                # Accept all chiyoda.tokyo subdomains and paths
                if 'chiyoda.tokyo' in domain or 'chiyoda.lg.jp' in domain:
                    print(f"        ✅ Chiyoda URL accepted: {url}")
                    return True
                else:
                    print(f"        ❌ Non-Chiyoda URL (testing only Chiyoda): {url}")
                    return False
            
            # For regular processing, check domain match with subdomain support
            if parsed.netloc != self.domain:
                # For Chiyoda, allow related subdomains
                if self.domain == "www.city.chiyoda.lg.jp" and "chiyoda" in parsed.netloc:
                    print(f"        ✅ Chiyoda subdomain accepted: {url}")
                    return True
                else:
                    print(f"        ❌ Domain mismatch: {url}")
                    return False
                
            # Basic URL validation
            if not url.startswith(('http://', 'https://')):
                print(f"        ❌ Invalid scheme: {url}")
                return False
                
            # Skip obvious non-content URLs (less restrictive)
            skip_patterns = ['.css', '.js', '.zip', '.exe', '.dmg']
            if any(pattern in path for pattern in skip_patterns):
                print(f"        ❌ Skip pattern matched: {url}")
                return False
            
            # Skip very long URLs (likely malformed)
            if len(url) > 2000:
                print(f"        ❌ URL too long: {url}")
                return False
                
            print(f"        ✅ URL accepted: {url}")
            return True
            
        except Exception as e:
            print(f"        ❌ Error processing URL {url}: {e}")
            return False
    
    def _get_popup_bypass_js(self) -> str:
        """Enhanced popup bypass specifically for J-SERVER translation warnings"""
        return """
        console.log('🚀 Starting J-SERVER popup bypass...');
        
        // Function to wait and retry
        function waitAndRetry(fn, retries = 3) {
            return new Promise((resolve) => {
                function attempt(remaining) {
                    const result = fn();
                    if (result > 0 || remaining <= 0) {
                        resolve(result);
                    } else {
                        setTimeout(() => attempt(remaining - 1), 500);
                    }
                }
                attempt(retries);
            });
        }
        
        // Detect if this is a J-SERVER warning page
        function isJServerWarning() {
            const content = document.body.textContent || '';
            return content.includes('KODENSHA_080201_144032_WARNING') || 
                   content.includes('J-SERVER Professional') ||
                   content.includes('machine translation system');
        }
        
        // Dismiss popups and warnings
        function dismissElements() {
            let dismissed = 0;
            
            // J-SERVER specific selectors
            const selectors = [
                'input[type="button"][value*="OK"]',
                'input[type="button"][value*="はい"]', 
                'input[type="button"][value*="続行"]',
                'button:contains("OK")',
                'button:contains("Continue")',
                'button:contains("はい")',
                '[onclick*="close"]',
                '[onclick*="dismiss"]',
                '.modal button',
                '.popup button',
                '.dialog button'
            ];
            
            selectors.forEach(selector => {
                try {
                    document.querySelectorAll(selector).forEach(el => {
                        if (el.offsetParent !== null) {
                            console.log('🎯 Clicking:', selector);
                            el.click();
                            dismissed++;
                        }
                    });
                } catch (e) {}
            });
            
            // Hide overlay elements
            document.querySelectorAll('[style*="position: fixed"], .modal, .popup, .overlay').forEach(el => {
                el.style.display = 'none';
                dismissed++;
            });
            
            return dismissed;
        }
        
        // Main bypass logic
        (async () => {
            try {
                if (isJServerWarning()) {
                    console.log('⚠️ J-SERVER warning detected, attempting bypass...');
                    
                    // Try multiple rounds of dismissal
                    await waitAndRetry(dismissElements);
                    
                    // Press Enter to dismiss any remaining dialogs
                    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
                    
                    // Wait for page to load actual content
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    console.log('✅ J-SERVER bypass completed');
                } else {
                    // Standard popup bypass
                    dismissElements();
                    console.log('✅ Standard popup bypass completed');
                }
            } catch (error) {
                console.error('❌ Popup bypass error:', error);
            }
        })();
        """
    
    # =================================================================
    # Results and Output
    # =================================================================
    
    def _generate_results(self, duration: float) -> Dict[str, Any]:
        """Generate final results"""
        total_attempted = sum(stats["attempted"] for stats in self.stats.values())
        total_successful = sum(stats["successful"] for stats in self.stats.values())
        total_urls = sum(stats["urls_found"] for stats in self.stats.values())
        
        return {
            "summary": {
                "total_urls_discovered": len(self.discovered_urls),
                "total_sitemaps_attempted": total_attempted,
                "total_sitemaps_successful": total_successful,
                "success_rate": total_successful / total_attempted if total_attempted > 0 else 0,
                "duration_seconds": duration
            },
            "method_stats": self.stats,
            "discovered_urls": list(self.discovered_urls),
            "sitemap_locations_tested": self.sitemap_urls
        }
    
    async def _save_urls(self):
        """Save discovered URLs to file"""
        try:
            with open(self.config.output_file, 'w', encoding='utf-8') as f:
                for url in sorted(self.discovered_urls):
                    f.write(f"{url}\n")
            print(f"💾 Saved {len(self.discovered_urls)} URLs to {self.config.output_file}")
        except Exception as e:
            logger.error(f"Failed to save URLs: {e}")

# =================================================================
# Main Testing Function
# =================================================================

async def test_sitemap_discovery():
    """Test sitemap discovery on Chiyoda only for debugging"""
    
    test_sites = [
        {
            "name": "Chiyoda",
            "url": "https://www.city.chiyoda.lg.jp"
        }
    ]
    
    # Test with your proxy
    proxy_url = "http://brd-customer-hl_c4d84340-zone-testingdc:l1yptwrxrmbr@brd.superproxy.io:33335"
    
    print("🚀 Testing Chiyoda Sitemap Discovery - Debug Mode")
    print("=" * 70)
    
    for site in test_sites:
        print(f"\n📊 Testing {site['name']} ({site['url']})")
        print("-" * 50)
        
        try:
            config = SitemapConfig(
                base_url=site['url'],
                proxy_url=proxy_url,
                timeout=15,
                output_file=f"sitemap_urls_{site['name'].lower()}_debug.txt",
                verbose=True
            )
            
            discoverer = SitemapDiscovery(config)
            results = await discoverer.discover_all_sitemaps()
            
            print(f"\n📈 Results for {site['name']}:")
            print(f"  ✅ URLs discovered: {results['summary']['total_urls_discovered']}")
            print(f"  📊 Success rate: {results['summary']['success_rate']:.1%}")
            print(f"  ⏱️ Duration: {results['summary']['duration_seconds']:.1f}s")
            
            # Show method breakdown
            for method, stats in results['method_stats'].items():
                if stats['attempted'] > 0:
                    print(f"  {method}: {stats['successful']}/{stats['attempted']} successful, {stats['urls_found']} URLs")
                    
        except Exception as e:
            print(f"❌ Test failed for {site['name']}: {e}")
        
        # Force cleanup delay between sites
        await asyncio.sleep(1.0)  # Longer delay for better cleanup
        
        # Force garbage collection
        import gc
        gc.collect()

if __name__ == "__main__":
    try:
        # Suppress all warnings at runtime
        import warnings
        warnings.simplefilter("ignore")
        
        # Set better asyncio event loop policy for Windows
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        asyncio.run(test_sitemap_discovery())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Script error: {e}")
    finally:
        print("🧹 Cleanup complete")
        # Force cleanup of any remaining processes
        try:
            import gc
            gc.collect()
        except:
            pass
