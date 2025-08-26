#!/usr/bin/env python3
"""
Cost-Effective Generic LLM Integration for URL Discovery
Provides smart, budget-conscious AI assistance for all phases
"""

import os
import json
import time
import logging
import re
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
    """Optimized LLM configuration for comprehensive URL discovery"""
    api_key: str = None
    model: str = "gemini-1.5-flash"  # Use your Gemini API
    max_tokens: int = 2000  # Increased for comprehensive URL discovery
    temperature: float = 0.1  # Very focused for URL generation
    rate_limit_delay: float = 0.3  # Faster with your API key
    cache_responses: bool = True  # Cache to avoid repeat costs
    enable_smart_batching: bool = True  # Batch requests
    max_daily_requests: int = 300  # Higher budget for thorough discovery
    api_key: str = None
    model: str = "gemini-1.5-flash"  # Use user's specified model
    max_tokens: int = 1500  # Increased for more comprehensive URL generation
    temperature: float = 0.2  # More focused on finding real URLs
    rate_limit_delay: float = 0.8  # Faster rate for comprehensive discovery
    cache_responses: bool = True  # Cache to avoid repeat costs
    enable_smart_batching: bool = True  # Batch requests
    max_daily_requests: int = 200  # Increased for comprehensive discovery

class CostEffectiveLLM:
    """Cost-effective LLM integration with budget controls"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = None
        self.request_count = 0
        self.daily_limit_reached = False
        self.response_cache = {}
        self.setup_client()
        
    def setup_client(self):
        """Setup Gemini client with user's API key"""
        try:
            # Use user's specific API key from .env
            api_key = self.config.api_key or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
            if api_key and genai:
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(self.config.model)
                print(f"✅ LLM client initialized with {self.config.model} for comprehensive .html discovery")
            else:
                print("⚠️  LLM client not available - using enhanced fallback patterns")
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
        """Generate URL patterns for any website type"""
        
        if not self._check_budget_limits() or not self.client:
            return self._fallback_patterns(domain, site_type, phase)
        
        # Create cache key
        cache_key = self._get_cache_key(f"{domain}_{site_type}_{phase}", str(len(discovered_urls)))
        
        # Check cache first
        if self.config.cache_responses and cache_key in self.response_cache:
            print(f"🔄 Using cached LLM response for {phase}")
            return self.response_cache[cache_key]
        
        try:
            # Create generic prompt based on site type and phase
            prompt = self._create_generic_prompt(domain, site_type, discovered_urls[:5], phase)
            
            print(f"🤖 LLM: Generating {phase} patterns for {site_type} site...")
            
            response = self.client.generate_content(prompt)
            self.request_count += 1
            
            # Extract URLs from response
            urls = self._parse_llm_response(response.text, domain)
            
            # Cache the response
            if self.config.cache_responses:
                self.response_cache[cache_key] = urls
            
            print(f"✅ LLM generated {len(urls)} potential URLs")
            time.sleep(self.config.rate_limit_delay)  # Rate limiting
            
            return urls
            
        except Exception as e:
            print(f"⚠️  LLM generation failed: {e}")
            return self._fallback_patterns(domain, site_type, phase)
    
    def _create_generic_prompt(self, domain: str, site_type: str, sample_urls: List[str], 
                             phase: str) -> str:
        """Create prompts for COMPREHENSIVE URL discovery - every single URL"""
        
        # Determine site type if not provided
        if not site_type:
            site_type = self._detect_site_type(domain)
        
        # MAXIMUM DISCOVERY prompts - find EVERY possible URL
        prompts = {
            "robots_analysis": f"""COMPREHENSIVE URL DISCOVERY for {site_type} website: {domain}
Sample URLs: {sample_urls[:3]}

Generate 20 likely URLs for COMPLETE site mapping:
- Admin/Management: /admin/, /administrator/, /manage/, /dashboard/
- Content Areas: /content/, /pages/, /articles/, /posts/, /news/
- Services: /services/, /products/, /solutions/, /offerings/
- Resources: /resources/, /documents/, /downloads/, /files/
- Support: /support/, /help/, /faq/, /contact/, /feedback/
- Technical: /api/, /rest/, /config/, /settings/, /tools/
- Archives: /archive/, /backup/, /old/, /temp/, /cache/

Include .html, .php, .asp, .jsp extensions. Return complete URLs.""",

            "directory_discovery": f"""MAXIMUM DIRECTORY DISCOVERY for {site_type} site {domain}:
Generate 25 directory patterns for EVERY possible content area:

CORE DIRECTORIES:
/admin/, /administrator/, /management/, /dashboard/, /control/
/content/, /pages/, /articles/, /posts/, /blog/, /news/
/services/, /products/, /solutions/, /catalog/, /portfolio/
/resources/, /documents/, /downloads/, /files/, /media/
/support/, /help/, /faq/, /contact/, /feedback/, /customer/
/api/, /rest/, /ajax/, /json/, /xml/, /data/

{site_type.upper()}-SPECIFIC:
- Government: /departments/, /council/, /ordinances/, /budget/
- Corporate: /investors/, /careers/, /press/, /partners/
- Education: /students/, /faculty/, /courses/, /research/

Return all as /directory/ format.""",

            "pattern_generation": f"""PATTERN-BASED URL GENERATION for {domain}:
Sample URLs: {sample_urls}

Generate 20 URL variations for MAXIMUM coverage:
1. NUMERIC PATTERNS:
   - ID sequences: /item1.html → /item2.html, /item3.html...
   - Year sequences: /2024/ → /2023/, /2022/, /2021/
   - Page numbers: /page1/ → /page2/, /page3/

2. CATEGORY PATTERNS:
   - Content types: /news/ → /events/, /announcements/
   - Languages: /en/ → /ja/, /es/, /fr/, /de/
   - Formats: .html → .php, .asp, .jsp

3. ARCHIVE PATTERNS:
   - Date archives: /archive/2024/ → /archive/2023/
   - Backup versions: /backup/, /old/, /previous/

Return COMPLETE URLs prioritizing .html but including all formats.""",

            "search_queries": f"""SEARCH QUERIES for COMPREHENSIVE {site_type} discovery on {domain}:

Generate 12 search terms to find HIDDEN content:
1. FILE-SPECIFIC:
   - "filetype:html site:{domain}"
   - "filetype:php site:{domain}"
   - "filetype:pdf site:{domain}"

2. ADMIN/HIDDEN:
   - "inurl:admin site:{domain}"
   - "inurl:login site:{domain}"
   - "inurl:config site:{domain}"
   - "inurl:backup site:{domain}"

3. CONTENT-SPECIFIC:
   - "{site_type} services"
   - "{site_type} resources"
   - "{site_type} documents"
   - "{site_type} information"

Return search terms for maximum URL discovery."""
        }
        
        return prompts.get(phase, prompts["robots_analysis"])
