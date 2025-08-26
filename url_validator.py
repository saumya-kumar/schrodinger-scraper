#!/usr/bin/env python3
"""
URL Validator - Check if discovered URLs actually exist and are accessible
"""

import asyncio
import aiohttp
import json
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class URLValidator:
    def __init__(self, base_domain: str, max_concurrent: int = 50, timeout: int = 10):
        self.base_domain = base_domain
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.session = None
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_url(self, url: str) -> Tuple[str, bool, int, str]:
        """Check if a URL exists and is accessible"""
        try:
            async with self.session.head(url, allow_redirects=True) as response:
                status = response.status
                is_valid = 200 <= status < 400
                content_type = response.headers.get('content-type', '')
                return url, is_valid, status, content_type
        except Exception as e:
            logger.debug(f"Error checking {url}: {e}")
            return url, False, 0, str(e)
    
    async def validate_urls(self, urls: List[str]) -> Dict[str, any]:
        """Validate a list of URLs and return detailed results"""
        start_time = time.time()
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def check_with_semaphore(url):
            async with semaphore:
                return await self.check_url(url)
        
        tasks = [check_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_urls = []
        invalid_urls = []
        html_urls = []
        redirect_urls = []
        
        for result in results:
            if isinstance(result, Exception):
                continue
                
            url, is_valid, status, content_type = result
            
            if is_valid:
                valid_urls.append({
                    'url': url,
                    'status': status,
                    'content_type': content_type
                })
                
                # Check if it's HTML content
                if 'text/html' in content_type.lower():
                    html_urls.append(url)
                
                # Check if it's a redirect
                if 300 <= status < 400:
                    redirect_urls.append({
                        'url': url,
                        'status': status
                    })
            else:
                invalid_urls.append({
                    'url': url,
                    'status': status,
                    'error': content_type
                })
        
        execution_time = time.time() - start_time
        
        return {
            'total_checked': len(urls),
            'valid_count': len(valid_urls),
            'invalid_count': len(invalid_urls),
            'html_count': len(html_urls),
            'redirect_count': len(redirect_urls),
            'execution_time': execution_time,
            'valid_urls': valid_urls,
            'invalid_urls': invalid_urls,
            'html_urls': html_urls,
            'redirect_urls': redirect_urls
        }

def load_discovered_urls(file_path: str) -> List[str]:
    """Load URLs from the all_urls.json file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_urls = set()
        
        # Collect URLs from all phases
        for phase_name, phase_data in data.get('phases', {}).items():
            if 'urls' in phase_data:
                all_urls.update(phase_data['urls'])
        
        return list(all_urls)
    except Exception as e:
        logger.error(f"Error loading URLs: {e}")
        return []

async def main():
    """Main validation function"""
    base_domain = "www.city.chiyoda.lg.jp"
    
    # Load discovered URLs
    all_urls_file = Path("all_urls.json")
    if not all_urls_file.exists():
        logger.error("all_urls.json not found!")
        return
    
    urls = load_discovered_urls(str(all_urls_file))
    logger.info(f"Loaded {len(urls)} URLs for validation")
    
    if not urls:
        logger.error("No URLs to validate!")
        return
    
    # Validate URLs
    async with URLValidator(base_domain, max_concurrent=30) as validator:
        logger.info("Starting URL validation...")
        results = await validator.validate_urls(urls)
    
    # Display results
    logger.info(f"\n=== URL Validation Results ===")
    logger.info(f"Total URLs checked: {results['total_checked']}")
    logger.info(f"Valid URLs: {results['valid_count']} ({results['valid_count']/results['total_checked']*100:.1f}%)")
    logger.info(f"Invalid URLs: {results['invalid_count']} ({results['invalid_count']/results['total_checked']*100:.1f}%)")
    logger.info(f"HTML pages: {results['html_count']} ({results['html_count']/results['total_checked']*100:.1f}%)")
    logger.info(f"Redirects: {results['redirect_count']}")
    logger.info(f"Validation time: {results['execution_time']:.2f} seconds")
    
    # Save validation results
    validation_results = {
        'base_domain': base_domain,
        'validation_timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'summary': {
            'total_checked': results['total_checked'],
            'valid_count': results['valid_count'],
            'invalid_count': results['invalid_count'],
            'html_count': results['html_count'],
            'redirect_count': results['redirect_count'],
            'execution_time': results['execution_time']
        },
        'valid_urls': results['valid_urls'],
        'invalid_urls': results['invalid_urls'][:50],  # Limit to first 50 invalid URLs
        'html_urls': results['html_urls']
    }
    
    with open('url_validation_results.json', 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, indent=2, ensure_ascii=False)
    
    logger.info("Results saved to url_validation_results.json")
    
    # Show some invalid URLs for debugging
    if results['invalid_urls']:
        logger.info(f"\nFirst 10 invalid URLs:")
        for invalid in results['invalid_urls'][:10]:
            logger.info(f"  {invalid['url']} - Status: {invalid['status']}, Error: {invalid['error']}")

if __name__ == "__main__":
    asyncio.run(main())
