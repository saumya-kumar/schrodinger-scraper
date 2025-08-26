#!/usr/bin/env python3
"""
QUICK START: Comprehensive URL Discovery
Run this to discover EVERY URL on any website
"""

import asyncio
import os

async def quick_comprehensive_discovery():
    """Quick start for comprehensive URL discovery"""
    
    # Import master controller
    from master_url_discovery import run_comprehensive_url_discovery
    
    print("🚀 COMPREHENSIVE URL DISCOVERY - QUICK START")
    print("=" * 60)
    print("Goal: Find EVERY single URL with .html priority")
    print("Method: 10-phase discovery with LLM assistance")
    print("=" * 60)
    
    # Target website
    target_url = "https://www.city.chiyoda.lg.jp"  # Change this to any website
    
    print(f"🎯 Target: {target_url}")
    print("🤖 Using Gemini API for enhanced discovery")
    print("\n🔄 Starting comprehensive discovery...")
    
    try:
        # Run comprehensive discovery
        results = await run_comprehensive_url_discovery(
            base_url=target_url,
            gemini_api_key=os.getenv('GOOGLE_API_KEY')  # Your API key from .env
        )
        
        # Show summary
        stats = results['discovery_statistics']
        print(f"\n🎉 DISCOVERY COMPLETE!")
        print(f"📊 Total URLs found: {stats['total_urls_discovered']}")
        print(f"🎯 HTML priority: {stats.get('html_priority_urls', 'N/A')}")
        print(f"📄 Content files: {stats.get('content_file_urls', 'N/A')}")
        print(f"📁 Other pages: {stats.get('other_page_urls', 'N/A')}")
        print(f"✅ Successful phases: {stats['successful_phases']}/10")
        print(f"⏱️  Total time: {stats['total_discovery_time']:.1f}s")
        
        if 'url_optimization' in results:
            print(f"\n🔍 TOP HTML PRIORITY URLs:")
            for url in results['url_optimization']['html_priority_urls'][:10]:
                print(f"  🎯 {url}")
        
        return results
        
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return None

if __name__ == "__main__":
    # Run comprehensive discovery
    asyncio.run(quick_comprehensive_discovery())
