#!/usr/bin/env python3
"""
COMPREHENSIVE URL FILTERING AND PRIORITIZATION
Optimized for finding EVERY URL with priority for .html content
"""

import re
from urllib.parse import urlparse
from typing import Set, List, Dict, Any

class ComprehensiveURLFilter:
    """Advanced URL filtering with .html prioritization but comprehensive discovery"""
    
    def __init__(self, domain: str):
        self.domain = domain
        self.priority_extensions = ['.html', '.htm', '.shtml', '.php', '.asp', '.jsp']
        self.content_extensions = []  # No longer prioritizing document files
        self.skip_extensions = [
            # Styles and scripts
            '.css', '.js',
            # Fonts
            '.woff', '.ttf', '.eot', '.otf',
            # Images
            '.ico', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp',
            # Documents to skip as per request
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.xml', '.txt',
            # Archives
            '.zip', '.rar', '.7z', '.tar', '.gz',
            # Data files
            '.json', '.csv',
            # Media
            '.mp3', '.mp4', '.avi', '.mov'
        ]
        
    def should_include_url(self, url: str, prioritize_html: bool = True) -> tuple[bool, int]:
        """
        Determine if URL should be included and its priority level
        Returns: (should_include, priority_score)
        Priority: 1=highest (HTML), 2=content, 3=other pages, 0=skip
        """
        try:
            parsed = urlparse(url)
            
            # Must be same domain
            if not self._is_same_domain(parsed.netloc):
                return False, 0
            
            path = parsed.path.lower()
            
            # Skip obvious non-content files
            if any(path.endswith(ext) for ext in self.skip_extensions):
                return False, 0
            
            # Skip non-HTTP protocols
            if parsed.scheme not in ['http', 'https']:
                return False, 0
            
            # Skip fragments and malformed URLs
            if len(url) > 1000 or 'javascript:' in url or 'mailto:' in url:
                return False, 0
            
            # PRIORITY 1: HTML files (highest priority)
            if any(path.endswith(ext) for ext in self.priority_extensions):
                return True, 1
            
            # PRIORITY 2: Other content pages (no longer used for documents)
            if any(path.endswith(ext) for ext in self.content_extensions):
                return True, 2
            
            # PRIORITY 3: Directory/page URLs without extension (likely HTML)
            if (path.endswith('/') or 
                '.' not in path.split('/')[-1] or
                self._looks_like_content_page(path)):
                return True, 3
            
            # PRIORITY 3: Other potentially useful URLs
            if self._is_likely_content_url(path):
                return True, 3
                
            return False, 0
            
        except Exception:
            return False, 0
    
    def _is_same_domain(self, url_domain: str) -> bool:
        """Check if URL belongs to target domain (allow subdomains)"""
        if not url_domain:
            return False
            
        # Exact match
        if url_domain == self.domain:
            return True
        
        # Subdomain match (e.g., www.example.com matches example.com)
        if self.domain in url_domain:
            # Extract main domain (last 2 parts)
            domain_parts = self.domain.split('.')
            url_parts = url_domain.split('.')
            
            if len(domain_parts) >= 2 and len(url_parts) >= 2:
                main_domain = '.'.join(domain_parts[-2:])
                url_main = '.'.join(url_parts[-2:])
                return main_domain == url_main
        
        return False
    
    def _looks_like_content_page(self, path: str) -> bool:
        """Check if path looks like a content page"""
        content_indicators = [
            '/news/', '/article/', '/post/', '/blog/', '/content/',
            '/page/', '/info/', '/about/', '/service/', '/product/',
            '/resource/', '/document/', '/help/', '/support/',
            '/contact/', '/press/', '/event/', '/announcement/'
        ]
        return any(indicator in path for indicator in content_indicators)
    
    def _is_likely_content_url(self, path: str) -> bool:
        """Check if URL is likely to contain content"""
        # Skip obvious system/technical paths
        system_patterns = [
            '/assets/', '/static/', '/cdn/', '/cache/', '/tmp/',
            '/system/', '/admin/assets/', '/wp-content/themes/',
            '/wp-content/plugins/', '/node_modules/', '/vendor/'
        ]
        
        if any(pattern in path for pattern in system_patterns):
            return False
        
        # Include admin/management areas (might contain useful pages)
        admin_patterns = [
            '/admin/', '/manage/', '/dashboard/', '/control/',
            '/config/', '/settings/', '/tools/'
        ]
        
        if any(pattern in path for pattern in admin_patterns):
            return True
        
        # Include API endpoints (might reveal structure)
        api_patterns = [
            '/api/', '/rest/', '/ajax/', '/json/', '/xml/'
        ]
        
        if any(pattern in path for pattern in api_patterns):
            return True
        
        return True  # Include by default for comprehensive discovery
    
    def filter_and_prioritize_urls(self, urls: Set[str]) -> Dict[int, List[str]]:
        """Filter URLs and organize by priority"""
        prioritized = {1: [], 2: [], 3: []}  # 1=HTML, 2=Unused, 3=Other
        
        for url in urls:
            should_include, priority = self.should_include_url(url)
            if should_include and priority > 0:
                prioritized[priority].append(url)
        
        # Sort each priority group
        for priority in prioritized:
            prioritized[priority] = sorted(list(set(prioritized[priority])))
        
        return prioritized
    
    def get_comprehensive_url_list(self, urls: Set[str]) -> List[str]:
        """Get comprehensive URL list with HTML prioritized but all included"""
        prioritized = self.filter_and_prioritize_urls(urls)
        
        # Combine all priorities: HTML first, then content, then others
        comprehensive_list = []
        comprehensive_list.extend(prioritized[1])  # HTML files first
        comprehensive_list.extend(prioritized[2])  # Content files second  
        comprehensive_list.extend(prioritized[3])  # Other pages third
        
        return comprehensive_list
    
    def get_statistics(self, urls: Set[str]) -> Dict[str, Any]:
        """Get filtering statistics"""
        prioritized = self.filter_and_prioritize_urls(urls)
        
        total_input = len(urls)
        total_included = sum(len(prioritized[p]) for p in prioritized)
        total_excluded = total_input - total_included
        
        return {
            "total_input_urls": total_input,
            "total_included_urls": total_included,
            "total_excluded_urls": total_excluded,
            "html_priority_urls": len(prioritized[1]),
            "content_priority_urls": len(prioritized[2]), 
            "other_priority_urls": len(prioritized[3]),
            "html_percentage": (len(prioritized[1]) / total_included * 100) if total_included > 0 else 0,
            "inclusion_rate": (total_included / total_input * 100) if total_input > 0 else 0
        }

