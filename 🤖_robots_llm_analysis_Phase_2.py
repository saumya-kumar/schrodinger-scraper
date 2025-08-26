#!/usr/bin/env python3
"""
Phase 2: Robots.txt & LLMs.txt Analysis
Progressive Enhancement URL Discovery using Robot Files and AI Analysis

This module implements Phase 2 of the comprehensive URL discovery system:
- Robots.txt analysis and URL extraction
- AI.txt (LLM guidance file) analysis and URL extraction
- LLM-powered intelligent URL pattern generation
- AI-driven content type prediction
- Progressive enhancement: Basic → Stealth → Undetected → Proxy → HTTP fallback
- Efficient early termination when successful results are found

AI.txt Support:
- ai.txt → tells AI scrapers and LLMs what data they're allowed to use for training/generation
- Meta tag detection (noai, noimageai) for AI usage restrictions
- Similar to robots.txt but specifically for AI/LLM guidance

Progressive Enhancement Bricks:
🧱 BRICK 1: Basic Crawl4AI (robots.txt + ai.txt parsing)
🧱 BRICK 2: Crawl4AI + Stealth Mode
🧱 BRICK 3: Crawl4AI + Stealth + Undetected Browser
🧱 BRICK 4: Crawl4AI + Stealth + Undetected + Proxy
🧱 BRICK 5: HTTP Fallback (direct requests)
"""

import asyncio
import json
import os
import sys
import time
import logging
import re
import warnings
import atexit
from datetime import datetime
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Set, List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import aiohttp
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
        ProxyConfig, RoundRobinProxyStrategy, CacheMode
    )
    from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
    print("✅ Crawl4AI imported successfully with advanced features")
except ImportError:
    print("❌ Crawl4AI not installed. Install with: pip install crawl4ai")
    sys.exit(1)

# Google Gemini API for LLM analysis
try:
    import google.generativeai as genai
    print("✅ Google Generative AI imported successfully")
except ImportError:
    print("⚠️  google-generativeai not installed - LLM features will use fallback")
    genai = None

# Configure logging
warnings.simplefilter("ignore")
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

@dataclass
class RobotsLLMConfig:
    """Configuration for Robots.txt & AI.txt & LLM Analysis"""
    base_url: str
    
    # Discovery Settings
    max_urls: int = 10000
    timeout: int = 10
    max_concurrent: int = 5
    
    # AI.txt Support
    check_ai_txt: bool = True  # Check for ai.txt files
    check_ai_meta_tags: bool = True  # Check for noai/noimageai meta tags
    
    # LLM Configuration
    gemini_api_key: str = None
    use_llm_analysis: bool = True
    llm_model: str = "gemini-1.5-flash"
    
    # Proxy Configuration (BrightData)
    proxy_enabled: bool = True
    brightdata_proxy: str = 'http://brd-customer-hl_c4d84340-zone-testingdc:l1yptwrxrmbr@brd.superproxy.io:33335'
    
    # Progressive Enhancement Settings
    early_termination: bool = True  # Stop when successful results found
    min_success_threshold: int = 10  # Minimum URLs to consider success (lowered for testing)
    smart_termination: bool = True  # Stop after first successful method if good results
    
    # Debugging Settings
    verbose_debugging: bool = True  # Enhanced debugging output
    show_individual_attempts: bool = True  # Show each individual try
    
    # Output Settings
    save_results: bool = True
    output_file: str = "robots_ai_llm_urls_{}.txt"
    
    # Testing Settings (only test Chiyoda for now)
    test_sites: List[Dict[str, str]] = None

