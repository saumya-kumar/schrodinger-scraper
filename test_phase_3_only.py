#!/usr/bin/env python3
"""Test Phase 3 individually"""

import sys
import time
import asyncio
sys.path.append('.')

def test_phase_3_individual():
    """Test Phase 3 - Ultra-Maximum URL Discovery individually"""
    print("🧪 TESTING PHASE 3 INDIVIDUALLY")
    print("🌐 PHASE 3: ULTRA-MAXIMUM URL DISCOVERY")
    print("=" * 60)
    
    base_url = "https://www.city.chiyoda.lg.jp/"
    start_time = time.time()
    discovered_urls = set()
    
    try:
        # Import the comprehensive URL seeding system
        from importlib import import_module
        enhanced_phase3 = import_module('🌐_url_seeding_Phase_3')
        
        async def run_phase3_discovery():
            print(f"🚀 Using ultra-comprehensive URL discovery system...")
            
            # Extract domain from base URL
            domain = base_url.replace('https://', '').replace('http://', '').rstrip('/')
            
            # Configure for maximum discovery
            config = enhanced_phase3.URLSeedingConfig(
                base_url=base_url,
                use_sitemap=True,
                use_common_crawl=True,
                use_enhanced_sitemaps=True,
                max_urls_per_domain=50000,  # Very high limit
                concurrency=50,
                hits_per_sec=25,
                extract_head=False,  # Skip for speed
                live_check=False,  # Skip for speed
                verbose=True,
                force_refresh=True,
                smart_filtering=True,
                recursive_sitemap_discovery=True,
                cross_domain_analysis=False,
                use_llm_analysis=False,  # Skip LLM for speed
                query="municipal government services information pages"
            )
            
            # Use the comprehensive seeder
            async with enhanced_phase3.EnhancedURLSeeder(config) as seeder:
                print("🔄 Running comprehensive URL discovery...")
                
                # Discover URLs
                results = await seeder.discover_urls([domain])
                
                # Extract all URLs
                all_discovered = set()
                if 'discovered_urls' in results:
                    for domain_name, urls in results['discovered_urls'].items():
                        if isinstance(urls, list):
                            for url in urls:
                                if isinstance(url, dict):
                                    if 'url' in url:
                                        all_discovered.add(url['url'])
                                elif isinstance(url, str):
                                    all_discovered.add(url)
                
                print(f"✅ Phase 3 discovery completed: {len(all_discovered)} URLs")
                return list(all_discovered)
        
        # Run the async function
        urls = asyncio.run(run_phase3_discovery())
        discovered_urls.update(urls)
        print(f"🎯 Phase 3 found: {len(urls)} URLs")
        
    except Exception as enhanced_error:
        print(f"⚠️ Enhanced system failed ({enhanced_error}), trying fallback...")
        
        try:
            # Fallback to AsyncUrlSeeder
            from crawl4ai import AsyncUrlSeeder, SeedingConfig
            
            async def run_fallback():
                domain = base_url.replace('https://', '').replace('http://', '').rstrip('/')
                
                async with AsyncUrlSeeder() as seeder:
                    config = SeedingConfig(
                        source="sitemap+cc",
                        pattern="*",
                        extract_head=False,
                        max_urls=10000,
                        concurrency=30,
                        hits_per_sec=20,
                        verbose=True,
                        force=True,
                        filter_nonsense_urls=False
                    )
                    
                    print("🔄 Running fallback URL seeding...")
                    urls = await seeder.urls(domain, config)
                    step_urls = [url["url"] if isinstance(url, dict) else url for url in urls]
                    print(f"✅ Fallback method found: {len(step_urls)} URLs")
                    return step_urls
            
            urls = asyncio.run(run_fallback())
            discovered_urls.update(urls)
            
        except Exception as fallback_error:
            print(f"❌ Fallback also failed ({fallback_error})")
            # Basic fallback
            import requests
            try:
                response = requests.get(f"{base_url}sitemap.html", timeout=10)
                if response.status_code == 200:
                    discovered_urls.add(f"{base_url}sitemap.html")
                    print("✅ Basic fallback found sitemap.html")
            except:
                print("❌ All methods failed")
    
    execution_time = time.time() - start_time
    
    print(f"\n✅ PHASE 3 INDIVIDUAL TEST COMPLETED")
    print(f"⏱️ Execution Time: {execution_time:.2f}s")
    print(f"📊 Total URLs Found: {len(discovered_urls)}")
    print(f"🎯 URLs per second: {len(discovered_urls)/execution_time:.1f}")
    
    # Show some sample URLs
    if discovered_urls:
        print(f"\n📋 Sample URLs found:")
        sample_urls = list(discovered_urls)[:10]
        for i, url in enumerate(sample_urls, 1):
            print(f"   {i:2d}. {url}")
        if len(discovered_urls) > 10:
            print(f"   ... and {len(discovered_urls) - 10} more URLs")
    
    return len(discovered_urls)

if __name__ == "__main__":
    result = test_phase_3_individual()
    print(f"\n🏁 Phase 3 Individual Test Result: {result} URLs discovered")
