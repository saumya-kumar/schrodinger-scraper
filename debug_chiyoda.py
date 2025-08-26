#!/usr/bin/env python3
"""
Debug script to see exactly what content we're getting from Chiyoda sitemaps
"""

import asyncio
import aiohttp
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def debug_chiyoda_content():
    """Debug what content we're actually getting from Chiyoda"""
    
    base_url = "https://www.city.chiyoda.lg.jp"
    sitemap_urls = [
        f"{base_url}/sitemap.xml",
        f"{base_url}/sitemap.html"
    ]
    
    print("🔍 Debugging Chiyoda Content")
    print("=" * 50)
    
    # Test with browser first
    print("\n📋 Testing with Crawl4AI Browser:")
    browser_config = BrowserConfig(headless=False, verbose=False)
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for url in sitemap_urls:
            print(f"\n🔍 Testing: {url}")
            
            try:
                result_container = await crawler.arun(
                    url=url, 
                    config=CrawlerRunConfig(page_timeout=15000, verbose=False)
                )
                
                if result_container and len(result_container._results) > 0:
                    result = result_container._results[0]
                    if result.success and result.markdown:
                        content = result.markdown
                        print(f"  📄 Content length: {len(content)} chars")
                        print(f"  📄 Content preview:")
                        print(f"  {content[:500]}...")
                        print(f"  📄 Last 200 chars:")
                        print(f"  ...{content[-200:]}")
                    else:
                        print(f"  ❌ Failed to get content")
                else:
                    print(f"  ❌ No results")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    # Test with direct HTTP
    print(f"\n🌐 Testing with Direct HTTP:")
    
    async with aiohttp.ClientSession() as session:
        for url in sitemap_urls:
            print(f"\n🔍 Testing: {url}")
            
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        print(f"  📄 Status: {response.status}")
                        print(f"  📄 Content length: {len(content)} chars")
                        print(f"  📄 Content preview:")
                        print(f"  {content[:500]}...")
                        if len(content) > 500:
                            print(f"  📄 Last 200 chars:")
                            print(f"  ...{content[-200:]}")
                    else:
                        print(f"  ❌ HTTP {response.status}")
                        
            except Exception as e:
                print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_chiyoda_content())
