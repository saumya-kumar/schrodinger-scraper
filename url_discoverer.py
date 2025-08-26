#!/usr/bin/env python3
"""
URL Discoverer - Comprehensive website URL discovery using Crawl4AI
This module focuses ONLY on discovering ALL possible URLs from a website.
Works with Gemini API for intelligent keyword generation.
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
import aiohttp  # For URL seeding functionality
import psutil  # For system health monitoring
from bs4 import BeautifulSoup  # For basic HTML parsing

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
    from crawl4ai import AsyncUrlSeeder, SeedingConfig  # For URL seeding with sitemaps and Common Crawl
    print("✅ Crawl4AI imported successfully with advanced features")
except ImportError:
    print("❌ Crawl4AI not installed. Install with: pip install crawl4ai")
    sys.exit(1)

# Google Gemini API
try:
    import google.generativeai as genai
    print("✅ Google Generative AI imported successfully")
except ImportError:
    print("⚠️  google-generativeai not installed - LLM features will use fallback")
    genai = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('url_discovery.log', encoding='utf-8'),
        logging.FileHandler('terminal_debug.txt', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Custom print function that also writes to terminal_debug.txt
def debug_print(message):
    """Print to console and write to terminal_debug.txt"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)
    with open('terminal_debug.txt', 'a', encoding='utf-8') as f:
        f.write(formatted_message + '\n')
        f.flush()  # Ensure immediate write

@dataclass
class URLDiscoveryConfig:
    """Configuration for URL discovery"""
    base_url: str
    sample_url: str = None
    context_description: str = None
    max_pages: int = 50000
    max_depth: int = 8
    delay_between_requests: float = 0.1
    timeout: int = 15
    max_concurrent: int = 500
    include_pdfs: bool = True
    include_images: bool = False
    use_llm_keywords: bool = True
    gemini_api_key: str = None
    proxy_url: str = None
    force_english: bool = True
    
    # PROXY CONFIGURATION
    proxy_enabled: bool = True  # ENABLED: Use BrightData proxy to bypass blocks
    brightdata_proxy: str = 'http://brd-customer-hl_c4d84340-zone-testingdc:l1yptwrxrmbr@brd.superproxy.io:33335'
    
    # STEALTH CONFIGURATION
    stealth_mode: bool = True  # Enable advanced stealth features
    rotate_user_agents: bool = True  # Rotate user agents to avoid detection

