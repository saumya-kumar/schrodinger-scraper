#!/usr/bin/env python3
"""
HTML URL Filter - Optimized for comprehensive .html URL discovery
Ensures we capture every possible .html file on the target website
"""

import re
from urllib.parse import urlparse, urljoin
from typing import Set, List, Optional

class HTMLURLFilter:
    """Advanced filtering system optimized for .html URL discovery"""
    
    def __init__(self, base_domain: str):
        self.base_domain = base_domain.lower()
        self.discovered_html_urls: Set[str] = set()
        
        # Expanded patterns for .html files
        self.html_extensions = ['.html', '.htm', '.shtml', '.xhtml']
        
        # Patterns that indicate potential .html content
        self.html_indicators = [
            'page', 'article', 'post', 'news', 'story', 'content',
            'document', 'report', 'guide', 'help', 'faq', 'about',
            'contact', 'info', 'detail', 'profile', 'index', 'main',
            'home', 'welcome', 'intro', 'overview', 'summary'
        ]
        
        # Skip these patterns as they're unlikely to be .html content
        self.skip_patterns = [
            # Media files
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.webp',
            '.mp4', '.avi', '.mov', '.wmv', '.mp3', '.wav', '.pdf',
            
            # Web assets
            '.css', '.js', '.scss', '.less', '.min.js', '.min.css',
            
            # Archives and executables
            '.zip', '.rar', '.tar', '.gz', '.exe', '.msi', '.dmg',
            
            # API and data endpoints
            '/api/', '/ajax/', '/json/', '/xml/', '/feed/',
            'api.', 'ajax.', 'json.', 'xml.',
            
            # Development and system files
            '.git', '.svn', '.htaccess', '.env', '.log',
            'node_modules', 'vendor', '.tmp', '.cache',
            
            # Common non-content patterns
            'javascript:', 'mailto:', 'tel:', 'ftp:', '#',
            '?download=', '?export=', '?print='
        ]
    
    def should_include_url(self, url: str, prioritize_html: bool = True) -> bool:
        """
        Determine if URL should be included, with strong preference for .html files
        """
        try:
            if not url or not isinstance(url, str):
                return False
            
            # Clean and normalize URL
            url = url.strip()
            parsed = urlparse(url)
            
            # Must be valid HTTP(S) URL
            if not parsed.scheme or parsed.scheme not in ['http', 'https']:
                return False
            
            # Must be same domain or subdomain
            if not self._is_same_domain(parsed.netloc):
                return False
            
            # Skip obvious non-content patterns
            if self._has_skip_patterns(url):
                return False
            
            # Strong preference for .html files
            if prioritize_html:
                return self._is_html_url(url) or self._might_contain_html(url)
            else:
                return True
                
        except Exception:
            return False
    
    def _is_same_domain(self, netloc: str) -> bool:
        """Check if netloc belongs to the same domain"""
        if not netloc:
            return False
        
        netloc = netloc.lower()
        
        # Exact match
        if netloc == self.base_domain:
            return True
        
        # Subdomain match
        if netloc.endswith('.' + self.base_domain):
            return True
        
        # Handle www variations
        if self.base_domain.startswith('www.'):
            main_domain = self.base_domain[4:]
            if netloc == main_domain or netloc.endswith('.' + main_domain):
                return True
        else:
            www_domain = 'www.' + self.base_domain
            if netloc == www_domain:
                return True
        
        return False
    
    def _has_skip_patterns(self, url: str) -> bool:
        """Check if URL matches skip patterns"""
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in self.skip_patterns)
    
    def _is_html_url(self, url: str) -> bool:
        """Check if URL is definitely an HTML file"""
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in self.html_extensions)
    
    def _might_contain_html(self, url: str) -> bool:
        """Check if URL might contain or lead to HTML content"""
        url_lower = url.lower()
        path = urlparse(url).path.lower()
        
        # Directory URLs that might contain HTML files
        if url.endswith('/'):
            return True
        
        # URLs without extensions (might be directories or HTML files)
        if '.' not in path.split('/')[-1]:
            return True
        
        # URLs with HTML-indicating keywords
        if any(indicator in url_lower for indicator in self.html_indicators):
            return True
        
        # Common HTML page patterns
        html_patterns = [
            'index', 'home', 'main', 'default', 'welcome',
            'about', 'contact', 'news', 'blog', 'article',
            'page', 'content', 'info', 'detail', 'profile'
        ]
        
        return any(pattern in path for pattern in html_patterns)
    
    def add_discovered_url(self, url: str) -> bool:
        """Add URL to discovered set if it's valid"""
        if self.should_include_url(url):
            self.discovered_html_urls.add(url)
            return True
        return False
    
    def filter_url_list(self, urls: List[str], prioritize_html: bool = True) -> List[str]:
        """Filter a list of URLs, returning only valid ones"""
        valid_urls = []
        for url in urls:
            if self.should_include_url(url, prioritize_html):
                valid_urls.append(url)
                self.discovered_html_urls.add(url)
        return valid_urls
    
    def get_html_url_stats(self) -> dict:
        """Get statistics about discovered HTML URLs"""
        total_urls = len(self.discovered_html_urls)
        
        # Count by type
        explicit_html = sum(1 for url in self.discovered_html_urls if self._is_html_url(url))
        potential_html = total_urls - explicit_html
        
        # Count by extension
        extension_counts = {}
        for url in self.discovered_html_urls:
            path = urlparse(url).path.lower()
            for ext in self.html_extensions:
                if path.endswith(ext):
                    extension_counts[ext] = extension_counts.get(ext, 0) + 1
                    break
            else:
                extension_counts['no_extension'] = extension_counts.get('no_extension', 0) + 1
        
        return {
            'total_urls': total_urls,
            'explicit_html_files': explicit_html,
            'potential_html_urls': potential_html,
            'extension_breakdown': extension_counts,
            'base_domain': self.base_domain
        }
    
    def generate_html_variations(self, base_url: str) -> List[str]:
        """Generate common .html variations of a URL"""
        variations = []
        parsed = urlparse(base_url)
        
        if not self._is_same_domain(parsed.netloc):
            return variations
        
        base_path = parsed.path.rstrip('/')
        
        # Add common HTML file variations
        html_files = [
            'index.html', 'main.html', 'home.html', 'default.html',
            'about.html', 'contact.html', 'info.html', 'help.html',
            'faq.html', 'news.html', 'blog.html', 'articles.html'
        ]
        
        for html_file in html_files:
            variation = f"{parsed.scheme}://{parsed.netloc}{base_path}/{html_file}"
            if self.should_include_url(variation):
                variations.append(variation)
        
        return variations