- Content areas (/content/, /pages/, /articles/)
- Documentation (/docs/, /help/, /support/)
- Archives (/archive/, /old/, /backup/)
- Special sections (technology-specific paths)

Format: Return only directory paths like /admin/, /docs/""",

            "pattern_generation": f"""Analyze these .html URL samples from {domain}:
{sample_urls}

Generate 15 similar .html URL variations by identifying patterns:
- If you see /news/2024/article.html, generate /news/2023/, /news/2022/ variants
- If you see /dept/admin.html, try other departments
- Look for numbered sequences (page1.html, page2.html)
- Try date patterns (jan.html, feb.html, 2024.html, 2023.html)
- Language variants (en.html, ja.html)

Focus on URLs that are most likely to exist as .html files.
Format: Return only complete URLs ending in .html""",

            "search_queries": f"""Generate 10 targeted search terms for {site_type} website {domain} to find .html pages:
- Content types that would be in .html format
- Administrative terms that might lead to .html pages
- Document/page names common for {site_type} sites
- Archive/historical content terms

Keep generic but focused on finding actual .html content.
Format: Return only search terms, one per line.""",

            "form_discovery": f"""For {site_type} website {domain}, suggest 8 common form submission endpoints and result pages:
- Contact form result pages (contact-success.html, thank-you.html)
- Search result pages (search-results.html, results.html)
- Login/registration pages (login.html, register.html, profile.html)
- Application/submission pages specific to {site_type}

Format: Return only .html URLs that would be form-related""",

            "hierarchical_crawling": f"""Based on {site_type} website structure, suggest 10 parent-child .html page relationships:
Sample structure: {sample_urls[:3]}

Predict parent directories that would contain child .html pages:
- If /services/ exists, what .html files might be inside?
- If /about/ exists, what sub-pages might exist? (team.html, history.html)
- Common organizational patterns for {site_type} sites

