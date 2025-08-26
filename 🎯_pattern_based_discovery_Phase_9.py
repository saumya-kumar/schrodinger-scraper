#!/usr/bin/env python3
"""
Phase 8: Pattern-Based Discovery - Generate URLs from discovered patterns
Advanced pattern analysis and URL generation based on discovered site structure
"""

import asyncio
import json
import os
import sys
import time
import logging
import re
from datetime import datetime, timedelta
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
        logging.FileHandler('phase8_pattern_based_discovery.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class PatternDiscoveryConfig:
    """Configuration for pattern-based discovery"""
    base_url: str
    max_generated_urls: int = 10000
    max_concurrent: int = 50
    delay_between_requests: float = 0.1
    timeout: int = 15
    include_pdfs: bool = False  # PDFs excluded per requirement
    include_images: bool = False
    
    # Pattern generation settings
    min_pattern_frequency: int = 2
    max_variations_per_pattern: int = 200
    generate_date_patterns: bool = True
    generate_numeric_patterns: bool = True
    generate_language_patterns: bool = True
    
    # PROXY CONFIGURATION
    proxy_enabled: bool = True
    brightdata_proxy: str = 'http://brd-customer-hl_c4d84340-zone-testingdc:l1yptwrxrmbr@brd.superproxy.io:33335'
    
    # STEALTH CONFIGURATION
    stealth_mode: bool = True
    rotate_user_agents: bool = True

class PatternBasedDiscoverer:
    """Phase 8: Pattern-Based Discovery - Generate URLs from discovered patterns"""
    
    def __init__(self, config: PatternDiscoveryConfig):
        self.config = config
        self.discovered_urls: Set[str] = set()
        self.input_urls: Set[str] = set()
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.domain = urlparse(config.base_url).netloc
        
        # Pattern analysis data
        self.url_patterns: Dict[str, int] = {}
        self.path_segments: Counter = Counter()
        self.numeric_patterns: Set[str] = set()
        self.date_patterns: Set[str] = set()
        self.file_extensions: Counter = Counter()
        self.query_parameters: Counter = Counter()
        
        # Discovery statistics
        self.discovery_stats = {
            "pattern_generated_urls": 0,
            "patterns_analyzed": 0,
            "url_variations_created": 0,
            "successful_patterns": 0,
            "tested_patterns": 0
        }
        
        # Browser configurations
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
        
        return configs
    
    async def run_pattern_based_discovery(self, input_urls: Set[str]) -> Dict[str, Any]:
        """Main pattern-based discovery method"""
        print("\n🎯 PHASE 8: PATTERN-BASED DISCOVERY")
        print("-" * 50)
        
        start_time = time.time()
        
        # Store input URLs for analysis
        self.input_urls = input_urls.copy()
        print(f"📂 Analyzing {len(input_urls)} input URLs for advanced patterns")
        
        # Step 1: Advanced pattern analysis
        pattern_data = await self._analyze_advanced_patterns()
        
        # Step 2: Generate URL variations based on patterns
        generated_urls = await self._generate_pattern_variations(pattern_data)
        
        # Step 3: Test generated URLs
        await self._test_pattern_urls_progressive(generated_urls)
        
        end_time = time.time()
        self.discovery_stats["pattern_generated_urls"] = len(self.discovered_urls)
        
        print(f"\n✅ Pattern-Based Discovery Complete!")
        print(f"📊 URLs discovered: {len(self.discovered_urls)}")
        print(f"📊 Patterns analyzed: {self.discovery_stats['patterns_analyzed']}")
        print(f"📊 URL variations created: {self.discovery_stats['url_variations_created']}")
        print(f"📊 Successful patterns: {self.discovery_stats['successful_patterns']}")
        print(f"⏱️  Total time: {end_time - start_time:.1f}s")
        
        return self._generate_results()
    
    async def _analyze_advanced_patterns(self) -> Dict[str, Any]:
        """Analyze URLs for advanced patterns"""
        print("  🔍 Analyzing advanced URL patterns...")
        
        pattern_data = {
            'year_patterns': set(),
            'month_patterns': set(),
            'date_patterns': set(),
            'numeric_sequences': set(),
            'id_patterns': set(),
            'category_patterns': set(),
            'file_patterns': set(),
            'query_patterns': set(),
            'path_structures': {},
            'language_patterns': set()
        }
        
        for url in self.input_urls:
            parsed = urlparse(url)
            path_parts = [part for part in parsed.path.split('/') if part]
            
            # Analyze each path component
            for part in path_parts:
                self.path_segments[part] += 1
                
                # Year patterns (2000-2030)
                if re.match(r'^20[0-3]\d$', part):
                    pattern_data['year_patterns'].add(int(part))
                
                # Month patterns
                if re.match(r'^(0[1-9]|1[0-2])$', part):
                    pattern_data['month_patterns'].add(int(part))
                
                # Numeric ID patterns
                if part.isdigit():
                    if len(part) <= 8:  # Reasonable ID length
                        pattern_data['id_patterns'].add(int(part))
                
                # Sequential patterns (like page1, item2, etc.)
                seq_match = re.match(r'^(\w+)(\d+)$', part)
                if seq_match:
                    prefix, number = seq_match.groups()
                    pattern_data['numeric_sequences'].add((prefix, int(number)))
                
                # Language patterns (en, ja, zh, etc.)
                if len(part) == 2 and part.isalpha():
                    pattern_data['language_patterns'].add(part.lower())
                
                # Category-like patterns (common website sections)
                if part.lower() in ['news', 'blog', 'article', 'post', 'page', 'category', 'tag']:
                    pattern_data['category_patterns'].add(part.lower())
            
            # File extension analysis
            if '.' in parsed.path:
                ext = parsed.path.split('.')[-1].lower()
                if len(ext) <= 5:
                    self.file_extensions[ext] += 1
                    pattern_data['file_patterns'].add(ext)
            
            # Query parameter analysis
            if parsed.query:
                params = parsed.query.split('&')
                for param in params:
                    if '=' in param:
                        key, value = param.split('=', 1)
                        self.query_parameters[key] += 1
                        pattern_data['query_patterns'].add(key)
            
            # Path structure analysis
            if len(path_parts) > 0:
                structure = '/'.join(['{}'] * len(path_parts))
                if structure in pattern_data['path_structures']:
                    pattern_data['path_structures'][structure] += 1
                else:
                    pattern_data['path_structures'][structure] = 1
        
        self.discovery_stats["patterns_analyzed"] = (
            len(pattern_data['year_patterns']) + len(pattern_data['month_patterns']) +
            len(pattern_data['id_patterns']) + len(pattern_data['numeric_sequences']) +
            len(pattern_data['category_patterns']) + len(pattern_data['file_patterns']) +
            len(pattern_data['query_patterns']) + len(pattern_data['language_patterns'])
        )
        
        print(f"    📊 Year patterns: {len(pattern_data['year_patterns'])}")
        print(f"    📊 Numeric sequences: {len(pattern_data['numeric_sequences'])}")
        print(f"    📊 ID patterns: {len(pattern_data['id_patterns'])}")
        print(f"    📊 Category patterns: {len(pattern_data['category_patterns'])}")
        print(f"    📊 File patterns: {len(pattern_data['file_patterns'])}")
        print(f"    📊 Query patterns: {len(pattern_data['query_patterns'])}")
        print(f"    📊 Language patterns: {len(pattern_data['language_patterns'])}")
        
        return pattern_data
    
    async def _generate_pattern_variations(self, pattern_data: Dict[str, Any]) -> Set[str]:
        """Generate URL variations based on discovered patterns"""
        print("  🎯 Generating URL variations from advanced patterns...")
        
        generated_urls = set()
        base = self.config.base_url.rstrip('/')
        
        # 1. Year-based patterns
        if self.config.generate_date_patterns and pattern_data['year_patterns']:
            year_urls = self._generate_year_variations(base, pattern_data['year_patterns'])
            generated_urls.update(year_urls)
        
        # 2. Month-based patterns
        if self.config.generate_date_patterns and pattern_data['month_patterns']:
            month_urls = self._generate_month_variations(base, pattern_data)
            generated_urls.update(month_urls)
        
        # 3. Numeric ID patterns
        if self.config.generate_numeric_patterns and pattern_data['id_patterns']:
            id_urls = self._generate_id_variations(base, pattern_data['id_patterns'])
            generated_urls.update(id_urls)
        
        # 4. Sequential patterns
        if self.config.generate_numeric_patterns and pattern_data['numeric_sequences']:
            seq_urls = self._generate_sequence_variations(base, pattern_data['numeric_sequences'])
            generated_urls.update(seq_urls)
        
        # 5. Category-based patterns
        if pattern_data['category_patterns']:
            category_urls = self._generate_category_variations(base, pattern_data['category_patterns'])
            generated_urls.update(category_urls)
        
        # 6. File extension patterns
        if pattern_data['file_patterns']:
            file_urls = self._generate_file_variations(base, pattern_data['file_patterns'])
            generated_urls.update(file_urls)
        
        # 7. Query parameter patterns
        if pattern_data['query_patterns']:
            query_urls = self._generate_query_variations(base, pattern_data['query_patterns'])
            generated_urls.update(query_urls)
        
        # 8. Language patterns
        if self.config.generate_language_patterns and pattern_data['language_patterns']:
            lang_urls = self._generate_language_variations(base, pattern_data['language_patterns'])
            generated_urls.update(lang_urls)
        
        # 9. Path structure variations
        if pattern_data['path_structures']:
            structure_urls = self._generate_structure_variations(base, pattern_data['path_structures'])
            generated_urls.update(structure_urls)
        
        # Limit total generated URLs
        if len(generated_urls) > self.config.max_generated_urls:
            generated_urls = set(list(generated_urls)[:self.config.max_generated_urls])
        
        self.discovery_stats["url_variations_created"] = len(generated_urls)
        print(f"    📊 Generated {len(generated_urls)} URL variations from patterns")
        
        return generated_urls
    
    def _generate_year_variations(self, base: str, year_patterns: Set[int]) -> Set[str]:
        """Generate year-based URL variations"""
        urls = set()
        current_year = datetime.now().year
        
        # Common year range
        year_range = range(2020, current_year + 2)
        
        # Generate variations for discovered years
        for year in year_patterns:
            # Archive patterns
            urls.add(f"{base}/archive/{year}/")
            urls.add(f"{base}/news/{year}/")
            urls.add(f"{base}/blog/{year}/")
            urls.add(f"{base}/posts/{year}/")
            urls.add(f"{base}/articles/{year}/")
            
            # Year-based sections
            urls.add(f"{base}/{year}/")
            urls.add(f"{base}/year/{year}/")
            urls.add(f"{base}/annual/{year}/")
        
        # Generate for extended year range
        for year in year_range:
            if year not in year_patterns:  # Only new years
                urls.add(f"{base}/archive/{year}/")
                urls.add(f"{base}/news/{year}/")
                urls.add(f"{base}/{year}/")
        
        return {url for url in urls if self._should_include_url(url)}
    
    def _generate_month_variations(self, base: str, pattern_data: Dict[str, Any]) -> Set[str]:
        """Generate month-based URL variations"""
        urls = set()
        
        years = pattern_data['year_patterns'] or {datetime.now().year}
        months = range(1, 13)
        
        for year in years:
            for month in months:
                month_str = f"{month:02d}"
                urls.add(f"{base}/archive/{year}/{month_str}/")
                urls.add(f"{base}/news/{year}/{month_str}/")
                urls.add(f"{base}/blog/{year}/{month_str}/")
                urls.add(f"{base}/{year}/{month_str}/")
                urls.add(f"{base}/posts/{year}-{month_str}/")
        
        return {url for url in urls if self._should_include_url(url)}
    
    def _generate_id_variations(self, base: str, id_patterns: Set[int]) -> Set[str]:
        """Generate ID-based URL variations"""
        urls = set()
        
        # Find ID range
        if id_patterns:
            min_id = min(id_patterns)
            max_id = max(id_patterns)
            
            # Generate variations around discovered IDs
            for id_val in id_patterns:
                # Common ID-based patterns
                urls.add(f"{base}/post/{id_val}/")
                urls.add(f"{base}/article/{id_val}/")
                urls.add(f"{base}/page/{id_val}/")
                urls.add(f"{base}/news/{id_val}/")
                urls.add(f"{base}/item/{id_val}/")
                urls.add(f"{base}/id/{id_val}/")
                
                # Generate nearby IDs
                for offset in [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5]:
                    new_id = id_val + offset
                    if new_id > 0:
                        urls.add(f"{base}/post/{new_id}/")
                        urls.add(f"{base}/article/{new_id}/")
                        urls.add(f"{base}/page/{new_id}/")
        
        return {url for url in urls if self._should_include_url(url)}
    
    def _generate_sequence_variations(self, base: str, sequences: Set[tuple]) -> Set[str]:
        """Generate sequential pattern variations"""
        urls = set()
        
        for prefix, number in sequences:
            # Generate variations around discovered sequences
            for i in range(max(1, number - 10), number + 11):
                urls.add(f"{base}/{prefix}{i}/")
                urls.add(f"{base}/content/{prefix}{i}/")
                urls.add(f"{base}/section/{prefix}{i}/")
        
        return {url for url in urls if self._should_include_url(url)}
    
    def _generate_category_variations(self, base: str, categories: Set[str]) -> Set[str]:
        """Generate category-based variations"""
        urls = set()
        
        # Common category combinations
        subcategories = [
            'archive', 'list', 'index', 'all', 'latest', 'recent',
            'popular', 'featured', 'top', 'best', 'new', 'old'
        ]
        
        for category in categories:
            urls.add(f"{base}/{category}/")
            urls.add(f"{base}/category/{category}/")
            urls.add(f"{base}/section/{category}/")
            
            for sub in subcategories:
                urls.add(f"{base}/{category}/{sub}/")
                urls.add(f"{base}/category/{category}/{sub}/")
        
        return {url for url in urls if self._should_include_url(url)}
    
    def _generate_file_variations(self, base: str, extensions: Set[str]) -> Set[str]:
        """Generate file-based variations"""
        urls = set()
        
        # Common filenames
        filenames = [
            'index', 'default', 'main', 'home', 'about', 'contact',
            'info', 'help', 'search', 'sitemap', 'news', 'blog',
            'archive', 'list', 'directory', 'contents', 'menu'
        ]
        
        for ext in extensions:
            for filename in filenames:
                urls.add(f"{base}/{filename}.{ext}")
                urls.add(f"{base}/pages/{filename}.{ext}")
                urls.add(f"{base}/content/{filename}.{ext}")
        
        return {url for url in urls if self._should_include_url(url)}
    
    def _generate_query_variations(self, base: str, query_params: Set[str]) -> Set[str]:
        """Generate query parameter variations"""
        urls = set()
        
        # Common parameter values
        param_values = {
            'page': ['1', '2', '3', '4', '5'],
            'id': ['1', '2', '3', '100', '1000'],
            'category': ['news', 'blog', 'article'],
            'type': ['list', 'detail', 'archive'],
            'lang': ['en', 'ja', 'zh'],
            'year': ['2023', '2024'],
            'sort': ['date', 'name', 'popular']
        }
        
        for param in query_params:
            values = param_values.get(param, ['1', '2', '3'])
            for value in values:
                urls.add(f"{base}/?{param}={value}")
                urls.add(f"{base}/index.html?{param}={value}")
        
        return {url for url in urls if self._should_include_url(url)}
    
    def _generate_language_variations(self, base: str, languages: Set[str]) -> Set[str]:
        """Generate language-based variations"""
        urls = set()
        
        # Common language codes
        all_languages = {'en', 'ja', 'zh', 'ko', 'es', 'fr', 'de', 'it', 'pt', 'ru'}
        all_languages.update(languages)
        
        for lang in all_languages:
            urls.add(f"{base}/{lang}/")
            urls.add(f"{base}/lang/{lang}/")
            urls.add(f"{base}/language/{lang}/")
            urls.add(f"{base}/{lang}/index.html")
            urls.add(f"{base}/{lang}/home/")
            urls.add(f"{base}/{lang}/about/")
        
        return {url for url in urls if self._should_include_url(url)}
    
    def _generate_structure_variations(self, base: str, structures: Dict[str, int]) -> Set[str]:
        """Generate variations based on path structures"""
        urls = set()
        
        # Get most common segments
        common_segments = [seg for seg, count in self.path_segments.most_common(30)]
        
        for structure, frequency in structures.items():
            if frequency < self.config.min_pattern_frequency:
                continue
            
            placeholder_count = structure.count('{}')
            
            if placeholder_count == 1:
                for segment in common_segments[:20]:
                    path = structure.format(segment)
                    urls.add(f"{base}/{path}")
            
            elif placeholder_count == 2:
                for seg1 in common_segments[:10]:
                    for seg2 in common_segments[:10]:
                        path = structure.format(seg1, seg2)
                        urls.add(f"{base}/{path}")
        
        return {url for url in urls if self._should_include_url(url)}
    
    async def _test_pattern_urls_progressive(self, generated_urls: Set[str]):
        """Test generated pattern URLs using progressive enhancement"""
        
        url_list = list(generated_urls)
        self.discovery_stats["tested_patterns"] = len(url_list)
        
        # 🧱 BRICK 1: HTTP HEAD requests (fastest)
        print("\n  🧱 BRICK 1: HTTP HEAD Pattern Testing")
        successful_urls = await self._test_pattern_urls_head(url_list)
        
        if successful_urls:
            print(f"    🎉 SUCCESS with HEAD requests: {len(successful_urls)} pattern URLs found!")
            self.discovered_urls.update(successful_urls)
            self.discovery_stats["successful_patterns"] = len(successful_urls)
            return
        
        # 🧱 BRICK 2: HTTP GET requests
        print("\n  🧱 BRICK 2: HTTP GET Pattern Testing")
        successful_urls = await self._test_pattern_urls_get(url_list)
        
        if successful_urls:
            print(f"    🎉 SUCCESS with GET requests: {len(successful_urls)} pattern URLs found!")
            self.discovered_urls.update(successful_urls)
            self.discovery_stats["successful_patterns"] = len(successful_urls)
            return
        
        # 🧱 BRICK 3: Crawl4AI testing
        print("\n  🧱 BRICK 3: Crawl4AI Pattern Testing")
        await self._test_pattern_urls_crawl4ai(url_list)
        
        print("\n  ✅ Progressive pattern URL testing complete")
    
    async def _test_pattern_urls_head(self, urls: List[str]) -> Set[str]:
        """Test pattern URLs with HTTP HEAD requests"""
        successful_urls = set()
        
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; PatternTester)'}
            
            connector = None
            if self.config.proxy_enabled:
                connector = aiohttp.TCPConnector()
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=connector
            ) as session:
                
                batch_size = min(self.config.max_concurrent, 100)
                
                for i in range(0, len(urls), batch_size):
                    batch = urls[i:i + batch_size]
                    print(f"      📊 Testing HEAD batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size}")
                    
                    tasks = [self._test_single_pattern_head(session, url) for url in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for j, result in enumerate(results):
                        if result is True:
                            successful_urls.add(batch[j])
                            print(f"        ✅ Pattern found: {batch[j]}")
                    
                    await asyncio.sleep(0.1)
        
        except Exception as e:
            print(f"      ❌ HEAD pattern testing failed: {str(e)}")
            logger.error(f"HEAD pattern testing failed: {e}")
        
        return successful_urls
    
    async def _test_single_pattern_head(self, session, url: str) -> bool:
        """Test a single pattern URL with HEAD request"""
        try:
            kwargs = {}
            if self.config.proxy_enabled:
                kwargs['proxy'] = self.config.brightdata_proxy
            
            async with session.head(url, **kwargs) as response:
                return response.status in [200, 301, 302]
        
        except Exception:
            return False
    
    async def _test_pattern_urls_get(self, urls: List[str]) -> Set[str]:
        """Test pattern URLs with HTTP GET requests"""
        successful_urls = set()
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; PatternTester)'}
            
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
                    print(f"      📊 Testing GET batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size}")
                    
                    tasks = [self._test_single_pattern_get(session, url) for url in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for j, result in enumerate(results):
                        if result is True:
                            successful_urls.add(batch[j])
                            print(f"        ✅ Pattern found: {batch[j]}")
                    
                    await asyncio.sleep(self.config.delay_between_requests)
        
        except Exception as e:
            print(f"      ❌ GET pattern testing failed: {str(e)}")
            logger.error(f"GET pattern testing failed: {e}")
        
        return successful_urls
    
    async def _test_single_pattern_get(self, session, url: str) -> bool:
        """Test a single pattern URL with GET request"""
        try:
            kwargs = {}
            if self.config.proxy_enabled:
                kwargs['proxy'] = self.config.brightdata_proxy
            
            async with session.get(url, **kwargs) as response:
                if response.status == 200:
                    content = await response.text()
                    return len(content) > 200 and '404' not in content.lower()
                return False
        
        except Exception:
            return False
    
    async def _test_pattern_urls_crawl4ai(self, urls: List[str]):
        """Test pattern URLs with Crawl4AI"""
        print("      🚀 Starting Crawl4AI pattern testing...")
        
        try:
            async with AsyncWebCrawler(config=self.browser_configs['basic']) as crawler:
                
                crawler_config = CrawlerRunConfig(
                    page_timeout=15000,
                    verbose=False,
                    wait_for_images=False,
                    delay_before_return_html=1000
                )
                
                batch_size = min(self.config.max_concurrent, 20)
                successful_urls = set()
                
                for i in range(0, len(urls), batch_size):
                    batch = urls[i:i + batch_size]
                    print(f"        📊 Testing Crawl4AI batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size}")
                    
                    tasks = [self._test_single_pattern_crawl4ai(crawler, url, crawler_config) for url in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for j, result in enumerate(results):
                        if result is True:
                            successful_urls.add(batch[j])
                            print(f"          ✅ Pattern found: {batch[j]}")
                    
                    await asyncio.sleep(self.config.delay_between_requests)
                
                self.discovered_urls.update(successful_urls)
                self.discovery_stats["successful_patterns"] = len(successful_urls)
                print(f"      ✅ Crawl4AI pattern testing complete: {len(successful_urls)} URLs found")
        
        except Exception as e:
            print(f"      ❌ Crawl4AI pattern testing failed: {str(e)}")
            logger.error(f"Crawl4AI pattern testing failed: {e}")
    
    async def _test_single_pattern_crawl4ai(self, crawler, url: str, crawler_config) -> bool:
        """Test a single pattern URL with Crawl4AI"""
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
            "phase": "pattern_based_discovery",
            "total_discovered_urls": len(self.discovered_urls),
            "input_urls_analyzed": len(self.input_urls),
            "patterns_analyzed": self.discovery_stats["patterns_analyzed"],
            "url_variations_created": self.discovery_stats["url_variations_created"],
            "tested_patterns": self.discovery_stats["tested_patterns"],
            "successful_patterns": self.discovery_stats["successful_patterns"],
            "discovered_urls": sorted(list(self.discovered_urls)),
            "pattern_analysis": {
                "common_path_segments": dict(self.path_segments.most_common(20)),
                "file_extensions": dict(self.file_extensions.most_common(10)),
                "query_parameters": dict(self.query_parameters.most_common(10))
            },
            "discovery_stats": self.discovery_stats,
            "config": {
                "base_url": self.config.base_url,
                "max_generated_urls": self.config.max_generated_urls,
                "max_variations_per_pattern": self.config.max_variations_per_pattern,
                "generate_date_patterns": self.config.generate_date_patterns,
                "generate_numeric_patterns": self.config.generate_numeric_patterns,
                "generate_language_patterns": self.config.generate_language_patterns,
                "proxy_enabled": self.config.proxy_enabled,
                "stealth_mode": self.config.stealth_mode
            }
        }
    
    def save_results(self, filename: str = None) -> str:
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"phase8_pattern_based_discovery_results_{timestamp}.json"
        
        results = self._generate_results()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")
        return filename

# Example usage
async def main():
    """Example usage of Phase 8: Pattern-Based Discovery"""
    
    # Configuration
    config = PatternDiscoveryConfig(
        base_url="https://www.city.chiyoda.lg.jp",
        max_generated_urls=5000,
        max_concurrent=50,
        max_variations_per_pattern=100,
        generate_date_patterns=True,
        generate_numeric_patterns=True,
        generate_language_patterns=True,
        proxy_enabled=True,
        stealth_mode=True
    )
    
    # Sample input URLs (would normally come from previous phases)
    sample_input_urls = {
        "https://www.city.chiyoda.lg.jp/koho/kurashi/index.html",
        "https://www.city.chiyoda.lg.jp/koho/bunka/index.html",
        "https://www.city.chiyoda.lg.jp/koho/kenko/index.html",
        "https://www.city.chiyoda.lg.jp/koho/kurashi/2024/news1.html",
        "https://www.city.chiyoda.lg.jp/koho/kurashi/2023/news2.html",
    }
    
    # Create discoverer
    discoverer = PatternBasedDiscoverer(config)
    
    # Run pattern-based discovery
    results = await discoverer.run_pattern_based_discovery(sample_input_urls)
    
    # Save results
    filename = discoverer.save_results()
    
    print(f"\n📊 Phase 8 Complete!")
    print(f"📂 URLs discovered: {results['total_discovered_urls']}")
    print(f"🔍 Patterns analyzed: {results['patterns_analyzed']}")
    print(f"🎯 Variations created: {results['url_variations_created']}")
    print(f"✅ Successful patterns: {results['successful_patterns']}")
    print(f"📁 Results saved: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