# Global filter instance
_url_filter = None

def get_html_filter(domain: str) -> HTMLURLFilter:
    """Get singleton HTML URL filter"""
    global _url_filter
    if _url_filter is None or _url_filter.base_domain != domain.lower():
        _url_filter = HTMLURLFilter(domain)
    return _url_filter

def filter_for_html_urls(urls: List[str], domain: str) -> List[str]:
    """Simple interface to filter URLs for HTML content"""
    filter_instance = get_html_filter(domain)
    return filter_instance.filter_url_list(urls, prioritize_html=True)

def should_include_html_url(url: str, domain: str) -> bool:
    """Simple interface to check if URL should be included"""
    filter_instance = get_html_filter(domain)
    return filter_instance.should_include_url(url, prioritize_html=True)

# Example usage
if __name__ == "__main__":
    # Test the filter
    domain = "www.city.chiyoda.lg.jp"
    filter_instance = HTMLURLFilter(domain)
    
    test_urls = [
        "https://www.city.chiyoda.lg.jp/koho/bunka/event.html",
        "https://www.city.chiyoda.lg.jp/admin/",
        "https://www.city.chiyoda.lg.jp/css/style.css", 
        "https://www.city.chiyoda.lg.jp/news/2024/",
        "https://www.city.chiyoda.lg.jp/images/logo.png",
        "https://www.city.chiyoda.lg.jp/about/index.html"
    ]
    
    print("🧪 Testing HTML URL Filter:")
    for url in test_urls:
        result = filter_instance.should_include_url(url)
        print(f"  {'✅' if result else '❌'} {url}")
    
    print(f"\n📊 Stats: {filter_instance.get_html_url_stats()}")
