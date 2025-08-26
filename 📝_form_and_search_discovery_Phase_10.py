#!/usr/bin/env python3
"""
Phase 9: Form and Search Discovery - Discover URLs through forms and search functionality
Advanced form interaction and search-based URL discovery
"""

import asyncio
import json
import os
import sys
import time
import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
from typing import Set, List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import deque, Counter
import aiohttp
import psutil
from bs4 import BeautifulSoup
import google.generativeai as genai

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
        logging.FileHandler('phase9_form_and_search_discovery.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class FormSearchConfig:
    """Configuration for form and search discovery"""
    base_url: str
    max_discovered_urls: int = 10000
    max_concurrent: int = 30
    delay_between_requests: float = 0.2
    timeout: int = 20
    max_search_queries: int = 50
    max_form_submissions: int = 100
    
    # Search configuration
    generate_search_queries: bool = True
    use_llm_queries: bool = True
    search_pagination_depth: int = 10
    
    # Form configuration
    test_common_forms: bool = True
    fill_form_fields: bool = True
    test_pagination_forms: bool = True
    
    # PROXY CONFIGURATION
    proxy_enabled: bool = True
    brightdata_proxy: str = 'http://brd-customer-hl_c4d84340-zone-testingdc:l1yptwrxrmbr@brd.superproxy.io:33335'
    
    # STEALTH CONFIGURATION
    stealth_mode: bool = True
    undetected_mode: bool = True
    rotate_user_agents: bool = True
    
    # LLM Configuration
    gemini_api_key: str = None

@dataclass
class FormData:
    """Information about discovered forms"""
    action_url: str
    method: str
    fields: Dict[str, str]
    form_type: str
    element_id: str = ""
    element_class: str = ""

@dataclass
class SearchData:
    """Information about search functionality"""
    search_url: str
    search_param: str
    method: str
    additional_params: Dict[str, str]
    search_type: str

class FormSearchDiscoverer:
    """Phase 9: Form and Search Discovery - Discover URLs through forms and search"""
    
    def __init__(self, config: FormSearchConfig):
        self.config = config
        self.discovered_urls: Set[str] = set()
        self.input_urls: Set[str] = set()
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.domain = urlparse(config.base_url).netloc
        
        # Discovery data
        self.discovered_forms: List[FormData] = []
        self.discovered_searches: List[SearchData] = []
        self.tested_queries: Set[str] = set()
        self.tested_forms: Set[str] = set()
        
        # Discovery statistics
        self.discovery_stats = {
            "forms_discovered": 0,
            "search_endpoints_discovered": 0,
            "queries_tested": 0,
            "forms_submitted": 0,
            "search_urls_found": 0,
            "form_urls_found": 0,
            "pagination_urls_found": 0
        }
        
        # Browser configurations
        self.browser_configs = self._create_browser_configs()
        
        # Initialize Gemini if configured
        self.gemini_client = None
        if config.gemini_api_key:
            try:
                genai.configure(api_key=config.gemini_api_key)
                self.gemini_client = genai.GenerativeModel('gemini-pro')
                print("✅ Gemini AI initialized for adaptive query generation")
            except Exception as e:
                print(f"⚠️  Gemini initialization failed: {e}")
        
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
        if self.config.undetected_mode:
            proxy_param = self.config.brightdata_proxy if self.config.proxy_enabled else None
            configs['undetected'] = BrowserConfig(
                headless=False,
                verbose=False,
                java_script_enabled=True,
                ignore_https_errors=True,
                viewport_width=1920,
                viewport_height=1080,
                proxy=proxy_param,
                adapter="undetected",
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
    
    async def run_form_search_discovery(self, input_urls: Set[str]) -> Dict[str, Any]:
        """Main form and search discovery method"""
        print("\n🔍 PHASE 9: FORM AND SEARCH DISCOVERY")
        print("-" * 50)
        
        start_time = time.time()
        
        # Store input URLs for analysis
        self.input_urls = input_urls.copy()
        print(f"📂 Analyzing {len(input_urls)} input URLs for forms and search functionality")
        
        # Step 1: Discover forms and search endpoints
        await self._discover_forms_and_search_progressive(input_urls)
        
        # Step 2: Generate search queries
        search_queries = await self._generate_search_queries()
        
        # Step 3: Test search functionality
        await self._test_search_functionality(search_queries)
        
        # Step 4: Test form submissions
        await self._test_form_submissions()
        
        # Step 5: Test pagination
        await self._test_pagination_discovery()
        
        end_time = time.time()
        
        print(f"\n✅ Form and Search Discovery Complete!")
        print(f"📊 Total URLs discovered: {len(self.discovered_urls)}")
        print(f"📊 Forms discovered: {self.discovery_stats['forms_discovered']}")
        print(f"📊 Search endpoints: {self.discovery_stats['search_endpoints_discovered']}")
        print(f"📊 Search URLs found: {self.discovery_stats['search_urls_found']}")
        print(f"📊 Form URLs found: {self.discovery_stats['form_urls_found']}")
        print(f"📊 Pagination URLs: {self.discovery_stats['pagination_urls_found']}")
        print(f"⏱️  Total time: {end_time - start_time:.1f}s")
        
        return self._generate_results()
    
    async def _discover_forms_and_search_progressive(self, urls: Set[str]):
        """Discover forms and search functionality using progressive enhancement"""
        print("\n  🔍 Discovering forms and search endpoints...")
        
        # 🧱 BRICK 1: Basic crawling
        print("\n  🧱 BRICK 1: Basic Form/Search Discovery")
        await self._discover_forms_basic(urls)
        
        # 🧱 BRICK 2: Stealth crawling
        if self.config.stealth_mode and not self.discovered_forms:
            print("\n  🧱 BRICK 2: Stealth Form/Search Discovery")
            await self._discover_forms_stealth(urls)
        
        # 🧱 BRICK 3: Undetected crawling
        if self.config.undetected_mode and not self.discovered_forms:
            print("\n  🧱 BRICK 3: Undetected Form/Search Discovery")
            await self._discover_forms_undetected(urls)
        
        print(f"\n  ✅ Discovery complete: {len(self.discovered_forms)} forms, {len(self.discovered_searches)} search endpoints")
    
    async def _discover_forms_basic(self, urls: Set[str]):
        """Discover forms using basic crawling"""
        try:
            async with AsyncWebCrawler(config=self.browser_configs['basic']) as crawler:
                
                crawler_config = CrawlerRunConfig(
                    page_timeout=self.config.timeout * 1000,
                    verbose=False,
                    wait_for_images=False,
                    delay_before_return_html=2000
                )
                
                batch_size = min(self.config.max_concurrent, 10)
                
                for i, url in enumerate(list(urls)[:20]):  # Limit for form discovery
                    print(f"    📊 Analyzing URL {i+1}/20: {url}")
                    
                    try:
                        result_container = await asyncio.wait_for(
                            crawler.arun(url=url, config=crawler_config),
                            timeout=self.config.timeout
                        )
                        
                        if result_container and len(result_container._results) > 0:
                            result = result_container._results[0]
                            if result.success and result.html:
                                await self._extract_forms_and_search(url, result.html)
                    
                    except Exception as e:
                        print(f"    ⚠️  Failed to analyze {url}: {str(e)}")
                        continue
                    
                    await asyncio.sleep(self.config.delay_between_requests)
        
        except Exception as e:
            print(f"    ❌ Basic form discovery failed: {str(e)}")
            logger.error(f"Basic form discovery failed: {e}")
    
    async def _discover_forms_stealth(self, urls: Set[str]):
        """Discover forms using stealth crawling"""
        try:
            async with AsyncWebCrawler(config=self.browser_configs['stealth']) as crawler:
                
                crawler_config = CrawlerRunConfig(
                    page_timeout=self.config.timeout * 1000,
                    verbose=False,
                    wait_for_images=False,
                    delay_before_return_html=3000
                )
                
                for i, url in enumerate(list(urls)[:15]):  # Limit for stealth
                    print(f"    📊 Stealth analyzing URL {i+1}/15: {url}")
                    
                    try:
                        result_container = await asyncio.wait_for(
                            crawler.arun(url=url, config=crawler_config),
                            timeout=self.config.timeout + 10
                        )
                        
                        if result_container and len(result_container._results) > 0:
                            result = result_container._results[0]
                            if result.success and result.html:
                                await self._extract_forms_and_search(url, result.html)
                    
                    except Exception as e:
                        print(f"    ⚠️  Stealth failed for {url}: {str(e)}")
                        continue
                    
                    await asyncio.sleep(self.config.delay_between_requests * 2)
        
        except Exception as e:
            print(f"    ❌ Stealth form discovery failed: {str(e)}")
            logger.error(f"Stealth form discovery failed: {e}")
    
    async def _discover_forms_undetected(self, urls: Set[str]):
        """Discover forms using undetected crawling"""
        try:
            async with AsyncWebCrawler(config=self.browser_configs['undetected']) as crawler:
                
                crawler_config = CrawlerRunConfig(
                    page_timeout=self.config.timeout * 1000,
                    verbose=False,
                    wait_for_images=False,
                    delay_before_return_html=4000
                )
                
                for i, url in enumerate(list(urls)[:10]):  # Limit for undetected
                    print(f"    📊 Undetected analyzing URL {i+1}/10: {url}")
                    
                    try:
                        result_container = await asyncio.wait_for(
                            crawler.arun(url=url, config=crawler_config),
                            timeout=self.config.timeout + 15
                        )
                        
                        if result_container and len(result_container._results) > 0:
                            result = result_container._results[0]
                            if result.success and result.html:
                                await self._extract_forms_and_search(url, result.html)
                    
                    except Exception as e:
                        print(f"    ⚠️  Undetected failed for {url}: {str(e)}")
                        continue
                    
                    await asyncio.sleep(self.config.delay_between_requests * 3)
        
        except Exception as e:
            print(f"    ❌ Undetected form discovery failed: {str(e)}")
            logger.error(f"Undetected form discovery failed: {e}")
    
    async def _extract_forms_and_search(self, page_url: str, html: str):
        """Extract forms and search functionality from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract forms
            forms = soup.find_all('form')
            for form in forms:
                await self._analyze_form(page_url, form)
            
            # Extract search inputs (not in forms)
            search_inputs = soup.find_all('input', {'type': ['search', 'text']})
            for search_input in search_inputs:
                if any(keyword in str(search_input).lower() for keyword in ['search', 'query', 'find', 'keyword']):
                    await self._analyze_search_input(page_url, search_input)
            
            # Extract search links
            search_links = soup.find_all('a', href=True)
            for link in search_links:
                href = link.get('href', '').lower()
                if any(keyword in href for keyword in ['search', 'query', 'find']):
                    await self._analyze_search_link(page_url, link)
        
        except Exception as e:
            logger.error(f"Failed to extract forms from {page_url}: {e}")
    
    async def _analyze_form(self, page_url: str, form_element):
        """Analyze a form element"""
        try:
            action = form_element.get('action', '')
            method = form_element.get('method', 'get').lower()
            form_id = form_element.get('id', '')
            form_class = form_element.get('class', '')
            
            # Convert action to absolute URL
            if action:
                action_url = urljoin(page_url, action)
            else:
                action_url = page_url
            
            # Extract form fields
            fields = {}
            inputs = form_element.find_all(['input', 'select', 'textarea'])
            
            for input_elem in inputs:
                name = input_elem.get('name', '')
                input_type = input_elem.get('type', 'text').lower()
                value = input_elem.get('value', '')
                
                if name and input_type not in ['submit', 'button', 'hidden']:
                    fields[name] = {
                        'type': input_type,
                        'value': value,
                        'required': input_elem.get('required') is not None
                    }
            
            # Determine form type
            form_type = self._classify_form(form_element, fields)
            
            # Create form data
            form_data = FormData(
                action_url=action_url,
                method=method,
                fields=fields,
                form_type=form_type,
                element_id=form_id,
                element_class=str(form_class) if form_class else ""
            )
            
            self.discovered_forms.append(form_data)
            self.discovery_stats["forms_discovered"] += 1
            
            print(f"    🔍 Form found: {form_type} -> {action_url}")
            
            # If it's a search form, also add to search endpoints
            if form_type == 'search':
                search_param = self._find_search_parameter(fields)
                if search_param:
                    search_data = SearchData(
                        search_url=action_url,
                        search_param=search_param,
                        method=method,
                        additional_params={k: v['value'] for k, v in fields.items() if k != search_param and v['value']},
                        search_type='form'
                    )
                    self.discovered_searches.append(search_data)
                    self.discovery_stats["search_endpoints_discovered"] += 1
        
        except Exception as e:
            logger.error(f"Failed to analyze form: {e}")
    
    def _classify_form(self, form_element, fields: Dict) -> str:
        """Classify the type of form"""
        form_text = str(form_element).lower()
        field_names = [name.lower() for name in fields.keys()]
        
        # Search forms
        if any(keyword in form_text for keyword in ['search', 'query', 'find', 'keyword']):
            return 'search'
        
        if any(keyword in ' '.join(field_names) for keyword in ['search', 'query', 'q', 'keyword', 'find']):
            return 'search'
        
        # Login forms
        if any(keyword in field_names for keyword in ['username', 'password', 'login', 'email']):
            return 'login'
        
        # Contact forms
        if any(keyword in field_names for keyword in ['name', 'email', 'message', 'subject']):
            return 'contact'
        
        # Newsletter forms
        if any(keyword in field_names for keyword in ['newsletter', 'subscribe', 'email']):
            return 'newsletter'
        
        # Filter/navigation forms
        if any(keyword in form_text for keyword in ['filter', 'sort', 'category', 'page']):
            return 'filter'
        
        return 'other'
    
    def _find_search_parameter(self, fields: Dict) -> Optional[str]:
        """Find the main search parameter in form fields"""
        # Priority order for search parameters
        search_params = ['q', 'query', 'search', 'keyword', 'term', 's', 'find']
        
        for param in search_params:
            if param in fields:
                return param
        
        # Look for fields with search-like names
        for field_name in fields.keys():
            if any(keyword in field_name.lower() for keyword in ['search', 'query', 'find']):
                return field_name
        
        return None
    
    async def _analyze_search_input(self, page_url: str, input_element):
        """Analyze a search input element"""
        try:
            name = input_element.get('name', '')
            input_id = input_element.get('id', '')
            placeholder = input_element.get('placeholder', '').lower()
            
            if name and any(keyword in name.lower() for keyword in ['search', 'query', 'find']):
                # Find the parent form or assume GET method
                form = input_element.find_parent('form')
                if form:
                    action = form.get('action', page_url)
                    method = form.get('method', 'get').lower()
                else:
                    action = page_url
                    method = 'get'
                
                action_url = urljoin(page_url, action)
                
                search_data = SearchData(
                    search_url=action_url,
                    search_param=name,
                    method=method,
                    additional_params={},
                    search_type='input'
                )
                
                self.discovered_searches.append(search_data)
                self.discovery_stats["search_endpoints_discovered"] += 1
                print(f"    🔍 Search input found: {name} -> {action_url}")
        
        except Exception as e:
            logger.error(f"Failed to analyze search input: {e}")
    
    async def _analyze_search_link(self, page_url: str, link_element):
        """Analyze a search-related link"""
        try:
            href = link_element.get('href', '')
            full_url = urljoin(page_url, href)
            
            # Parse URL to extract search parameters
            parsed = urlparse(full_url)
            query_params = parse_qs(parsed.query)
            
            # Look for search parameters
            search_param = None
            for param in ['q', 'query', 'search', 'keyword', 's']:
                if param in query_params:
                    search_param = param
                    break
            
            if search_param:
                search_data = SearchData(
                    search_url=f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                    search_param=search_param,
                    method='get',
                    additional_params={k: v[0] for k, v in query_params.items() if k != search_param},
                    search_type='link'
                )
                
                self.discovered_searches.append(search_data)
                self.discovery_stats["search_endpoints_discovered"] += 1
                print(f"    🔍 Search link found: {search_param} -> {full_url}")
        
        except Exception as e:
            logger.error(f"Failed to analyze search link: {e}")
    
    async def _generate_search_queries(self) -> List[str]:
        """Generate search queries for testing"""
        print("\n  🎯 Generating search queries...")
        
        queries = set()
        
        # Basic domain-relevant queries
        domain_name = self.domain.replace('www.', '').split('.')[0]
        basic_queries = [
            domain_name,
            'news',
            'information',
            'service',
            'about',
            'contact',
            'help',
            'search',
            'index',
            'home',
            'main',
            '2024',
            '2023',
            'list',
            'archive'
        ]
        queries.update(basic_queries)
        
        # Japanese queries for Japanese sites
        if 'jp' in self.domain:
            japanese_queries = [
                'お知らせ',
                'ニュース',
                '情報',
                'サービス',
                'について',
                'お問い合わせ',
                'ヘルプ',
                '検索',
                'トップ',
                'メイン',
                '一覧',
                'アーカイブ'
            ]
            queries.update(japanese_queries)
        
        # LLM-generated queries
        if self.config.use_llm_queries and self.gemini_client:
            llm_queries = await self._generate_llm_queries()
            queries.update(llm_queries)
        
        # Common search patterns
        patterns = [
            'a', 'e', 'i', 'o', 'u',  # Single letters
            '1', '2', '3', '4', '5',  # Numbers
            'test', 'demo', 'sample'  # Common terms
        ]
        queries.update(patterns)
        
        query_list = list(queries)[:self.config.max_search_queries]
        print(f"    📊 Generated {len(query_list)} search queries")
        
        return query_list
    
    async def _generate_llm_queries(self) -> List[str]:
        """Generate search queries using LLM"""
        try:
            domain_info = f"website domain: {self.domain}"
            
            prompt = f"""Generate 20 relevant search queries for the {domain_info}.
            Focus on:
            1. Services and information the website might offer
            2. Common user search intents
            3. Navigation-related terms
            4. Content categories
            
            Return only the queries, one per line, without numbering or explanation.
            Include both English and local language terms if applicable."""
            
            response = await asyncio.to_thread(
                self.gemini_client.generate_content,
                prompt
            )
            
            if response and response.text:
                queries = [
                    line.strip() 
                    for line in response.text.split('\n') 
                    if line.strip() and len(line.strip()) > 1
                ]
                print(f"    🤖 LLM generated {len(queries)} queries")
                return queries[:20]
        
        except Exception as e:
            print(f"    ⚠️  LLM query generation failed: {e}")
        
        return []
    
    async def _test_search_functionality(self, queries: List[str]):
        """Test search functionality with generated queries"""
        print(f"\n  🔍 Testing search functionality with {len(queries)} queries...")
        
        if not self.discovered_searches:
            print("    ⚠️  No search endpoints discovered, skipping search testing")
            return
        
        for search_data in self.discovered_searches:
            print(f"    🎯 Testing search endpoint: {search_data.search_url}")
            
            batch_size = min(10, len(queries))
            for i in range(0, len(queries), batch_size):
                batch = queries[i:i + batch_size]
                
                search_urls = await self._perform_search_batch(search_data, batch)
                
                # Validate and add discovered URLs
                for url in search_urls:
                    if self._should_include_url(url):
                        self.discovered_urls.add(url)
                        self.discovery_stats["search_urls_found"] += 1
                
                await asyncio.sleep(self.config.delay_between_requests)
        
        print(f"    ✅ Search testing complete: {self.discovery_stats['search_urls_found']} URLs found")
    
    async def _perform_search_batch(self, search_data: SearchData, queries: List[str]) -> Set[str]:
        """Perform a batch of search queries"""
        discovered_urls = set()
        
        try:
            async with AsyncWebCrawler(config=self.browser_configs['basic']) as crawler:
                
                crawler_config = CrawlerRunConfig(
                    page_timeout=self.config.timeout * 1000,
                    verbose=False,
                    wait_for_images=False,
                    delay_before_return_html=1000
                )
                
                for query in queries:
                    try:
                        # Build search URL
                        search_url = self._build_search_url(search_data, query)
                        self.tested_queries.add(query)
                        self.discovery_stats["queries_tested"] += 1
                        
                        # Perform search
                        result_container = await asyncio.wait_for(
                            crawler.arun(url=search_url, config=crawler_config),
                            timeout=self.config.timeout
                        )
                        
                        if result_container and len(result_container._results) > 0:
                            result = result_container._results[0]
                            if result.success and result.html:
                                # Extract URLs from search results
                                search_result_urls = self._extract_search_result_urls(result.html, search_url)
                                discovered_urls.update(search_result_urls)
                                
                                # Test pagination
                                pagination_urls = await self._extract_search_pagination(result.html, search_url)
                                discovered_urls.update(pagination_urls)
                    
                    except Exception as e:
                        print(f"      ⚠️  Search failed for query '{query}': {str(e)}")
                        continue
                    
                    await asyncio.sleep(0.1)
        
        except Exception as e:
            print(f"    ❌ Search batch failed: {str(e)}")
        
        return discovered_urls
    
    def _build_search_url(self, search_data: SearchData, query: str) -> str:
        """Build a search URL with the given query"""
        if search_data.method.lower() == 'get':
            # Build GET URL with parameters
            params = {search_data.search_param: query}
            params.update(search_data.additional_params)
            
            query_string = urlencode(params)
            separator = '&' if '?' in search_data.search_url else '?'
            
            return f"{search_data.search_url}{separator}{query_string}"
        else:
            # For POST, return base URL (would need form submission)
            return search_data.search_url
    
    def _extract_search_result_urls(self, html: str, search_url: str) -> Set[str]:
        """Extract URLs from search result HTML"""
        urls = set()
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all links
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href')
                if href:
                    # Convert to absolute URL
                    absolute_url = urljoin(search_url, href)
                    
                    # Basic validation
                    if self._should_include_url(absolute_url):
                        urls.add(absolute_url)
        
        except Exception as e:
            logger.error(f"Failed to extract search result URLs: {e}")
        
        return urls
    
    async def _extract_search_pagination(self, html: str, search_url: str) -> Set[str]:
        """Extract pagination URLs from search results"""
        urls = set()
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for pagination links
            pagination_selectors = [
                'a[href*="page"]',
                'a[href*="p="]',
                'a[href*="offset"]',
                'a[href*="start"]',
                '.pagination a',
                '.pager a',
                '.page-numbers a'
            ]
            
            for selector in pagination_selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        absolute_url = urljoin(search_url, href)
                        if self._should_include_url(absolute_url):
                            urls.add(absolute_url)
                            self.discovery_stats["pagination_urls_found"] += 1
        
        except Exception as e:
            logger.error(f"Failed to extract pagination URLs: {e}")
        
        return urls
    
    async def _test_form_submissions(self):
        """Test form submissions to discover new URLs"""
        print(f"\n  📝 Testing form submissions...")
        
        if not self.discovered_forms:
            print("    ⚠️  No forms discovered, skipping form testing")
            return
        
        for form_data in self.discovered_forms:
            if form_data.form_type in ['search', 'filter', 'other']:
                print(f"    📝 Testing {form_data.form_type} form: {form_data.action_url}")
                
                try:
                    form_urls = await self._submit_form_variations(form_data)
                    
                    for url in form_urls:
                        if self._should_include_url(url):
                            self.discovered_urls.add(url)
                            self.discovery_stats["form_urls_found"] += 1
                    
                    self.tested_forms.add(form_data.action_url)
                    self.discovery_stats["forms_submitted"] += 1
                
                except Exception as e:
                    print(f"      ⚠️  Form submission failed: {str(e)}")
                    continue
                
                await asyncio.sleep(self.config.delay_between_requests)
        
        print(f"    ✅ Form testing complete: {self.discovery_stats['form_urls_found']} URLs found")
    
    async def _submit_form_variations(self, form_data: FormData) -> Set[str]:
        """Submit form with various input combinations"""
        discovered_urls = set()
        
        # Generate test values for form fields
        test_values = self._generate_form_test_values(form_data.fields)
        
        try:
            async with AsyncWebCrawler(config=self.browser_configs['basic']) as crawler:
                
                crawler_config = CrawlerRunConfig(
                    page_timeout=self.config.timeout * 1000,
                    verbose=False,
                    wait_for_images=False,
                    delay_before_return_html=2000
                )
                
                for values in test_values[:5]:  # Limit form submissions
                    try:
                        # Build form submission URL
                        form_url = self._build_form_url(form_data, values)
                        
                        result_container = await asyncio.wait_for(
                            crawler.arun(url=form_url, config=crawler_config),
                            timeout=self.config.timeout
                        )
                        
                        if result_container and len(result_container._results) > 0:
                            result = result_container._results[0]
                            if result.success and result.html:
                                # Extract URLs from form response
                                response_urls = self._extract_search_result_urls(result.html, form_url)
                                discovered_urls.update(response_urls)
                    
                    except Exception as e:
                        print(f"      ⚠️  Form submission failed for {values}: {str(e)}")
                        continue
                    
                    await asyncio.sleep(0.2)
        
        except Exception as e:
            print(f"    ❌ Form variations failed: {str(e)}")
        
        return discovered_urls
    
    def _generate_form_test_values(self, fields: Dict) -> List[Dict[str, str]]:
        """Generate test values for form fields"""
        test_combinations = []
        
        # Common test values by field type
        test_values = {
            'search': ['test', 'info', 'news', 'service', 'a'],
            'query': ['test', 'info', 'news', 'service', 'a'],
            'q': ['test', 'info', 'news', 'service', 'a'],
            'keyword': ['test', 'info', 'news'],
            'category': ['1', '2', 'all', 'news'],
            'page': ['1', '2', '3'],
            'sort': ['date', 'name', 'title'],
            'year': ['2024', '2023'],
            'month': ['01', '02', '12'],
            'type': ['all', 'list', 'detail']
        }
        
        # Generate combinations
        for field_name, field_info in fields.items():
            field_name_lower = field_name.lower()
            
            # Get appropriate test values
            values = []
            for key, test_vals in test_values.items():
                if key in field_name_lower:
                    values = test_vals
                    break
            
            if not values:
                # Default values based on field type
                if field_info['type'] == 'number':
                    values = ['1', '2', '10']
                elif field_info['type'] == 'email':
                    values = ['test@example.com']
                else:
                    values = ['test', 'a', '1']
            
            # Create combinations
            for value in values[:3]:  # Limit combinations
                combination = {field_name: value}
                
                # Add default values for other required fields
                for other_field, other_info in fields.items():
                    if other_field != field_name and other_info.get('required', False):
                        combination[other_field] = other_info.get('value', 'test')
                
                test_combinations.append(combination)
        
        return test_combinations[:10]  # Limit total combinations
    
    def _build_form_url(self, form_data: FormData, values: Dict[str, str]) -> str:
        """Build URL for form submission"""
        if form_data.method.lower() == 'get':
            # Build GET URL
            params = values.copy()
            query_string = urlencode(params)
            separator = '&' if '?' in form_data.action_url else '?'
            return f"{form_data.action_url}{separator}{query_string}"
        else:
            # For POST, return base URL (would need actual form submission)
            return form_data.action_url
    
    async def _test_pagination_discovery(self):
        """Test pagination patterns on discovered URLs"""
        print(f"\n  📄 Testing pagination patterns...")
        
        # Test pagination on some discovered URLs
        test_urls = list(self.discovered_urls)[:20] if self.discovered_urls else list(self.input_urls)[:10]
        
        pagination_urls = set()
        
        for base_url in test_urls:
            # Generate pagination variants
            variants = self._generate_pagination_variants(base_url)
            
            # Test variants
            for variant in variants[:5]:  # Limit testing
                if await self._test_url_exists(variant):
                    pagination_urls.add(variant)
                    self.discovery_stats["pagination_urls_found"] += 1
                    print(f"    📄 Pagination found: {variant}")
        
        self.discovered_urls.update(pagination_urls)
        print(f"    ✅ Pagination testing complete: {len(pagination_urls)} URLs found")
    
    def _generate_pagination_variants(self, base_url: str) -> List[str]:
        """Generate pagination URL variants"""
        variants = []
        parsed = urlparse(base_url)
        
        # Query parameter pagination
        for page in range(2, 6):  # Pages 2-5
            for param in ['page', 'p', 'pagenum', 'offset', 'start']:
                if '?' in base_url:
                    variants.append(f"{base_url}&{param}={page}")
                else:
                    variants.append(f"{base_url}?{param}={page}")
        
        # Path-based pagination
        base_path = parsed.path.rstrip('/')
        for page in range(2, 6):
            variants.append(f"{parsed.scheme}://{parsed.netloc}{base_path}/page/{page}/")
            variants.append(f"{parsed.scheme}://{parsed.netloc}{base_path}/{page}/")
        
        return variants
    
    async def _test_url_exists(self, url: str) -> bool:
        """Test if a URL exists"""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.head(url) as response:
                    return response.status in [200, 301, 302]
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
            skip_extensions = ['.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.pdf', '.zip', '.exe']
            if any(path.endswith(ext) for ext in skip_extensions):
                return False
            
            # Skip obvious non-content URLs
            skip_patterns = [
                '/css/', '/js/', '/images/', '/img/', '/assets/', '/static/',
                '#', 'javascript:', 'mailto:'
            ]
            
            if any(pattern in url.lower() for pattern in skip_patterns):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _generate_results(self) -> Dict[str, Any]:
        """Generate comprehensive results"""
        return {
            "phase": "form_and_search_discovery",
            "total_discovered_urls": len(self.discovered_urls),
            "input_urls_analyzed": len(self.input_urls),
            "forms_discovered": self.discovery_stats["forms_discovered"],
            "search_endpoints_discovered": self.discovery_stats["search_endpoints_discovered"],
            "queries_tested": self.discovery_stats["queries_tested"],
            "forms_submitted": self.discovery_stats["forms_submitted"],
            "search_urls_found": self.discovery_stats["search_urls_found"],
            "form_urls_found": self.discovery_stats["form_urls_found"],
            "pagination_urls_found": self.discovery_stats["pagination_urls_found"],
            "discovered_urls": sorted(list(self.discovered_urls)),
            "discovered_forms": [
                {
                    "action_url": form.action_url,
                    "method": form.method,
                    "form_type": form.form_type,
                    "fields": list(form.fields.keys()),
                    "element_id": form.element_id,
                    "element_class": form.element_class
                }
                for form in self.discovered_forms
            ],
            "discovered_searches": [
                {
                    "search_url": search.search_url,
                    "search_param": search.search_param,
                    "method": search.method,
                    "search_type": search.search_type,
                    "additional_params": search.additional_params
                }
                for search in self.discovered_searches
            ],
            "discovery_stats": self.discovery_stats,
            "config": {
                "base_url": self.config.base_url,
                "max_search_queries": self.config.max_search_queries,
                "max_form_submissions": self.config.max_form_submissions,
                "generate_search_queries": self.config.generate_search_queries,
                "use_llm_queries": self.config.use_llm_queries,
                "test_common_forms": self.config.test_common_forms,
                "proxy_enabled": self.config.proxy_enabled,
                "stealth_mode": self.config.stealth_mode,
                "undetected_mode": self.config.undetected_mode
            }
        }
    
    def save_results(self, filename: str = None) -> str:
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"phase9_form_search_discovery_results_{timestamp}.json"
        
        results = self._generate_results()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")
        return filename

# Example usage
async def main():
    """Example usage of Phase 9: Form and Search Discovery"""
    
    # Configuration
    config = FormSearchConfig(
        base_url="https://www.city.chiyoda.lg.jp",
        max_search_queries=30,
        max_form_submissions=50,
        generate_search_queries=True,
        use_llm_queries=True,
        test_common_forms=True,
        proxy_enabled=True,
        stealth_mode=True,
        undetected_mode=True,
        gemini_api_key=os.getenv("GEMINI_API_KEY")
    )
    
    # Sample input URLs (would normally come from previous phases)
    sample_input_urls = {
        "https://www.city.chiyoda.lg.jp/",
        "https://www.city.chiyoda.lg.jp/koho/index.html",
        "https://www.city.chiyoda.lg.jp/koho/kurashi/index.html",
    }
    
    # Create discoverer
    discoverer = FormSearchDiscoverer(config)
    
    # Run form and search discovery
    results = await discoverer.run_form_search_discovery(sample_input_urls)
    
    # Save results
    filename = discoverer.save_results()
    
    print(f"\n📊 Phase 9 Complete!")
    print(f"📂 URLs discovered: {results['total_discovered_urls']}")
    print(f"📝 Forms discovered: {results['forms_discovered']}")
    print(f"🔍 Search endpoints: {results['search_endpoints_discovered']}")
    print(f"🎯 Search URLs found: {results['search_urls_found']}")
    print(f"📝 Form URLs found: {results['form_urls_found']}")
    print(f"📄 Pagination URLs: {results['pagination_urls_found']}")
    print(f"📁 Results saved: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
