#!/usr/bin/env python3
"""
Phase 4: Recursive Link Crawling Test
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def test_phase_4(base_url, seed_urls=None):
    print("Phase 4: Recursive Link Crawling")
    print("=" * 40)
    
    if not seed_urls:
        seed_urls = [base_url]
    
    discovered_urls = set()
    processed_urls = set()
    
    try:
        for seed_url in seed_urls[:5]:  # Limit to first 5 for testing
            if seed_url in processed_urls:
                continue
                
            print(f"🔍 Crawling: {seed_url}")
            processed_urls.add(seed_url)
            
            try:
                response = requests.get(seed_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract all links
                    links = soup.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        full_url = urljoin(seed_url, href)
                        
                        # Only keep same-domain links
                        if urlparse(full_url).netloc == urlparse(base_url).netloc:
                            if full_url.endswith('.html') or full_url.endswith('/'):
                                discovered_urls.add(full_url)
                
                print(f"✅ Found {len(discovered_urls)} links from {seed_url}")
                
            except Exception as e:
                print(f"❌ Failed to crawl {seed_url}: {e}")
        
        print(f"📊 Phase 4 discovered {len(discovered_urls)} URLs via recursive crawling")
        return list(discovered_urls)
        
    except Exception as e:
        print(f"❌ Phase 4 ERROR: {e}")
        return []

if __name__ == "__main__":
    test_url = "https://www.city.chiyoda.lg.jp/"
    urls = test_phase_4(test_url)
