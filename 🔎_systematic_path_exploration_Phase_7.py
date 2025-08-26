#!/usr/bin/env python3
"""
Phase 6: Systematic Path Exploration (NO LLM) - Pure pattern analysis
Analyze discovered URLs to generate additional path variations using pattern recognition
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
from collections import deque, Counter
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
        logging.FileHandler('phase6_systematic_path_exploration.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SystematicPathConfig:
    """Configuration for systematic path exploration"""
    base_url: str
    max_generated_urls: int = 5000
    max_concurrent: int = 50
    delay_between_requests: float = 0.1
    timeout: int = 15
    include_pdfs: bool = False  # PDFs excluded per requirement
    include_images: bool = False
    
    # Pattern generation settings
    min_pattern_frequency: int = 2  # Minimum times a pattern must appear
    max_variations_per_pattern: int = 100  # Maximum variations to generate per pattern
    
    # PROXY CONFIGURATION
    proxy_enabled: bool = True
    brightdata_proxy: str = 'http://brd-customer-hl_c4d84340-zone-testingdc:l1yptwrxrmbr@brd.superproxy.io:33335'
    
    # STEALTH CONFIGURATION
    stealth_mode: bool = True
    rotate_user_agents: bool = True

class SystematicPathExplorer:
    """Phase 6: Systematic Path Exploration (NO LLM) - Pure pattern analysis"""
    
    def __init__(self, config: SystematicPathConfig):
        self.config = config
        self.discovered_urls: Set[str] = set()
        self.input_urls: Set[str] = set()  # URLs to analyze for patterns
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.domain = urlparse(config.base_url).netloc
        
        # Pattern analysis data
        self.url_segments: Counter = Counter()
        self.numeric_patterns: Set[str] = set()
        self.date_patterns: Set[str] = set()
        self.path_structures: Dict[str, int] = {}
        self.file_extensions: Counter = Counter()
        
        # Discovery statistics
        self.discovery_stats = {
            "systematic_exploration_urls": 0,
            "patterns_analyzed": 0,
            "patterns_generated": 0,
            "url_variations_created": 0,
            "successful_variations": 0
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
    
    async def run_systematic_path_exploration(self, input_urls: Set[str]) -> Dict[str, Any]:
        """Main systematic path exploration method"""
        print("\n🔍 PHASE 6: SYSTEMATIC PATH EXPLORATION (NO LLM)")
        print("-" * 50)
        
        start_time = time.time()
        
        # Store input URLs for analysis
        self.input_urls = input_urls.copy()
        print(f"📂 Analyzing {len(input_urls)} input URLs for patterns")
        
        # Step 1: Analyze URL patterns (NO LLM - pure pattern recognition)
        pattern_data = await self._analyze_url_patterns()
        
        # Step 2: Generate URL variations based on patterns
        generated_urls = await self._generate_url_variations(pattern_data)
        
        # Step 3: Test generated URLs for existence
        await self._test_generated_urls_progressive(generated_urls)
        
        end_time = time.time()
        self.discovery_stats["systematic_exploration_urls"] = len(self.discovered_urls)
        
        print(f"\n✅ Systematic Path Exploration Complete!")
        print(f"📊 URLs discovered: {len(self.discovered_urls)}")
        print(f"📊 Patterns analyzed: {self.discovery_stats['patterns_analyzed']}")
        print(f"📊 URL variations created: {self.discovery_stats['url_variations_created']}")
        print(f"📊 Successful variations: {self.discovery_stats['successful_variations']}")
        print(f"⏱️  Total time: {end_time - start_time:.1f}s")
        
        return self._generate_results()
    
    async def _analyze_url_patterns(self) -> Dict[str, Any]:
        """Analyze discovered URLs to find patterns (NO LLM - pure pattern analysis)"""
        print("  🔍 Analyzing URL patterns...")
        
        pattern_data = {
            'segments': {},
            'numeric_patterns': set(),
            'date_patterns': set(),
            'structures': {},
            'extensions': {}
        }
        
        for url in self.input_urls:
            parsed = urlparse(url)
            path_parts = [part for part in parsed.path.split('/') if part]
            
            # Collect all segments
            for part in path_parts:
                self.url_segments[part] += 1
            
            # Look for numeric patterns
            for part in path_parts:
                if part.isdigit():
                    self.numeric_patterns.add(part)
                elif re.match(r'\d+', part):  # Contains numbers
                    self.numeric_patterns.add(part)
            
            # Look for date patterns (YYYY, YYYY-MM, YYYY-MM-DD, etc.)
            for part in path_parts:
                # Year patterns (2000-2030)
                if re.match(r'^20[0-3]\d$', part):
                    self.date_patterns.add('year')
                # Month patterns (01-12)
                elif re.match(r'^(0[1-9]|1[0-2])$', part):
                    self.date_patterns.add('month')
                # Day patterns (01-31)
                elif re.match(r'^(0[1-9]|[12]\d|3[01])$', part):
                    self.date_patterns.add('day')
                # Date-like patterns
                elif re.match(r'\d{4}-\d{2}-\d{2}', part):
                    self.date_patterns.add('full_date')
                elif re.match(r'\d{4}-\d{2}', part):
                    self.date_patterns.add('year_month')
            
            # Analyze path structures
            structure = '/'.join(['{}' for _ in path_parts]) + '/'
            if structure in self.path_structures:
                self.path_structures[structure] += 1
            else:
                self.path_structures[structure] = 1
            
            # Analyze file extensions
            if '.' in parsed.path:
                ext = parsed.path.split('.')[-1].lower()
                if len(ext) <= 5:  # Reasonable extension length
                    self.file_extensions[ext] += 1
        
        # Filter patterns by frequency
        frequent_segments = {seg: count for seg, count in self.url_segments.items() 
                           if count >= self.config.min_pattern_frequency}
        
        pattern_data['segments'] = frequent_segments
        pattern_data['numeric_patterns'] = self.numeric_patterns
        pattern_data['date_patterns'] = self.date_patterns
        pattern_data['structures'] = {struct: count for struct, count in self.path_structures.items() 
                                    if count >= self.config.min_pattern_frequency}
        pattern_data['extensions'] = dict(self.file_extensions.most_common(10))
        
        self.discovery_stats["patterns_analyzed"] = (
            len(frequent_segments) + len(self.numeric_patterns) + 
            len(self.date_patterns) + len(pattern_data['structures'])
        )
        
        print(f"    📊 Found {len(frequent_segments)} frequent segments")
        print(f"    📊 Found {len(self.numeric_patterns)} numeric patterns")
        print(f"    📊 Found {len(self.date_patterns)} date patterns")
        print(f"    📊 Found {len(pattern_data['structures'])} common structures")
        
        return pattern_data
    
    async def _generate_url_variations(self, pattern_data: Dict[str, Any]) -> Set[str]:
        """Generate URL variations based on discovered patterns"""
        print("  🎯 Generating URL variations from patterns...")
        
        generated_urls = set()
        base = self.config.base_url.rstrip('/')
        
        # 1. Generate variations based on frequent segments
        for segment, frequency in pattern_data['segments'].items():
            if len(generated_urls) >= self.config.max_generated_urls:
                break
            
            variations = self._generate_segment_variations(segment, frequency)
            for variation in variations[:self.config.max_variations_per_pattern]:
                new_url = f"{base}/{variation}/"
                if self._should_include_url(new_url):
                    generated_urls.add(new_url)
        
        # 2. Generate numeric pattern variations
        for pattern in pattern_data['numeric_patterns']:
            if len(generated_urls) >= self.config.max_generated_urls:
                break
            
            variations = self._generate_numeric_variations(pattern)
            for variation in variations[:self.config.max_variations_per_pattern]:
                new_url = f"{base}/{variation}/"
                if self._should_include_url(new_url):
                    generated_urls.add(new_url)
        
        # 3. Generate date pattern variations
        if pattern_data['date_patterns']:
            date_variations = self._generate_date_variations()
            for variation in date_variations[:self.config.max_variations_per_pattern]:
                if len(generated_urls) >= self.config.max_generated_urls:
                    break
                new_url = f"{base}/{variation}/"
                if self._should_include_url(new_url):
                    generated_urls.add(new_url)
        
        # 4. Generate variations based on common structures
        for structure, frequency in pattern_data['structures'].items():
            if len(generated_urls) >= self.config.max_generated_urls:
                break
            
            variations = self._generate_structure_variations(structure, pattern_data['segments'])
            for variation in variations[:self.config.max_variations_per_pattern]:
                new_url = f"{base}/{variation}"
                if self._should_include_url(new_url):
                    generated_urls.add(new_url)
        
        # 5. Generate extension-based variations
        for ext, frequency in pattern_data['extensions'].items():
            if len(generated_urls) >= self.config.max_generated_urls:
                break
            
            # Try common filenames with discovered extensions
            common_filenames = [
                'index', 'default', 'main', 'home', 'about', 'contact',
                'info', 'help', 'search', 'sitemap', 'news', 'blog'
            ]
            
            for filename in common_filenames:
                new_url = f"{base}/{filename}.{ext}"
                if self._should_include_url(new_url):
                    generated_urls.add(new_url)
        
        self.discovery_stats["url_variations_created"] = len(generated_urls)
        print(f"    📊 Generated {len(generated_urls)} URL variations")
        
        return generated_urls
    
    def _generate_segment_variations(self, segment: str, frequency: int) -> List[str]:
        """Generate variations of a URL segment"""
        variations = []
        
        # Add the original segment
        variations.append(segment)
        
        # Try plural/singular variations
        if segment.endswith('s') and len(segment) > 2:
            variations.append(segment[:-1])  # Remove 's'
        elif not segment.endswith('s'):
            variations.append(segment + 's')  # Add 's'
        
        # Try with common prefixes/suffixes
        prefixes = ['new', 'old', 'latest', 'recent', 'current', 'archived']
        suffixes = ['list', 'page', 'index', 'detail', 'view', 'archive']
        
        for prefix in prefixes:
            variations.append(f"{prefix}-{segment}")
            variations.append(f"{prefix}_{segment}")
        
        for suffix in suffixes:
            variations.append(f"{segment}-{suffix}")
            variations.append(f"{segment}_{suffix}")
        
        # Try with numbers
        for i in range(1, 11):
            variations.append(f"{segment}{i}")
            variations.append(f"{segment}-{i}")
            variations.append(f"{segment}_{i}")
        
        return variations
    
    def _generate_numeric_variations(self, pattern: str) -> List[str]:
        """Generate variations based on numeric patterns"""
        variations = []
        
        if pattern.isdigit():
            num = int(pattern)
            # Generate nearby numbers
            for i in range(max(1, num - 10), num + 11):
                variations.append(str(i))
            
            # Generate padded versions
            if len(pattern) > 1:
                for i in range(max(1, num - 5), num + 6):
                    variations.append(str(i).zfill(len(pattern)))
        
        else:
            # Pattern contains numbers - try to increment/decrement them
            numbers = re.findall(r'\d+', pattern)
            for num_str in numbers:
                num = int(num_str)
                for i in range(max(1, num - 5), num + 6):
                    new_pattern = pattern.replace(num_str, str(i), 1)
                    variations.append(new_pattern)
        
        return variations
    
    def _generate_date_variations(self) -> List[str]:
        """Generate date-based variations"""
        variations = []
        current_year = datetime.now().year
        
        # Year variations
        for year in range(2020, current_year + 2):
            variations.append(str(year))
            variations.append(f"year-{year}")
            variations.append(f"archive-{year}")
        
        # Month variations
        for month in range(1, 13):
            variations.append(f"{month:02d}")
            variations.append(f"month-{month:02d}")
            
            # Year-month combinations
            for year in range(current_year - 2, current_year + 1):
                variations.append(f"{year}-{month:02d}")
                variations.append(f"{year}/{month:02d}")
        
        # Common date formats
        common_dates = [
            '2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06',
            '2023-12', '2023-11', '2023-10', '2023-09', '2023-08', '2023-07'
        ]
        variations.extend(common_dates)
        
        return variations
    
    def _generate_structure_variations(self, structure: str, segments: Dict[str, int]) -> List[str]:
        """Generate variations based on common path structures"""
        variations = []
        
        # Count placeholders in structure
        placeholder_count = structure.count('{}')
        
        if placeholder_count == 0:
            return [structure]
        
        # Get most common segments for filling placeholders
        common_segments = list(segments.keys())[:20]  # Top 20 most common
        
        # Generate combinations (limited to prevent explosion)
        if placeholder_count == 1:
            for segment in common_segments[:50]:
                variations.append(structure.format(segment))
        
        elif placeholder_count == 2:
            for seg1 in common_segments[:10]:
                for seg2 in common_segments[:5]:
                    variations.append(structure.format(seg1, seg2))
        
        elif placeholder_count == 3:
            for seg1 in common_segments[:5]:
                for seg2 in common_segments[:3]:
                    for seg3 in common_segments[:3]:
                        variations.append(structure.format(seg1, seg2, seg3))
        
        return variations
    
    async def _test_generated_urls_progressive(self, generated_urls: Set[str]):
        """Test generated URLs using progressive enhancement"""
        
        # Convert to list for batch processing
        url_list = list(generated_urls)
        
        # 🧱 BRICK 1: HTTP HEAD requests (fastest)
        print("\n  🧱 BRICK 1: HTTP HEAD Request Testing")
        successful_urls = await self._test_urls_with_head_requests(url_list)
        
        if successful_urls:
            print(f"    🎉 SUCCESS with HEAD requests: {len(successful_urls)} URLs found!")
            self.discovered_urls.update(successful_urls)
            self.discovery_stats["successful_variations"] = len(successful_urls)
            return
        
        # 🧱 BRICK 2: Basic HTTP GET requests
        print("\n  🧱 BRICK 2: HTTP GET Request Testing")
        successful_urls = await self._test_urls_with_get_requests(url_list)
        
        if successful_urls:
            print(f"    🎉 SUCCESS with GET requests: {len(successful_urls)} URLs found!")
            self.discovered_urls.update(successful_urls)
            self.discovery_stats["successful_variations"] = len(successful_urls)
            return
        
        # 🧱 BRICK 3: Crawl4AI testing (slowest but most comprehensive)
        print("\n  🧱 BRICK 3: Crawl4AI Testing")
        await self._test_urls_with_crawl4ai(url_list)
        
        print("\n  ✅ Progressive URL testing complete")
    
    async def _test_urls_with_head_requests(self, urls: List[str]) -> Set[str]:
        """Test URLs with HTTP HEAD requests (fastest method)"""
        successful_urls = set()
        
        try:
            timeout = aiohttp.ClientTimeout(total=5)  # Short timeout for HEAD requests
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; URLTester)'}
            
            # Configure proxy if enabled
            connector = None
            if self.config.proxy_enabled:
                connector = aiohttp.TCPConnector()
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=connector
            ) as session:
                
                batch_size = min(self.config.max_concurrent, 100)  # Higher concurrency for HEAD
                
                for i in range(0, len(urls), batch_size):
                    batch = urls[i:i + batch_size]
                    print(f"      📊 Testing HEAD batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size} ({len(batch)} URLs)")
                    
                    # Create tasks for concurrent HEAD requests
                    tasks = []
                    for url in batch:
                        task = self._test_single_url_head(session, url)
                        tasks.append(task)
                    
                    # Process batch concurrently
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Collect successful URLs
                    for j, result in enumerate(results):
                        if result is True:  # URL exists
                            successful_urls.add(batch[j])
                            print(f"        ✅ Found: {batch[j]}")
                    
                    await asyncio.sleep(0.1)  # Small delay between batches
        
        except Exception as e:
            print(f"      ❌ HEAD request testing failed: {str(e)}")
            logger.error(f"HEAD request testing failed: {e}")
        
        return successful_urls
    
    async def _test_single_url_head(self, session, url: str) -> bool:
        """Test a single URL with HEAD request"""
        try:
            kwargs = {}
            if self.config.proxy_enabled:
                kwargs['proxy'] = self.config.brightdata_proxy
            
            async with session.head(url, **kwargs) as response:
                return response.status in [200, 301, 302]  # Success or redirect
        
        except Exception:
            return False
    
    async def _test_urls_with_get_requests(self, urls: List[str]) -> Set[str]:
        """Test URLs with HTTP GET requests"""
        successful_urls = set()
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; URLTester)'}
            
            # Configure proxy if enabled
            connector = None
            if self.config.proxy_enabled:
                connector = aiohttp.TCPConnector()
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=connector
            ) as session:
                
                batch_size = min(self.config.max_concurrent, 50)
                
                for i in range(0, len(urls), batch_size):
                    batch = urls[i:i + batch_size]
                    print(f"      📊 Testing GET batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size} ({len(batch)} URLs)")
                    
                    # Create tasks for concurrent GET requests
                    tasks = []
                    for url in batch:
                        task = self._test_single_url_get(session, url)
                        tasks.append(task)
                    
                    # Process batch concurrently
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Collect successful URLs
                    for j, result in enumerate(results):
                        if result is True:  # URL exists and has content
                            successful_urls.add(batch[j])
                            print(f"        ✅ Found: {batch[j]}")
                    
                    await asyncio.sleep(self.config.delay_between_requests)
        
        except Exception as e:
            print(f"      ❌ GET request testing failed: {str(e)}")
            logger.error(f"GET request testing failed: {e}")
        
        return successful_urls
    
    async def _test_single_url_get(self, session, url: str) -> bool:
        """Test a single URL with GET request"""
        try:
            kwargs = {}
            if self.config.proxy_enabled:
                kwargs['proxy'] = self.config.brightdata_proxy
            
            async with session.get(url, **kwargs) as response:
                if response.status == 200:
                    content = await response.text()
                    # Basic content validation
                    return len(content) > 200 and '404' not in content.lower()
                return False
        
        except Exception:
            return False
    
    async def _test_urls_with_crawl4ai(self, urls: List[str]):
        """Test URLs with Crawl4AI (most comprehensive)"""
        print("      🚀 Starting Crawl4AI testing...")
        
        try:
            async with AsyncWebCrawler(config=self.browser_configs['basic']) as crawler:
                
                crawler_config = CrawlerRunConfig(
                    page_timeout=15000,
                    verbose=False,
                    wait_for_images=False,
                    delay_before_return_html=1000
                )
                
                batch_size = min(self.config.max_concurrent, 20)  # Smaller batches for Crawl4AI
                successful_urls = set()
                
                for i in range(0, len(urls), batch_size):
                    batch = urls[i:i + batch_size]
                    print(f"        📊 Testing Crawl4AI batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size} ({len(batch)} URLs)")
                    
                    # Create tasks for concurrent crawling
                    tasks = []
                    for url in batch:
                        task = self._test_single_url_crawl4ai(crawler, url, crawler_config)
                        tasks.append(task)
                    
                    # Process batch concurrently
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Collect successful URLs
                    for j, result in enumerate(results):
                        if result is True:  # URL exists and has valid content
                            successful_urls.add(batch[j])
                            print(f"          ✅ Found: {batch[j]}")
                    
                    await asyncio.sleep(self.config.delay_between_requests)
                
                self.discovered_urls.update(successful_urls)
                self.discovery_stats["successful_variations"] = len(successful_urls)
                print(f"      ✅ Crawl4AI testing complete: {len(successful_urls)} URLs found")
        
        except Exception as e:
            print(f"      ❌ Crawl4AI testing failed: {str(e)}")
            logger.error(f"Crawl4AI testing failed: {e}")
    
    async def _test_single_url_crawl4ai(self, crawler, url: str, crawler_config) -> bool:
        """Test a single URL with Crawl4AI"""
        try:
            result_container = await asyncio.wait_for(
                crawler.arun(url=url, config=crawler_config),
                timeout=self.config.timeout
            )
            
            if result_container and len(result_container._results) > 0:
                result = result_container._results[0]
                return result.success and result.html and len(result.html) > 200
            
            return False
            
        except Exception:
            return False
    
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
            "phase": "systematic_path_exploration",
            "total_discovered_urls": len(self.discovered_urls),
            "input_urls_analyzed": len(self.input_urls),
            "patterns_analyzed": self.discovery_stats["patterns_analyzed"],
            "url_variations_created": self.discovery_stats["url_variations_created"],
            "successful_variations": self.discovery_stats["successful_variations"],
            "discovered_urls": sorted(list(self.discovered_urls)),
            "pattern_analysis": {
                "frequent_segments": dict(self.url_segments.most_common(20)),
                "numeric_patterns": list(self.numeric_patterns),
                "date_patterns": list(self.date_patterns),
                "common_structures": dict(list(self.path_structures.items())[:10]),
                "file_extensions": dict(self.file_extensions.most_common(10))
            },
            "discovery_stats": self.discovery_stats,
            "config": {
                "base_url": self.config.base_url,
                "max_generated_urls": self.config.max_generated_urls,
                "min_pattern_frequency": self.config.min_pattern_frequency,
                "max_variations_per_pattern": self.config.max_variations_per_pattern,
                "proxy_enabled": self.config.proxy_enabled,
                "stealth_mode": self.config.stealth_mode
            }
        }
    
    def save_results(self, filename: str = None) -> str:
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"phase6_systematic_path_exploration_results_{timestamp}.json"
        
        results = self._generate_results()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")
        return filename

# Example usage
async def main():
    """Example usage of Phase 6: Systematic Path Exploration"""
    
    # Configuration
    config = SystematicPathConfig(
        base_url="https://www.city.chiyoda.lg.jp",
        max_generated_urls=3000,
        max_concurrent=50,
        min_pattern_frequency=2,
        max_variations_per_pattern=50,
        proxy_enabled=True,
        stealth_mode=True
    )
    
    # Sample input URLs (would normally come from previous phases)
    sample_input_urls = {
        "https://www.city.chiyoda.lg.jp/koho/kurashi/index.html",
        "https://www.city.chiyoda.lg.jp/koho/bunka/index.html",
        "https://www.city.chiyoda.lg.jp/koho/kenko/index.html",
    }
    
    # Create explorer
    explorer = SystematicPathExplorer(config)
    
    # Run systematic path exploration
    results = await explorer.run_systematic_path_exploration(sample_input_urls)
    
    # Save results
    filename = explorer.save_results()
    
    print(f"\n📊 Phase 6 Complete!")
    print(f"📂 URLs discovered: {results['total_discovered_urls']}")
    print(f"🔍 Patterns analyzed: {results['patterns_analyzed']}")
    print(f"🎯 Variations created: {results['url_variations_created']}")
    print(f"✅ Successful variations: {results['successful_variations']}")
    print(f"📁 Results saved: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