class RobotsLLMDiscoverer:
    """
    Progressive Enhancement Robots.txt & AI.txt & LLM URL Discovery
    
    Uses 5 progressive bricks to discover URLs:
    1. Basic Crawl4AI
    2. Stealth Mode
    3. Undetected Browser
    4. Proxy Enabled
    5. HTTP Fallback
    
    New Features:
    - AI.txt file analysis (emerging standard for LLM guidance)
    - Meta tag detection (noai, noimageai)
    - Enhanced debugging with individual attempt tracking
    """
    
    def __init__(self, config: RobotsLLMConfig):
        self.config = config
        self.discovered_urls: Set[str] = set()
        self.llm_generated_urls: Set[str] = set()
        self.robots_urls: Set[str] = set()
        self.ai_txt_urls: Set[str] = set()  # New: Track AI.txt URLs
        self.domain = urlparse(config.base_url).netloc
        
        # Progressive enhancement tracking
        self.successful_methods: Set[str] = set()
        self.method_results: Dict[str, Dict[str, Any]] = {}
        self.debug_log: List[str] = []  # Enhanced debugging
        
        # Resource cleanup
        self._browser_crawler = None
        self._http_session = None
        atexit.register(self._cleanup_on_exit)
        
        # Setup Gemini API
        self._setup_gemini_api()
        
        # Setup logging
        logger = logging.getLogger(__name__)
        
    def _debug_log(self, message: str, level: str = "INFO"):
        """Enhanced debugging with individual attempt tracking"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {level}: {message}"
        
        if self.config.verbose_debugging:
            print(f"    🔍 {message}")
        
        self.debug_log.append(log_entry)
    
    def _debug_attempt(self, method: str, step: str, url: str = "", status: str = ""):
        """Debug individual attempts within each phase"""
        if self.config.show_individual_attempts:
            if status:
                print(f"      ├─ {step}: {url} → {status}")
            else:
                print(f"      ├─ {step}: {url}")
    
    def _debug_result(self, method: str, result_type: str, count: int):
        """Debug results for each discovery method"""
        if self.config.verbose_debugging:
            print(f"      └─ ✅ {result_type}: {count} URLs found")
        
        print("🤖 Robots.txt & AI.txt & LLM Analysis Discoverer initialized")
        print(f"🎯 Target domain: {self.domain}")
        if self.config.use_llm_analysis and self.gemini_client:
            print("✅ LLM analysis enabled with Gemini")
        else:
            print("⚠️  LLM analysis disabled or unavailable")
        if self.config.check_ai_txt:
            print("🤖 AI.txt analysis enabled")
        if self.config.verbose_debugging:
            print("🔍 Enhanced debugging enabled")
    
    def _cleanup_on_exit(self):
        """Cleanup on exit"""
        try:
            if hasattr(self, '_browser_crawler') and self._browser_crawler:
                # Schedule cleanup for async resources
                pass
        except:
            pass
    
    def _cleanup_resources(self):
        """Cleanup HTTP resources"""
        try:
            if self._http_session and not self._http_session.closed:
                # Will be cleaned up by context manager
                pass
        except:
            pass
    
    def _setup_gemini_api(self):
        """Setup Gemini API client"""
        self.gemini_client = None
        
        try:
            api_key = self.config.gemini_api_key or os.getenv('GOOGLE_API_KEY')
            if api_key and genai:
                genai.configure(api_key=api_key)
                self.gemini_client = genai.GenerativeModel(self.config.llm_model)
                logger.info("✅ Gemini API configured successfully")
            else:
                logger.warning("⚠️  Gemini API not configured")
        except Exception as e:
            logger.warning(f"⚠️  Failed to setup Gemini API: {e}")
    
    async def discover_urls(self, site_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Main progressive enhancement discovery method
        Tests each brick until successful results are found
        """
        site_name = site_info.get('name', 'Unknown')
        base_url = site_info.get('url', self.config.base_url)
        
        print(f"\n🤖 Starting Robots.txt & LLM Analysis for {site_name}")
        print(f"🌐 URL: {base_url}")
        print("="*80)
        
        start_time = time.time()
        total_found = 0
        
        # Define progressive enhancement bricks
        bricks = [
            ("BASIC_CRAWL4AI", self._test_basic_crawl4ai),
            ("STEALTH_MODE", self._test_stealth_mode),
            ("UNDETECTED_BROWSER", self._test_undetected_browser),
            ("PROXY_ENABLED", self._test_proxy_enabled),
            ("HTTP_FALLBACK", self._test_http_fallback)
        ]
        
        for i, (method_name, method_func) in enumerate(bricks, 1):
            # Check if we already have sufficient results before trying next method
            if total_found >= self.config.min_success_threshold:
                print(f"\n🎯 EARLY TERMINATION: {total_found} URLs already found")
                print(f"🚀 Skipping remaining {len(bricks) - i + 1} bricks to save time")
                self._debug_log(f"Early termination: {total_found} URLs sufficient", "SUCCESS")
                break
            
            print(f"\n🧱 BRICK {i}: {method_name.replace('_', ' ').title()}")
            
            try:
                result = await method_func(base_url)
                
                if result.get('success'):
                    urls_found = len(result.get('urls', []))
                    total_found += urls_found
                    self.discovered_urls.update(result.get('urls', []))
                    self.successful_methods.add(method_name)
                    
                    print(f"  ✅ Success! Found {urls_found} URLs (Total: {total_found})")
                    
                    # Smart termination: Stop after first successful method if good results
                    if (hasattr(self.config, 'smart_termination') and self.config.smart_termination and 
                        urls_found >= 3 and i == 1):
                        print(f"  🎯 Smart termination: First method succeeded with {urls_found} URLs")
                        print(f"  🚀 Skipping remaining {len(bricks) - i} bricks (results sufficient)")
                        self._debug_log(f"Smart termination after first success: {urls_found} URLs", "SUCCESS")
                        break
                    
                    # Early termination check after each successful method
                    elif total_found >= self.config.min_success_threshold:
                        print(f"  🎯 Early termination triggered: {total_found} URLs >= {self.config.min_success_threshold} threshold")
                        print(f"  🚀 Skipping remaining {len(bricks) - i} bricks")
                        self._debug_log(f"Early termination after {method_name}: {total_found} URLs", "SUCCESS")
                        break
                        
                    # Also check if this method found substantial results for conservative termination
                    elif urls_found >= 5 and i <= 2:  # First 2 methods with good results
                        print(f"  💡 Good results from early method: {urls_found} URLs")
                        print(f"  � Consider that further methods may yield similar results")
                        # Continue but note the success
                        
                else:
                    print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
                
                self.method_results[method_name] = result
                
                # Brief delay between methods
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"  ❌ Exception: {e}")
                self.method_results[method_name] = {'success': False, 'error': str(e)}
        
        # Generate final results
        duration = time.time() - start_time
        results = await self._generate_results(site_info, duration, total_found)
        
        # Save results if configured
        if self.config.save_results and self.discovered_urls:
            await self._save_results(site_name)
        
        return results
    
    async def _test_basic_crawl4ai(self, base_url: str) -> Dict[str, Any]:
        """Test basic Crawl4AI with robots.txt + ai.txt parsing and LLM analysis"""
        self._debug_log("Starting basic Crawl4AI analysis", "INFO")
        
        try:
            # Step 1: Analyze robots.txt
            self._debug_attempt("basic", "robots.txt analysis", base_url)
            robots_result = await self._analyze_robots_txt(base_url, method="basic")
            self._debug_result("basic", "robots.txt", len(robots_result.get('urls', [])))
            
            # Step 2: Analyze ai.txt
            ai_txt_result = {'urls': []}
            if self.config.check_ai_txt:
                self._debug_attempt("basic", "ai.txt analysis", base_url)
                ai_txt_result = await self._analyze_ai_txt(base_url, method="basic")
                self._debug_result("basic", "ai.txt", len(ai_txt_result.get('urls', [])))
            
            # Step 3: Extract meta tags
            meta_result = {'urls': [], 'meta_tags': {}}
            if self.config.check_ai_meta_tags:
                self._debug_attempt("basic", "meta tag extraction", base_url)
                meta_result = await self._extract_meta_tags(base_url, method="basic")
                self._debug_result("basic", "meta tags", len(meta_result.get('meta_tags', {})))
            
            # Step 4: LLM analysis for URL generation
            self._debug_attempt("basic", "LLM pattern generation", base_url)
            llm_result = await self._perform_llm_analysis(base_url, method="basic")
            self._debug_result("basic", "LLM patterns", len(llm_result.get('urls', [])))
            
            # Combine results
            all_urls = set()
            all_urls.update(robots_result.get('urls', []))
            all_urls.update(ai_txt_result.get('urls', []))
            all_urls.update(meta_result.get('urls', []))
            all_urls.update(llm_result.get('urls', []))
            
            success = len(all_urls) > 0
            self._debug_log(f"Basic Crawl4AI completed: {len(all_urls)} total URLs", "SUCCESS" if success else "FAIL")
            
            return {
                'success': success,
                'urls': list(all_urls),
                'robots_urls': len(robots_result.get('urls', [])),
                'ai_txt_urls': len(ai_txt_result.get('urls', [])),
                'meta_tags': len(meta_result.get('meta_tags', {})),
                'meta_urls': len(meta_result.get('urls', [])),
                'llm_urls': len(llm_result.get('urls', [])),
                'method': 'basic_crawl4ai'
            }
            
        except Exception as e:
            self._debug_log(f"Basic Crawl4AI failed: {str(e)}", "ERROR")
            return {'success': False, 'error': str(e), 'method': 'basic_crawl4ai'}
    
    async def _test_stealth_mode(self, base_url: str) -> Dict[str, Any]:
        """Test with stealth mode enabled"""
        self._debug_log("Starting stealth mode analysis", "INFO")
        
        try:
            # Step 1: Stealth robots.txt analysis
            self._debug_attempt("stealth", "robots.txt analysis", base_url)
            robots_result = await self._analyze_robots_txt(base_url, method="stealth")
            self._debug_result("stealth", "robots.txt", len(robots_result.get('urls', [])))
            
            # Step 2: Stealth ai.txt analysis
            ai_txt_result = {'urls': []}
            if self.config.check_ai_txt:
                self._debug_attempt("stealth", "ai.txt analysis", base_url)
                ai_txt_result = await self._analyze_ai_txt(base_url, method="stealth")
                self._debug_result("stealth", "ai.txt", len(ai_txt_result.get('urls', [])))
            
            # Step 3: Stealth meta tag extraction
            meta_result = {'urls': [], 'meta_tags': {}}
            if self.config.check_ai_meta_tags:
                self._debug_attempt("stealth", "meta tag extraction", base_url)
                meta_result = await self._extract_meta_tags(base_url, method="stealth")
                self._debug_result("stealth", "meta tags", len(meta_result.get('meta_tags', {})))
            
            # Step 4: Enhanced LLM analysis with stealth browsing
            self._debug_attempt("stealth", "LLM pattern generation", base_url)
            llm_result = await self._perform_llm_analysis(base_url, method="stealth")
            self._debug_result("stealth", "LLM patterns", len(llm_result.get('urls', [])))
            
            # Combine results
            all_urls = set()
            all_urls.update(robots_result.get('urls', []))
            all_urls.update(ai_txt_result.get('urls', []))
            all_urls.update(meta_result.get('urls', []))
            all_urls.update(llm_result.get('urls', []))
            
            success = len(all_urls) > 0
            self._debug_log(f"Stealth mode completed: {len(all_urls)} total URLs", "SUCCESS" if success else "FAIL")
            
            return {
                'success': success,
                'urls': list(all_urls),
                'robots_urls': len(robots_result.get('urls', [])),
                'ai_txt_urls': len(ai_txt_result.get('urls', [])),
                'meta_tags': len(meta_result.get('meta_tags', {})),
                'meta_urls': len(meta_result.get('urls', [])),
                'llm_urls': len(llm_result.get('urls', [])),
                'method': 'stealth_mode'
            }
            
        except Exception as e:
            self._debug_log(f"Stealth mode failed: {str(e)}", "ERROR")
            return {'success': False, 'error': str(e), 'method': 'stealth_mode'}
    
    async def _test_undetected_browser(self, base_url: str) -> Dict[str, Any]:
        """Test with undetected browser"""
        try:
            # Step 1: Undetected robots.txt analysis
            robots_result = await self._analyze_robots_txt(base_url, method="undetected")
            
            # Step 2: Deep LLM analysis with undetected browsing
            llm_result = await self._perform_llm_analysis(base_url, method="undetected")
            
            # Combine results
            all_urls = set()
            all_urls.update(robots_result.get('urls', []))
            all_urls.update(llm_result.get('urls', []))
            
            success = len(all_urls) > 0
            
            return {
                'success': success,
                'urls': list(all_urls),
                'robots_urls': len(robots_result.get('urls', [])),
                'llm_urls': len(llm_result.get('urls', [])),
                'method': 'undetected_browser'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'method': 'undetected_browser'}
    
    async def _test_proxy_enabled(self, base_url: str) -> Dict[str, Any]:
        """Test with proxy enabled"""
        try:
            # Step 1: Proxy-enabled robots.txt analysis
            robots_result = await self._analyze_robots_txt(base_url, method="proxy")
            
            # Step 2: LLM analysis through proxy
            llm_result = await self._perform_llm_analysis(base_url, method="proxy")
            
            # Combine results
            all_urls = set()
            all_urls.update(robots_result.get('urls', []))
            all_urls.update(llm_result.get('urls', []))
            
            success = len(all_urls) > 0
            
            return {
                'success': success,
                'urls': list(all_urls),
                'robots_urls': len(robots_result.get('urls', [])),
                'llm_urls': len(llm_result.get('urls', [])),
                'method': 'proxy_enabled'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'method': 'proxy_enabled'}
    
    async def _test_http_fallback(self, base_url: str) -> Dict[str, Any]:
        """Test with direct HTTP requests as fallback"""
        try:
            # Step 1: Direct HTTP robots.txt analysis
            robots_result = await self._analyze_robots_txt_http(base_url)
            
            # Step 2: Direct HTTP ai.txt analysis
            ai_txt_result = {'urls': []}
            if self.config.check_ai_txt:
                ai_txt_result = await self._analyze_ai_txt_http(base_url)
            
            # Step 3: Direct HTTP meta tag analysis
            meta_result = {'urls': [], 'meta_tags': {}}
            if self.config.check_ai_meta_tags:
                meta_result = await self._extract_meta_tags_http(base_url)
            
            # Step 4: LLM analysis with HTTP fallback
            llm_result = await self._perform_llm_analysis_http(base_url)
            
            # Combine results
            all_urls = set()
            all_urls.update(robots_result.get('urls', []))
            all_urls.update(ai_txt_result.get('urls', []))
            all_urls.update(meta_result.get('urls', []))
            all_urls.update(llm_result.get('urls', []))
            
            success = len(all_urls) > 0
            
            return {
                'success': success,
                'urls': list(all_urls),
                'robots_urls': len(robots_result.get('urls', [])),
                'ai_txt_urls': len(ai_txt_result.get('urls', [])),
                'meta_tags': len(meta_result.get('meta_tags', {})),
                'meta_urls': len(meta_result.get('urls', [])),
                'llm_urls': len(llm_result.get('urls', [])),
                'method': 'http_fallback'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'method': 'http_fallback'}
    
    async def _analyze_robots_txt(self, base_url: str, method: str = "basic") -> Dict[str, Any]:
        """Analyze robots.txt using Crawl4AI with specified method"""
        robots_url = urljoin(base_url, '/robots.txt')
        discovered_urls = set()
        
        try:
            # Create browser config based on method
            browser_config = self._create_browser_config(method)
            
            # Create crawler config
            crawler_config = CrawlerRunConfig(
                page_timeout=self.config.timeout * 1000,
                verbose=False,
                wait_for_images=False,
                delay_before_return_html=2.0,
                remove_overlay_elements=True
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=robots_url, config=crawler_config)
                
                if result.success and result.markdown:
                    # Parse robots.txt content
                    urls_from_robots = self._parse_robots_txt(result.markdown, base_url)
                    discovered_urls.update(urls_from_robots)
                    
                    print(f"    🤖 Robots.txt: Found {len(urls_from_robots)} URLs via {method}")
                else:
                    print(f"    ⚠️  Robots.txt: Failed to fetch via {method}")
            
            return {
                'success': len(discovered_urls) > 0,
                'urls': list(discovered_urls),
                'method': method,
                'source': 'robots_txt'
            }
            
        except Exception as e:
            print(f"    ❌ Robots.txt analysis failed ({method}): {e}")
            return {'success': False, 'error': str(e), 'urls': []}
    
    async def _analyze_robots_txt_http(self, base_url: str) -> Dict[str, Any]:
        """Analyze robots.txt using direct HTTP requests"""
        robots_url = urljoin(base_url, '/robots.txt')
        discovered_urls = set()
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Use proxy if configured
            connector_kwargs = {}
            if self.config.proxy_enabled and self.config.brightdata_proxy:
                connector_kwargs['proxy'] = self.config.brightdata_proxy
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(
                headers=headers, 
                timeout=timeout,
                **connector_kwargs
            ) as session:
                async with session.get(robots_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        urls_from_robots = self._parse_robots_txt(content, base_url)
                        discovered_urls.update(urls_from_robots)
                        
                        print(f"    🌐 HTTP Robots.txt: Found {len(urls_from_robots)} URLs")
                    else:
                        print(f"    ⚠️  HTTP Robots.txt: Status {response.status}")
            
            return {
                'success': len(discovered_urls) > 0,
                'urls': list(discovered_urls),
                'method': 'http',
                'source': 'robots_txt'
            }
            
        except Exception as e:
            print(f"    ❌ HTTP Robots.txt analysis failed: {e}")
            return {'success': False, 'error': str(e), 'urls': []}
    
    def _parse_robots_txt(self, content: str, base_url: str) -> Set[str]:
        """Parse robots.txt content and extract URLs"""
        urls = set()
        
        try:
            lines = content.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Extract sitemap URLs
                if line.lower().startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    if sitemap_url:
                        full_url = urljoin(base_url, sitemap_url)
                        urls.add(full_url)
                
                # Extract disallow patterns (these might point to interesting directories)
                elif line.lower().startswith('disallow:'):
                    disallow_path = line.split(':', 1)[1].strip()
                    if disallow_path and disallow_path != '/' and not disallow_path.startswith('*'):
                        # Convert disallow patterns to discoverable URLs
                        potential_urls = self._convert_disallow_to_urls(disallow_path, base_url)
                        urls.update(potential_urls)
                
                # Extract allow patterns
                elif line.lower().startswith('allow:'):
                    allow_path = line.split(':', 1)[1].strip()
                    if allow_path and allow_path != '/':
                        full_url = urljoin(base_url, allow_path)
                        urls.add(full_url)
        
        except Exception as e:
            print(f"    ⚠️  Error parsing robots.txt: {e}")
        
        return urls
    
    def _convert_disallow_to_urls(self, disallow_path: str, base_url: str) -> Set[str]:
        """Convert disallow patterns to potential discoverable URLs"""
        urls = set()
        
        try:
            # Remove wildcards and clean up path
            clean_path = disallow_path.replace('*', '').strip()
            
            if clean_path and clean_path != '/':
                # Create base URL from disallow path
                if clean_path.endswith('/'):
                    # Directory path - add index files
                    base_dir_url = urljoin(base_url, clean_path)
                    urls.add(base_dir_url)
                    urls.add(urljoin(base_dir_url, 'index.html'))
                    urls.add(urljoin(base_dir_url, 'index.php'))
                else:
                    # File or directory without trailing slash
                    full_url = urljoin(base_url, clean_path)
                    urls.add(full_url)
                    
                    # Also try as directory
                    if not clean_path.endswith(('.html', '.htm', '.php', '.asp')):
                        dir_url = urljoin(base_url, clean_path + '/')
                        urls.add(dir_url)
                        urls.add(urljoin(dir_url, 'index.html'))
        
        except Exception as e:
            print(f"    ⚠️  Error converting disallow pattern: {e}")
        
        return urls
    
    async def _analyze_ai_txt(self, base_url: str, method: str = "basic") -> Dict[str, Any]:
        """Analyze ai.txt using Crawl4AI with specified method"""
        ai_txt_url = urljoin(base_url, '/ai.txt')
        discovered_urls = set()
        
        try:
            self._debug_attempt(method, "Fetching ai.txt", ai_txt_url)
            
            # Create browser config based on method
            browser_config = self._create_browser_config(method)
            
            # Create crawler config
            crawler_config = CrawlerRunConfig(
                page_timeout=self.config.timeout * 1000,
                verbose=False,
                wait_for_images=False,
                delay_before_return_html=2.0,
                remove_overlay_elements=True
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=ai_txt_url, config=crawler_config)
                
                if result.success and result.markdown:
                    self._debug_attempt(method, "Parsing ai.txt content", "", "SUCCESS")
                    # Parse ai.txt content
                    urls_from_ai_txt = self._parse_ai_txt(result.markdown, base_url)
                    discovered_urls.update(urls_from_ai_txt)
                    
                    print(f"    🤖 AI.txt: Found {len(urls_from_ai_txt)} URLs via {method}")
                else:
                    self._debug_attempt(method, "AI.txt fetch", ai_txt_url, "FAILED")
                    print(f"    ⚠️  AI.txt: Failed to fetch via {method}")
            
            return {
                'success': len(discovered_urls) > 0,
                'urls': list(discovered_urls),
                'method': method,
                'source': 'ai_txt'
            }
            
        except Exception as e:
            self._debug_attempt(method, "AI.txt analysis error", ai_txt_url, f"ERROR: {str(e)}")
            print(f"    ❌ AI.txt analysis failed ({method}): {e}")
            return {'success': False, 'error': str(e), 'urls': []}
    
    async def _analyze_ai_txt_http(self, base_url: str) -> Dict[str, Any]:
        """Analyze ai.txt using direct HTTP requests"""
        ai_txt_url = urljoin(base_url, '/ai.txt')
        discovered_urls = set()
        
        try:
            self._debug_attempt("http", "Fetching ai.txt via HTTP", ai_txt_url)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Use proxy if configured
            connector_kwargs = {}
            if self.config.proxy_enabled and self.config.brightdata_proxy:
                connector_kwargs['proxy'] = self.config.brightdata_proxy
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(
                headers=headers, 
                timeout=timeout,
                **connector_kwargs
            ) as session:
                async with session.get(ai_txt_url) as response:
                    if response.status == 200:
                        self._debug_attempt("http", "AI.txt fetch", ai_txt_url, "SUCCESS")
                        content = await response.text()
                        urls_from_ai_txt = self._parse_ai_txt(content, base_url)
                        discovered_urls.update(urls_from_ai_txt)
                        
                        print(f"    🌐 HTTP AI.txt: Found {len(urls_from_ai_txt)} URLs")
                    else:
                        self._debug_attempt("http", "AI.txt fetch", ai_txt_url, f"HTTP {response.status}")
                        print(f"    ⚠️  HTTP AI.txt: Status {response.status}")
            
            return {
                'success': len(discovered_urls) > 0,
                'urls': list(discovered_urls),
                'method': 'http',
                'source': 'ai_txt'
            }
            
        except Exception as e:
            self._debug_attempt("http", "AI.txt analysis error", ai_txt_url, f"ERROR: {str(e)}")
            print(f"    ❌ HTTP AI.txt analysis failed: {e}")
            return {'success': False, 'error': str(e), 'urls': []}
    
    def _parse_ai_txt(self, content: str, base_url: str) -> Set[str]:
        """Parse ai.txt content and extract URLs and directives"""
        urls = set()
        
        try:
            self._debug_log("Parsing ai.txt content", "INFO")
            lines = content.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Extract sitemap URLs (same as robots.txt)
                if line.lower().startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    if sitemap_url:
                        full_url = urljoin(base_url, sitemap_url)
                        urls.add(full_url)
                        self._debug_attempt("parse", "Found sitemap in ai.txt", full_url)
                
                # Extract training data URLs
                elif line.lower().startswith('training-data:'):
                    training_url = line.split(':', 1)[1].strip()
                    if training_url:
                        full_url = urljoin(base_url, training_url)
                        urls.add(full_url)
                        self._debug_attempt("parse", "Found training-data URL", full_url)
                
                # Extract AI-disallow patterns (convert to discoverable URLs)
                elif line.lower().startswith('ai-disallow:'):
                    disallow_path = line.split(':', 1)[1].strip()
                    if disallow_path and disallow_path != '/' and not disallow_path.startswith('*'):
                        potential_urls = self._convert_disallow_to_urls(disallow_path, base_url)
                        urls.update(potential_urls)
                        self._debug_attempt("parse", "Converted ai-disallow to URLs", disallow_path)
                
                # Extract AI-allow patterns
                elif line.lower().startswith('ai-allow:'):
                    allow_path = line.split(':', 1)[1].strip()
                    if allow_path and allow_path != '/':
                        full_url = urljoin(base_url, allow_path)
                        urls.add(full_url)
                        self._debug_attempt("parse", "Found ai-allow URL", full_url)
                
                # Extract model-specific directives
                elif any(directive in line.lower() for directive in ['gpt-disallow:', 'claude-disallow:', 'gemini-disallow:']):
                    # Extract the path part after the colon
                    directive_path = line.split(':', 1)[1].strip()
                    if directive_path and directive_path != '/':
                        potential_urls = self._convert_disallow_to_urls(directive_path, base_url)
                        urls.update(potential_urls)
                        self._debug_attempt("parse", "Found model-specific directive", directive_path)
        
        except Exception as e:
            self._debug_log(f"Error parsing ai.txt: {str(e)}", "ERROR")
            print(f"    ⚠️  Error parsing ai.txt: {e}")
        
        self._debug_log(f"AI.txt parsing complete: {len(urls)} URLs extracted", "SUCCESS")
        return urls
    
    async def _perform_llm_analysis(self, base_url: str, method: str = "basic") -> Dict[str, Any]:
        """Perform LLM analysis to generate intelligent URL patterns"""
        if not self.config.use_llm_analysis or not self.gemini_client:
            return {'success': False, 'urls': [], 'error': 'LLM not available'}
        
        discovered_urls = set()
        
        try:
            # Step 1: Fetch homepage for context
            homepage_content = await self._fetch_homepage_content(base_url, method)
            
            # Step 2: Generate URL patterns using LLM
            if homepage_content:
                llm_patterns = await self._generate_llm_url_patterns(base_url, homepage_content)
                
                # Step 3: Convert patterns to actual URLs
                generated_urls = await self._validate_llm_patterns(base_url, llm_patterns, method)
                discovered_urls.update(generated_urls)
                
                print(f"    🧠 LLM Analysis: Generated {len(discovered_urls)} URLs via {method}")
            else:
                print(f"    ⚠️  LLM Analysis: Could not fetch homepage via {method}")
            
            return {
                'success': len(discovered_urls) > 0,
                'urls': list(discovered_urls),
                'method': method,
                'source': 'llm_analysis'
            }
            
        except Exception as e:
            print(f"    ❌ LLM analysis failed ({method}): {e}")
            return {'success': False, 'error': str(e), 'urls': []}
    
    async def _perform_llm_analysis_http(self, base_url: str) -> Dict[str, Any]:
        """Perform LLM analysis using direct HTTP requests"""
        if not self.config.use_llm_analysis or not self.gemini_client:
            return {'success': False, 'urls': [], 'error': 'LLM not available'}
        
        discovered_urls = set()
        
        try:
            # Step 1: Fetch homepage via HTTP
            homepage_content = await self._fetch_homepage_content_http(base_url)
            
            # Step 2: Generate URL patterns using LLM
            if homepage_content:
                llm_patterns = await self._generate_llm_url_patterns(base_url, homepage_content)
                
                # Step 3: Validate patterns via HTTP
                generated_urls = await self._validate_llm_patterns_http(base_url, llm_patterns)
                discovered_urls.update(generated_urls)
                
                print(f"    🌐 HTTP LLM Analysis: Generated {len(discovered_urls)} URLs")
            else:
                print(f"    ⚠️  HTTP LLM Analysis: Could not fetch homepage")
            
            return {
                'success': len(discovered_urls) > 0,
                'urls': list(discovered_urls),
                'method': 'http',
                'source': 'llm_analysis'
            }
            
        except Exception as e:
            print(f"    ❌ HTTP LLM analysis failed: {e}")
            return {'success': False, 'error': str(e), 'urls': []}
    
    async def _fetch_homepage_content(self, base_url: str, method: str) -> str:
        """Fetch homepage content using Crawl4AI"""
        try:
            browser_config = self._create_browser_config(method)
            crawler_config = CrawlerRunConfig(
                page_timeout=self.config.timeout * 1000,
                verbose=False,
                wait_for_images=False,
                delay_before_return_html=2.0,
                remove_overlay_elements=True
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=base_url, config=crawler_config)
                
                if result.success and result.markdown:
                    return result.markdown[:5000]  # First 5k chars for context
                
        except Exception as e:
            print(f"    ⚠️  Failed to fetch homepage via {method}: {e}")
        
        return ""
    
    async def _fetch_homepage_content_http(self, base_url: str) -> str:
        """Fetch homepage content using direct HTTP"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Use proxy if configured
            connector_kwargs = {}
            if self.config.proxy_enabled and self.config.brightdata_proxy:
                connector_kwargs['proxy'] = self.config.brightdata_proxy
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(
                headers=headers, 
                timeout=timeout,
                **connector_kwargs
            ) as session:
                async with session.get(base_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Extract text content using BeautifulSoup
                        soup = BeautifulSoup(content, 'html.parser')
                        text_content = soup.get_text()
                        return text_content[:5000]  # First 5k chars for context
                        
        except Exception as e:
            print(f"    ⚠️  Failed to fetch homepage via HTTP: {e}")
        
        return ""
    
    async def _generate_llm_url_patterns(self, base_url: str, content: str) -> List[str]:
        """Generate URL patterns using LLM analysis"""
        if not self.gemini_client:
            return []
        
        try:
            domain = urlparse(base_url).netloc
            
            prompt = f"""
Analyze this website content and generate likely URL patterns that might exist on this domain.

Domain: {domain}
Content snippet: {content[:2000]}

Based on the content type and structure, generate 20-30 realistic URL patterns that are likely to exist on this website. Focus on:

1. Common page types (about, contact, services, news, etc.)
2. Directory structures that match the content theme
3. File patterns (index.html, index.php, etc.)
4. Language-specific patterns if content is in Japanese
5. Administrative or backend URLs that might be accessible

Return ONLY a JSON array of URL paths (starting with /), like:
["/about/", "/services/", "/news/", "/contact.html", "/admin/", "/search/"]

Do not include the domain, just the paths. Be realistic and practical.
"""
            
            response = await asyncio.wait_for(
                asyncio.to_thread(self.gemini_client.generate_content, prompt),
                timeout=30
            )
            
            if response and response.text:
                # Extract JSON from response
                json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
                if json_match:
                    try:
                        patterns = json.loads(json_match.group())
                        return [p for p in patterns if isinstance(p, str) and p.startswith('/')]
                    except json.JSONDecodeError:
                        pass
            
        except Exception as e:
            print(f"    ⚠️  LLM pattern generation failed: {e}")
        
        return []
    
    async def _validate_llm_patterns(self, base_url: str, patterns: List[str], method: str) -> Set[str]:
        """Validate LLM-generated patterns using Crawl4AI"""
        valid_urls = set()
        
        if not patterns:
            return valid_urls
        
        try:
            browser_config = self._create_browser_config(method)
            crawler_config = CrawlerRunConfig(
                page_timeout=5000,  # 5 seconds for validation
                verbose=False,
                wait_for_images=False
            )
            
            # Test patterns in small batches
            batch_size = 5
            for i in range(0, len(patterns), batch_size):
                batch_patterns = patterns[i:i + batch_size]
                
                async with AsyncWebCrawler(config=browser_config) as crawler:
                    for pattern in batch_patterns:
                        try:
                            test_url = urljoin(base_url, pattern)
                            result = await crawler.arun(url=test_url, config=crawler_config)
                            
                            if result.success and result.status_code == 200:
                                valid_urls.add(test_url)
                                
                        except Exception:
                            continue  # Skip failed URLs
                
                # Brief delay between batches
                await asyncio.sleep(0.1)
                
                # Limit total validation time
                if len(valid_urls) >= 50:  # Stop after finding 50 valid URLs
                    break
            
        except Exception as e:
            print(f"    ⚠️  Pattern validation failed: {e}")
        
        return valid_urls
    
    async def _validate_llm_patterns_http(self, base_url: str, patterns: List[str]) -> Set[str]:
        """Validate LLM-generated patterns using direct HTTP"""
        valid_urls = set()
        
        if not patterns:
            return valid_urls
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Use proxy if configured
            connector_kwargs = {}
            if self.config.proxy_enabled and self.config.brightdata_proxy:
                connector_kwargs['proxy'] = self.config.brightdata_proxy
            
            timeout = aiohttp.ClientTimeout(total=5)  # Short timeout for validation
            async with aiohttp.ClientSession(
                headers=headers, 
                timeout=timeout,
                **connector_kwargs
            ) as session:
                # Test patterns in small batches
                semaphore = asyncio.Semaphore(self.config.max_concurrent)
                
                async def test_pattern(pattern: str):
                    async with semaphore:
                        try:
                            test_url = urljoin(base_url, pattern)
                            async with session.get(test_url) as response:
                                if response.status == 200:
                                    valid_urls.add(test_url)
                        except Exception:
                            pass  # Skip failed URLs
                
                # Test first 30 patterns (limit for efficiency)
                tasks = [test_pattern(pattern) for pattern in patterns[:30]]
                await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            print(f"    ⚠️  HTTP pattern validation failed: {e}")
        
        return valid_urls
    
    async def _extract_meta_tags(self, base_url: str, method: str = "basic") -> Dict[str, Any]:
        """Extract AI-related meta tags from homepage"""
        discovered_urls = set()
        meta_tags = {}
        
        try:
            self._debug_attempt(method, "Extracting meta tags", base_url)
            
            # Create browser config based on method
            browser_config = self._create_browser_config(method)
            
            # Create crawler config
            crawler_config = CrawlerRunConfig(
                page_timeout=self.config.timeout * 1000,
                verbose=False,
                wait_for_images=False,
                delay_before_return_html=2.0,
                remove_overlay_elements=True
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=base_url, config=crawler_config)
                
                if result.success and result.html:
                    self._debug_attempt(method, "Parsing meta tags", "", "SUCCESS")
                    # Parse meta tags from HTML
                    meta_info = self._parse_meta_tags(result.html, base_url)
                    meta_tags.update(meta_info['tags'])
                    discovered_urls.update(meta_info['urls'])
                    
                    print(f"    🏷️ Meta Tags: Found {len(meta_tags)} AI-related tags, {len(meta_info['urls'])} URLs via {method}")
                else:
                    self._debug_attempt(method, "Meta tag extraction", base_url, "FAILED")
                    print(f"    ⚠️  Meta Tags: Failed to fetch homepage via {method}")
            
            return {
                'success': len(meta_tags) > 0 or len(discovered_urls) > 0,
                'urls': list(discovered_urls),
                'meta_tags': meta_tags,
                'method': method,
                'source': 'meta_tags'
            }
            
        except Exception as e:
            self._debug_attempt(method, "Meta tag extraction error", base_url, f"ERROR: {str(e)}")
            print(f"    ❌ Meta tag extraction failed ({method}): {e}")
            return {'success': False, 'error': str(e), 'urls': [], 'meta_tags': {}}
    
    async def _extract_meta_tags_http(self, base_url: str) -> Dict[str, Any]:
        """Extract AI-related meta tags using direct HTTP requests"""
        discovered_urls = set()
        meta_tags = {}
        
        try:
            self._debug_attempt("http", "Extracting meta tags via HTTP", base_url)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Use proxy if configured
            connector_kwargs = {}
            if self.config.proxy_enabled and self.config.brightdata_proxy:
                connector_kwargs['proxy'] = self.config.brightdata_proxy
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(
                headers=headers, 
                timeout=timeout,
                **connector_kwargs
            ) as session:
                async with session.get(base_url) as response:
                    if response.status == 200:
                        self._debug_attempt("http", "Meta tag extraction", base_url, "SUCCESS")
                        html_content = await response.text()
                        meta_info = self._parse_meta_tags(html_content, base_url)
                        meta_tags.update(meta_info['tags'])
                        discovered_urls.update(meta_info['urls'])
                        
                        print(f"    🌐 HTTP Meta Tags: Found {len(meta_tags)} AI-related tags, {len(meta_info['urls'])} URLs")
                    else:
                        self._debug_attempt("http", "Meta tag extraction", base_url, f"HTTP {response.status}")
                        print(f"    ⚠️  HTTP Meta Tags: Status {response.status}")
            
            return {
                'success': len(meta_tags) > 0 or len(discovered_urls) > 0,
                'urls': list(discovered_urls),
                'meta_tags': meta_tags,
                'method': 'http',
                'source': 'meta_tags'
            }
            
        except Exception as e:
            self._debug_attempt("http", "Meta tag extraction error", base_url, f"ERROR: {str(e)}")
            print(f"    ❌ HTTP Meta tag extraction failed: {e}")
            return {'success': False, 'error': str(e), 'urls': [], 'meta_tags': {}}
    
    def _parse_meta_tags(self, html_content: str, base_url: str) -> Dict[str, Any]:
        """Parse HTML content for AI-related meta tags"""
        tags = {}
        urls = set()
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            self._debug_log("Parsing HTML for meta tags", "INFO")
            
            # Find all meta tags
            meta_tags = soup.find_all('meta')
            
            for tag in meta_tags:
                name = tag.get('name', '').lower()
                content = tag.get('content', '')
                
                # Check for AI-related meta tags
                if name in ['robots', 'googlebot', 'bingbot', 'noai', 'noimageai']:
                    tags[name] = content
                    self._debug_attempt("parse", f"Found meta tag: {name}", content)
                    
                    # Extract URLs from content if applicable
                    if 'follow' in content.lower() or 'index' in content.lower():
                        # This suggests the page is indexable, add current URL
                        urls.add(base_url)
                
                # Check for specific AI directives
                elif 'ai' in name or 'gpt' in name or 'claude' in name or 'gemini' in name:
                    tags[name] = content
                    self._debug_attempt("parse", f"Found AI-specific meta tag: {name}", content)
            
            # Also check for specific meta tag patterns
            noai_tags = soup.find_all('meta', {'name': re.compile(r'.*noai.*', re.I)})
            for tag in noai_tags:
                name = tag.get('name', '').lower()
                content = tag.get('content', '')
                tags[name] = content
                self._debug_attempt("parse", f"Found noai meta tag: {name}", content)
            
            # Check for canonical URLs and other discoverable links
            canonical = soup.find('link', {'rel': 'canonical'})
            if canonical and canonical.get('href'):
                canonical_url = urljoin(base_url, canonical['href'])
                urls.add(canonical_url)
                self._debug_attempt("parse", "Found canonical URL", canonical_url)
            
            # Check for alternate language versions
            alternates = soup.find_all('link', {'rel': 'alternate'})
            for alt in alternates:
                if alt.get('href'):
                    alt_url = urljoin(base_url, alt['href'])
                    urls.add(alt_url)
                    self._debug_attempt("parse", "Found alternate URL", alt_url)
        
        except Exception as e:
            self._debug_log(f"Error parsing meta tags: {str(e)}", "ERROR")
            print(f"    ⚠️  Error parsing meta tags: {e}")
        
        self._debug_log(f"Meta tag parsing complete: {len(tags)} tags, {len(urls)} URLs", "SUCCESS")
        return {'tags': tags, 'urls': urls}
    
    def _create_browser_config(self, method: str) -> BrowserConfig:
        """Create browser configuration based on method"""
        if method == "basic":
            return BrowserConfig(
                headless=True,
                verbose=False
            )
        
        elif method == "stealth":
            stealth_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            
            return BrowserConfig(
                headless=False,
                verbose=False,
                headers=headers,
                extra_args=stealth_args
            )
        
        elif method == "undetected":
            # For undetected mode, use basic config since UndetectedAdapter may not be compatible
            return BrowserConfig(
                headless=True,
                verbose=False
            )
        
        elif method == "proxy":
            proxy = self.config.brightdata_proxy if self.config.proxy_enabled else None
            return BrowserConfig(
                headless=True,
                verbose=False,
                proxy=proxy
            )
        
        else:  # fallback
            return BrowserConfig(
                headless=True,
                verbose=False
            )
    
    async def _generate_results(self, site_info: Dict[str, str], duration: float, total_found: int) -> Dict[str, Any]:
        """Generate comprehensive results"""
        return {
            'site_name': site_info.get('name', 'Unknown'),
            'site_url': site_info.get('url', self.config.base_url),
            'total_urls_found': total_found,
            'discovery_duration': duration,
            'successful_methods': list(self.successful_methods),
            'method_results': self.method_results,
            'discovered_urls': list(self.discovered_urls),
            'robots_urls': len(self.robots_urls),
            'llm_generated_urls': len(self.llm_generated_urls),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _save_results(self, site_name: str):
        """Save discovered URLs to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.config.output_file.format(f"{site_name}_{timestamp}")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# Robots.txt & LLM Analysis Results for {site_name}\n")
                f.write(f"# Generated on {datetime.now().isoformat()}\n")
                f.write(f"# Total URLs found: {len(self.discovered_urls)}\n\n")
                
                for url in sorted(self.discovered_urls):
                    f.write(f"{url}\n")
            
            print(f"💾 Saved {len(self.discovered_urls)} URLs to {filename}")
            
        except Exception as e:
            print(f"⚠️  Failed to save results: {e}")

async def test_robots_llm_discovery():
    """Test the Robots.txt & LLM Analysis discovery system"""
    
    # Test only Chiyoda for now (matching sitemap_discovery behavior)
    test_sites = [
        {
            'name': 'Chiyoda',
            'url': 'https://www.city.chiyoda.lg.jp'
        }
    ]
    
    config = RobotsLLMConfig(
        base_url='https://www.city.chiyoda.lg.jp',
        use_llm_analysis=True,
        early_termination=True,
        min_success_threshold=20,  # Lower threshold for robots.txt
        save_results=True,
        test_sites=test_sites
    )
    
    discoverer = RobotsLLMDiscoverer(config)
    
    print("🚀 Starting Phase 2: Robots.txt & LLM Analysis")
    print("="*80)
    
    all_results = []
    
    for site in test_sites:
        try:
            print(f"\n🎯 Testing {site['name']}")
            result = await discoverer.discover_urls(site)
            all_results.append(result)
            
            # Summary for this site
            print(f"\n📊 Results for {site['name']}:")
            print(f"  ✅ URLs discovered: {result['total_urls_found']}")
            print(f"  ⏱️ Duration: {result['discovery_duration']:.1f}s")
            print(f"  🎯 Successful methods: {', '.join(result['successful_methods'])}")
            
            if result['method_results']:
                for method, method_result in result['method_results'].items():
                    if method_result.get('success'):
                        robots_count = method_result.get('robots_urls', 0)
                        llm_count = method_result.get('llm_urls', 0)
                        print(f"  {method}: {robots_count} robots URLs + {llm_count} LLM URLs")
        
        except Exception as e:
            print(f"❌ Test failed for {site['name']}: {e}")
        
        # Brief delay between sites
        await asyncio.sleep(0.5)
    
    # Overall summary
    total_urls = sum(r['total_urls_found'] for r in all_results)
    total_time = sum(r['discovery_duration'] for r in all_results)
    
    print("\n" + "="*80)
    print("🏁 PHASE 2 COMPLETE: Robots.txt & LLM Analysis")
    print("="*80)
    print(f"📊 Total URLs discovered: {total_urls}")
    print(f"⏱️ Total time: {total_time:.1f}s")
    print(f"🎯 Sites tested: {len(test_sites)}")
    
    if total_urls > 0:
        print(f"📈 Average URLs per site: {total_urls / len(test_sites):.1f}")
        print(f"⚡ Discovery rate: {total_urls / total_time:.1f} URLs/second")
    
    print("\n✅ Phase 2 discovery system ready for integration!")
    
    return all_results

if __name__ == "__main__":
    try:
        # Suppress all warnings at runtime
        import warnings
        warnings.simplefilter("ignore")
        
        # Set better asyncio event loop policy for Windows
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        asyncio.run(test_robots_llm_discovery())
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
