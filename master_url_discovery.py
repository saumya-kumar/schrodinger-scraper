#!/usr/bin/env python3
"""
MASTER URL DISCOVERY CONTROLLER
Runs all 10 phases for COMPREHENSIVE website URL discovery
Optimized for finding EVERY single URL with HTML priority
"""

import asyncio
import json
import time
import logging
from datetime import datetime
from typing import Set, List, Dict, Any
from urllib.parse import urlparse
import importlib.util
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_url_discovery.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def import_module_from_path(module_name: str, file_path: str) -> Any:
    """Dynamically imports a module from a given file path."""
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            raise ImportError(f"Could not load spec for module {module_name} from {file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except FileNotFoundError:
        raise ImportError(f"File not found for module {module_name} at {file_path}")

class ComprehensiveURLDiscoveryMaster:
    """Master controller for running all 10 URL discovery phases"""
    
    def __init__(self, base_url: str, gemini_api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.gemini_api_key = gemini_api_key
        
        # Master URL collection
        self.all_discovered_urls: Set[str] = set()
        self.phase_results: Dict[str, Dict] = {}
        
        # Discovery statistics
        self.discovery_stats = {
            "total_phases_run": 0,
            "successful_phases": 0,
            "failed_phases": 0,
            "total_urls_discovered": 0,
            "html_priority_urls": 0,
            "other_page_urls": 0,
            "discovery_start_time": None,
            "discovery_end_time": None,
            "total_discovery_time": 0
        }
    
    async def run_comprehensive_discovery(self) -> Dict[str, Any]:
        """Run all 10 phases for maximum URL discovery"""
        
        print("🚀 STARTING COMPREHENSIVE URL DISCOVERY")
        print("=" * 80)
        print(f"🎯 Target: {self.base_url}")
        print(f"🌐 Domain: {self.domain}")
        print(f"🤖 LLM: {'Enabled' if self.gemini_api_key else 'Fallback patterns'}")
        print("=" * 80)
        
        self.discovery_stats["discovery_start_time"] = time.time()
        
        # Phase execution order optimized for maximum discovery
        phases = [
            ("Phase 1: Sitemap Discovery", self._run_sitemap_discovery),
            ("Phase 2: Robots.txt & LLM Analysis", self._run_robots_llm_analysis),
            ("Phase 3: URL Seeding", self._run_url_seeding),
            ("Phase 4: Recursive Link Crawling", self._run_recursive_crawling),
            ("Phase 5: Hierarchical Parent Crawling", self._run_hierarchical_crawling),
            ("Phase 6: Directory Discovery", self._run_directory_discovery),
            ("Phase 7: Systematic Path Exploration", self._run_path_exploration),
            ("Phase 8: Aggressive Deep Crawling", self._run_aggressive_crawling),
            ("Phase 9: Pattern-Based Discovery", self._run_pattern_discovery),
            ("Phase 10: Form and Search Discovery", self._run_form_search_discovery)
        ]
        
        # Run each phase
        for phase_name, phase_func in phases:
            try:
                print(f"\n🔄 {phase_name}")
                print("-" * 60)
                
                phase_start = time.time()
                result = await phase_func()
                phase_end = time.time()
                
                if result and result.get('success', False):
                    new_urls = set(result.get('urls', []))
                    phase_new_count = len(new_urls - self.all_discovered_urls)
                    self.all_discovered_urls.update(new_urls)
                    
                    self.phase_results[phase_name] = {
                        **result,
                        'execution_time': phase_end - phase_start,
                        'new_urls_found': phase_new_count,
                        'total_urls_after_phase': len(self.all_discovered_urls)
                    }
                    
                    self.discovery_stats["successful_phases"] += 1
                    
                    print(f"✅ {phase_name} completed successfully")
                    print(f"   📊 New URLs found: {phase_new_count}")
                    print(f"   📊 Total URLs now: {len(self.all_discovered_urls)}")
                    print(f"   ⏱️  Phase time: {phase_end - phase_start:.1f}s")
                    
                else:
                    self.phase_results[phase_name] = {
                        'success': False,
                        'error': result.get('error', 'Unknown error') if result else 'No result',
                        'execution_time': phase_end - phase_start
                    }
                    self.discovery_stats["failed_phases"] += 1
                    
                    print(f"❌ {phase_name} failed: {result.get('error', 'Unknown error') if result else 'No result'}")
                
                self.discovery_stats["total_phases_run"] += 1
                
                # Brief pause between phases
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"❌ {phase_name} exception: {e}")
                self.phase_results[phase_name] = {
                    'success': False,
                    'error': str(e),
                    'execution_time': 0
                }
                self.discovery_stats["failed_phases"] += 1
                self.discovery_stats["total_phases_run"] += 1
                
                # Continue to next phase even if one fails
                continue
        
        # Finalize discovery
        self.discovery_stats["discovery_end_time"] = time.time()
        self.discovery_stats["total_discovery_time"] = (
            self.discovery_stats["discovery_end_time"] - 
            self.discovery_stats["discovery_start_time"]
        )
        
        # Generate final results
        final_results = await self._generate_final_results()
        
        # Save comprehensive results
        await self._save_comprehensive_results(final_results)
        
        return final_results
    
    async def _run_sitemap_discovery(self) -> Dict[str, Any]:
        """Run Phase 1: Sitemap Discovery"""
        try:
            # Dynamically import sitemap discovery
            sitemap_module = import_module_from_path(
                "sitemap_discovery", 
                os.path.join(os.path.dirname(__file__), "🗺️_sitemap_discovery_Phase_1.py")
            )
            SitemapDiscovery = getattr(sitemap_module, "SitemapDiscovery")
            SitemapConfig = getattr(sitemap_module, "SitemapConfig")
            
            config = SitemapConfig(
                base_url=self.base_url,
                timeout=15,
                output_file="temp_sitemap_results.json",
                verbose=True
            )
            
            discoverer = SitemapDiscovery(config)
            results = await discoverer.discover_all_sitemaps()
            
            return {
                'success': True,
                'urls': list(discoverer.discovered_urls),
                'phase_stats': results.get('summary', {}),
                'method_breakdown': results.get('method_stats', {})
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_robots_llm_analysis(self) -> Dict[str, Any]:
        """Run Phase 2: Robots.txt & LLM Analysis"""
        try:
            # Dynamically import LLM integration
            llm_module = import_module_from_path(
                "llm_integration_comprehensive",
                os.path.join(os.path.dirname(__file__), "llm_integration_comprehensive.py")
            )
            generate_phase_patterns = getattr(llm_module, "generate_phase_patterns")
            
            # Generate LLM patterns for comprehensive discovery
            llm_urls = await generate_phase_patterns(
                domain=self.domain,
                discovered_urls=list(self.all_discovered_urls)[:5],
                phase="robots_analysis",
                api_key=self.gemini_api_key
            )
            
            return {
                'success': True,
                'urls': llm_urls,
                'phase_stats': {'llm_generated_urls': len(llm_urls)}
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_url_seeding(self) -> Dict[str, Any]:
        """Run Phase 3: URL Seeding"""
        # Strategy:
        # 1. Prefer the enhanced seeding module (🌐_url_seeding_Phase_3.py) which can leverage
        #    Common Crawl + (optionally) recursive sitemaps / deep crawl. We constrain features
        #    here to only sitemap + Common Crawl for speed/cost unless explicitly enabled.
        # 2. Fallback to lightweight LLM pattern generation if enhanced module not available
        #    or fails (e.g., crawl4ai missing, network blocked).
        # 3. Apply the global filtering rules (skip binary/doc asset extensions, keep same domain).
        try:
            enhanced_path = os.path.join(os.path.dirname(__file__), "🌐_url_seeding_Phase_3.py")
            seeding_module = import_module_from_path("enhanced_url_seeding_phase3", enhanced_path)
            URLSeedingConfig = getattr(seeding_module, "URLSeedingConfig")
            EnhancedURLSeeder = getattr(seeding_module, "EnhancedURLSeeder")
            # Determine which URLSeedingConfig signature we have (there are two variants in the file)
            cfg_kwargs = {}
            annotations = getattr(URLSeedingConfig, '__annotations__', {})
            if 'source' in annotations:  # First lightweight config (top of file)
                cfg_kwargs = {
                    'source': 'sitemap+cc',
                    'max_urls': -1,
                    'enable_common_crawl': True,
                    'enable_recursive_sitemap': True,
                    'enable_deep_crawling': False,
                    'max_depth': 1,
                    'verbose': False,
                    'force_refresh': False
                }
            else:  # Enhanced second config requires base_url and different flags
                cfg_kwargs = {
                    'base_url': self.base_url,
                    'use_sitemap': True,
                    'use_common_crawl': True,
                    'use_enhanced_sitemaps': True,
                    'recursive_sitemap_discovery': True,
                    'cross_domain_analysis': False,
                    'smart_filtering': True,
                    'verbose': False,
                    'use_llm_analysis': False
                }
            cfg = URLSeedingConfig(**cfg_kwargs)

            seeded_urls: Set[str] = set()
            # Some environments may lack crawl4ai dependency; guard with try/except
            try:
                async with EnhancedURLSeeder(cfg) as seeder:
                    discovered = await seeder.discover_urls(self.base_url)
                    # Handle both return shapes: List[str] or Dict[domain -> List[dict/url]]
                    if isinstance(discovered, dict):
                        # Two possibilities: dict of domain->list[str] OR domain->list[dict]
                        for dom, entries in discovered.items():
                            if not entries:
                                continue
                            if isinstance(entries, list) and entries and isinstance(entries[0], dict):
                                seeded_urls.update([e.get('url') for e in entries if 'url' in e])
                            else:
                                seeded_urls.update(entries)
                    elif isinstance(discovered, (list, set, tuple)):
                        seeded_urls.update(discovered)
                    # Attempt to read stats attributes defensively
                    cc_count = getattr(seeder, 'stats', {}).get('common_crawl_urls') or getattr(seeder, 'stats', {}).get('discovery_stats', {}).get('common_crawl_urls', 0)
                    sitemap_seed = getattr(seeder, 'stats', {}).get('sitemap_urls') or getattr(seeder, 'stats', {}).get('discovery_stats', {}).get('sitemap_urls', 0)
                    recursive_component = getattr(seeder, 'stats', {}).get('recursive_sitemap_urls') or getattr(seeder, 'stats', {}).get('discovery_stats', {}).get('recursive_sitemap_urls', 0)
                    phase_stats = {
                        'seeded_urls': len(seeded_urls),
                        'common_crawl_urls': cc_count or 0,
                        'sitemap_seed_urls': sitemap_seed or 0,
                        'recursive_sitemap_component': recursive_component or 0
                    }
            except Exception as enhanced_err:
                # Fallback to original LLM pattern expansion
                llm_module = import_module_from_path(
                    "llm_integration_comprehensive",
                    os.path.join(os.path.dirname(__file__), "llm_integration_comprehensive.py")
                )
                generate_phase_patterns = getattr(llm_module, "generate_phase_patterns")
                patterns = await generate_phase_patterns(
                    domain=self.domain,
                    discovered_urls=list(self.all_discovered_urls)[:5],
                    phase="pattern_generation",
                    api_key=self.gemini_api_key
                )
                seeded_urls.update(patterns)
                phase_stats = {
                    'seeded_urls': len(seeded_urls),
                    'fallback_llm_used': True,
                    'fallback_error': str(enhanced_err)
                }

            # Filtering (defensive – enhanced seeder already attempts minimal filtering)
            skip_exts = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.css', '.js', '.xml', '.json', '.csv', '.zip', '.rar', '.7z', '.mp3', '.mp4', '.avi', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')
            domain_host = self.domain.lower()
            filtered = []
            for u in seeded_urls:
                lu = u.lower()
                if any(lu.endswith(ext) for ext in skip_exts):
                    continue
                if domain_host not in lu.split('//', 1)[-1]:  # basic same-domain check
                    continue
                filtered.append(u)

            return {
                'success': True,
                'urls': filtered,
                'phase_stats': phase_stats
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_recursive_crawling(self) -> Dict[str, Any]:
        """Run Phase 4: Recursive Link Crawling"""
        try:
            recursive_module = import_module_from_path(
                "recursive_link_crawling",
                os.path.join(os.path.dirname(__file__), "🔄_recursive_link_crawling_Phase_4.py")
            )
            RecursiveLinkCrawler = getattr(recursive_module, "RecursiveLinkCrawler")
            RecursiveCrawlConfig = getattr(recursive_module, "RecursiveCrawlConfig")

            config = RecursiveCrawlConfig(
                base_url=self.base_url,
                include_pdfs=False,
                include_images=False,
                stealth_mode=True,
                proxy_enabled=False
            )
            crawler = RecursiveLinkCrawler(config)
            # Seed with current URLs (sitemaps + earlier phases)
            seed = self.all_discovered_urls.copy() or {self.base_url}
            crawler.discovered_urls.update(seed)
            results = await crawler.run_recursive_crawling() if hasattr(crawler, 'run_recursive_crawling') else {'discovered_urls': list(seed), 'discovery_stats': {}}

            urls = set(results.get('discovered_urls', []))
            # Filter out skipped file types defensively
            skip_exts = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.css', '.js', '.xml', '.json', '.csv', '.zip', '.rar', '.7z')
            urls = {u for u in urls if not any(u.lower().endswith(e) for e in skip_exts)}

            return {
                'success': True,
                'urls': list(urls),
                'phase_stats': results.get('discovery_stats', {})
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_hierarchical_crawling(self) -> Dict[str, Any]:
        """Run Phase 5: Hierarchical Parent Crawling"""
        try:
            # Dynamically import hierarchical crawler
            hierarchical_module = import_module_from_path(
                "hierarchical_crawling",
                os.path.join(os.path.dirname(__file__), "🌳_hierarchical_parent_crawling_Phase_5.py")
            )
            HierarchicalParentCrawler = getattr(hierarchical_module, "HierarchicalParentCrawler")
            HierarchicalCrawlConfig = getattr(hierarchical_module, "HierarchicalCrawlConfig")
            
            config = HierarchicalCrawlConfig(
                base_url=self.base_url,
                max_pages=1000,
                proxy_enabled=False,  # Disable for testing
                stealth_mode=True
            )
            
            crawler = HierarchicalParentCrawler(config)
            results = await crawler.run_hierarchical_crawling(seed_urls=self.all_discovered_urls)
            
            return {
                'success': True,
                'urls': results.get('discovered_urls', []),
                'phase_stats': results.get('discovery_stats', {})
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_directory_discovery(self) -> Dict[str, Any]:
        """Run Phase 6: Directory Discovery"""
        try:
            # Dynamically import LLM integration
            llm_module = import_module_from_path(
                "llm_integration_comprehensive",
                os.path.join(os.path.dirname(__file__), "llm_integration_comprehensive.py")
            )
            generate_phase_patterns = getattr(llm_module, "generate_phase_patterns")
            
            directory_urls = await generate_phase_patterns(
                domain=self.domain,
                discovered_urls=list(self.all_discovered_urls)[:5],
                phase="directory_discovery",
                api_key=self.gemini_api_key
            )
            
            return {
                'success': True,
                'urls': directory_urls,
                'phase_stats': {'directory_urls': len(directory_urls)}
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_path_exploration(self) -> Dict[str, Any]:
        """Run Phase 7: Systematic Path Exploration"""
        try:
            path_module = import_module_from_path(
                "systematic_path_exploration",
                os.path.join(os.path.dirname(__file__), "🔎_systematic_path_exploration_Phase_7.py")
            )
            SystematicPathExplorer = getattr(path_module, "SystematicPathExplorer")
            SystematicPathConfig = getattr(path_module, "SystematicPathConfig")

            config = SystematicPathConfig(
                base_url=self.base_url,
                include_pdfs=False,
                stealth_mode=True,
                proxy_enabled=False
            )
            explorer = SystematicPathExplorer(config)
            input_urls = self.all_discovered_urls.copy()
            explorer.input_urls.update(input_urls)
            results = await explorer.run_systematic_path_exploration(input_urls) if hasattr(explorer, 'run_systematic_path_exploration') else {'discovered_urls': list(input_urls), 'discovery_stats': {}}

            urls = set(results.get('discovered_urls', []))
            skip_exts = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.css', '.js', '.xml', '.json', '.csv', '.zip', '.rar', '.7z')
            urls = {u for u in urls if not any(u.lower().endswith(e) for e in skip_exts)}

            return {
                'success': True,
                'urls': list(urls),
                'phase_stats': results.get('discovery_stats', {})
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_aggressive_crawling(self) -> Dict[str, Any]:
        """Run Phase 8: Aggressive Deep Crawling"""
        try:
            aggressive_module = import_module_from_path(
                "aggressive_deep_crawling",
                os.path.join(os.path.dirname(__file__), "🔥_aggressive_deep_crawling_Phase_8.py")
            )
            AggressiveDeepCrawler = getattr(aggressive_module, "AggressiveDeepCrawler")
            AggressiveCrawlConfig = getattr(aggressive_module, "AggressiveCrawlConfig")

            config = AggressiveCrawlConfig(
                base_url=self.base_url,
                include_pdfs=False,
                stealth_mode=True,
                proxy_enabled=False
            )
            crawler = AggressiveDeepCrawler(config)
            crawler.input_urls.update(self.all_discovered_urls)
            results = await crawler.run_aggressive_crawling() if hasattr(crawler, 'run_aggressive_crawling') else {'discovered_urls': list(self.all_discovered_urls), 'discovery_stats': {}}

            urls = set(results.get('discovered_urls', []))
            skip_exts = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.css', '.js', '.xml', '.json', '.csv', '.zip', '.rar', '.7z')
            urls = {u for u in urls if not any(u.lower().endswith(e) for e in skip_exts)}

            return {
                'success': True,
                'urls': list(urls),
                'phase_stats': results.get('discovery_stats', {})
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_pattern_discovery(self) -> Dict[str, Any]:
        """Run Phase 9: Pattern-Based Discovery"""
        try:
            # Dynamically import LLM integration
            llm_module = import_module_from_path(
                "llm_integration_comprehensive",
                os.path.join(os.path.dirname(__file__), "llm_integration_comprehensive.py")
            )
            generate_phase_patterns = getattr(llm_module, "generate_phase_patterns")
            
            pattern_urls = await generate_phase_patterns(
                domain=self.domain,
                discovered_urls=list(self.all_discovered_urls)[:10],
                phase="pattern_generation",
                api_key=self.gemini_api_key
            )
            
            return {
                'success': True,
                'urls': pattern_urls,
                'phase_stats': {'pattern_urls': len(pattern_urls)}
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _run_form_search_discovery(self) -> Dict[str, Any]:
        """Run Phase 10: Form and Search Discovery"""
        try:
            # Dynamically import LLM integration
            llm_module = import_module_from_path(
                "llm_integration_comprehensive",
                os.path.join(os.path.dirname(__file__), "llm_integration_comprehensive.py")
            )
            generate_phase_patterns = getattr(llm_module, "generate_phase_patterns")
            
            search_urls = await generate_phase_patterns(
                domain=self.domain,
                discovered_urls=list(self.all_discovered_urls)[:5],
                phase="search_queries",
                api_key=self.gemini_api_key
            )
            
            return {
                'success': True,
                'urls': search_urls,
                'phase_stats': {'search_urls': len(search_urls)}
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _generate_final_results(self) -> Dict[str, Any]:
        """Generate comprehensive final results"""
        
        # Use comprehensive filtering for final results
        try:
            # Dynamically import comprehensive filter
            filter_module = import_module_from_path(
                "comprehensive_url_filter",
                os.path.join(os.path.dirname(__file__), "comprehensive_url_filter.py")
            )
            optimize_url_discovery_for_phases = getattr(filter_module, "optimize_url_discovery_for_phases")
            
            optimization_results = optimize_url_discovery_for_phases(
                self.all_discovered_urls, 
                self.domain
            )
            
            self.discovery_stats.update({
                "total_urls_discovered": len(optimization_results["comprehensive_urls"]),
                "html_priority_urls": len(optimization_results["html_priority_urls"]),
                # Priority 2 currently unused (reserved), priority 3 = other page-like URLs
                "other_page_urls": len(optimization_results["prioritized_urls"][3])
            })
            
            return {
                "comprehensive_discovery_complete": True,
                "base_url": self.base_url,
                "domain": self.domain,
                "discovery_statistics": self.discovery_stats,
                "url_optimization": optimization_results,
                "phase_results": self.phase_results,
                "final_url_list": optimization_results["comprehensive_urls"],
                "prioritized_urls": optimization_results["prioritized_urls"]
            }
            
        except Exception as e:
            print(f"⚠️  Final optimization failed, using basic results: {e}")
            
            self.discovery_stats["total_urls_discovered"] = len(self.all_discovered_urls)
            
            return {
                "comprehensive_discovery_complete": True,
                "base_url": self.base_url,
                "domain": self.domain,
                "discovery_statistics": self.discovery_stats,
                "phase_results": self.phase_results,
                "final_url_list": sorted(list(self.all_discovered_urls))
            }
    
    async def _save_comprehensive_results(self, results: Dict[str, Any]):
        """Save comprehensive discovery results"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_url_discovery_{self.domain}_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 COMPREHENSIVE RESULTS SAVED: {filename}")
            print(f"📊 Total URLs discovered: {results['discovery_statistics']['total_urls_discovered']}")
            print(f"🎯 HTML priority URLs: {results['discovery_statistics'].get('html_priority_urls', 'N/A')}")
            print(f"✅ Successful phases: {results['discovery_statistics']['successful_phases']}/10")
            print(f"⏱️  Total discovery time: {results['discovery_statistics']['total_discovery_time']:.1f}s")
            
        except Exception as e:
            print(f"❌ Failed to save comprehensive results: {e}")

async def run_comprehensive_url_discovery(base_url: str, gemini_api_key: str = None) -> Dict[str, Any]:
    """Main function to run comprehensive URL discovery"""
    
    master = ComprehensiveURLDiscoveryMaster(base_url, gemini_api_key)
    return await master.run_comprehensive_discovery()

# Example usage
async def main():
    """Example usage for comprehensive discovery"""
    
    # Get user input for target website
    print("🌐 COMPREHENSIVE URL DISCOVERY SYSTEM")
    print("=" * 50)
    
    while True:
        website_url = input("Enter target website URL: ").strip()
        
        if not website_url:
            print("❌ Please enter a valid URL")
            continue
            
        # Add https:// if no protocol provided
        if not website_url.startswith(('http://', 'https://')):
            website_url = 'https://' + website_url
            
        try:
            # Use urlparse from the imported module
            parsed = urlparse(website_url)
            if not parsed.netloc:
                print("❌ Invalid URL format. Please try again.")
                continue
            break
        except Exception:
            print("❌ Invalid URL format. Please try again.")
            continue
    
    print(f"\n🚀 Starting comprehensive discovery for: {website_url}")
    
    # Run comprehensive discovery
    results = await run_comprehensive_url_discovery(
        base_url=website_url,
        gemini_api_key=None  # Will use environment variable
    )
    
    print("\n🎉 COMPREHENSIVE URL DISCOVERY COMPLETE!")

if __name__ == "__main__":
    asyncio.run(main())
