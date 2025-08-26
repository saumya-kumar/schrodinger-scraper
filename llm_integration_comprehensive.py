#!/usr/bin/env python3
"""
COMPREHENSIVE URL DISCOVERY LLM Integration
Optimized for finding EVERY possible URL with focus on .html content
"""

import os
import json
import time
import logging
from typing import List, Dict, Set, Optional, Any
from urllib.parse import urlparse
from dataclasses import dataclass

try:
    import google.generativeai as genai
    print("✅ Google Generative AI imported successfully")
except ImportError:
    print("⚠️  google-generativeai not installed - LLM features disabled")
    genai = None

@dataclass
class LLMConfig:
    """Optimized LLM configuration for MAXIMUM URL discovery"""
    api_key: str = None
    model: str = "gemini-1.5-flash"  # Your Gemini API
    max_tokens: int = 2000  # Increased for comprehensive discovery
    temperature: float = 0.1  # Very focused for URL generation
    rate_limit_delay: float = 0.3  # Fast with your API key
    cache_responses: bool = True  # Cache to save costs
    enable_smart_batching: bool = True  # Batch requests
    max_daily_requests: int = 500  # High budget for comprehensive discovery

class ComprehensiveURLDiscoveryLLM:
    """LLM integration for finding EVERY single URL on a website"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = None
        self.request_count = 0
        self.daily_limit_reached = False
        self.response_cache = {}
        self.setup_client()
        
    def setup_client(self):
        """Setup Gemini client with your API key"""
        try:
            api_key = self.config.api_key or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
            if api_key and genai:
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(self.config.model)
                print(f"✅ LLM client initialized for COMPREHENSIVE URL discovery")
            else:
                print("⚠️  LLM client not available - using fallback patterns")
        except Exception as e:
            print(f"⚠️  LLM setup failed: {e}")
            
    def _check_budget_limits(self) -> bool:
        """Check if we're within budget limits"""
        if self.request_count >= self.config.max_daily_requests:
            if not self.daily_limit_reached:
                print(f"💰 Daily LLM limit reached ({self.config.max_daily_requests} requests)")
                self.daily_limit_reached = True
            return False
        return True
    
    def _get_cache_key(self, prompt: str, context: str = "") -> str:
        """Generate cache key for prompt"""
        import hashlib
        key_text = f"{prompt}_{context}"
        return hashlib.md5(key_text.encode()).hexdigest()[:16]
    
    async def generate_patterns(self, domain: str, site_type: str, discovered_urls: List[str], 
                              phase: str) -> List[str]:
        """Generate URL patterns for MAXIMUM website discovery"""
        
        if not self._check_budget_limits() or not self.client:
            return self._fallback_patterns(domain, site_type, phase)
        
        # Create cache key
        cache_key = self._get_cache_key(f"{domain}_{site_type}_{phase}", str(len(discovered_urls)))
        
        # Check cache first
        if self.config.cache_responses and cache_key in self.response_cache:
            print(f"🔄 Using cached LLM response for {phase}")
            return self.response_cache[cache_key]
        
        try:
            # Create comprehensive prompt for maximum discovery
            prompt = self._create_comprehensive_prompt(domain, site_type, discovered_urls[:5], phase)
            
            print(f"🤖 LLM: Generating {phase} patterns for COMPREHENSIVE discovery...")
            
            response = self.client.generate_content(prompt)
            self.request_count += 1
            
            # Extract URLs from response
            urls = self._parse_llm_response(response.text, domain)
            
            # Cache the response
            if self.config.cache_responses:
                self.response_cache[cache_key] = urls
            
            print(f"✅ LLM generated {len(urls)} potential URLs for maximum discovery")
            time.sleep(self.config.rate_limit_delay)  # Rate limiting
            
            return urls
            
        except Exception as e:
            print(f"⚠️  LLM generation failed: {e}")
            return self._fallback_patterns(domain, site_type, phase)
    
    def _create_comprehensive_prompt(self, domain: str, site_type: str, sample_urls: List[str], 
                                   phase: str) -> str:
        """Create prompts for MAXIMUM URL discovery - find EVERY possible URL"""
        
        # Determine site type if not provided
        if not site_type:
            site_type = self._detect_site_type(domain)
        
        # COMPREHENSIVE DISCOVERY prompts - optimized for finding ALL URLs
        prompts = {
            "robots_analysis": f"""COMPREHENSIVE URL DISCOVERY for {site_type} website: {domain}
Sample URLs: {sample_urls[:3]}

Generate 20 likely page URLs for COMPLETE site mapping (prioritize .html and page-like paths; EXCLUDE file assets like .pdf .docx .css .js .xml images):

ADMINISTRATIVE AREAS:
- /admin/, /administrator/, /manage/, /dashboard/, /control/
- /config/, /settings/, /tools/, /utilities/, /system/

CONTENT AREAS (pages only):
- /content/, /pages/, /articles/, /posts/, /news/, /blog/
- /resources/, /guides/, /help/, /support/, /knowledge/

SERVICE AREAS:
- /services/, /products/, /solutions/, /offerings/, /catalog/
- /support/, /help/, /faq/, /contact/, /feedback/

TECHNICAL/STRUCTURAL AREAS (only page endpoints, not raw data files):
- /api/, /rest/, /ajax/, /data/ (skip direct .json/.xml files)
- /backup/, /archive/, /temp/, /cache/, /logs/ (only if browsable)

Allowed extensions for explicit files: .html .php .asp .jsp (NO .pdf/.doc/.xml/.json)
Return complete URLs only for pages or page-like endpoints.""",

            "directory_discovery": f"""MAXIMUM DIRECTORY DISCOVERY for {site_type} site {domain} (exclude asset/data/document file types):
Generate 25 directory patterns for EVERY possible content area (no file extensions):

ESSENTIAL DIRECTORIES:
/admin/, /administrator/, /management/, /dashboard/, /control/
/content/, /pages/, /articles/, /posts/, /blog/, /news/
/services/, /products/, /solutions/, /catalog/, /portfolio/
/resources/, /documents/, /downloads/, /files/, /media/
/support/, /help/, /faq/, /contact/, /feedback/, /customer/
/api/, /rest/, /ajax/, /json/, /xml/, /data/, /database/
/backup/, /archive/, /temp/, /cache/, /logs/, /config/

{site_type.upper()}-SPECIFIC DIRECTORIES:
- Government: /departments/, /council/, /ordinances/, /budget/, /statistics/
- Corporate: /investors/, /careers/, /press/, /partners/, /team/
- Education: /students/, /faculty/, /courses/, /research/, /library/

Return all as /directory/ format.""",

            "pattern_generation": f"""PATTERN-BASED PAGE URL GENERATION for {domain} (exclude doc/pdf/css/js/xml/image/data files):
Sample URLs: {sample_urls}

Generate 25 page URL variations for MAXIMUM coverage:

NUMERIC PATTERNS (page or section paths only, no file assets):
- ID sequences: /item1.html → /item2.html, /item3.html, /item4.html
- Year sequences: /2024/ → /2023/, /2022/, /2021/, /2020/
- Page numbers: /page1/ → /page2/, /page3/, /page4/

CATEGORY PATTERNS:
- Content types: /news/ → /events/, /announcements/, /updates/
- Languages: /en/ → /ja/, /es/, /fr/, /de/, /zh/
- Formats: .html → .php, .asp, .jsp (no .pdf)

DATE PATTERNS:
- Monthly: /2024/01/ → /2024/02/, /2024/03/
- Archive: /archive/2024/ → /archive/2023/, /archive/2022/

SECTION PATTERNS:
- Departments: /dept1/ → /dept2/, /dept3/
- Services: /service1/ → /service2/, /service3/

Return COMPLETE page URLs (.html/.php/.asp/.jsp or extension-less directories).""",

            "search_queries": f"""SEARCH QUERIES for COMPREHENSIVE {site_type} page discovery on {domain} (avoid filetype:pdf/doc/xml/css/js):

Generate 15 search terms to find HIDDEN content:

PAGE FORMAT SEARCHES:
- "filetype:html site:{domain}"
- "filetype:php site:{domain}"

ADMIN/HIDDEN SEARCHES (structure only):
- "inurl:admin site:{domain}"
- "inurl:login site:{domain}"
- "inurl:config site:{domain}"
- "inurl:backup site:{domain}"
- "inurl:test site:{domain}"

CONTENT-SPECIFIC SEARCHES (pages):
- "{site_type} services site:{domain}"
- "{site_type} resources site:{domain}"
- "{site_type} information site:{domain}"
- "{site_type} contact site:{domain}"

Return search terms for maximum PAGE URL discovery only."""
        }
        
        return prompts.get(phase, prompts["robots_analysis"])
    
    def _detect_site_type(self, domain: str) -> str:
        """Detect website type from domain for targeted discovery"""
        domain_lower = domain.lower()
        
        if any(term in domain_lower for term in ['gov', 'city', 'municipal', 'admin', 'lg.jp']):
            return "government"
        elif any(term in domain_lower for term in ['edu', 'university', 'school', 'ac.jp']):
            return "educational"
        elif any(term in domain_lower for term in ['news', 'media', 'blog', 'press']):
            return "news/media"
        elif any(term in domain_lower for term in ['shop', 'store', 'ecommerce', 'buy']):
            return "ecommerce"
        elif any(term in domain_lower for term in ['org', 'nonprofit', 'ngo']):
            return "organization"
        else:
            return "corporate"
    
    def _parse_llm_response(self, response_text: str, domain: str) -> List[str]:
        """Parse LLM response and extract ALL valid URLs"""
        lines = response_text.strip().split('\n')
        urls = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines, comments, and explanatory text
            if not line or line.startswith('#') or line.startswith('//') or line.startswith('-'):
                continue
            
            # Handle different URL formats
            if line.startswith('http'):
                # Full URL - validate domain
                if domain in line:
                    urls.append(line)
            elif line.startswith('/'):
                # Path only - construct full URL
                parsed_domain = urlparse(f"https://{domain}")
                full_url = f"{parsed_domain.scheme}://{parsed_domain.netloc}{line}"
                urls.append(full_url)
            elif '/' in line and not line.startswith('http'):
                # Relative path
                parsed_domain = urlparse(f"https://{domain}")
                full_url = f"{parsed_domain.scheme}://{parsed_domain.netloc}/{line.lstrip('/')}"
                urls.append(full_url)
        
        # Remove duplicates and validate
        valid_urls = []
        for url in set(urls):
            if self._validate_url(url, domain):
                valid_urls.append(url)
        
        return valid_urls
    
    def _validate_url(self, url: str, domain: str) -> bool:
        """Validate generated URL for comprehensive discovery"""
        try:
            parsed = urlparse(url)
            return (parsed.scheme in ['http', 'https'] and 
                   domain in parsed.netloc and
                   len(url) < 1000 and  # Reasonable length
                   not any(skip in url.lower() for skip in ['javascript:', 'mailto:', 'tel:']))
        except:
            return False
    
    def _fallback_patterns(self, domain: str, site_type: str, phase: str) -> List[str]:
        """Comprehensive fallback patterns when LLM unavailable"""
        base_url = f"https://{domain}"
        
        # COMPREHENSIVE fallback patterns for maximum discovery
        fallback_patterns = {
            "government": [
                f"{base_url}/admin/", f"{base_url}/administration/", f"{base_url}/management/",
                f"{base_url}/council/", f"{base_url}/departments/", f"{base_url}/services/",
                f"{base_url}/documents/", f"{base_url}/statistics/", f"{base_url}/budget/",
                f"{base_url}/policies/", f"{base_url}/ordinances/", f"{base_url}/meetings/",
                f"{base_url}/news/", f"{base_url}/press/", f"{base_url}/events/",
                f"{base_url}/resources/", f"{base_url}/downloads/", f"{base_url}/forms/",
                f"{base_url}/contact/", f"{base_url}/feedback/", f"{base_url}/help/"
            ],
            "corporate": [
                f"{base_url}/admin/", f"{base_url}/management/", f"{base_url}/dashboard/",
                f"{base_url}/api/", f"{base_url}/docs/", f"{base_url}/documentation/",
                f"{base_url}/support/", f"{base_url}/help/", f"{base_url}/resources/",
                f"{base_url}/products/", f"{base_url}/services/", f"{base_url}/solutions/",
                f"{base_url}/contact/", f"{base_url}/about/", f"{base_url}/careers/",
                f"{base_url}/news/", f"{base_url}/press/", f"{base_url}/blog/",
                f"{base_url}/downloads/", f"{base_url}/files/", f"{base_url}/media/"
            ],
            "educational": [
                f"{base_url}/admin/", f"{base_url}/administration/", f"{base_url}/management/",
                f"{base_url}/students/", f"{base_url}/faculty/", f"{base_url}/staff/",
                f"{base_url}/courses/", f"{base_url}/programs/", f"{base_url}/departments/",
                f"{base_url}/research/", f"{base_url}/library/", f"{base_url}/resources/",
                f"{base_url}/admissions/", f"{base_url}/enrollment/", f"{base_url}/registration/",
                f"{base_url}/news/", f"{base_url}/events/", f"{base_url}/calendar/",
                f"{base_url}/documents/", f"{base_url}/forms/", f"{base_url}/downloads/"
            ]
        }
        
        patterns = fallback_patterns.get(site_type, fallback_patterns["corporate"])
        print(f"🔄 Using comprehensive fallback patterns for {site_type} site")
        return patterns[:20]  # Return 20 for maximum coverage