def optimize_url_discovery_for_phases(discovered_urls: Set[str], domain: str) -> Dict[str, Any]:
    """Optimize discovered URLs for maximum coverage with HTML priority"""
    
    filter_system = ComprehensiveURLFilter(domain)
    
    # Get comprehensive filtered list
    comprehensive_urls = filter_system.get_comprehensive_url_list(discovered_urls)
    
    # Get statistics
    stats = filter_system.get_statistics(discovered_urls)
    
    # Get prioritized breakdown
    prioritized = filter_system.filter_and_prioritize_urls(discovered_urls)
    
    print(f"🔍 URL DISCOVERY OPTIMIZATION RESULTS:")
    print(f"  📊 Total Input URLs: {stats['total_input_urls']}")
    print(f"  ✅ Total Included: {stats['total_included_urls']} ({stats['inclusion_rate']:.1f}%)")
    print(f"  🎯 HTML Priority: {stats['html_priority_urls']} ({stats['html_percentage']:.1f}%)")
    print(f"  📄 Content Files: {stats['content_priority_urls']}")
    print(f"  📁 Other Pages: {stats['other_priority_urls']}")
    print(f"  ❌ Excluded: {stats['total_excluded_urls']}")
    
    return {
        "comprehensive_urls": comprehensive_urls,
        "prioritized_urls": prioritized,
        "statistics": stats,
        "html_priority_urls": prioritized[1],
        "all_content_urls": prioritized[1] + prioritized[2] + prioritized[3]
    }

# Example usage
if __name__ == "__main__":
    # Test with sample URLs
    test_urls = {
        "https://www.city.chiyoda.lg.jp/koho/bunka/event.html",
        "https://www.city.chiyoda.lg.jp/admin/dashboard.php",
        "https://www.city.chiyoda.lg.jp/documents/report.pdf",
        "https://www.city.chiyoda.lg.jp/api/data.json",
        "https://www.city.chiyoda.lg.jp/assets/style.css",  # Should be excluded
        "https://www.city.chiyoda.lg.jp/news/",
        "https://www.city.chiyoda.lg.jp/services/citizen-services/",
        "https://www.city.chiyoda.lg.jp/contact/form.html"
    }
    
    results = optimize_url_discovery_for_phases(test_urls, "www.city.chiyoda.lg.jp")
    
    print(f"\n🎯 HTML PRIORITY URLS:")
    for url in results["html_priority_urls"][:5]:
        print(f"  ✅ {url}")
    
    print(f"\n📋 COMPREHENSIVE URL LIST (first 10):")
    for url in results["comprehensive_urls"][:10]:
        print(f"  📄 {url}")