Format: Return directory paths that would contain .html files"""
        }
        
        return prompts.get(phase, prompts["robots_analysis"])
    
    def _detect_site_type(self, domain: str) -> str:
        """Detect website type from domain"""
        domain_lower = domain.lower()
        
        if any(term in domain_lower for term in ['gov', 'city', 'municipal', 'admin']):
            return "government"
        elif any(term in domain_lower for term in ['edu', 'university', 'school']):
            return "educational"
        elif any(term in domain_lower for term in ['news', 'media', 'blog']):
            return "news/media"
        elif any(term in domain_lower for term in ['shop', 'store', 'ecommerce']):
            return "ecommerce"
        elif any(term in domain_lower for term in ['org', 'nonprofit']):
            return "organization"
        else:
            return "corporate"
    
    def _parse_llm_response(self, response_text: str, domain: str) -> List[str]:
        """Parse LLM response and extract valid .html URLs"""
        lines = response_text.strip().split('\n')
        urls = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            # Remove any bullet points or numbering
            line = re.sub(r'^[\d\.\-\*\+]\s*', '', line)
            line = line.strip()
            
            # Handle different formats
            if line.startswith('http'):
                # Full URL
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
        
        # Filter for .html URLs specifically and remove duplicates
        html_urls = []
        for url in urls:
            if self._validate_url(url, domain):
                # Prioritize .html URLs but include directories that might contain .html
                if url.endswith('.html') or url.endswith('.htm'):
                    html_urls.append(url)
                elif url.endswith('/'):
                    # Directory that might contain .html files
                    html_urls.append(url)
                elif '.' not in url.split('/')[-1]:
                    # Path without extension - might be directory
                    html_urls.append(url)
        
        return list(set(html_urls))
    
    def _validate_url(self, url: str, domain: str) -> bool:
        """Validate generated URL"""
        try:
            parsed = urlparse(url)
            return (parsed.scheme in ['http', 'https'] and 
                   domain in parsed.netloc and
                   len(url) < 500)  # Reasonable length
        except:
            return False
    
    def _fallback_patterns(self, domain: str, site_type: str, phase: str) -> List[str]:
        """Enhanced fallback patterns focused on .html URL discovery"""
        base_url = f"https://{domain}"
        
        # Enhanced fallback patterns prioritizing .html files
        fallback_patterns = {
            "government": [
                f"{base_url}/admin/", f"{base_url}/admin/index.html", f"{base_url}/admin/dashboard.html",
                f"{base_url}/council/", f"{base_url}/council/meetings.html", f"{base_url}/council/members.html",
                f"{base_url}/departments/", f"{base_url}/departments/list.html",
                f"{base_url}/services/", f"{base_url}/services/index.html", f"{base_url}/services/online.html",
                f"{base_url}/documents/", f"{base_url}/documents/archive.html", f"{base_url}/documents/forms.html",
                f"{base_url}/statistics/", f"{base_url}/statistics/annual.html", f"{base_url}/statistics/monthly.html",
                f"{base_url}/budget/", f"{base_url}/budget/current.html", f"{base_url}/budget/history.html",
                f"{base_url}/policies/", f"{base_url}/policies/index.html"
            ],
            "corporate": [
                f"{base_url}/admin/", f"{base_url}/admin/login.html", f"{base_url}/admin/dashboard.html",
                f"{base_url}/api/", f"{base_url}/docs/", f"{base_url}/docs/index.html",
                f"{base_url}/support/", f"{base_url}/support/faq.html", f"{base_url}/support/contact.html",
                f"{base_url}/resources/", f"{base_url}/resources/downloads.html",
                f"{base_url}/products/", f"{base_url}/products/index.html", f"{base_url}/products/catalog.html",
                f"{base_url}/services/", f"{base_url}/services/overview.html",
                f"{base_url}/about/", f"{base_url}/about/team.html", f"{base_url}/about/history.html",
                f"{base_url}/contact/", f"{base_url}/contact/form.html"
            ],
            "educational": [
                f"{base_url}/admin/", f"{base_url}/admin/portal.html",
                f"{base_url}/students/", f"{base_url}/students/portal.html", f"{base_url}/students/services.html",
                f"{base_url}/faculty/", f"{base_url}/faculty/directory.html", f"{base_url}/faculty/resources.html",
                f"{base_url}/courses/", f"{base_url}/courses/catalog.html", f"{base_url}/courses/schedule.html",
                f"{base_url}/research/", f"{base_url}/research/projects.html",
                f"{base_url}/library/", f"{base_url}/library/catalog.html",
                f"{base_url}/admissions/", f"{base_url}/admissions/apply.html", f"{base_url}/admissions/requirements.html",
                f"{base_url}/departments/", f"{base_url}/departments/list.html"
            ]
        }
        
        patterns = fallback_patterns.get(site_type, fallback_patterns["corporate"])
        print(f"🔄 Using enhanced .html fallback patterns for {site_type} site")
        return patterns[:15]  # Increased to 15 for comprehensive discovery

# Global LLM instance
_llm_instance = None

def get_llm_instance(api_key: str = None) -> CostEffectiveLLM:
    """Get singleton LLM instance optimized for comprehensive .html discovery"""
    global _llm_instance
    if _llm_instance is None:
        config = LLMConfig(
            api_key=api_key,
            max_daily_requests=200,  # Increased for comprehensive discovery
            rate_limit_delay=0.8,    # Faster rate for thorough coverage
            cache_responses=True,    # Save costs with caching
            max_tokens=1500         # More comprehensive responses
        )
        _llm_instance = CostEffectiveLLM(config)
    return _llm_instance

async def generate_phase_patterns(domain: str, discovered_urls: List[str], 
                                phase: str, api_key: str = None) -> List[str]:
    """Simple interface for phases to get LLM patterns"""
    llm = get_llm_instance(api_key)
    site_type = llm._detect_site_type(domain)
    return await llm.generate_patterns(domain, site_type, discovered_urls, phase)

# Example usage for testing
async def test_llm_integration():
    """Test the LLM integration"""
    domain = "example.com"
    sample_urls = [
        "https://example.com/about/",
        "https://example.com/services/web-design/",
        "https://example.com/contact/"
    ]
    
    llm = get_llm_instance()
    
    # Test different phases
    for phase in ["robots_analysis", "directory_discovery", "pattern_generation"]:
        print(f"\n🧪 Testing {phase}...")
        results = await llm.generate_patterns(domain, "corporate", sample_urls, phase)
        print(f"Generated: {results}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_llm_integration())
