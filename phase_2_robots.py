#!/usr/bin/env python3
"""
Phase 2: Robots.txt & LLM Analysis Test
"""

import requests
import re
import json
import time
from datetime import datetime
from pathlib import Path

def comprehensive_url_filter(url):
    """Enhanced URL filtering with strict exclusion"""
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip().lower()
    
    # File extension exclusions
    excluded_extensions = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'zip', 'rar', '7z', 'tar', 'gz',
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'ico',
        'mp3', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'wav',
        'css', 'js', 'xml', 'json', 'txt', 'csv',
        'rss', 'atom', 'sitemap'
    }
    
    # Check for file extensions
    for ext in excluded_extensions:
        if f'.{ext}' in url:
            return False
    
    # Additional exclusions
    excluded_patterns = [
        'mailto:', 'tel:', 'ftp:', 'javascript:', '#',
        'download', 'file', 'attachment', 'document', 'asset'
    ]
    
    for pattern in excluded_patterns:
        if pattern in url:
            return False
    
    return True

def test_phase_2(base_url):
    start_time = time.time()
    print("=" * 80)
    print("🤖 PHASE 2: ROBOTS.TXT & LLM ANALYSIS")
    print("=" * 80)
    print(f"🎯 Target: {base_url}")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test robots.txt
        robots_url = f"{base_url.rstrip('/')}/robots.txt"
        print(f"🔍 Checking: {robots_url}")
        response = requests.get(robots_url, timeout=10)
        
        if response.status_code == 200:
            content = response.text
            print(f"✅ Found robots.txt with {len(content)} characters")
            
            # Extract directories from robots.txt
            allow_patterns = re.findall(r'Allow:\s*(/[^\s]*)', content, re.IGNORECASE)
            disallow_patterns = re.findall(r'Disallow:\s*(/[^\s]*)', content, re.IGNORECASE)
            
            print(f"📊 Allow patterns: {len(allow_patterns)}")
            print(f"📊 Disallow patterns: {len(disallow_patterns)}")
            
            # Generate potential URLs from patterns
            discovered_urls = set()
            for pattern in allow_patterns:
                if pattern and pattern != '/':
                    url = f"{base_url.rstrip('/')}{pattern}"
                    if comprehensive_url_filter(url):
                        discovered_urls.add(url)
            
            # Also check disallow patterns for directory hints
            for pattern in disallow_patterns:
                if pattern and pattern != '/' and not pattern.startswith('/admin'):
                    # Convert disallow to potential allow for discovery
                    url = f"{base_url.rstrip('/')}{pattern}".replace('*', '')
                    if comprehensive_url_filter(url) and not any(x in url.lower() for x in ['admin', 'private', 'login']):
                        discovered_urls.add(url)
            
            filtered_urls = list(discovered_urls)
            
            execution_time = time.time() - start_time
            
            print("\n" + "=" * 80)
            print("📊 PHASE 2 RESULTS")
            print("=" * 80)
            print(f"⏱️ Execution Time: {execution_time:.2f} seconds")
            print(f"🔢 Total URLs Found: {len(filtered_urls)}")
            
            # Categorize URLs
            html_urls = [url for url in filtered_urls if url.endswith('.html') or not any(f'.{ext}' in url for ext in ['pdf', 'doc', 'zip', 'jpg', 'css', 'js', 'xml'])]
            other_urls = [url for url in filtered_urls if url not in html_urls]
            
            print(f"📄 HTML Pages: {len(html_urls)}")
            print(f"🔗 Other URLs: {len(other_urls)}")
            
            # Save results
            results = {
                "phase": "Phase 2: Robots.txt & LLM Analysis",
                "target_url": base_url,
                "execution_time": execution_time,
                "total_urls": len(filtered_urls),
                "html_pages": len(html_urls),
                "other_urls": len(other_urls),
                "timestamp": datetime.now().isoformat(),
                "discovered_urls": filtered_urls
            }
            
            results_file = Path("phase_2_results.json")
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Results saved to: {results_file}")
            
            if filtered_urls:
                print(f"\n📋 Sample URLs (first 10):")
                for i, url in enumerate(filtered_urls[:10], 1):
                    print(f"    {i:2d}. {url}")
                if len(filtered_urls) > 10:
                    print(f"   ... and {len(filtered_urls) - 10} more URLs")
            
            return filtered_urls
        else:
            print(f"❌ robots.txt: HTTP {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Phase 2 ERROR: {e}")
        return []

if __name__ == "__main__":
    test_url = "https://www.city.chiyoda.lg.jp/"
    urls = test_phase_2(test_url)