# Global LLM instance for comprehensive discovery
_comprehensive_llm_instance = None

def get_comprehensive_llm(api_key: str = None) -> ComprehensiveURLDiscoveryLLM:
    """Get singleton LLM instance optimized for comprehensive URL discovery"""
    global _comprehensive_llm_instance
    if _comprehensive_llm_instance is None:
        config = LLMConfig(
            api_key=api_key,
            max_daily_requests=500,  # High budget for comprehensive discovery
            rate_limit_delay=0.3,    # Fast with your API key
            cache_responses=True,    # Save costs with caching
            max_tokens=2000         # Detailed responses
        )
        _comprehensive_llm_instance = ComprehensiveURLDiscoveryLLM(config)
    return _comprehensive_llm_instance

async def generate_phase_patterns(domain: str, discovered_urls: List[str], 
                                phase: str, api_key: str = None) -> List[str]:
    """Simple interface for phases to get comprehensive LLM patterns"""
    llm = get_comprehensive_llm(api_key)
    site_type = llm._detect_site_type(domain)
    return await llm.generate_patterns(domain, site_type, discovered_urls, phase)

# Example usage for testing comprehensive discovery
async def test_comprehensive_discovery():
    """Test comprehensive URL discovery"""
    domain = "city.chiyoda.lg.jp"
    sample_urls = [
        "https://www.city.chiyoda.lg.jp/koho/bunka/",
        "https://www.city.chiyoda.lg.jp/koho/press/",
        "https://www.city.chiyoda.lg.jp/service/"
    ]
    
    llm = get_comprehensive_llm()
    
    # Test all phases for maximum discovery
    phases = ["robots_analysis", "directory_discovery", "pattern_generation", "search_queries"]
    
    for phase in phases:
        print(f"\n🧪 Testing {phase} for COMPREHENSIVE discovery...")
        results = await llm.generate_patterns(domain, "government", sample_urls, phase)
        print(f"Generated {len(results)} URLs: {results[:5]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_comprehensive_discovery())
