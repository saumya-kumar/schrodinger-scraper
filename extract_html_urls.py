#!/usr/bin/env python3
"""
Extract HTML URLs from all_urls.json
Filters only URLs ending with .html and saves to html_urls.json
"""

import json
from datetime import datetime
from pathlib import Path

def extract_html_urls():
    """Extract only .html URLs from all_urls.json and save to html_urls.json"""
    
    print("🔍 EXTRACTING HTML URLs FROM all_urls.json")
    print("=" * 60)
    
    # Read all_urls.json
    try:
        with open('all_urls.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded all_urls.json successfully")
    except Exception as e:
        print(f"❌ Error loading all_urls.json: {e}")
        return
    
    # Extract all URLs and filter for .html
    all_urls = set()
    html_urls = set()
    
    print("\n📊 Processing phases:")
    for phase_name, phase_data in data.get('phases', {}).items():
        if isinstance(phase_data, dict) and 'urls' in phase_data:
            phase_urls = phase_data['urls']
            all_urls.update(phase_urls)
            
            # Filter for .html URLs
            phase_html_urls = [url for url in phase_urls if url.endswith('.html')]
            html_urls.update(phase_html_urls)
            
            print(f"  {phase_name:20} | {len(phase_urls):5d} total | {len(phase_html_urls):5d} .html")
    
    print(f"\n📊 SUMMARY:")
    print(f"  Total URLs: {len(all_urls)}")
    print(f"  HTML URLs:  {len(html_urls)}")
    print(f"  Percentage: {len(html_urls)/len(all_urls)*100:.1f}%")
    
    # Create output structure
    html_data = {
        "schema_version": "1.0",
        "description": "HTML URLs only - filtered from all_urls.json",
        "source_file": "all_urls.json",
        "filter_criteria": "URLs ending with .html",
        "created_at_utc": datetime.now().isoformat(),
        "statistics": {
            "total_html_urls": len(html_urls),
            "total_source_urls": len(all_urls),
            "filter_percentage": round(len(html_urls)/len(all_urls)*100, 2)
        },
        "html_urls": sorted(list(html_urls))
    }
    
    # Save to html_urls.json
    try:
        with open('html_urls.json', 'w', encoding='utf-8') as f:
            json.dump(html_data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Successfully saved {len(html_urls)} HTML URLs to html_urls.json")
    except Exception as e:
        print(f"❌ Error saving html_urls.json: {e}")
        return
    
    # Print some sample URLs
    print(f"\n📋 Sample HTML URLs:")
    sample_urls = sorted(list(html_urls))[:10]
    for i, url in enumerate(sample_urls, 1):
        print(f"  {i:2d}. {url}")
    
    if len(html_urls) > 10:
        print(f"  ... and {len(html_urls) - 10} more")
    
    print(f"\n🎯 EXTRACTION COMPLETE")
    print(f"📁 Output file: html_urls.json")
    print(f"📊 HTML URLs extracted: {len(html_urls)}")

if __name__ == "__main__":
    extract_html_urls()