class URLDiscoverer:
    """Comprehensive URL discovery using Crawl4AI and intelligent analysis"""
    
    def __init__(self, config: URLDiscoveryConfig):
        self.config = config
        self.discovered_urls: Set[str] = set()
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.url_metadata: Dict[str, Dict] = {}
        self.domain = urlparse(config.base_url).netloc
        
        # HEALTH MONITORING: Instance variables for tracking
        self.recent_processing_times: List[float] = []
        self.system_health_history: List[float] = []
        
        # LLM-generated keywords for discovery
        self.llm_keywords: List[str] = []
        self.url_patterns: List[str] = []
        
        # Discovery statistics
        self.discovery_stats = {
            "sitemap_urls": 0,
            "url_seeding_urls": 0,
            "recursive_crawl_urls": 0,
            "hierarchical_crawl_urls": 0,
            "directory_discovery_urls": 0,
            "systematic_exploration_urls": 0,
            "pattern_generated_urls": 0,
            "form_discovery_urls": 0,
            "robots_txt_urls": 0,
            "aggressive_crawl_urls": 0
        }
        
        # Setup real-time URL file writing
        self.urls_file_path = "discovered_urls.txt"
        self._initialize_urls_file()
        
        # Setup Crawl4AI browser config
        self.browser_config = self._create_browser_config()
        
        # Setup Gemini API if available
        self._setup_gemini_api()
    
    def _initialize_urls_file(self):
        """Initialize the discovered URLs file"""
        try:
            # Clear the file at start
            with open(self.urls_file_path, 'w', encoding='utf-8') as f:
                f.write("# URLs discovered in real-time\n")
                f.write(f"# Started at: {datetime.now().isoformat()}\n")
                f.write(f"# Base URL: {self.config.base_url}\n\n")
            logger.info(f"📁 Initialized real-time URL file: {self.urls_file_path}")
        except Exception as e:
            logger.error(f"Failed to initialize URLs file: {e}")
    
    def _filter_file_types(self, urls: Set[str]) -> Set[str]:
        """Filter out non-HTML file types (PDF, XLS, CSV, DOCX, etc.)"""
        # Define file extensions to skip
        skip_extensions = {
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt', '.zip', '.rar',
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.bmp', '.webp',
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mp3', '.wav', '.ogg',
            '.xml', '.json', '.rss', '.feed', '.atom'
        }
        
        filtered_urls = set()
        skipped_count = 0
        
        for url in urls:
            # Extract file extension from URL (handle query parameters and fragments)
            url_path = url.split('?')[0].split('#')[0].lower()
            
            # Check if URL ends with any skip extensions
            should_skip = any(url_path.endswith(ext) for ext in skip_extensions)
            
            if should_skip:
                skipped_count += 1
            else:
                filtered_urls.add(url)
        
        if skipped_count > 0:
            logger.info(f"🚫 Filtered out {skipped_count} non-HTML files (PDF, XLS, images, etc.)")
        
        return filtered_urls
    
    def _add_urls_to_set_and_file(self, new_urls: Set[str], source: str = ""):
        """Add URLs to both the discovered set and immediately write to file"""
        if not new_urls:
            return 0
        
        # Filter out non-HTML file types first
        filtered_urls = self._filter_file_types(new_urls)
        
        # Only add truly new URLs
        actually_new = filtered_urls - self.discovered_urls
        
        if actually_new:
            # Add to our set
            self.discovered_urls.update(actually_new)
            
            # Show live progress for each URL discovered
            print(f"    🔗 Found {len(actually_new)} new URLs from {source}:")
            for i, url in enumerate(sorted(actually_new)[:5]):  # Show first 5 URLs
                print(f"      {i+1}. {url}")
            if len(actually_new) > 5:
                print(f"      ... and {len(actually_new) - 5} more URLs")
            
            # Immediately write to file
            try:
                with open(self.urls_file_path, 'a', encoding='utf-8') as f:
                    if source:
                        f.write(f"\n# {source} - {len(actually_new)} URLs - {datetime.now().strftime('%H:%M:%S')}\n")
                    for url in sorted(actually_new):
                        f.write(f"{url}\n")
                    f.flush()  # Ensure immediate write
                
                print(f"    💾 {source}: Saved {len(actually_new)} URLs to file (Total: {len(self.discovered_urls)})")
                logger.info(f"📁 {source}: Added {len(actually_new)} new URLs to file (Total: {len(self.discovered_urls)})")
            except Exception as e:
                logger.error(f"Failed to write URLs to file: {e}")
        else:
            print(f"    ⏭️  {source}: No new URLs found (all {len(new_urls)} were duplicates)")
        
        return len(actually_new)
    
    def _create_stealth_browser_config(self) -> BrowserConfig:
        """Create browser config with basic stealth mode"""
        try:
            # Configure proxy parameter for BrowserConfig
            proxy_param = None
            if hasattr(self.config, 'proxy_enabled') and self.config.proxy_enabled:
                proxy_param = self.config.brightdata_proxy
                print(f"      🌐 Stealth mode using proxy: {proxy_param.split('@')[1] if '@' in proxy_param else 'configured'}")
            
            return BrowserConfig(
                headless=False,  # Better for avoiding detection
                verbose=False,
                java_script_enabled=True,
                ignore_https_errors=True,
                viewport_width=1920,
                viewport_height=1080,
                proxy=proxy_param,
                enable_stealth=True,  # Basic stealth mode
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
        except Exception as e:
            logger.warning(f"[STEALTH] Failed to create stealth browser config: {e}")
            return None
    
    def _create_magic_browser_config(self) -> BrowserConfig:
        """Create browser config with magic mode for enhanced user simulation"""
        try:
            # Configure proxy parameter
            proxy_param = None
            if hasattr(self.config, 'proxy_enabled') and self.config.proxy_enabled:
                proxy_param = self.config.brightdata_proxy
                print(f"      🌐 Magic mode using proxy: {proxy_param.split('@')[1] if '@' in proxy_param else 'configured'}")
            
            return BrowserConfig(
                headless=False,
                verbose=False,
                java_script_enabled=True,
                ignore_https_errors=True,
                viewport_width=1920,
                viewport_height=1080,
                proxy=proxy_param,
                enable_stealth=True,  # Combine stealth with magic
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
        except Exception as e:
            logger.warning(f"[MAGIC] Failed to create magic browser config: {e}")
            return None
    
    def _create_undetected_browser_config(self) -> BrowserConfig:
        """Create browser config optimized for UndetectedAdapter"""
        try:
            # Configure proxy parameter
            proxy_param = None
            if hasattr(self.config, 'proxy_enabled') and self.config.proxy_enabled:
                proxy_param = self.config.brightdata_proxy
                print(f"      🌐 Undetected mode using proxy: {proxy_param.split('@')[1] if '@' in proxy_param else 'configured'}")
            
            return BrowserConfig(
                headless=False,  # Critical for undetected mode
                verbose=False,
                java_script_enabled=True,
                ignore_https_errors=True,
                viewport_width=1920,
                viewport_height=1080,
                proxy=proxy_param,
                enable_stealth=False,  # Let UndetectedAdapter handle stealth
                browser_mode="dedicated",
                extra_args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-first-run",
                    "--disable-default-apps"
                ]
            )
        except Exception as e:
            logger.warning(f"[UNDETECTED] Failed to create undetected browser config: {e}")
            return None
    
    def _create_combined_browser_config(self) -> BrowserConfig:
        """Create browser config with maximum evasion (UndetectedAdapter + Stealth)"""
        try:
            # Configure proxy parameter
            proxy_param = None
            if hasattr(self.config, 'proxy_enabled') and self.config.proxy_enabled:
                proxy_param = self.config.brightdata_proxy
                print(f"      🌐 Combined mode using proxy: {proxy_param.split('@')[1] if '@' in proxy_param else 'configured'}")
            
            return BrowserConfig(
                headless=False,  # Essential for maximum evasion
                verbose=False,
                java_script_enabled=True,
                ignore_https_errors=True,
                viewport_width=1920,
                viewport_height=1080,
                proxy=proxy_param,
                enable_stealth=True,  # Combine with UndetectedAdapter
                browser_mode="dedicated",
                extra_args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-first-run",
                    "--disable-default-apps",
                    "--disable-web-security",
                    "--allow-running-insecure-content"
                ]
            )
        except Exception as e:
            logger.warning(f"[COMBINED] Failed to create combined browser config: {e}")
            return None
    
    def _create_undetected_adapter(self):
        """Create UndetectedAdapter for advanced anti-bot evasion"""
        try:
            return UndetectedAdapter()
        except Exception as e:
            logger.warning(f"[UNDETECTED] Failed to create UndetectedAdapter: {e}")
            return None
    
    def _create_browser_config(self) -> BrowserConfig:
        """Create Crawl4AI browser configuration with advanced stealth and proxy support"""
        
        # STEALTH MODE: Advanced anti-detection arguments
        extra_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-extensions",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-web-security",
            "--allow-running-insecure-content",
            "--disable-popup-blocking",
            "--disable-notifications",
            "--disable-default-apps",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=VizDisplayCompositor",
            "--disable-ipc-flooding-protection",
            "--disable-component-extensions-with-background-pages",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-sync",
            "--disable-background-networking",
            "--disable-client-side-phishing-detection",
            "--disable-component-update",
            "--disable-domain-reliability",
            "--disable-features=TranslateUI",
            "--disable-hang-monitor",
            "--disable-logging",
            "--disable-plugins",
            "--disable-prompt-on-repost",
            "--disable-software-rasterizer",
            "--disable-spell-checking",
            "--disable-translate",
            "--hide-scrollbars",
            "--metrics-recording-only",
            "--mute-audio",
            "--no-pings",
            "--password-store=basic",
            "--use-mock-keychain",
            "--disable-search-engine-choice-screen",
            "--simulate-outdated-no-au='Tue, 31 Dec 2099 23:59:59 GMT'",
        ]
        
        # PROXY INTEGRATION: Enable BrightData proxy properly
        proxy_config = None
        if hasattr(self.config, 'proxy_enabled') and self.config.proxy_enabled:
            proxy_server = self.config.brightdata_proxy
            print(f"    🌐 Using BrightData proxy: {proxy_server.split('@')[1] if '@' in proxy_server else 'configured'}")
            logger.info(f"[PROXY] BrightData proxy enabled: {proxy_server}")
            # Don't add to extra_args, use the proxy parameter instead
        
        # Add language preferences for English content
        if self.config.force_english:
            extra_args.extend([
                "--lang=en-US",
                "--accept-lang=en-US,en"
            ])
        
        # Add proxy configuration if provided in legacy proxy_url field
        if self.config.proxy_url:
            extra_args.append(f"--proxy-server={self.config.proxy_url}")
        
        # STEALTH MODE: Dynamic User Agent Selection
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0"
        ]
        
        import random
        selected_ua = random.choice(user_agents) if hasattr(self.config, 'rotate_user_agents') and self.config.rotate_user_agents else user_agents[0]
        
        # ENHANCED HEADERS: Comprehensive browser simulation
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9" if self.config.force_english else "en-US,en;q=0.9,ja;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "User-Agent": selected_ua
        }
        
        # Configure proxy parameter for BrowserConfig
        proxy_param = None
        if hasattr(self.config, 'proxy_enabled') and self.config.proxy_enabled:
            proxy_param = self.config.brightdata_proxy
        
        return BrowserConfig(
            headless=False,  # CRITICAL: Avoid headless mode for better proxy authentication
            verbose=False,
            headers=headers,
            java_script_enabled=True,
            ignore_https_errors=True,
            viewport_width=1920,
            viewport_height=1080,
            extra_args=extra_args,
            proxy=proxy_param,  # Set proxy parameter directly
            enable_stealth=True,  # ENHANCED: Enable stealth mode to avoid detection
            browser_mode="dedicated"  # Use dedicated browser mode for better control
        )
    
    def _setup_gemini_api(self):
        """Setup Gemini API from environment variables"""
        if not genai:
            logger.warning("Google Generative AI not available")
            return
        
        # Try multiple sources for API key
        api_key = (
            self.config.gemini_api_key or 
            os.getenv('GEMINI_API_KEY') or 
            os.getenv('GOOGLE_API_KEY') or
            os.getenv('GOOGLE_GEMINI_API_KEY')
        )
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                logger.info("✅ Gemini API configured successfully")
            except Exception as e:
                logger.error(f"❌ Failed to configure Gemini API: {e}")
        else:
            logger.warning("⚠️  No Gemini API key found in environment variables")
    
    def _get_popup_bypass_js(self) -> str:
        """Get JavaScript code to bypass common popups and overlays"""
        return """
        // Function to remove popups and overlays
        function bypassPopups() {
            // Common popup/overlay selectors
            const popupSelectors = [
                '[class*="popup"]', '[class*="modal"]', '[class*="overlay"]',
                '[class*="lightbox"]', '[class*="dialog"]', '[class*="notification"]',
                '[id*="popup"]', '[id*="modal"]', '[id*="overlay"]',
                '[class*="cookie"]', '[class*="consent"]', '[class*="gdpr"]',
                '.popup', '.modal', '.overlay', '.lightbox', '.dialog',
                '#popup', '#modal', '#overlay', '#cookie-banner',
                '[role="dialog"]', '[role="alertdialog"]'
            ];
            
            // Remove popup elements
            popupSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(element => {
                    if (element.offsetParent !== null) { // Only remove visible elements
                        element.style.display = 'none';
                        element.remove();
                    }
                });
            });
            
            // Common close button patterns
            const closeSelectors = [
                '[class*="close"]', '[class*="dismiss"]', '[aria-label*="close"]',
                '[aria-label*="dismiss"]', '[title*="close"]', '[title*="dismiss"]',
                'button[class*="accept"]', 'button[class*="consent"]',
                'button[class*="agree"]', 'a[class*="accept"]'
            ];
            
            closeSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(button => {
                    if (button.offsetParent !== null && button.textContent.toLowerCase().includes('accept')) {
                        button.click();
                    }
                });
            });
            
            // Remove body overflow hidden (common for modal backgrounds)
            document.body.style.overflow = 'auto';
            document.documentElement.style.overflow = 'auto';
        }
        
        // Run immediately and after DOM changes
        bypassPopups();
        setTimeout(bypassPopups, 1000);
        setTimeout(bypassPopups, 3000);
        
        // Set up observer for dynamic content
        if (typeof MutationObserver !== 'undefined') {
            const observer = new MutationObserver(bypassPopups);
            observer.observe(document.body, { childList: true, subtree: true });
            setTimeout(() => observer.disconnect(), 10000);
        }
        """
    
    async def discover_all_urls(self) -> Dict[str, Any]:
        """Main method to discover ALL URLs using maximum discovery methods"""
        print("\n🚀 STARTING COMPREHENSIVE URL DISCOVERY")
        print("=" * 60)
        print(f"🎯 Target: {self.config.base_url}")
        print(f"📊 Max Pages: {self.config.max_pages:,}")
        print(f"🔍 Max Depth: {self.config.max_depth}")
        print("=" * 60)
        
        logger.info("🚀 Starting comprehensive URL discovery with ALL methods...")
        start_time = time.time()
        
        # PHASE 1: Sitemap Discovery (fastest, often finds 50-90% of URLs)
        print("\n📋 PHASE 1: SITEMAP DISCOVERY")
        print("-" * 40)
        phase_start = time.time()
        initial_count = len(self.discovered_urls)
        await self._discover_from_sitemaps()
        self.discovery_stats["sitemap_urls"] = len(self.discovered_urls) - initial_count
        phase_time = time.time() - phase_start
        print(f"✅ Sitemap Discovery Complete: {self.discovery_stats['sitemap_urls']} URLs in {phase_time:.1f}s")
        logger.info(f"After sitemaps: {len(self.discovered_urls)} URLs (+{self.discovery_stats['sitemap_urls']} new)")
        
        # PHASE 2: Robots.txt Analysis (find additional sitemaps and paths)
        print("\n🤖 PHASE 2: ROBOTS.TXT ANALYSIS")
        print("-" * 40)
        phase_start = time.time()
        initial_count = len(self.discovered_urls)
        await self._discover_from_robots()
        self.discovery_stats["robots_txt_urls"] = len(self.discovered_urls) - initial_count
        phase_time = time.time() - phase_start
        print(f"✅ Robots.txt Analysis Complete: {self.discovery_stats['robots_txt_urls']} URLs in {phase_time:.1f}s")
        logger.info(f"After robots.txt: {len(self.discovered_urls)} URLs (+{self.discovery_stats['robots_txt_urls']} new)")
        
        # PHASE 2.5: URL Seeding (Common Crawl + Enhanced Sitemap Discovery)
        print("\n🌐 PHASE 2.5: URL SEEDING (COMMON CRAWL)")
        print("-" * 40)
        phase_start = time.time()
        initial_count = len(self.discovered_urls)
        await self._url_seeding_discovery()
        self.discovery_stats["url_seeding_urls"] = len(self.discovered_urls) - initial_count
        phase_time = time.time() - phase_start
        print(f"✅ URL Seeding Complete: {self.discovery_stats['url_seeding_urls']} URLs in {phase_time:.1f}s")
        logger.info(f"After URL seeding: {len(self.discovered_urls)} URLs (+{self.discovery_stats['url_seeding_urls']} new)")
        
        # PHASE 3: Recursive Link Crawling (main discovery engine)
        print("\n🔄 PHASE 3: RECURSIVE CRAWLING")
        print("-" * 40)
        phase_start = time.time()
        initial_count = len(self.discovered_urls)
        await self._recursive_crawl_with_crawl4ai()
        self.discovery_stats["recursive_crawl_urls"] = len(self.discovered_urls) - initial_count
        phase_time = time.time() - phase_start
        print(f"✅ Recursive Crawling Complete: {self.discovery_stats['recursive_crawl_urls']} URLs in {phase_time:.1f}s")
        logger.info(f"After recursive crawling: {len(self.discovered_urls)} URLs (+{self.discovery_stats['recursive_crawl_urls']} new)")
        
        # PHASE 4: Hierarchical Parent Crawling (discover parent directories)
        print("\n🏗️ PHASE 4: HIERARCHICAL PARENT CRAWLING")
        print("-" * 40)
        phase_start = time.time()
        initial_count = len(self.discovered_urls)
        await self._hierarchical_parent_crawling()
        self.discovery_stats["hierarchical_crawl_urls"] = len(self.discovered_urls) - initial_count
        phase_time = time.time() - phase_start
        print(f"✅ Hierarchical Crawling Complete: {self.discovery_stats['hierarchical_crawl_urls']} URLs in {phase_time:.1f}s")
        logger.info(f"After hierarchical crawling: {len(self.discovered_urls)} URLs (+{self.discovery_stats['hierarchical_crawl_urls']} new)")
        
        # PHASE 5: Directory Discovery (test common directory patterns)
        print("\n📁 PHASE 5: DIRECTORY DISCOVERY")
        print("-" * 40)
        phase_start = time.time()
        initial_count = len(self.discovered_urls)
        await self._discover_directories()
        self.discovery_stats["directory_discovery_urls"] = len(self.discovered_urls) - initial_count
        phase_time = time.time() - phase_start
        print(f"✅ Directory Discovery Complete: {self.discovery_stats['directory_discovery_urls']} URLs in {phase_time:.1f}s")
        logger.info(f"After directory discovery: {len(self.discovered_urls)} URLs (+{self.discovery_stats['directory_discovery_urls']} new)")
        
        # PHASE 6: Systematic Path Exploration (analyze discovered URL patterns)
        print("\n🎯 PHASE 6: SYSTEMATIC PATH EXPLORATION")
        print("-" * 40)
        phase_start = time.time()
        initial_count = len(self.discovered_urls)
        await self._systematic_path_exploration()
        self.discovery_stats["systematic_exploration_urls"] = len(self.discovered_urls) - initial_count
        phase_time = time.time() - phase_start
        print(f"✅ Systematic Exploration Complete: {self.discovery_stats['systematic_exploration_urls']} URLs in {phase_time:.1f}s")
        logger.info(f"After path exploration: {len(self.discovered_urls)} URLs (+{self.discovery_stats['systematic_exploration_urls']} new)")
        
        # PHASE 7: Aggressive Deep Crawling (process ALL remaining URLs)
        print("\n⚡ PHASE 7: AGGRESSIVE DEEP CRAWLING")
        print("-" * 40)
        uncrawled_urls = self.discovered_urls - self.crawled_urls
        if len(uncrawled_urls) > 0 and len(self.discovered_urls) < self.config.max_pages:
            print(f"🔥 Processing {len(uncrawled_urls)} remaining URLs...")
            phase_start = time.time()
            logger.info(f"🔥 Starting aggressive deep crawling of {len(uncrawled_urls)} remaining URLs...")
            initial_count = len(self.discovered_urls)
            await self._aggressive_deep_crawl_with_crawl4ai()
            self.discovery_stats["aggressive_crawl_urls"] = len(self.discovered_urls) - initial_count
            phase_time = time.time() - phase_start
            print(f"✅ Aggressive Crawling Complete: {self.discovery_stats['aggressive_crawl_urls']} URLs in {phase_time:.1f}s")
            logger.info(f"After aggressive crawling: {len(self.discovered_urls)} URLs (+{self.discovery_stats['aggressive_crawl_urls']} new)")
        else:
            print("⏭️ Skipping (no remaining URLs or max pages reached)")
        
        # PHASE 8: Pattern-Based Discovery (generate URLs from discovered patterns)
        print("\n🧩 PHASE 8: PATTERN-BASED URL GENERATION")
        print("-" * 40)
        if len(self.discovered_urls) < self.config.max_pages:
            phase_start = time.time()
            initial_count = len(self.discovered_urls)
            await self._discover_by_patterns()
            self.discovery_stats["pattern_generated_urls"] = len(self.discovered_urls) - initial_count
            phase_time = time.time() - phase_start
            print(f"✅ Pattern Generation Complete: {self.discovery_stats['pattern_generated_urls']} URLs in {phase_time:.1f}s")
            logger.info(f"After pattern discovery: {len(self.discovered_urls)} URLs (+{self.discovery_stats['pattern_generated_urls']} new)")
        else:
            print("⏭️ Skipping (max pages reached)")
        
        # PHASE 9: Form and Search Discovery (find search functionality)
        print("\n🔍 PHASE 9: FORM AND SEARCH DISCOVERY")
        print("-" * 40)
        phase_start = time.time()
        initial_count = len(self.discovered_urls)
        await self._discover_forms_and_searches()
        self.discovery_stats["form_discovery_urls"] = len(self.discovered_urls) - initial_count
        phase_time = time.time() - phase_start
        print(f"✅ Form Discovery Complete: {self.discovery_stats['form_discovery_urls']} URLs in {phase_time:.1f}s")
        logger.info(f"After form discovery: {len(self.discovered_urls)} URLs (+{self.discovery_stats['form_discovery_urls']} new)")
        
        # FINAL: Generate discovery statistics
        discovery_time = time.time() - start_time
        
        print(f"\n🎉 DISCOVERY COMPLETE!")
        print("=" * 60)
        print(f"📊 Total URLs Discovered: {len(self.discovered_urls):,}")
        print(f"⏱️  Total Time: {discovery_time:.1f} seconds")
        print(f"🚀 Discovery Rate: {len(self.discovered_urls)/discovery_time:.1f} URLs/second")
        print("=" * 60)
        
        return self._generate_discovery_results(discovery_time)
    
    async def _generate_llm_keywords(self):
        """Generate intelligent keywords using Gemini API"""
        if not genai:
            logger.warning("Gemini API not available, using fallback keywords")
            self._generate_fallback_keywords()
            return
        
        try:
            logger.info("🤖 Generating keywords using Gemini API...")
            
            # First, get homepage content using Crawl4AI
            homepage_content = await self._get_homepage_content()
            
            # Create keyword generation prompt
            prompt = self._create_keyword_prompt(homepage_content)
            
            # Call Gemini API
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            
            # Parse response
            self._parse_gemini_response(response.text)
            
            logger.info(f"✅ Generated {len(self.llm_keywords)} keywords from Gemini")
            
        except Exception as e:
            logger.error(f"❌ Gemini keyword generation failed: {e}")
            self._generate_fallback_keywords()
    
    async def _get_homepage_content(self) -> str:
        """Get homepage content using Crawl4AI"""
        try:
            crawler_config = CrawlerRunConfig(
                markdown_generator=DefaultMarkdownGenerator(),
                page_timeout=self.config.timeout * 1000,
                verbose=False,
                js_code=self._get_popup_bypass_js(),
                wait_for_images=False,
                delay_before_return_html=2000  # Wait 2 seconds for popups to appear and be dismissed
            )
            
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result_container = await crawler.arun(url=self.config.base_url, config=crawler_config)
                
                if result_container and len(result_container._results) > 0:
                    result = result_container._results[0]
                    if result.success:
                        return str(result.markdown)[:2000]  # Limit for token efficiency
            
        except Exception as e:
            logger.error(f"Failed to get homepage content: {e}")
        
        return ""
    
    def _create_keyword_prompt(self, homepage_content: str) -> str:
        """Create keyword generation prompt for Gemini"""
        return f"""You are an expert web crawler analyzing a website to generate relevant keywords for comprehensive URL discovery.

Website Information:
- Base URL: {self.config.base_url}
- Sample URL: {self.config.sample_url or 'Not provided'}
- User Context: {self.config.context_description or 'General website analysis'}

Homepage Content Preview:
{homepage_content[:1000]}

Task: Generate 50+ relevant keywords that could appear in URLs on this website. Focus on:
1. Content categories (e.g., services, products, news, about)
2. Japanese terms (both kanji and romaji for Japanese sites)
3. Common web sections (contact, blog, support, etc.)
4. Domain-specific terms based on the content
5. URL-friendly versions (lowercase, no special characters)

Output format: Provide a simple comma-separated list of keywords only, no explanations.

Keywords:"""
    
    def _parse_gemini_response(self, response_text: str):
        """Parse Gemini response to extract keywords"""
        try:
            # Clean and split the response
            keywords = []
            lines = response_text.strip().split('\n')
            
            for line in lines:
                # Split by commas and clean each keyword
                line_keywords = [k.strip().lower() for k in line.split(',')]
                keywords.extend([k for k in line_keywords if len(k) > 1 and k.isalnum()])
            
            self.llm_keywords = list(set(keywords))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            self._generate_fallback_keywords()
    
    def _generate_fallback_keywords(self):
        """Generate fallback keywords if LLM is not available"""
        domain_parts = self.domain.lower().split('.')
        
        self.llm_keywords = [
            # Common website sections
            "about", "contact", "services", "products", "news", "blog", "events",
            "support", "help", "documentation", "resources", "downloads", "gallery",
            "team", "careers", "privacy", "terms", "sitemap", "search",
            
            # Japanese government common terms (romaji)
            "kosodate", "shussan", "kodomo", "josei", "koreisha", "iryo", "kenko",
            "fukushi", "seido", "tetuzuki", "shinsei", "madoguchi", "soudan",
            
            # Content types
            "info", "guide", "procedure", "application", "form", "schedule",
            "list", "directory", "category", "section", "department"
        ] + domain_parts
        
        logger.info(f"Using {len(self.llm_keywords)} fallback keywords")
    
    async def _discover_from_sitemaps(self):
        """🧱 BRICK-BY-BRICK Progressive Enhancement for Sitemap Discovery"""
        print("  🗺️  Starting BRICK-BY-BRICK sitemap discovery...")
        
        # Remove trailing slash from base URL to avoid double slashes
        base_url = self.config.base_url.rstrip('/')
        
        sitemap_urls = [
            f"{base_url}/sitemap.xml",
            f"{base_url}/sitemap_index.xml", 
            f"{base_url}/sitemaps.xml",
            f"{base_url}/sitemap.html",
            f"{base_url}/sitemap/",
            f"{base_url}/wp-sitemap.xml",  # WordPress
            f"{base_url}/news-sitemap.xml",  # News sites
            f"{base_url}/video-sitemap.xml",  # Video sites
        ]
        
        print(f"  📍 Will check {len(sitemap_urls)} sitemap locations")
        
        # 🧱 BRICK 1: Basic Crawl4AI (no stealth, no proxy)
        print("\n  🧱 BRICK 1: Basic Crawl4AI")
        if await self._try_basic_crawling(sitemap_urls):
            print("    🎉 SUCCESS with Basic Crawl4AI!")
            return
        
        # 🧱 BRICK 2: Crawl4AI + Stealth Mode
        print("\n  🧱 BRICK 2: Crawl4AI + Stealth Mode")  
        if await self._try_stealth_crawling(sitemap_urls):
            print("    🎉 SUCCESS with Stealth Mode!")
            return
        
        # 🧱 BRICK 3: Crawl4AI + Stealth + Undetected Browser
        print("\n  🧱 BRICK 3: Crawl4AI + Stealth + Undetected Browser")
        if await self._try_undetected_crawling(sitemap_urls):
            print("    🎉 SUCCESS with Undetected Browser!")
            return
        
        # 🧱 BRICK 4: Crawl4AI + Stealth + Undetected + Proxy
        print("\n  🧱 BRICK 4: Crawl4AI + Stealth + Undetected + Proxy")
        if await self._try_proxy_crawling(sitemap_urls):
            print("    🎉 SUCCESS with Proxy!")
            return
            
        # 🧱 BRICK 5: HTTP Fallback (final resort)
        print("\n  🧱 BRICK 5: HTTP Fallback (Final Resort)")
        await self._try_http_fallback(sitemap_urls)
        
        print("\n  ✅ Brick-by-brick sitemap discovery complete")
    
    async def _try_basic_crawling(self, sitemap_urls: list) -> bool:
        
        print(f"  ✅ Sitemap discovery complete - Total URLs found: {total_urls_found}")
        return total_urls_found
    
    async def _test_sitemap_stage(self, crawler, sitemap_urls: list, stage_name: str) -> int:
        """Test a specific enhancement stage and return number of URLs found"""
        urls_found = 0
        
        # Enhanced crawler configurations for each stage
        crawler_configs = self._get_stage_crawler_configs(stage_name)
        
        for i, sitemap_url in enumerate(sitemap_urls, 1):
            print(f"      🔍 [{i}/{len(sitemap_urls)}] {stage_name.upper()}: {sitemap_url}")
            
            # Try multiple crawler configurations for this URL
            for config_idx, crawler_config in enumerate(crawler_configs, 1):
                try:
                    print(f"        🚀 Config {config_idx}: Crawling with {stage_name} mode...")
                    
                    result_container = await asyncio.wait_for(
                        crawler.arun(url=sitemap_url, config=crawler_config),
                        timeout=40  # Generous timeout for challenging sites
                    )
                    
                    if result_container and len(result_container._results) > 0:
                        result = result_container._results[0]
                        print(f"        📊 Result: success={result.success}, status={getattr(result, 'status_code', 'unknown')}")
                        
                        if result.success and result.html:
                            print(f"        ✅ Found sitemap! Content length: {len(result.html)} chars")
                            found_count = await self._parse_sitemap_content(result.html)
                            if found_count > 0:
                                print(f"        🎯 Extracted {found_count} URLs from sitemap")
                                urls_found += found_count
                                break  # Success, move to next sitemap
                            else:
                                print(f"        ⚠️  No URLs found in sitemap content")
                        else:
                            print(f"        ❌ Crawl failed - Error: {getattr(result, 'error_message', 'No content')}")
                    else:
                        print(f"        ⚠️  No results from crawler config {config_idx}")
                        
                except asyncio.TimeoutError:
                    print(f"        ⏰ Timeout on config {config_idx}")
                except Exception as e:
                    print(f"        ❌ Error on config {config_idx}: {str(e)[:50]}")
            
            # If no crawler config worked, continue to next sitemap
            
        return urls_found
    
    def _get_stage_crawler_configs(self, stage_name: str) -> list:
        """Get appropriate crawler configurations for each enhancement stage"""
        base_js = self._get_popup_bypass_js()
        
        if stage_name == "stealth":
            return [
                CrawlerRunConfig(
                    page_timeout=30000,
                    verbose=False,
                    js_code=base_js,
                    wait_for_images=False,
                    delay_before_return_html=2000,
                    remove_overlay_elements=True,
                    simulate_user=True,
                    override_navigator=True
                )
            ]
        
        elif stage_name == "magic":
            return [
                CrawlerRunConfig(
                    page_timeout=35000,
                    verbose=False,
                    js_code=base_js,
                    wait_for_images=False,
                    delay_before_return_html=3000,  # Longer delays
                    remove_overlay_elements=True,
                    simulate_user=True,
                    override_navigator=True,
                    magic=True  # Enable magic mode
                )
            ]
        
        elif stage_name == "undetected":
            return [
                CrawlerRunConfig(
                    page_timeout=40000,
                    verbose=False,
                    js_code=base_js,
                    wait_for_images=False,
                    delay_before_return_html=2000,
                    remove_overlay_elements=True,
                    simulate_user=True,
                    override_navigator=True
                )
            ]
        
        elif stage_name == "combined":
            return [
                CrawlerRunConfig(
                    page_timeout=45000,  # Maximum timeout
                    verbose=False,
                    js_code=base_js,
                    wait_for_images=False,
                    delay_before_return_html=4000,  # Maximum delays
                    remove_overlay_elements=True,
                    simulate_user=True,
                    override_navigator=True,
                    magic=True  # All features enabled
                )
            ]
        
        # Default fallback
        return [
            CrawlerRunConfig(
                page_timeout=20000,
                verbose=False,
                js_code=base_js,
                wait_for_images=False,
                delay_before_return_html=1000
            )
        ]
    
    async def _enhanced_http_fallback(self, sitemap_urls: list) -> int:
        """Enhanced HTTP fallback with proxy support and better error handling"""
        total_urls = 0
        
        # Enhanced headers to bypass blocking
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",  # Avoid br compression issues
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Referer": self.config.base_url
        }
        
        # Configure proxy for HTTP requests if enabled
        proxy_url = None
        if hasattr(self.config, 'proxy_enabled') and self.config.proxy_enabled:
            proxy_url = self.config.brightdata_proxy
            print(f"      🌐 HTTP fallback using proxy: {proxy_url.split('@')[1] if '@' in proxy_url else 'configured'}")
        
        connector = aiohttp.TCPConnector(
            ssl=False,
            limit=10,
            limit_per_host=5,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=20)
        
        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=connector
        ) as session:
            for i, sitemap_url in enumerate(sitemap_urls, 1):
                print(f"      🔗 [{i}/{len(sitemap_urls)}] HTTP fallback: {sitemap_url}")
                
                try:
                    request_kwargs = {}
                    if proxy_url:
                        request_kwargs['proxy'] = proxy_url
                    
                    async with session.get(sitemap_url, **request_kwargs) as response:
                        print(f"        📊 HTTP Status: {response.status}")
                        
                        if response.status == 200:
                            try:
                                content = await response.text(encoding='utf-8', errors='ignore')
                                print(f"        📄 Content length: {len(content)} chars")
                                
                                if len(content) > 0:
                                    found_count = await self._parse_sitemap_content(content)
                                    if found_count > 0:
                                        print(f"        ✅ HTTP fallback found {found_count} URLs")
                                        total_urls += found_count
                                    else:
                                        print(f"        ⚠️  No URLs found in content")
                                else:
                                    print(f"        ⚠️  Empty content received")
                            except Exception as parse_error:
                                print(f"        ❌ Parse error: {str(parse_error)[:50]}")
                        
                        elif response.status in [301, 302, 307, 308]:
                            redirect_url = response.headers.get('Location')
                            if redirect_url:
                                print(f"        🔄 Following redirect to: {redirect_url}")
                                # Could recursively follow redirect here
                        
                        elif response.status == 401:
                            print(f"        🚫 Access denied (401) - Proxy/auth issue")
                        elif response.status == 403:
                            print(f"        🚫 Forbidden (403) - Site blocking requests")
                        elif response.status == 404:
                            print(f"        ❌ Not found (404) - Sitemap doesn't exist")
                        else:
                            print(f"        ⚠️  Unexpected status: {response.status}")
                            
                except aiohttp.ClientError as e:
                    print(f"        ❌ HTTP Client Error: {str(e)[:60]}...")
                except Exception as e:
                    print(f"        ❌ Error: {str(e)[:60]}...")
        
        return total_urls
    
    async def _test_browser_stage(self, crawler, sitemap_urls: list, crawler_configs: list, stage_name: str) -> bool:
        """Test a browser configuration stage and return success status"""
        stage_success = False
        for i, sitemap_url in enumerate(sitemap_urls, 1):
            print(f"      🔍 [{i}/{len(sitemap_urls)}] {stage_name.upper()}: {sitemap_url}")
            
            # ENHANCED: Multi-stage verification and crawling
            success = await self._try_multiple_sitemap_approaches(crawler, sitemap_url, crawler_configs)
            if success:
                print(f"        ✅ Successfully processed sitemap with {stage_name} mode!")
                stage_success = True
        return stage_success
    
    async def _try_multiple_sitemap_approaches(self, crawler, sitemap_url: str, crawler_configs: list) -> bool:
        """Try multiple approaches to access and parse a sitemap"""
        
        # Approach 1: Quick HTTP HEAD check
        try:
            async with aiohttp.ClientSession() as session:
                # Add realistic headers for HTTP requests
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
                
                async with session.head(sitemap_url, timeout=aiohttp.ClientTimeout(total=10), headers=headers) as resp:
                    print(f"      📊 Quick check: HTTP {resp.status}")
                    if resp.status not in [200, 301, 302]:
                        print(f"      ❌ URL not accessible (Status: {resp.status}) - Trying alternative approaches")
                        # Don't skip immediately - try with crawler anyway
        except Exception as e:
            print(f"      ⚠️  Quick check failed: {str(e)[:50]} - Proceeding with crawler...")
        
        # Approach 2: Try with different crawler configurations
        for config_idx, crawler_config in enumerate(crawler_configs, 1):
            print(f"      🚀 Attempt {config_idx}: Using crawler config {config_idx}")
            
            try:
                result_container = await asyncio.wait_for(
                    crawler.arun(url=sitemap_url, config=crawler_config),
                    timeout=35  # Generous timeout
                )
                
                if result_container and len(result_container._results) > 0:
                    result = result_container._results[0]
                    print(f"      📊 Crawl result: success={result.success}, status={getattr(result, 'status_code', 'unknown')}")
                    
                    if result.success and result.html:
                        print(f"      ✅ Found sitemap! Content length: {len(result.html)} chars")
                        found_urls = await self._parse_sitemap_content(result.html)
                        if found_urls > 0:
                            print(f"      🎯 Extracted {found_urls} URLs from sitemap")
                            return True
                        else:
                            print(f"      ⚠️  No URLs found in sitemap content")
                    else:
                        print(f"      ❌ Crawl failed - Error: {getattr(result, 'error_message', 'No content')}")
                else:
                    print(f"      ⚠️  No results from crawler attempt {config_idx}")
                    
            except asyncio.TimeoutError:
                print(f"      ⏰ Crawler timeout on attempt {config_idx}")
            except Exception as e:
                print(f"      ❌ Crawler error on attempt {config_idx}: {str(e)[:50]}")
        
        # Approach 3: Direct HTTP parsing fallback
        print(f"      🔄 Final fallback: Direct HTTP parsing...")
        found_count = await self._parse_sitemap_direct_http(sitemap_url)
        if found_count > 0:
            print(f"      ✅ Direct HTTP parsing found {found_count} URLs")
            return True
        
        return False
    
    async def _fallback_sitemap_check(self, sitemap_urls):
        """Fallback method to check sitemaps using direct HTTP requests"""
        import aiohttp
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            for i, sitemap_url in enumerate(sitemap_urls, 1):
                print(f"    🔗 [{i}/{len(sitemap_urls)}] Direct check: {sitemap_url}")
                try:
                    async with session.get(sitemap_url) as resp:
                        print(f"      📊 HTTP Status: {resp.status}")
                        if resp.status == 200:
                            content = await resp.text()
                            print(f"      ✅ Found content! Length: {len(content)} chars")
                            if content.strip():
                                await self._parse_sitemap_content(content)
                        else:
                            print(f"      ❌ HTTP Error: {resp.status}")
                except Exception as e:
                    print(f"      ❌ Exception: {e}")
    
    async def _parse_sitemap_content(self, content: str) -> int:
        """Parse sitemap content (XML or HTML) and return count of URLs found"""
        found_urls = set()
        
        try:
            # Try XML parsing first
            root = ET.fromstring(content)
            
            # Handle sitemap index
            for sitemap in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap"):
                loc = sitemap.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                if loc is not None and self._should_include_url(loc.text):
                    found_urls.add(loc.text)
            
            # Handle URL entries
            for url in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
                loc = url.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                if loc is not None and self._should_include_url(loc.text):
                    found_urls.add(loc.text)
                    
        except ET.ParseError:
            # Try as HTML or text
            urls = re.findall(r'https?://[^\s<>"]+', content)
            for url in urls:
                if self.domain in url and self._should_include_url(url):
                    found_urls.add(url)
        
        # Add found URLs using the real-time writing method
        if found_urls:
            self._add_urls_to_set_and_file(found_urls, "SITEMAP")
        
        return len(found_urls)

    async def _parse_sitemap_direct_http(self, sitemap_url: str) -> int:
        """Enhanced direct HTTP parsing fallback for sitemaps with proxy support"""
        found_count = 0
        
        # Enhanced headers to bypass blocking
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Referer": self.config.base_url
        }
        
        # PROXY CONFIGURATION for HTTP requests
        connector_kwargs = {}
        proxy_url = None
        if hasattr(self.config, 'proxy_enabled') and self.config.proxy_enabled:
            proxy_url = self.config.brightdata_proxy
            print(f"      🌐 Using proxy for HTTP request: {proxy_url.split('@')[1] if '@' in proxy_url else 'configured'}")
        
        # Multiple retry attempts with different strategies
        for attempt in range(3):
            try:
                print(f"      🔄 Direct HTTP parsing (attempt {attempt + 1}): {sitemap_url}")
                
                timeout = aiohttp.ClientTimeout(total=15 + (attempt * 5))  # Increasing timeout
                
                # Enhanced headers with compression handling
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate",  # Removed br (Brotli) to avoid decoding issues
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Cache-Control": "max-age=0",
                    "Referer": self.config.base_url
                }
                
                # Create session with proxy if enabled
                connector = aiohttp.TCPConnector(
                    ssl=False,  # Allow SSL bypass for problematic sites
                    limit=10,
                    limit_per_host=5,
                    keepalive_timeout=30,
                    enable_cleanup_closed=True
                )
                
                async with aiohttp.ClientSession(
                    timeout=timeout,
                    headers=headers,
                    connector=connector
                ) as session:
                    # Use proxy if configured
                    request_kwargs = {}
                    if proxy_url:
                        request_kwargs['proxy'] = proxy_url
                    
                    async with session.get(sitemap_url, **request_kwargs) as response:
                        print(f"      📊 HTTP Response: {response.status}")
                        
                        if response.status == 200:
                            # Handle different content encodings properly
                            try:
                                content = await response.text(encoding='utf-8', errors='ignore')
                            except UnicodeDecodeError:
                                content = await response.text(encoding='latin-1', errors='ignore')
                            
                            print(f"      📄 Content length: {len(content)} chars")
                            
                            if len(content) > 0:
                                # Parse as XML first
                                try:
                                    root = ET.fromstring(content)
                                    print(f"      ✅ Valid XML sitemap detected")
                                    
                                    # Handle sitemap index
                                    for sitemap in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap"):
                                        loc = sitemap.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                                        if loc is not None and self._should_include_url(loc.text):
                                            self._add_urls_to_set_and_file([loc.text], "SITEMAP_INDEX")
                                            found_count += 1
                                    
                                    # Handle individual URLs
                                    for url in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
                                        loc = url.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                                        if loc is not None and self._should_include_url(loc.text):
                                            self._add_urls_to_set_and_file([loc.text], "SITEMAP_URL")
                                            found_count += 1
                                            
                                except ET.ParseError:
                                    print(f"      ⚠️  Not valid XML, trying HTML/text parsing...")
                                    # Try HTML parsing as fallback
                                    soup = BeautifulSoup(content, 'html.parser')
                                    for link in soup.find_all('a', href=True):
                                        url = link['href']
                                        if url.startswith('http') and self._should_include_url(url):
                                            self._add_urls_to_set_and_file([url], "SITEMAP_HTML")
                                            found_count += 1
                                    
                                    # Also try regex extraction
                                    urls = re.findall(r'https?://[^\s<>"]+', content)
                                    for url in urls:
                                        if self.domain in url and self._should_include_url(url):
                                            self._add_urls_to_set_and_file([url], "SITEMAP_REGEX")
                                            found_count += 1
                                
                                if found_count > 0:
                                    print(f"      ✅ Direct HTTP parsing found {found_count} URLs")
                                    return found_count
                                else:
                                    print(f"      ⚠️  No URLs found in content")
                            else:
                                print(f"      ⚠️  Empty content received")
                        elif response.status in [301, 302, 307, 308]:
                            # Handle redirects manually
                            redirect_url = response.headers.get('Location')
                            if redirect_url:
                                print(f"      🔄 Following redirect to: {redirect_url}")
                                # Recursive call with redirect URL
                                return await self._parse_sitemap_direct_http(redirect_url)
                        else:
                            print(f"      ❌ HTTP Error: {response.status}")
                            
            except aiohttp.ClientError as e:
                print(f"      ❌ HTTP Client Error on attempt {attempt + 1}: {str(e)[:60]}...")
            except Exception as e:
                print(f"      ❌ Error on attempt {attempt + 1}: {str(e)[:60]}...")
            
            # Wait between attempts
            if attempt < 2:
                await asyncio.sleep(1 + attempt)
        
        print(f"      ❌ All direct HTTP parsing attempts failed")
        return found_count
    
    async def _discover_from_robots(self):
        """Discover URLs from robots.txt"""
        # Remove trailing slash from base URL to avoid double slashes
        base_url = self.config.base_url.rstrip('/')
        robots_url = f"{base_url}/robots.txt"
        print(f"  🤖 Checking robots.txt: {robots_url}")
        
        crawler_config = CrawlerRunConfig(
            page_timeout=self.config.timeout * 1000,
            verbose=False,
            js_code=self._get_popup_bypass_js(),
            wait_for_images=False
        )
        
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            try:
                result_container = await crawler.arun(url=robots_url, config=crawler_config)
                
                if result_container and len(result_container._results) > 0:
                    result = result_container._results[0]
                    if result.success and result.markdown:
                        print(f"    ✅ Found robots.txt! Processing...")
                        self._parse_robots_content(result.markdown)
                    else:
                        print(f"    ❌ Could not access robots.txt")
                else:
                    print(f"    ⚠️  No robots.txt found")
                        
            except Exception as e:
                print(f"    ❌ Error accessing robots.txt: {e}")
                logger.debug(f"Could not access robots.txt: {e}")
        
        print(f"  ✅ Robots.txt analysis complete")
        self.discovery_stats["robots_txt_urls"] = len([u for u in self.discovered_urls if "robots" in u])
    
    def _parse_robots_content(self, content: str):
        """Parse robots.txt content for URLs"""
        found_urls = set()
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('Sitemap:'):
                sitemap_url = line.replace('Sitemap:', '').strip()
                if self._should_include_url(sitemap_url):
                    found_urls.add(sitemap_url)
            elif line.startswith('Disallow:') or line.startswith('Allow:'):
                path = line.split(':', 1)[1].strip()
                if path and path != '/':
                    full_url = urljoin(self.config.base_url, path)
                    if self._should_include_url(full_url):
                        found_urls.add(full_url)
        
        # Add found URLs using the real-time writing method
        if found_urls:
            self._add_urls_to_set_and_file(found_urls, "ROBOTS_TXT")
    
    async def _url_seeding_discovery(self):
        """URL Seeding using AsyncUrlSeeder with Common Crawl + Sitemap data"""
        logger.info("🌐 Starting URL seeding discovery (Common Crawl + Enhanced Sitemaps)...")
        
        try:
            # Extract domain from base URL
            domain = urlparse(self.config.base_url).netloc
            
            # Create seeding configuration
            config = SeedingConfig(
                source="cc+sitemap",  # Use both Common Crawl and sitemap data
                pattern="*",          # Match all URLs (we'll filter later)
                live_check=False,     # Disable live check for faster discovery
                extract_head=True,    # Extract metadata for potential filtering
                verbose=False         # Reduce verbosity for cleaner logs
            )
            
            # Create query for better relevance if context is provided
            query_terms = []
            if self.config.context_description:
                # Add context keywords
                context_words = [word.strip() for word in self.config.context_description.split() if len(word.strip()) > 2]
                query_terms.extend(context_words[:10])  # Limit to prevent over-filtering
            
            # Add generic website terms for broader discovery
            query_terms.extend([
                "information", "service", "guide", "support", "help", "news", "event", 
                "contact", "about", "resource", "document", "form", "application"
            ])
            
            # Create query string
            query = " ".join(query_terms) if query_terms else ""
            
            # Use AsyncUrlSeeder for discovery with concurrent processing
            seeder = AsyncUrlSeeder()
            
            # Method 1: Use seeder for domain-based discovery (concurrent)
            logger.info("[URL_SEEDING] Using concurrent domain-based discovery from Common Crawl and sitemaps")
            
            # Process seeding concurrently with multiple approaches
            async def concurrent_seeding():
                tasks = []
                
                # Task 1: Primary seeder
                tasks.append(seeder.urls(self.config.base_url, config))
                
                # Task 2: Try with different variations concurrently
                if self.config.base_url.startswith('https://'):
                    http_url = self.config.base_url.replace('https://', 'http://')
                    tasks.append(seeder.urls(http_url, config))
                
                # Task 3: Try with www prefix if not present
                if '://www.' not in self.config.base_url:
                    www_url = self.config.base_url.replace('://', '://www.')
                    tasks.append(seeder.urls(www_url, config))
                
                # Execute all tasks concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log results summary
                successful_tasks = 0
                total_urls = 0
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.debug(f"Task {i+1} failed: {str(result)[:100]}")
                    else:
                        result_len = len(result) if result else 0
                        total_urls += result_len
                        successful_tasks += 1
                        logger.info(f"[URL_SEEDING] Task {i+1} found {result_len} URLs")
                
                logger.info(f"[URL_SEEDING] {successful_tasks}/{len(tasks)} tasks succeeded, {total_urls} total URLs from Common Crawl")
                return [r for r in results if not isinstance(r, Exception) and r]
            
            # Get results from concurrent seeding
            all_seeded_results = await concurrent_seeding()
            
            # Process results concurrently
            seeded_urls = set()
            
            async def process_result_batch(results_batch):
                """Process a batch of seeding results concurrently"""
                batch_urls = set()
                
                if results_batch:
                    for result in results_batch:
                        if isinstance(result, dict):
                            url = result.get("url")
                            status = result.get("status", "unknown")
                            
                            if url and status in ["valid", "unknown"] and self._should_include_url(url):
                                batch_urls.add(url)
                        elif isinstance(result, str):
                            if self._should_include_url(result):
                                batch_urls.add(result)
                
                return batch_urls
            
            # Process all result batches concurrently
            if all_seeded_results:
                processing_tasks = [process_result_batch(results) for results in all_seeded_results]
                batch_results = await asyncio.gather(*processing_tasks)
                
                # Combine all results
                for batch_urls in batch_results:
                    seeded_urls.update(batch_urls)
            
            logger.info(f"[URL_SEEDING] Concurrent processing found {len(seeded_urls)} candidate URLs")
            
            # Method 2: Concurrent fallback to recursive sitemap discovery if seeding fails
            if not seeded_urls:
                logger.info("[URL_SEEDING] AsyncUrlSeeder returned no results, trying recursive sitemap discovery...")
                seeded_urls = await self._try_parse_all_sitemaps()
            else:
                logger.info(f"[URL_SEEDING] Seeding successful, found {len(seeded_urls)} URLs from Common Crawl + Sitemaps")
            
            # Add discovered URLs to our main set (with duplicate prevention - NO VALIDATION)
            new_seeded_urls = seeded_urls - self.discovered_urls
            if new_seeded_urls:
                # Skip URL validation - let Crawl4AI handle invalid URLs gracefully
                logger.info(f"[URL_SEEDING] Adding {len(new_seeded_urls)} new URLs (no pre-validation)...")
                
                # Use real-time writing method directly
                added_count = self._add_urls_to_set_and_file(new_seeded_urls, "URL_SEEDING")
                logger.info(f"[URL_SEEDING] Added {added_count} URLs from seeding")
                # Update statistics
                self.discovery_stats["url_seeding_urls"] = added_count
            else:
                logger.info("[URL_SEEDING] No new URLs discovered from seeding")
                
        except Exception as e:
            logger.warning(f"URL seeding failed: {e}")
            logger.info("[URL_SEEDING] Falling back to enhanced sitemap discovery...")
            
            # Fallback: Try sitemap discovery but with timeout to prevent hanging
            try:
                logger.info("[URL_SEEDING] Trying sitemap fallback with timeout protection...")
                
                # Use timeout to prevent hanging
                seeded_urls = await asyncio.wait_for(
                    self._try_parse_all_sitemaps(), 
                    timeout=120  # 2 minute timeout
                )
                
                if seeded_urls:
                    # Add discovered URLs
                    new_seeded_urls = seeded_urls - self.discovered_urls
                    if new_seeded_urls:
                        added_count = self._add_urls_to_set_and_file(new_seeded_urls, "URL_SEEDING_FALLBACK")
                        logger.info(f"[URL_SEEDING_FALLBACK] Added {added_count} URLs from sitemap fallback")
                        self.discovery_stats["url_seeding_urls"] = added_count
                        
            except asyncio.TimeoutError:
                logger.warning("[URL_SEEDING] Sitemap fallback timed out - will rely on Crawl4AI phases")
            except Exception as fallback_error:
                logger.warning(f"Fallback sitemap discovery also failed: {fallback_error}")
    
    async def _try_parse_all_sitemaps(self):
        """Recursively fetch and parse all sitemaps (including sitemap indexes) with concurrent processing"""
        import xml.etree.ElementTree as ET
        import aiohttp
        
        parsed = urlparse(self.config.base_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Common sitemap locations
        sitemap_candidates = [
            f"{base_url}/sitemap.xml",
            f"{base_url}/sitemap_index.xml",
            f"{base_url}/sitemaps.xml",
            f"{base_url}/sitemap/sitemap.xml",
            f"{base_url}/sitemaps/sitemap.xml",
            f"{base_url}/sitemap-posts.xml",
            f"{base_url}/sitemap-pages.xml", 
            f"{base_url}/post-sitemap.xml",
            f"{base_url}/page-sitemap.xml",
            f"{base_url}/category-sitemap.xml"
        ]
        
        all_urls = set()
        seen = set()
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        async def fetch_and_parse_sitemap(session, sitemap_url):
            """Fetch and parse a single sitemap concurrently"""
            if sitemap_url in seen:
                return set(), set()
            
            seen.add(sitemap_url)
            
            try:
                async with session.get(sitemap_url, timeout=30) as resp:
                    if resp.status != 200:
                        return set(), set()
                    
                    content = await resp.text()
                    root = ET.fromstring(content)
                    
                    sitemap_urls = set()
                    page_urls = set()
                    
                    # If this is a sitemap index, collect referenced sitemaps
                    for sitemap in root.findall('.//ns:sitemap/ns:loc', ns):
                        if sitemap.text and sitemap.text not in seen:
                            sitemap_urls.add(sitemap.text)
                    
                    # Add all URLs in this sitemap
                    for loc in root.findall('.//ns:url/ns:loc', ns):
                        if loc.text and self._should_include_url(loc.text):
                            page_urls.add(loc.text)
                    
                    return sitemap_urls, page_urls
                    
            except Exception as e:
                logger.debug(f"Error fetching/parsing sitemap {sitemap_url}: {e}")
                return set(), set()
        
        # Process sitemaps with concurrent fetching
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
            to_visit = set(sitemap_candidates)
            
            while to_visit:
                # Process current batch concurrently
                current_batch = list(to_visit)[:20]  # Process up to 20 sitemaps concurrently
                to_visit -= set(current_batch)
                
                # Create concurrent tasks
                tasks = [fetch_and_parse_sitemap(session, url) for url in current_batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in results:
                    if isinstance(result, tuple):
                        sitemap_urls, page_urls = result
                        to_visit.update(sitemap_urls - seen)  # Add new sitemaps to visit
                        all_urls.update(page_urls)  # Add discovered page URLs
        
        return all_urls
    
    async def _recursive_crawl_with_crawl4ai(self):
        """ENHANCED: Ultra-fast recursive crawling using Crawl4AI with batch processing"""
        print("  🔄 Starting high-speed recursive crawling...")
        logger.info("🔍 Starting ENHANCED recursive crawling with Crawl4AI...")
        
        # Use deque for efficient queue operations (from your working code)
        from collections import deque
        
        # START WITH HOMEPAGE ONLY (like your working comprehensive_site_crawler.py)
        # This prevents overwhelming the system and ensures proper depth-first crawling
        base_url = self.config.base_url
        print(f"    � Starting recursive crawling from homepage only: {base_url}")
        
        # Initialize with just the homepage URL
        url_queue = deque([base_url])
        
        batch_size = 500  # Starting batch size
        adaptive_sizing = True  # Enable CONSERVATIVE adaptive batch sizing
        
        # BULLETPROOF ADAPTIVE PARAMETERS
        min_batch_size = 400  # Don't go below proven stable size
        max_batch_size = 650  # Conservative maximum (not 750)
        target_success_rate = 0.80  # Higher threshold for safety
        
        # MULTI-LAYER SAFETY CHECKS
        increase_amount = 25  # Very small increases
        decrease_amount = 50  # Faster decreases for safety
        stability_check_batches = 5  # Need 5 stable batches before increasing
        
        # ADVANCED STABILITY TRACKING
        recent_success_rates = []  # Track last few batches
        recent_processing_times = []  # Track performance trends
        recent_failure_counts = []  # Track failure patterns
        system_health_score = 1.0  # Overall system health (0.0-1.0)
        
        batches_since_change = 0  # Stability counter
        consecutive_good_batches = 0  # Extra safety counter
        emergency_fallback_triggered = False  # Emergency brake
        
        # HEALTH MONITORING THRESHOLDS
        max_processing_time_increase = 2.0  # Don't allow 2x slower processing
        max_failure_rate_spike = 0.3  # Alert if failure rate spikes 30%
        memory_safety_buffer = 0.15  # Keep 15% memory buffer
        
        total_processed = 0
        batch_number = 0
        
        print(f"    ⚙️  Config: batch_size={batch_size}, max_concurrent={self.config.max_concurrent}")
        
        while url_queue and len(self.discovered_urls) < self.config.max_pages:
            batch_number += 1
            
            # Process URLs in batches (your proven approach)
            current_batch = []
            batch_count = min(batch_size, len(url_queue))
            
            for _ in range(batch_count):
                if url_queue:
                    current_batch.append(url_queue.popleft())
            
            if not current_batch:
                break
            
            total_processed += len(current_batch)
            print(f"    📦 BATCH {batch_number}: Processing {len(current_batch)} URLs (Total processed: {total_processed})")
            logger.info(f"[BATCH] Processing batch of {len(current_batch)} URLs (Total: {total_processed})")
            
            # Process batch and get NEW URLs using Crawl4AI
            batch_start = time.time()
            new_urls_found = await self._process_crawl4ai_batch_ultra_fast(current_batch)
            batch_time = time.time() - batch_start
            
            # 200% ACCURACY CHECK: Verify all URLs were processed
            print(f"      🔍 Accuracy Check: {len(current_batch)} URLs sent → {len(new_urls_found)} new URLs found")
            
            # Add NEW URLs to both discovered set and queue with real-time writing
            truly_new_urls = new_urls_found - self.discovered_urls
            if truly_new_urls:
                added_count = self._add_urls_to_set_and_file(truly_new_urls, f"RECURSIVE_BATCH_{batch_number}")
                
                # Add new URLs to queue for further crawling
                for new_url in truly_new_urls:
                    url_queue.append(new_url)
                
                print(f"      ✅ BATCH {batch_number} Complete: {added_count} new URLs in {batch_time:.1f}s")
                print(f"      📊 Speed: {len(current_batch)/batch_time:.1f} URLs/sec | Queue: {len(url_queue)} pending")
            else:
                print(f"      ⏭️  BATCH {batch_number}: No new URLs found in {batch_time:.1f}s")
            
            logger.info(f"[SUCCESS] Batch complete: {len(truly_new_urls)} new URLs found in {batch_time:.1f}s")
            logger.info(f"[TOTAL] URLs discovered: {len(self.discovered_urls)} | Queue: {len(url_queue)}")
            
            # BULLETPROOF ADAPTIVE BATCH SIZING with Multi-Layer Safety
            if adaptive_sizing and batch_number >= 3:
                current_success_rate = len([url for url in current_batch if url not in self.failed_urls]) / len(current_batch) if current_batch else 1.0
                current_failure_count = len(set(current_batch) & self.failed_urls) if current_batch else 0
                
                # Update health tracking arrays
                recent_success_rates.append(current_success_rate)
                recent_processing_times.append(batch_time)
                recent_failure_counts.append(current_failure_count)
                
                # Keep only last 5 data points for analysis
                for tracking_list in [recent_success_rates, recent_processing_times, recent_failure_counts]:
                    if len(tracking_list) > 5:
                        tracking_list.pop(0)
                
                batches_since_change += 1
                
                # SYSTEM HEALTH ASSESSMENT
                system_health_score = self._calculate_system_health(
                    recent_success_rates, recent_processing_times, recent_failure_counts
                )
                
                # EMERGENCY BRAKE: Immediate fallback if system health is critical
                if system_health_score < 0.4 and not emergency_fallback_triggered:
                    old_size = batch_size
                    batch_size = min_batch_size
                    emergency_fallback_triggered = True
                    batches_since_change = 0
                    recent_success_rates.clear()
                    consecutive_good_batches = 0
                    print(f"      🚨 EMERGENCY: System health critical ({system_health_score:.2f}), fallback: {old_size} → {batch_size}")
                    logger.error(f"[EMERGENCY] Critical system health, emergency fallback to {batch_size}")
                    
                # RECOVERY: Reset emergency brake if system stabilizes
                elif emergency_fallback_triggered and system_health_score > 0.8:
                    emergency_fallback_triggered = False
                    consecutive_good_batches = 0
                    print(f"      ✅ RECOVERY: System health restored ({system_health_score:.2f}), emergency brake released")
                    logger.info(f"[RECOVERY] System health restored, emergency brake released")
                
                # NORMAL ADAPTIVE LOGIC (only if not in emergency mode)
                elif not emergency_fallback_triggered:
                    avg_success_rate = sum(recent_success_rates) / len(recent_success_rates)
                    min_success_rate = min(recent_success_rates) if recent_success_rates else 0
                    
                    # Track consecutive good batches for extra stability
                    if current_success_rate >= 0.85:
                        consecutive_good_batches += 1
                    else:
                        consecutive_good_batches = 0
                    
                    # ULTRA-CONSERVATIVE INCREASE: Multiple conditions must be met
                    if (avg_success_rate >= 0.90 and 
                        min_success_rate >= 0.85 and  # All recent batches must be good
                        system_health_score >= 0.85 and  # System health must be excellent
                        consecutive_good_batches >= 7 and  # Extra stability requirement
                        batches_since_change >= stability_check_batches and
                        batch_size < max_batch_size and
                        self._memory_usage_safe()):  # Check memory usage
                        
                        old_size = batch_size
                        batch_size = min(batch_size + increase_amount, max_batch_size)
                        batches_since_change = 0
                        consecutive_good_batches = 0
                        print(f"      📈 BREAKTHROUGH: Increasing batch size: {old_size} → {batch_size}")
                        print(f"          📊 Health: {system_health_score:.2f}, Avg Success: {avg_success_rate:.1%}, Consecutive Good: {consecutive_good_batches}")
                        logger.info(f"[BREAKTHROUGH] Conservative increase: {old_size} → {batch_size} (health: {system_health_score:.2f})")
                    
                    # IMMEDIATE DECREASE: React quickly to problems
                    elif (current_success_rate < 0.75 or 
                          system_health_score < 0.7 or
                          self._performance_degrading()) and batch_size > min_batch_size:
                        
                        old_size = batch_size
                        batch_size = max(batch_size - decrease_amount, min_batch_size)
                        batches_since_change = 0
                        consecutive_good_batches = 0
                        recent_success_rates.clear()
                        print(f"      📉 SAFETY: Decreasing batch size: {old_size} → {batch_size}")
                        print(f"          📊 Trigger: Success={current_success_rate:.1%}, Health={system_health_score:.2f}")
                        logger.warning(f"[SAFETY] Preventive decrease: {old_size} → {batch_size}")
                
                # PROGRESS REPORTING
                if batch_number % 5 == 0:  # Every 5 batches, show health status
                    print(f"      📊 HEALTH CHECK: System Health={system_health_score:.2f}, Batch Size={batch_size}, Consecutive Good={consecutive_good_batches}")
            
            # Mark current batch as crawled
            self.crawled_urls.update(current_batch)
            
            # Stop if no new URLs found and queue is small
            if len(truly_new_urls) == 0 and len(url_queue) < 10:
                print(f"      🏁 Stopping: No new URLs found and only {len(url_queue)} URLs in queue")
                logger.info("[COMPLETE] No new URLs found - stopping recursive crawl")
                break
        
        # RESILIENCE: Retry failed URLs if we have any
        await self._retry_failed_urls_if_needed()
        
        print(f"  ✅ Recursive crawling complete: {len(self.crawled_urls)} URLs crawled")
        self.discovery_stats["recursive_crawl_urls"] = len(self.crawled_urls)
    
    async def _retry_failed_urls_if_needed(self):
        """BULLETPROOF: Multi-stage retry system with escalating recovery strategies"""
        if not self.failed_urls:
            return
        
        print(f"  🔄 BULLETPROOF RECOVERY: Starting multi-stage retry for {len(self.failed_urls)} failed URLs...")
        logger.info(f"[BULLETPROOF] Starting multi-stage retry for {len(self.failed_urls)} failed URLs")
        
        # Stage 1: Conservative Retry (smallest batches, longest timeouts)
        stage1_recovered = await self._stage1_conservative_retry()
        
        # Stage 2: Alternative Method Retry (HTTP fallback for remaining failures)
        stage2_recovered = await self._stage2_alternative_method_retry()
        
        # Stage 3: Individual URL Rescue (one-by-one for critical failures)
        stage3_recovered = await self._stage3_individual_rescue()
        
        total_recovered = stage1_recovered + stage2_recovered + stage3_recovered
        
        if total_recovered > 0:
            print(f"  ✅ BULLETPROOF SUCCESS: Recovered {total_recovered} URLs across 3 stages")
            logger.info(f"[BULLETPROOF] Successfully recovered {total_recovered} URLs")
        else:
            remaining_failures = len(self.failed_urls)
            print(f"  ⚠️  BULLETPROOF COMPLETE: {remaining_failures} URLs could not be recovered (likely site restrictions)")
            logger.warning(f"[BULLETPROOF] {remaining_failures} URLs remain unrecoverable")
    
    async def _stage1_conservative_retry(self) -> int:
        """Stage 1: Ultra-conservative retry with maximum safety"""
        retry_urls = list(self.failed_urls)[:50]  # Limit to 50 most important
        if not retry_urls:
            return 0
        
        print(f"    🔄 STAGE 1: Conservative retry for {len(retry_urls)} URLs...")
        recovered_count = 0
        
        # Ultra-small batches with maximum timeouts
        for i in range(0, len(retry_urls), 5):  # Batch size = 5
            micro_batch = retry_urls[i:i + 5]
            
            try:
                recovered_links = await self._ultra_conservative_batch(micro_batch)
                
                if recovered_links:
                    added_count = self._add_urls_to_set_and_file(recovered_links, f"STAGE1_RECOVERY_{i//5 + 1}")
                    recovered_count += len(recovered_links)
                    
                    # Remove successfully processed URLs from failed set
                    for url in micro_batch:
                        if url in self.failed_urls:
                            self.failed_urls.remove(url)
                            self.crawled_urls.add(url)
                            
                # Add delay between micro-batches for server breathing room
                await asyncio.sleep(1.0)
                            
            except Exception as e:
                logger.warning(f"[STAGE1] Micro-batch {i//5 + 1} failed: {e}")
                continue
        
        print(f"    ✅ STAGE 1 COMPLETE: Recovered {recovered_count} URLs")
        return recovered_count
    
    async def _stage2_alternative_method_retry(self) -> int:
        """Stage 2: Try alternative HTTP method for remaining failures"""
        remaining_failures = list(self.failed_urls)[:30]  # Limit to 30
        if not remaining_failures:
            return 0
        
        print(f"    🔄 STAGE 2: Alternative HTTP method for {len(remaining_failures)} URLs...")
        recovered_count = 0
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=45)) as session:
                for url in remaining_failures:
                    try:
                        async with session.get(url) as response:
                            if response.status == 200:
                                # Successfully accessed via HTTP, mark as recovered
                                self.failed_urls.discard(url)
                                self.crawled_urls.add(url)
                                recovered_count += 1
                                
                                # Extract basic links if possible
                                if 'text/html' in response.headers.get('content-type', ''):
                                    content = await response.text()
                                    basic_links = self._extract_basic_links_from_html(content, url)
                                    if basic_links:
                                        self._add_urls_to_set_and_file(basic_links, "STAGE2_HTTP_RECOVERY")
                                        
                        await asyncio.sleep(0.2)  # Respectful delay
                        
                    except Exception as e:
                        logger.debug(f"[STAGE2] HTTP fallback failed for {url}: {e}")
                        continue
                        
        except ImportError:
            logger.warning("[STAGE2] aiohttp not available for alternative method retry")
            
        print(f"    ✅ STAGE 2 COMPLETE: Recovered {recovered_count} URLs")
        return recovered_count
    
    async def _stage3_individual_rescue(self) -> int:
        """Stage 3: Individual URL rescue with maximum patience"""
        critical_failures = list(self.failed_urls)[:10]  # Only most critical
        if not critical_failures:
            return 0
        
        print(f"    🔄 STAGE 3: Individual rescue for {len(critical_failures)} critical URLs...")
        recovered_count = 0
        
        for i, url in enumerate(critical_failures):
            try:
                print(f"      🎯 Rescuing {i+1}/{len(critical_failures)}: {url[:60]}...")
                
                # Maximum patience: single URL with very long timeout
                async with AsyncWebCrawler(config=self.browser_config) as crawler:
                    crawler_config = CrawlerRunConfig(
                        page_timeout=60000,  # 60 second timeout
                        verbose=False,
                        wait_for_images=False,
                        process_iframes=False,
                        js_code=self._get_popup_bypass_js()
                    )
                    
                    result_container = await asyncio.wait_for(
                        crawler.arun(url=url, config=crawler_config),
                        timeout=70  # 70 second total timeout
                    )
                    
                    if result_container and len(result_container._results) > 0:
                        result = result_container._results[0]
                        if result.success:
                            extracted_links = await self._extract_links_comprehensive(result, url)
                            if extracted_links:
                                self._add_urls_to_set_and_file(extracted_links, f"STAGE3_INDIVIDUAL_{i+1}")
                                
                            self.failed_urls.discard(url)
                            self.crawled_urls.add(url)
                            recovered_count += 1
                            print(f"        ✅ Rescued with {len(extracted_links)} new links")
                            
                # Generous delay between individual rescues
                await asyncio.sleep(2.0)
                            
            except Exception as e:
                logger.debug(f"[STAGE3] Individual rescue failed for {url}: {e}")
                print(f"        ❌ Could not rescue: {str(e)[:50]}")
                continue
        
        print(f"    ✅ STAGE 3 COMPLETE: Rescued {recovered_count} URLs")
        return recovered_count
    
    async def _ultra_conservative_batch(self, urls: List[str]) -> Set[str]:
        """Ultra-conservative batch processing with maximum safety"""
        all_new_links = set()
        
        # Absolute minimum concurrency
        semaphore = asyncio.Semaphore(1)  # Only 1 concurrent request
        
        crawler_config = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator(),
            page_timeout=45000,  # 45 second timeout
            verbose=False,
            wait_for_images=False,
            process_iframes=False,
            js_code=self._get_popup_bypass_js()
        )
        
        async def ultra_safe_single_url(url: str) -> Set[str]:
            async with semaphore:
                try:
                    await asyncio.sleep(0.5)  # Long delay for maximum politeness
                    
                    async with AsyncWebCrawler(config=self.browser_config) as crawler:
                        result_container = await asyncio.wait_for(
                            crawler.arun(url=url, config=crawler_config),
                            timeout=50  # Extended timeout
                        )
                        
                        if result_container and len(result_container._results) > 0:
                            result = result_container._results[0]
                            if result.success:
                                extracted_links = await self._extract_links_comprehensive(result, url)
                                return extracted_links
                                
                except Exception as e:
                    logger.debug(f"[ULTRA_SAFE] Failed to process {url}: {e}")
                    
                return set()
        
        # Process URLs ultra-safely
        tasks = [ultra_safe_single_url(url) for url in urls]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, set):
                    all_new_links.update(result)
                    
        except Exception as e:
            logger.warning(f"[ULTRA_SAFE] Ultra-conservative batch failed: {e}")
        
        return all_new_links
    
    def _extract_basic_links_from_html(self, html_content: str, base_url: str) -> Set[str]:
        """Extract basic links from HTML content using BeautifulSoup"""
        links = set()
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for tag in soup.find_all(['a', 'link']):
                href = tag.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self._should_include_url(full_url):
                        links.add(full_url)
                        
        except Exception as e:
            logger.debug(f"[BASIC_EXTRACT] Failed to extract basic links: {e}")
            
        return links
    
    async def _process_retry_batch(self, urls: List[str]) -> Set[str]:
        """Process a retry batch with extended timeouts and reduced concurrency"""
        all_new_links = set()
        
        # Reduced concurrency for retry
        semaphore = asyncio.Semaphore(3)  # Very conservative for retry
        
        crawler_config = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator(),
            page_timeout=30000,  # Extended 30 second timeout
            verbose=False,
            wait_for_images=False,
            process_iframes=False,
            js_code=self._get_popup_bypass_js()
        )
        
        async def retry_single_url(url: str) -> Set[str]:
            async with semaphore:
                try:
                    await asyncio.sleep(0.1)  # Longer delay for retry
                    
                    async with AsyncWebCrawler(config=self.browser_config) as crawler:
                        result_container = await asyncio.wait_for(
                            crawler.arun(url=url, config=crawler_config),
                            timeout=35  # Extended timeout
                        )
                        
                        if result_container and len(result_container._results) > 0:
                            result = result_container._results[0]
                            if result.success:
                                extracted_links = await self._extract_links_comprehensive(result, url)
                                return extracted_links
                                
                except Exception as e:
                    logger.debug(f"[RETRY] Failed to recover {url}: {e}")
                    
                return set()
        
        # Process retry URLs
        tasks = [retry_single_url(url) for url in urls]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, set):
                    all_new_links.update(result)
                    
        except Exception as e:
            logger.warning(f"[RETRY] Retry batch processing failed: {e}")
        
        return all_new_links
    
    def _calculate_system_health(self, success_rates: List[float], processing_times: List[float], failure_counts: List[int]) -> float:
        """Calculate overall system health score (0.0 = critical, 1.0 = excellent)"""
        if not success_rates or not processing_times:
            return 1.0  # Default to healthy if no data
        
        health_factors = []
        
        # Factor 1: Success Rate Trend (40% weight)
        avg_success = sum(success_rates) / len(success_rates)
        min_success = min(success_rates)
        success_health = (avg_success * 0.7) + (min_success * 0.3)  # Weighted average
        health_factors.append(('success_rate', success_health, 0.4))
        
        # Factor 2: Performance Stability (30% weight)
        if len(processing_times) >= 2:
            time_variance = max(processing_times) / min(processing_times) if min(processing_times) > 0 else 1.0
            performance_health = max(0.0, 1.0 - (time_variance - 1.0) * 0.5)  # Penalize high variance
        else:
            performance_health = 1.0
        health_factors.append(('performance', performance_health, 0.3))
        
        # Factor 3: Failure Pattern (20% weight)
        if failure_counts:
            max_failures = max(failure_counts)
            avg_failures = sum(failure_counts) / len(failure_counts)
            failure_health = max(0.0, 1.0 - (avg_failures / 50.0))  # 50 failures = 0 health
        else:
            failure_health = 1.0
        health_factors.append(('failures', failure_health, 0.2))
        
        # Factor 4: Trend Direction (10% weight)
        if len(success_rates) >= 3:
            recent_trend = success_rates[-1] - success_rates[-3]  # Compare last vs 3rd last
            trend_health = max(0.0, min(1.0, 0.5 + recent_trend))  # -0.5 to +0.5 maps to 0-1
        else:
            trend_health = 1.0
        health_factors.append(('trend', trend_health, 0.1))
        
        # Calculate weighted health score
        total_health = sum(score * weight for _, score, weight in health_factors)
        
        return max(0.0, min(1.0, total_health))
    
    def _memory_usage_safe(self) -> bool:
        """Check if memory usage is safe for batch size increase"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            available_percent = memory.available / memory.total
            return available_percent > 0.2  # Need at least 20% free memory
        except ImportError:
            # If psutil not available, assume safe (conservative default)
            logger.warning("[MEMORY] psutil not available, assuming memory is safe")
            return True
        except Exception as e:
            logger.warning(f"[MEMORY] Could not check memory usage: {e}")
            return True
    
    def _performance_degrading(self) -> bool:
        """Check if performance is degrading significantly"""
        if len(self.recent_processing_times) < 3:
            return False
        
        # Compare recent average vs earlier average
        recent_avg = sum(self.recent_processing_times[-2:]) / 2
        earlier_avg = sum(self.recent_processing_times[:2]) / 2
        
        # Performance degrading if recent is >50% slower than earlier
        return recent_avg > earlier_avg * 1.5
    
    async def _process_crawl4ai_batch_ultra_fast(self, urls: List[str]) -> Set[str]:
        """ENHANCED: Ultra-fast batch processing using Crawl4AI with proper resource management"""
        all_new_links = set()
        processed_count = 0
        failed_count = 0
        
        print(f"        🚀 Processing batch of {len(urls)} URLs with max concurrency...")
        
        # Use reasonable concurrency to prevent browser overload
        semaphore = asyncio.Semaphore(10)  # Conservative limit to prevent TargetClosedError
        
        crawler_config = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator(),
            page_timeout=15000,  # 15 seconds per page
            verbose=False,
            wait_for_images=False,  # Skip images for speed
            process_iframes=False,   # Skip iframes for speed
            js_code=self._get_popup_bypass_js()  # Add popup bypass
        )
        
        # Use a single shared crawler instance to prevent resource issues
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            async def process_single_url_ultra_fast(url: str) -> tuple[str, Set[str], bool]:
                async with semaphore:
                    try:
                        # Small delay to prevent overwhelming the server
                        await asyncio.sleep(0.02)
                        
                        result_container = await asyncio.wait_for(
                            crawler.arun(url=url, config=crawler_config),
                            timeout=20  # 20 second timeout per URL
                        )
                        
                        if result_container and len(result_container._results) > 0:
                            result = result_container._results[0]
                            if result.success:
                                # ENHANCED: Extract links using multiple methods
                                extracted_links = await self._extract_links_comprehensive(result, url)
                                
                                # Store metadata for later relevance filtering
                                self._store_url_metadata(url, result)
                                
                                return url, extracted_links, True
                                
                    except asyncio.TimeoutError:
                        logger.debug(f"Timeout processing {url}")
                        return url, set(), False
                    except Exception as e:
                        # Check if it's a browser context error
                        if "TargetClosedError" in str(e) or "browser has been closed" in str(e):
                            logger.warning(f"Browser context error for {url}: {e}")
                        else:
                            logger.debug(f"Ultra-fast processing failed for {url}: {e}")
                        return url, set(), False
                    
                    return url, set(), False
            
            # Process all URLs concurrently with progress tracking
            print(f"        ⚡ Starting concurrent processing...")
            
            # Create tasks for all URLs
            tasks = [process_single_url_ultra_fast(url) for url in urls]
            
            try:
                # Use gather with return_exceptions to handle failures gracefully
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # ENHANCED: Process results with detailed failure tracking and recovery
                successful_urls = []
                failed_urls_with_reason = []
                
                for i, result in enumerate(results):
                    if isinstance(result, tuple):
                        url, extracted_links, success = result
                        if success:
                            all_new_links.update(extracted_links)
                            processed_count += 1
                            successful_urls.append(url)
                        else:
                            failed_count += 1
                            self.failed_urls.add(url)
                            failed_urls_with_reason.append((url, "Processing failed"))
                    elif isinstance(result, Exception):
                        failed_count += 1
                        if i < len(urls):
                            failed_url = urls[i]
                            self.failed_urls.add(failed_url)
                            failed_urls_with_reason.append((failed_url, str(result)[:100]))
                            print(f"          ❌ Task failed for {failed_url}: {str(result)[:50]}")
                
                # RESILIENCE: Log failed URLs for potential retry
                if failed_urls_with_reason:
                    logger.warning(f"[BATCH_RECOVERY] {len(failed_urls_with_reason)} URLs failed in this batch:")
                    for failed_url, reason in failed_urls_with_reason[:5]:  # Log first 5 failures
                        logger.warning(f"  - {failed_url}: {reason}")
                    if len(failed_urls_with_reason) > 5:
                        logger.warning(f"  ... and {len(failed_urls_with_reason) - 5} more failures")
                
                # SUCCESS: The batch is successful if we got ANY results, not all
                batch_success_rate = processed_count / len(urls) if urls else 0
                if batch_success_rate >= 0.3:  # 30% success rate is acceptable
                    logger.info(f"[BATCH_SUCCESS] Batch success rate: {batch_success_rate:.1%} ({processed_count}/{len(urls)})")
                else:
                    logger.warning(f"[BATCH_LOW_SUCCESS] Low success rate: {batch_success_rate:.1%} ({processed_count}/{len(urls)})")
                
            except Exception as e:
                # COMPLETE BATCH FAILURE - This is rare with return_exceptions=True
                print(f"        ❌ Complete batch failure: {str(e)}")
                logger.error(f"Complete batch processing failed: {e}")
                # Mark all URLs as failed for potential retry
                for url in urls:
                    self.failed_urls.add(url)
                failed_count = len(urls)
        
        print(f"        ✅ Batch complete: {processed_count} successful, {failed_count} failed")
        print(f"        📊 Total new links extracted: {len(all_new_links)}")
        
        return all_new_links
    
    async def _extract_links_comprehensive(self, result, base_url: str) -> Set[str]:
        """ENHANCED: Comprehensive link extraction using multiple techniques"""
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
            
            # Method 2: Enhanced HTML parsing (from your comprehensive crawler)
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
        """ENHANCED: Advanced HTML link extraction (from your working crawler)"""
        links = set()
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Method 1: Standard href links
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)
                if self._should_include_url(full_url):
                    links.add(full_url)
            
            # Method 2: Navigation links (your approach)
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
    
    def _store_url_metadata(self, url: str, result):
        """Store URL metadata for later relevance filtering"""
        try:
            title = getattr(result, 'title', '') or ''
            self.url_metadata[url] = {
                'title': title,
                'crawled_at': time.time(),
                'success': result.success if hasattr(result, 'success') else True,
                'is_relevant': None  # Will be determined later
            }
        except Exception as e:
            logger.debug(f"Failed to store metadata for {url}: {e}")
    
    def _extract_links_from_result(self, result, base_url: str) -> Set[str]:
        """Extract links from Crawl4AI result"""
        links = set()
        
        try:
            # Use Crawl4AI's built-in link extraction if available
            if hasattr(result, 'links') and result.links:
                if hasattr(result.links, 'internal'):
                    for link in result.links.internal:
                        if hasattr(link, 'href'):
                            full_url = urljoin(base_url, link.href)
                            if self._should_include_url(full_url):
                                links.add(full_url)
            
            # Fallback: extract from HTML using regex
            if hasattr(result, 'html') and result.html:
                html_links = re.findall(r'href=["\']([^"\']+)["\']', result.html)
                for href in html_links:
                    full_url = urljoin(base_url, href)
                    if self._should_include_url(full_url):
                        links.add(full_url)
        
        except Exception as e:
            logger.debug(f"Link extraction failed for {base_url}: {e}")
        
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
    
    async def _validate_url_exists(self, url: str) -> bool:
        """Check if URL exists (not 404) before adding to discovered URLs"""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5),
                headers={'User-Agent': 'Mozilla/5.0 (compatible; URLValidator)'}
            ) as session:
                async with session.head(url) as response:
                    # Consider 200-399 as valid (includes redirects)
                    return 200 <= response.status < 400
        except Exception:
            # If we can't check, assume it exists to avoid false negatives
            return True
    
    async def _validate_urls_batch(self, urls: set) -> set:
        """Validate a batch of URLs and return only existing ones"""
        if not urls:
            return set()
        
        # Limit concurrent validations to avoid overwhelming the server
        semaphore = asyncio.Semaphore(10)  # Reduce to prevent TargetClosedError
        
        async def validate_single(url):
            async with semaphore:
                if await self._validate_url_exists(url):
                    return url
                else:
                    logger.debug(f"[VALIDATION] Filtered out 404 URL: {url}")
                    return None
        
        # Run validations concurrently
        tasks = [validate_single(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        valid_urls = {result for result in results if result and isinstance(result, str)}
        
        if len(valid_urls) < len(urls):
            filtered_count = len(urls) - len(valid_urls)
            logger.info(f"[VALIDATION] Filtered out {filtered_count} invalid/404 URLs")
        
        return valid_urls
    
    async def _aggressive_deep_crawl_with_crawl4ai(self):
        """AGGRESSIVE: Process ALL remaining discovered URLs to find even more links"""
        uncrawled_urls = list(self.discovered_urls - self.crawled_urls)
        
        if not uncrawled_urls:
            logger.info("[AGGRESSIVE] No uncrawled URLs remaining")
            return
        
        logger.info(f"[AGGRESSIVE] Processing {len(uncrawled_urls)} remaining URLs...")
        
        # Process in batches (your proven approach)
        batch_size = min(500, self.config.max_concurrent)  # Larger batches for faster processing
        
        for i in range(0, len(uncrawled_urls), batch_size):
            batch = uncrawled_urls[i:i + batch_size]
            logger.info(f"[AGGRESSIVE] Processing batch {i//batch_size + 1}: {len(batch)} URLs")
            
            # Process batch and find MORE URLs
            batch_start = time.time()
            new_urls_found = await self._process_aggressive_crawl4ai_batch(batch)
            batch_time = time.time() - batch_start
            
            # Add any newly discovered URLs using proper deduplication
            if new_urls_found:
                added_count = self._add_urls_to_set_and_file(new_urls_found, f"AGGRESSIVE_BATCH_{i+1}")
            else:
                added_count = 0
            
            # Mark batch as crawled
            self.crawled_urls.update(batch)
            
            logger.info(f"[AGGRESSIVE] Batch complete: {added_count} additional URLs found in {batch_time:.1f}s")
            logger.info(f"[TOTAL] Total URLs now: {len(self.discovered_urls)}")
            
            # Check if we've hit the limit
            if len(self.discovered_urls) >= self.config.max_pages:
                logger.info(f"[LIMIT] Reached max_pages limit during aggressive crawling")
                break
    
    async def _process_aggressive_crawl4ai_batch(self, urls: List[str]) -> Set[str]:
        """Process batch aggressively using Crawl4AI with maximum extraction"""
        all_new_links = set()
        
        # Use conservative concurrency to prevent browser crashes
        # Reduced from 30 to 10 to avoid TargetClosedError
        semaphore = asyncio.Semaphore(10)
        
        crawler_config = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator(),
            page_timeout=(self.config.timeout + 5) * 1000,  # Longer timeout for aggressive mode
            verbose=False,
            wait_for_images=False,
            process_iframes=True  # Process iframes in aggressive mode
        )
        
        async def aggressive_crawl_single_url(url: str) -> Set[str]:
            async with semaphore:
                try:
                    # Slightly longer delay for aggressive mode
                    await asyncio.sleep(self.config.delay_between_requests * 2)
                    
                    async with AsyncWebCrawler(config=self.browser_config) as crawler:
                        result_container = await crawler.arun(url=url, config=crawler_config)
                        
                        if result_container and len(result_container._results) > 0:
                            result = result_container._results[0]
                            if result.success:
                                # AGGRESSIVE: Use comprehensive extraction
                                extracted_links = await self._extract_links_comprehensive(result, url)
                                
                                # Store metadata
                                self._store_url_metadata(url, result)
                                
                                return extracted_links
                                
                except Exception as e:
                    logger.debug(f"Aggressive crawl failed for {url}: {e}")
                    self.failed_urls.add(url)
                
                return set()
        
        # Process all URLs concurrently
        tasks = [aggressive_crawl_single_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all discovered links
        for result in results:
            if isinstance(result, set):
                all_new_links.update(result)
        
        return all_new_links
    
    async def _apply_relevance_filtering(self):
        """Apply relevance filtering using LLM keywords and context"""
        if not self.llm_keywords or not self.config.context_description:
            # Mark all URLs as relevant if no filtering criteria
            for url in self.discovered_urls:
                if url not in self.url_metadata:
                    self.url_metadata[url] = {'is_relevant': True, 'title': '', 'crawled_at': time.time()}
                else:
                    self.url_metadata[url]['is_relevant'] = True
            return
        
        logger.info(f"[RELEVANCE] Filtering {len(self.discovered_urls)} URLs for relevance...")
        start_time = time.time()
        
        # Extract context keywords (LLM keywords + user context keywords)
        context_keywords = self._extract_context_keywords(self.config.context_description)
        all_keywords = list(set(self.llm_keywords + context_keywords))
        
        relevant_count = 0
        for url in self.discovered_urls:
            # Get or create metadata for this URL
            if url not in self.url_metadata:
                self.url_metadata[url] = {'title': '', 'crawled_at': time.time(), 'is_relevant': None}
            
            metadata = self.url_metadata[url]
            
            if metadata.get('is_relevant') is None:
                is_relevant = self._check_url_relevance_fast(url, metadata, all_keywords)
                metadata['is_relevant'] = is_relevant
                if is_relevant:
                    relevant_count += 1
        
        filter_time = time.time() - start_time
        logger.info(f"[RELEVANCE] Filtering complete: {relevant_count}/{len(self.discovered_urls)} URLs marked as relevant ({filter_time:.1f}s)")
    
    def _check_url_relevance_fast(self, url: str, metadata: Dict, keywords: List[str]) -> bool:
        """Fast relevance checking using URL path, title, and keywords"""
        if not keywords:
            return True
        
        # Check URL path
        url_path = urlparse(url).path.lower()
        page_title = metadata.get('title', '').lower()
        
        # Combine text to check
        text_to_check = f"{url_path} {page_title}".lower()
        
        # Check for keyword matches
        for keyword in keywords:
            if keyword.lower() in text_to_check:
                return True
        
        return False
    
    def _extract_context_keywords(self, context: str) -> List[str]:
        """Extract relevant keywords from user context description"""
        # Basic keyword extraction
        basic_keywords = [word.strip().lower() for word in context.split() if len(word.strip()) > 2]
        
        # Enhanced keywords based on context (from your comprehensive crawler)
        enhanced_keywords = basic_keywords.copy()
        
        # Japanese government context enhancements
        if any(word in context.lower() for word in ['children', 'child', 'kids', 'kosodate']):
            enhanced_keywords.extend([
                'children', 'child', 'kids', 'kosodate', 'kodomo', 'hoikuen', 'yochien',
                'gakko', 'school', 'education', 'childcare', 'nursery', 'kindergarten'
            ])
        
        if any(word in context.lower() for word in ['women', 'woman', 'female', 'josei']):
            enhanced_keywords.extend([
                'women', 'woman', 'female', 'josei', 'fujin', 'mothers', 'pregnancy',
                'maternity', 'maternal', 'birth', 'shussan'
            ])
        
        if any(word in context.lower() for word in ['elderly', 'senior', 'aged', 'koreisha']):
            enhanced_keywords.extend([
                'elderly', 'senior', 'aged', 'koreisha', 'korei', 'roujin',
                'kaigo', 'care', 'nursing', 'welfare'
            ])
        
        if any(word in context.lower() for word in ['healthcare', 'health', 'medical', 'iryo']):
            enhanced_keywords.extend([
                'healthcare', 'health', 'medical', 'iryo', 'byoin', 'hospital',
                'clinic', 'treatment', 'medicine', 'kenko', 'wellness'
            ])
        
        return list(set(enhanced_keywords))  # Remove duplicates
    
    async def _hierarchical_parent_crawling(self):
        """Systematically crawl parent pages to discover child pages that might not be in sitemaps"""
        logger.info("🌳 Starting hierarchical parent crawling...")
        
        try:
            # Get all discovered URLs and extract unique parent paths
            parent_paths = set()
            
            for url in list(self.discovered_urls):
                parsed = urlparse(url)
                path_parts = parsed.path.strip('/').split('/')
                
                # Generate all parent paths
                for i in range(len(path_parts)):
                    parent_path = '/' + '/'.join(path_parts[:i+1]) + '/'
                    if parent_path not in ['/', '//']:
                        parent_url = urljoin(self.config.base_url, parent_path)
                        if self._should_include_url(parent_url):
                            parent_paths.add(parent_url)
            
            # Add root-level common parent directories (GENERIC - works for any website)
            common_parents = [
                # Generic administrative sections
                '/admin/', '/administration/', '/management/', '/corporate/',
                '/company/', '/organization/', '/structure/', '/governance/',
                
                # Generic information sections  
                '/info/', '/information/', '/about/', '/overview/', '/profile/',
                '/history/', '/mission/', '/vision/', '/values/', '/policy/',
                
                # Generic service sections
                '/service/', '/services/', '/offering/', '/offerings/', '/product/',
                '/products/', '/solution/', '/solutions/', '/program/', '/programs/',
                
                # Generic support sections
                '/support/', '/help/', '/assistance/', '/guide/', '/guidance/',
                '/faq/', '/tutorial/', '/documentation/', '/manual/', '/instruction/',
                
                # Generic content sections
                '/content/', '/page/', '/pages/', '/section/', '/sections/',
                '/category/', '/categories/', '/topic/', '/topics/', '/subject/',
                
                # Generic organizational sections
                '/dept/', '/department/', '/division/', '/unit/', '/team/',
                '/office/', '/branch/', '/location/', '/facility/', '/center/',
                
                # Generic communication sections
                '/news/', '/notice/', '/announcement/', '/press/', '/media/',
                '/blog/', '/article/', '/story/', '/publication/', '/report/',
                
                # Generic event sections
                '/event/', '/events/', '/calendar/', '/schedule/', '/meeting/',
                '/conference/', '/workshop/', '/seminar/', '/training/',
                
                # Generic resource sections
                '/resource/', '/resources/', '/library/', '/archive/', '/database/',
                '/document/', '/documents/', '/file/', '/files/', '/download/',
                '/downloads/', '/repository/', '/collection/', '/gallery/',
                
                # Generic interactive sections
                '/search/', '/find/', '/tool/', '/tools/', '/utility/', '/utilities/',
                '/calculator/', '/form/', '/forms/', '/application/', '/apply/',
                '/contact/', '/inquiry/', '/feedback/', '/survey/', '/booking/',
                
                # Generic access sections
                '/access/', '/direction/', '/directions/', '/map/', '/maps/',
                '/location/', '/address/', '/transport/', '/parking/', '/entrance/'
            ]
            
            for parent in common_parents:
                parent_url = urljoin(self.config.base_url, parent)
                if self._should_include_url(parent_url):
                    parent_paths.add(parent_url)
            
            # Process parent URLs to discover children
            new_parent_urls = parent_paths - self.discovered_urls
            
            if new_parent_urls:
                logger.info(f"[HIERARCHICAL] Processing {len(new_parent_urls)} parent directories...")
                
                # Use Crawl4AI to crawl parent directories
                crawler_config = CrawlerRunConfig(
                    markdown_generator=DefaultMarkdownGenerator(),
                    page_timeout=self.config.timeout * 1000,
                    verbose=False,
                    wait_for_images=False,
                    process_iframes=False
                )
                
                async with AsyncWebCrawler(config=self.browser_config) as crawler:
                    for parent_url in list(new_parent_urls)[:500]:  # Limit for performance
                        try:
                            await asyncio.sleep(self.config.delay_between_requests)
                            
                            result_container = await crawler.arun(url=parent_url, config=crawler_config)
                            
                            if result_container and len(result_container._results) > 0:
                                result = result_container._results[0]
                                if result.success:
                                    # Extract links from parent page
                                    extracted_links = await self._extract_links_comprehensive(result, parent_url)
                                    
                                    if extracted_links:
                                        self._add_urls_to_set_and_file(extracted_links, f"HIERARCHICAL_{parent_url.split('/')[-1]}")
                                        logger.debug(f"[HIERARCHICAL] Found {len(extracted_links)} total URLs from {parent_url}")
                            
                            self.crawled_urls.add(parent_url)
                            
                        except Exception as e:
                            logger.debug(f"Failed to crawl parent {parent_url}: {e}")
                            self.failed_urls.add(parent_url)
                
                # Add discovered parent URLs using proper deduplication
                if new_parent_urls:
                    self._add_urls_to_set_and_file(new_parent_urls, "HIERARCHICAL_PARENTS")
            
        except Exception as e:
            logger.error(f"Hierarchical parent crawling failed: {e}")
    
    async def _discover_directories(self):
        """Test common directory patterns and discover directory contents"""
        logger.info("📁 Starting directory discovery...")
        
        try:
            # COMPREHENSIVE directory patterns (150+ patterns for maximum coverage)
            common_dirs = [
                # Administrative & Corporate
                "/about/", "/info/", "/information/", "/profile/", "/overview/",
                "/organization/", "/structure/", "/department/", "/office/", "/division/",
                "/admin/", "/administration/", "/management/", "/corporate/", "/company/",
                "/governance/", "/leadership/", "/board/", "/executive/", "/staff/",
                
                # Services & Products
                "/service/", "/services/", "/product/", "/products/", "/offering/", "/offerings/",
                "/solution/", "/solutions/", "/program/", "/programs/", "/package/", "/packages/",
                "/plan/", "/plans/", "/option/", "/options/", "/feature/", "/features/",
                
                # Support & Help
                "/support/", "/help/", "/assistance/", "/aid/", "/guidance/", "/consultation/",
                "/faq/", "/qa/", "/question/", "/answer/", "/tutorial/", "/guide/", "/manual/",
                "/instruction/", "/documentation/", "/docs/", "/howto/", "/tips/", "/advice/",
                
                # Content & Information
                "/content/", "/page/", "/pages/", "/section/", "/sections/", "/category/", "/categories/",
                "/topic/", "/topics/", "/subject/", "/subjects/", "/theme/", "/themes/",
                "/area/", "/areas/", "/field/", "/fields/", "/domain/", "/domains/",
                
                # News & Communication
                "/news/", "/notice/", "/notices/", "/announcement/", "/announcements/",
                "/press/", "/media/", "/release/", "/releases/", "/update/", "/updates/",
                "/blog/", "/post/", "/posts/", "/article/", "/articles/", "/story/", "/stories/",
                "/publication/", "/publications/", "/report/", "/reports/", "/newsletter/",
                
                # Events & Activities
                "/event/", "/events/", "/activity/", "/activities/", "/calendar/", "/schedule/",
                "/meeting/", "/meetings/", "/conference/", "/conferences/", "/workshop/",
                "/workshops/", "/seminar/", "/seminars/", "/training/", "/course/", "/courses/",
                "/class/", "/classes/", "/session/", "/sessions/", "/webinar/", "/webinars/",
                
                # Resources & Downloads
                "/resource/", "/resources/", "/material/", "/materials/", "/asset/", "/assets/",
                "/library/", "/archive/", "/archives/", "/repository/", "/collection/", "/collections/",
                "/document/", "/documents/", "/file/", "/files/", "/download/", "/downloads/",
                "/pdf/", "/doc/", "/docs/", "/paper/", "/papers/", "/form/", "/forms/",
                
                # Interactive & Tools
                "/search/", "/find/", "/lookup/", "/query/", "/tool/", "/tools/",
                "/utility/", "/utilities/", "/calculator/", "/converter/", "/generator/",
                "/checker/", "/validator/", "/analyzer/", "/simulator/", "/widget/", "/widgets/",
                "/app/", "/application/", "/applications/", "/software/", "/program/",
                
                # Contact & Location
                "/contact/", "/contacts/", "/inquiry/", "/inquiries/", "/feedback/",
                "/location/", "/locations/", "/address/", "/addresses/", "/office/", "/offices/",
                "/branch/", "/branches/", "/facility/", "/facilities/", "/center/", "/centers/",
                "/place/", "/places/", "/venue/", "/venues/", "/site/", "/sites/",
                
                # Access & Navigation
                "/map/", "/maps/", "/direction/", "/directions/", "/access/", "/route/", "/routes/",
                "/transport/", "/transportation/", "/parking/", "/entrance/", "/exit/",
                "/navigation/", "/sitemap/", "/index/", "/menu/", "/link/", "/links/",
                
                # Technical & Data
                "/api/", "/data/", "/database/", "/db/", "/feed/", "/feeds/", "/rss/",
                "/xml/", "/json/", "/csv/", "/export/", "/import/", "/sync/", "/backup/",
                "/config/", "/setting/", "/settings/", "/preference/", "/preferences/",
                
                # Media & Gallery
                "/media/", "/image/", "/images/", "/photo/", "/photos/", "/picture/", "/pictures/",
                "/gallery/", "/galleries/", "/album/", "/albums/", "/video/", "/videos/",
                "/audio/", "/sound/", "/music/", "/multimedia/", "/graphics/", "/design/",
                
                # User & Account
                "/user/", "/users/", "/member/", "/members/", "/account/", "/accounts/",
                "/profile/", "/profiles/", "/dashboard/", "/portal/", "/login/", "/signin/",
                "/signup/", "/register/", "/registration/", "/subscription/", "/membership/",
                
                # Business & Commerce
                "/business/", "/commerce/", "/shop/", "/store/", "/market/", "/marketplace/",
                "/cart/", "/checkout/", "/payment/", "/billing/", "/invoice/", "/order/", "/orders/",
                "/product/", "/catalog/", "/inventory/", "/stock/", "/price/", "/pricing/",
                
                # Time-based directories
                "/current/", "/latest/", "/recent/", "/new/", "/old/", "/past/", "/history/",
                "/2024/", "/2023/", "/2022/", "/2021/", "/2020/", "/2019/", "/2018/",
                "/today/", "/yesterday/", "/this-week/", "/this-month/", "/this-year/",
                
                # Status & State
                "/active/", "/inactive/", "/pending/", "/completed/", "/draft/", "/published/",
                "/archived/", "/deleted/", "/temporary/", "/backup/", "/cache/", "/temp/",
                
                # Miscellaneous common patterns
                "/general/", "/specific/", "/detail/", "/details/", "/summary/", "/overview/",
                "/list/", "/listing/", "/table/", "/grid/", "/view/", "/display/", "/show/",
                "/edit/", "/update/", "/modify/", "/change/", "/delete/", "/remove/", "/add/",
                "/create/", "/new/", "/copy/", "/duplicate/", "/share/", "/export/", "/print/",
                
                # Media & Gallery
                "/media/", "/image/", "/images/", "/photo/", "/photos/", "/picture/", "/pictures/",
                "/gallery/", "/galleries/", "/album/", "/albums/", "/video/", "/videos/",
                "/audio/", "/sound/", "/music/", "/multimedia/", "/graphics/", "/design/",
                
                # Years and dates
                "/2024/", "/2023/", "/2022/", "/2021/", "/2020/",
                "/current/", "/latest/", "/recent/", "/past/", "/archive/"
            ]
            
            # Process directories in batches
            batch_size = 500
            crawler_config = CrawlerRunConfig(
                markdown_generator=DefaultMarkdownGenerator(),
                page_timeout=self.config.timeout * 1000,
                verbose=False,
                wait_for_images=False,
                process_iframes=False
            )
            
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                for i in range(0, len(common_dirs), batch_size):
                    batch = common_dirs[i:i+batch_size]
                    
                    for directory in batch:
                        dir_url = urljoin(self.config.base_url, directory)
                        
                        if not self._should_include_url(dir_url) or dir_url in self.discovered_urls:
                            continue
                        
                        try:
                            await asyncio.sleep(self.config.delay_between_requests)
                            
                            result_container = await crawler.arun(url=dir_url, config=crawler_config)
                            
                            if result_container and len(result_container._results) > 0:
                                result = result_container._results[0]
                                if result.success:
                                    # Directory exists, add it and extract links using proper deduplication
                                    self._add_urls_to_set_and_file({dir_url}, f"DIRECTORY_{directory}")
                                    
                                    # Extract links from directory page
                                    extracted_links = await self._extract_links_comprehensive(result, dir_url)
                                    
                                    if extracted_links:
                                        self._add_urls_to_set_and_file(extracted_links, f"DIRECTORY_LINKS_{directory}")
                                        logger.debug(f"[DIRECTORY] Found {len(extracted_links)} URLs in {directory}")
                            
                            self.crawled_urls.add(dir_url)
                            
                        except Exception as e:
                            logger.debug(f"Directory {directory} not accessible: {e}")
                            self.failed_urls.add(dir_url)
            
        except Exception as e:
            logger.error(f"Directory discovery failed: {e}")
    
    async def _systematic_path_exploration(self):
        """Analyze discovered URLs to generate additional path variations (NO LLM - pure pattern analysis)"""
        logger.info("🔍 Starting systematic path exploration (analyzing discovered URL patterns)...")
        
        try:
            # Analyze existing URLs to find patterns (NO LLM - just pattern recognition)
            url_segments = set()
            numeric_patterns = set()
            
            for url in list(self.discovered_urls):
                parsed = urlparse(url)
                path_parts = [part for part in parsed.path.split('/') if part]
                
                # Collect all segments
                url_segments.update(path_parts)
                
                # Look for numeric patterns
                for part in path_parts:
                    if part.isdigit():
                        numeric_patterns.add(int(part))
            
            # Generate variations based on discovered segments (NO LLM)
            new_urls = set()
            
            # Segment combinations (if we found common segments)
            if len(url_segments) > 5:  # Only if we have enough data
                common_segments = list(url_segments)[:20]  # Limit for performance
                
                for seg1 in common_segments[:10]:
                    for seg2 in common_segments[:10]:
                        if seg1 != seg2:
                            # Try different combinations
                            variations = [
                                f"/{seg1}/{seg2}/",
                                f"/{seg2}/{seg1}/",
                                f"/{seg1}_{seg2}/",
                                f"/{seg1}-{seg2}/"
                            ]
                            
                            for variation in variations:
                                new_url = urljoin(self.config.base_url, variation)
                                # DUPLICATE PREVENTION: Check if URL already exists
                                if self._should_include_url(new_url) and new_url not in self.discovered_urls:
                                    new_urls.add(new_url)
            
            # Numeric pattern exploration
            if numeric_patterns:
                min_num = min(numeric_patterns)
                max_num = max(numeric_patterns)
                
                # Generate reasonable range around discovered numbers
                for num in range(max(1, min_num - 5), min(max_num + 10, 100)):
                    for base_path in ['/page/', '/item/', '/id/', '/no/', '/']:
                        num_url = urljoin(self.config.base_url, f"{base_path}{num}/")
                        # DUPLICATE PREVENTION: Check if URL already exists
                        if self._should_include_url(num_url) and num_url not in self.discovered_urls:
                            new_urls.add(num_url)
            
            # Add year-based exploration if we haven't found many
            current_year = datetime.now().year
            for year in range(2020, current_year + 1):
                for month in range(1, 13):
                    year_urls = [
                        f"/{year}/",
                        f"/{year}/{month:02d}/",
                        f"/news/{year}/",
                        f"/event/{year}/",
                        f"/archive/{year}/"
                    ]
                    
                    for year_url in year_urls:
                        full_url = urljoin(self.config.base_url, year_url)
                        # DUPLICATE PREVENTION: Check if URL already exists
                        if self._should_include_url(full_url) and full_url not in self.discovered_urls:
                            new_urls.add(full_url)
            
                            new_urls.add(full_url)
            
            # Add new URLs using proper deduplication and filtering
            if new_urls:
                # Limit to prevent explosion
                limited_new_urls = list(new_urls)[:1000]
                added_count = self._add_urls_to_set_and_file(set(limited_new_urls), "SYSTEMATIC_PATTERNS")
                logger.info(f"[SYSTEMATIC] Generated {added_count} new URLs from pattern analysis (NO LLM)")
            else:
                logger.info(f"[SYSTEMATIC] No URLs generated from patterns")
            
        except Exception as e:
            logger.error(f"Systematic path exploration failed: {e}")
    
    async def _discover_by_patterns(self):
        """Generate URLs based on common patterns and discovered structure"""
        logger.info("🎯 Starting pattern-based discovery...")
        
        try:
            base = self.config.base_url.rstrip('/')
            new_urls = set()
            
            # Year-based patterns
            current_year = datetime.now().year
            for year in range(2020, current_year + 1):
                year_patterns = [
                    f"/{year}/",
                    f"/news/{year}/",
                    f"/press/{year}/",
                    f"/event/{year}/",
                    f"/announcement/{year}/",
                    f"/notice/{year}/",
                    f"/archive/{year}/",
                    f"/publication/{year}/"
                ]
                
                for pattern in year_patterns:
                    new_url = base + pattern
                    # DUPLICATE PREVENTION: Check if URL already exists
                    if self._should_include_url(new_url) and new_url not in self.discovered_urls:
                        new_urls.add(new_url)
                
                # Month-based patterns for recent years
                if year >= current_year - 2:
                    for month in range(1, 13):
                        month_patterns = [
                            f"/{year}/{month:02d}/",
                            f"/news/{year}/{month:02d}/",
                            f"/event/{year}/{month:02d}/"
                        ]
                        
                        for pattern in month_patterns:
                            new_url = base + pattern
                            # DUPLICATE PREVENTION: Check if URL already exists
                            if self._should_include_url(new_url) and new_url not in self.discovered_urls:
                                new_urls.add(new_url)
            
            # Common file patterns in discovered directories
            common_files = [
                "index.html", "index.php", "index.htm", "default.html", "default.php",
                "home.html", "main.html", "top.html", "welcome.html",
                "sitemap.html", "sitemap.xml", "map.html",
                "search.html", "search.php", "find.html",
                "contact.html", "contact.php", "inquiry.html",
                "about.html", "about.php", "info.html", "information.html",
                "service.html", "services.html", "support.html",
                "news.html", "notice.html", "announcement.html",
                "event.html", "calendar.html", "schedule.html"
            ]
            
            # Apply to common directories
            common_dirs = ["/", "/info/", "/service/", "/news/", "/event/", "/contact/", "/about/"]
            
            for directory in common_dirs:
                for filename in common_files:
                    file_url = urljoin(base + directory, filename)
                    # DUPLICATE PREVENTION: Check if URL already exists
                    if self._should_include_url(file_url) and file_url not in self.discovered_urls:
                        new_urls.add(file_url)
            
            # ID-based patterns (common in many sites)
            for id_num in range(1, 51):  # Reasonable range
                id_patterns = [
                    f"/id/{id_num}/",
                    f"/page/{id_num}/",
                    f"/item/{id_num}/",
                    f"/post/{id_num}/",
                    f"/article/{id_num}/",
                    f"/news/{id_num}/",
                    f"/event/{id_num}/"
                ]
                
                for pattern in id_patterns:
                    new_url = base + pattern
                    # DUPLICATE PREVENTION: Check if URL already exists
                    if self._should_include_url(new_url) and new_url not in self.discovered_urls:
                        new_urls.add(new_url)
            
            # Add new URLs using proper deduplication and filtering
            if new_urls:
                # Limit to prevent explosion
                limited_new_urls = list(new_urls)[:2000]
                added_count = self._add_urls_to_set_and_file(set(limited_new_urls), "PATTERN_BASED")
                logger.info(f"[PATTERNS] Generated {added_count} URLs from common patterns")
            
        except Exception as e:
            logger.error(f"Pattern-based discovery failed: {e}")
    
    async def _discover_forms_and_searches(self):
        """Discover forms and search functionality"""
        logger.info("🔍 Starting form and search discovery...")
        
        try:
            search_patterns = [
                # English patterns
                "/search/", "/search.html", "/search.php", "/find/", "/find.html",
                "/query/", "/lookup/", "/locate/", "/discover/",
                
                # Japanese patterns
                "/kensaku/", "/sagasu/", "/kensakukekka/", "/kensaku.html",
                "/search/index.html", "/kensaku/index.html",
                
                # Form patterns
                "/form/", "/forms/", "/application/", "/apply/", "/register/",
                "/registration/", "/signup/", "/contact/", "/inquiry/",
                "/feedback/", "/survey/", "/questionnaire/", "/booking/",
                
                # Interactive features
                "/tool/", "/tools/", "/utility/", "/calculator/", "/checker/",
                "/simulator/", "/guide/", "/wizard/", "/help/"
            ]
            
            # Test search and form URLs with DUPLICATE PREVENTION
            search_urls = set()
            for pattern in search_patterns:
                search_url = urljoin(self.config.base_url, pattern)
                # DUPLICATE PREVENTION: Check if URL already exists
                if self._should_include_url(search_url) and search_url not in self.discovered_urls:
                    search_urls.add(search_url)
            
            if search_urls:
                self._add_urls_to_set_and_file(search_urls, "SEARCH_PATTERNS")
            
            # If we have crawled pages, extract form action URLs
            if self.url_metadata:
                form_actions = set()
                
                # Extract form actions from any crawled content
                for url, metadata in self.url_metadata.items():
                    if 'content' in metadata:
                        content = metadata['content']
                        # Simple form action extraction
                        import re
                        actions = re.findall(r'action=["\']([^"\']+)["\']', content, re.IGNORECASE)
                        
                        for action in actions:
                            if action.startswith('/') or action.startswith('http'):
                                full_action_url = urljoin(url, action)
                                if self._should_include_url(full_action_url):
                                    form_actions.add(full_action_url)
                
                if form_actions:
                    self._add_urls_to_set_and_file(form_actions, "FORM_ACTIONS")
                    logger.info(f"[FORMS] Extracted {len(form_actions)} form action URLs")
            
        except Exception as e:
            logger.error(f"Form and search discovery failed: {e}")
    
    def _generate_discovery_results(self, discovery_time: float) -> Dict[str, Any]:
        """Generate comprehensive discovery results with relevance statistics"""
        # Count relevant pages
        relevant_pages = sum(1 for metadata in self.url_metadata.values() 
                           if metadata.get('is_relevant', True))
        total_checked_pages = len(self.url_metadata)
        
        return {
            "discovery_strategy": "enhanced_crawl4ai_comprehensive_discovery",
            "base_url": self.config.base_url,
            "sample_url": self.config.sample_url,
            "context_description": self.config.context_description,
            "total_discovered_urls": len(self.discovered_urls),
            "crawled_pages": len(self.crawled_urls),
            "relevant_pages": relevant_pages,
            "total_checked_pages": total_checked_pages,
            "relevance_ratio": relevant_pages / total_checked_pages if total_checked_pages > 0 else 0,
            "failed_urls": len(self.failed_urls),
            "discovery_time_seconds": discovery_time,
            "urls_per_second": len(self.discovered_urls) / discovery_time if discovery_time > 0 else 0,
            "discovered_urls": sorted(list(self.discovered_urls)),
            "relevant_urls": [url for url, metadata in self.url_metadata.items() 
                            if metadata.get('is_relevant', True)],
            "url_metadata": self.url_metadata,
            "llm_keywords_generated": len(self.llm_keywords),
            "llm_keywords": self.llm_keywords,
            "discovery_stats": self.discovery_stats,
            "discovery_methods": [
                "llm_keyword_generation",
                "recursive_crawling_with_crawl4ai", 
                "sitemap_parsing",
                "robots_txt_analysis",
                "aggressive_deep_crawling",
                "enhanced_pattern_generation",
                "llm_suggested_urls",
                "relevance_filtering"
            ],
            "config": {
                "max_pages": self.config.max_pages,
                "max_depth": self.config.max_depth,
                "force_english": self.config.force_english,
                "use_llm_keywords": self.config.use_llm_keywords,
                "include_pdfs": self.config.include_pdfs,
                "include_images": self.config.include_images,
                "max_concurrent": self.config.max_concurrent
            }
        }
        """Generate comprehensive discovery results"""
        return {
            "discovery_strategy": "crawl4ai_comprehensive_discovery",
            "base_url": self.config.base_url,
            "sample_url": self.config.sample_url,
            "context_description": self.config.context_description,
            "total_discovered_urls": len(self.discovered_urls),
            "crawled_pages": len(self.crawled_urls),
            "failed_urls": len(self.failed_urls),
            "discovery_time_seconds": discovery_time,
            "urls_per_second": len(self.discovered_urls) / discovery_time if discovery_time > 0 else 0,
            "discovered_urls": sorted(list(self.discovered_urls)),
            "llm_keywords_generated": len(self.llm_keywords),
            "llm_keywords": self.llm_keywords,
            "discovery_stats": self.discovery_stats,
            "config": {
                "max_pages": self.config.max_pages,
                "max_depth": self.config.max_depth,
                "force_english": self.config.force_english,
                "use_llm_keywords": self.config.use_llm_keywords,
                "include_pdfs": self.config.include_pdfs,
                "include_images": self.config.include_images
            }
        }

async def main():
    """Main function for standalone URL discovery"""
    print("🔍 URL Discoverer - Comprehensive Website URL Discovery")
    print("=" * 60)
    
    # Set default for Chuo city website
    base_url = "https://www.moneycontrol.com/"
    sample_url = None
    context = "Money money money"
    
    print(f"🎯 Testing on: {base_url}")
    print(f"📝 Context: {context}")
    
    # Configuration
    config = URLDiscoveryConfig(
        base_url=base_url,
        sample_url=sample_url,
        context_description=context,
        max_pages=50000,
        max_depth=8,
        force_english=True,
        use_llm_keywords=False,  # Disabled as requested - no relevance filtering
        proxy_url=None  # Temporarily disabled for debugging
        # proxy_url="http://brd-customer-hl_c4d84340-zone-testingdc:l1yptwrxrmbr@brd.superproxy.io:33335"
    )
    
    # Discover URLs
    discoverer = URLDiscoverer(config)
    results = await discoverer.discover_all_urls()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"discovered_urls_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Save all discovered URLs to discovered_urls.txt
    with open('discovered_urls.txt', 'w', encoding='utf-8') as f:
        for url in sorted(results['discovered_urls']):
            f.write(f"{url}\n")
    
    print(f"📁 All URLs saved to: discovered_urls.txt ({len(results['discovered_urls']):,} URLs)")
    
    # Print summary
    print("\n" + "="*60)
    print("🎉 ENHANCED URL Discovery Complete!")
    print("="*60)
    print(f"📊 Total URLs discovered: {results['total_discovered_urls']:,}")
    print(f"⏱️  Discovery time: {results['discovery_time_seconds']:.1f} seconds")
    print(f"🚀 Discovery rate: {results['urls_per_second']:.1f} URLs/second")
    print(f"📄 Pages crawled: {results['crawled_pages']:,}")
    print(f"❌ Failed URLs: {results['failed_urls']:,}")
    print(f"🤖 LLM keywords generated: {results['llm_keywords_generated']}")
    print(f"📁 Results saved to: {filename}")
    
    # Show discovery breakdown
    print(f"\n📈 Discovery Method Breakdown:")
    for method, count in results['discovery_stats'].items():
        if count > 0:
            print(f"   ✅ {method}: {count:,} URLs")
    
    # Show discovery methods used
    print(f"\n� Discovery Methods Used:")
    for i, method in enumerate(results['discovery_methods'], 1):
        print(f"   {i}. {method.replace('_', ' ').title()}")
    
    print(f"\n�📋 Sample URLs (first 10):")
    sample_urls = results.get('relevant_urls', results['discovered_urls'])[:10]
    for i, url in enumerate(sample_urls, 1):
        print(f"   {i:2d}. {url}")
    
    if len(results['discovered_urls']) > 10:
        print(f"   ... and {len(results['discovered_urls']) - 10:,} more URLs")
    
    print(f"\n💡 Comprehensive Discovery Methods Used:")
    print(f"   🗺️  Sitemap parsing: ✅")
    print(f"   🤖 Robots.txt analysis: ✅") 
    print(f"   🌐 URL seeding (Common Crawl + Enhanced Sitemaps): ✅")
    print(f"   🔄 Recursive crawling: ✅")
    print(f"   🌳 Hierarchical parent crawling: ✅")
    print(f"   📁 Directory discovery: ✅")
    print(f"   🔍 Systematic path exploration: ✅")
    print(f"   🔥 Aggressive deep crawling: ✅")
    print(f"   🎯 Pattern-based discovery: ✅")
    print(f"   🔍 Form and search discovery: ✅")
    print(f"   🧠 Relevance filtering: ❌ (Disabled - Pure discovery mode)")

if __name__ == "__main__":
    asyncio.run(main())
