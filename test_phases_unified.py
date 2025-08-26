#!/usr/bin/env python3
"""
Unified Phase Testing - Each phase runs individually with unique URL tracking
All results stored in a single file with proper deduplication
"""

import json
import time
from datetime import datetime
from pathlib import Path
import requests
import re
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

class UnifiedURLTracker:
    """Central URL tracking with sets for deduplication"""
    
    def __init__(self, base_url, results_file="unified_results.json"):
        self.base_url = base_url
        self.results_file = Path(results_file)
        self.all_urls = set()  # Master set of all unique URLs
        self.phase_results = {}
        
        # Load existing results if file exists
        if self.results_file.exists():
            try:
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.phase_results = data.get('phases', {})
                    # Rebuild all_urls set from existing data
                    for phase_data in self.phase_results.values():
                        self.all_urls.update(phase_data.get('urls', []))
            except Exception as e:
                print(f"⚠️ Could not load existing results: {e}")
    
    def comprehensive_url_filter(self, url):
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
            'rss', 'atom'
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
    
    def add_phase_results(self, phase_name, urls, execution_time, method_description=""):
        """Add results from a phase, tracking unique URLs"""
        # Filter URLs
        filtered_urls = [url for url in urls if self.comprehensive_url_filter(url)]
        
        # Convert to set for this phase
        phase_url_set = set(filtered_urls)
        
        # Track new URLs (not seen before)
        new_urls = phase_url_set - self.all_urls
        
        # Update master set
        self.all_urls.update(phase_url_set)
        
        # Categorize URLs
        html_urls = [url for url in phase_url_set if url.endswith('.html') or not any(f'.{ext}' in url for ext in ['pdf', 'doc', 'zip', 'jpg', 'css', 'js', 'xml'])]
        other_urls = [url for url in phase_url_set if url not in html_urls]
        
        # Store phase results
        self.phase_results[phase_name] = {
            "method": method_description,
            "execution_time": execution_time,
            "urls_found": len(phase_url_set),
            "new_urls_found": len(new_urls),
            "html_pages": len(html_urls),
            "other_urls": len(other_urls),
            "timestamp": datetime.now().isoformat(),
            "urls": list(phase_url_set)
        }
        
        # Save to file
        self.save_results()
        
        return {
            "total_found": len(phase_url_set),
            "new_unique": len(new_urls),
            "html_pages": len(html_urls),
            "execution_time": execution_time
        }
    
    def save_results(self):
        """Save all results to unified file"""
        results = {
            "schema_version": "2.0",
            "base_url": self.base_url,
            "total_unique_urls": len(self.all_urls),
            "last_updated": datetime.now().isoformat(),
            "phases": self.phase_results,
            "summary": {
                "total_phases_run": len(self.phase_results),
                "total_unique_urls": len(self.all_urls),
                "all_unique_urls": list(self.all_urls)
            }
        }
        
        with open(self.results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    
    def get_summary(self):
        """Get summary of all phases"""
        return {
            "total_unique_urls": len(self.all_urls),
            "phases_run": len(self.phase_results),
            "phase_breakdown": {name: data["urls_found"] for name, data in self.phase_results.items()}
        }

def test_phase_1_sitemap(tracker):
    """Phase 1: Sitemap Discovery"""
    print("=" * 80)
    print("🗺️ PHASE 1: SITEMAP DISCOVERY")
    print("=" * 80)
    
    start_time = time.time()
    discovered_urls = set()
    
    base_url = tracker.base_url
    print(f"🎯 Target: {base_url}")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Try different sitemap locations
    sitemap_locations = [
        "sitemap.html",
        "sitemap.xml", 
        "sitemap_index.xml",
        "sitemaps.xml"
    ]
    
    for location in sitemap_locations:
        try:
            sitemap_url = urljoin(base_url, location)
            print(f"🔍 Trying: {sitemap_url}")
            
            response = requests.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                if location.endswith('.html'):
                    # Parse HTML sitemap
                    content = response.text
                    print(f"✅ Found {location} with {len(content)} characters")
                    
                    # Extract URLs from HTML
                    import re
                    url_pattern = r'href=["\']([^"\']+)["\']'
                    matches = re.findall(url_pattern, content)
                    
                    for match in matches:
                        full_url = urljoin(base_url, match)
                        if full_url.startswith(('http://', 'https://')):
                            discovered_urls.add(full_url)
                    
                    print(f"📊 Extracted {len(discovered_urls)} URLs from HTML sitemap")
                
                elif location.endswith('.xml'):
                    # Parse XML sitemap
                    print(f"✅ Found {location} with {len(response.content)} bytes")
                    
                    try:
                        root = ET.fromstring(response.content)
                        # Handle different XML namespaces
                        for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                            loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                            if loc_elem is not None:
                                discovered_urls.add(loc_elem.text)
                        
                        print(f"📊 Extracted {len(discovered_urls)} URLs from XML sitemap")
                    except ET.ParseError:
                        print(f"⚠️ Could not parse XML sitemap")
            else:
                print(f"❌ {location}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error checking {location}: {e}")
    
    execution_time = time.time() - start_time
    
    # Add to tracker
    result = tracker.add_phase_results(
        "phase_1_sitemap", 
        list(discovered_urls), 
        execution_time,
        "Sitemap Discovery (HTML/XML)"
    )
    
    print(f"\n📊 PHASE 1 RESULTS")
    print(f"⏱️ Execution Time: {execution_time:.2f} seconds")
    print(f"🔢 URLs Found: {result['total_found']}")
    print(f"🆕 New Unique URLs: {result['new_unique']}")
    print(f"📄 HTML Pages: {result['html_pages']}")
    
    return result

def test_phase_2_robots(tracker):
    """Phase 2: Robots.txt Analysis"""
    print("\n" + "=" * 80)
    print("🤖 PHASE 2: ROBOTS.TXT ANALYSIS")
    print("=" * 80)
    
    start_time = time.time()
    discovered_urls = set()
    
    base_url = tracker.base_url
    print(f"🎯 Target: {base_url}")
    
    try:
        robots_url = f"{base_url.rstrip('/')}/robots.txt"
        print(f"🔍 Checking: {robots_url}")
        
        response = requests.get(robots_url, timeout=10)
        if response.status_code == 200:
            content = response.text
            print(f"✅ Found robots.txt with {len(content)} characters")
            
            # Extract patterns from robots.txt
            allow_patterns = re.findall(r'Allow:\s*(/[^\s]*)', content, re.IGNORECASE)
            disallow_patterns = re.findall(r'Disallow:\s*(/[^\s]*)', content, re.IGNORECASE)
            
            print(f"📊 Allow patterns: {len(allow_patterns)}")
            print(f"📊 Disallow patterns: {len(disallow_patterns)}")
            
            # Generate URLs from patterns
            for pattern in allow_patterns:
                if pattern and pattern != '/':
                    url = f"{base_url.rstrip('/')}{pattern}"
                    discovered_urls.add(url)
            
            # Convert some disallow patterns to discovery hints
            for pattern in disallow_patterns:
                if pattern and pattern != '/' and not any(x in pattern.lower() for x in ['admin', 'private', 'login', 'cgi-bin']):
                    url = f"{base_url.rstrip('/')}{pattern}".replace('*', '')
                    discovered_urls.add(url)
                    
        else:
            print(f"❌ robots.txt: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    execution_time = time.time() - start_time
    
    # Add to tracker
    result = tracker.add_phase_results(
        "phase_2_robots", 
        list(discovered_urls), 
        execution_time,
        "Robots.txt Pattern Analysis"
    )
    
    print(f"\n📊 PHASE 2 RESULTS")
    print(f"⏱️ Execution Time: {execution_time:.2f} seconds")
    print(f"🔢 URLs Found: {result['total_found']}")
    print(f"🆕 New Unique URLs: {result['new_unique']}")
    print(f"📄 HTML Pages: {result['html_pages']}")
    
    return result

def main():
    """Run all phases with unified tracking"""
    base_url = "https://www.city.chiyoda.lg.jp/"
    
    # Initialize tracker
    tracker = UnifiedURLTracker(base_url, "unified_phase_results.json")
    
    print("🚀 UNIFIED PHASE TESTING")
    print("=" * 80)
    print(f"📋 Target Website: {base_url}")
    print(f"📅 Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💾 Results File: unified_phase_results.json")
    
    # Run Phase 1
    result1 = test_phase_1_sitemap(tracker)
    
    # Run Phase 2  
    result2 = test_phase_2_robots(tracker)
    
    # Final Summary
    summary = tracker.get_summary()
    
    print("\n" + "=" * 80)
    print("📊 FINAL SUMMARY")
    print("=" * 80)
    print(f"🔢 Total Unique URLs Discovered: {summary['total_unique_urls']}")
    print(f"📋 Phases Completed: {summary['phases_run']}")
    print("\n📈 Per-Phase Breakdown:")
    
    for phase, count in summary['phase_breakdown'].items():
        print(f"    {phase}: {count} URLs")
    
    print(f"\n💾 All results saved to: unified_phase_results.json")
    print("✅ Testing Complete!")

if __name__ == "__main__":
    main()
