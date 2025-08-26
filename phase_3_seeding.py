#!/usr/bin/env python3
"""
Phase 3: URL Seeding Test
"""

def test_phase_3(base_url):
    print("Phase 3: URL Seeding")
    print("=" * 40)
    
    # Common government website patterns
    common_paths = [
        '/admin/', '/administration/', '/management/',
        '/council/', '/departments/', '/services/',
        '/documents/', '/statistics/', '/budget/',
        '/policies/', '/ordinances/', '/meetings/',
        '/news/', '/press/', '/events/',
        '/resources/', '/downloads/', '/forms/',
        '/contact/', '/feedback/'
    ]
    
    discovered_urls = []
    
    try:
        import requests
        
        for path in common_paths:
            url = f"{base_url.rstrip('/')}{path}"
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    discovered_urls.append(url)
                    print(f"✅ Found: {url}")
            except:
                pass  # Skip failed requests
        
        print(f"📊 Phase 3 discovered {len(discovered_urls)} URLs via seeding")
        return discovered_urls
        
    except Exception as e:
        print(f"❌ Phase 3 ERROR: {e}")
        return []

if __name__ == "__main__":
    test_url = "https://www.city.chiyoda.lg.jp/"
    urls = test_phase_3(test_url)
