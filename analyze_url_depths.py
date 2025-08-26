#!/usr/bin/env python3
"""
Analyze URL depths from html_urls.json
Calculates depth based on path segments in the URL
"""

import json
from urllib.parse import urlparse
from collections import defaultdict

def analyze_url_depths():
    """Analyze the depth of URLs in html_urls.json"""
    
    print("📊 ANALYZING URL DEPTHS FROM html_urls.json")
    print("=" * 60)
    
    # Read html_urls.json
    try:
        with open('html_urls.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded html_urls.json successfully")
        html_urls = data.get('html_urls', [])
        print(f"📋 Found {len(html_urls)} HTML URLs to analyze")
    except Exception as e:
        print(f"❌ Error loading html_urls.json: {e}")
        return
    
    # Analyze depths
    depth_counts = defaultdict(int)
    depth_examples = defaultdict(list)
    
    print(f"\n🔍 Analyzing URL depths...")
    
    for url in html_urls:
        try:
            # Parse the URL
            parsed = urlparse(url)
            path = parsed.path
            
            # Remove leading and trailing slashes
            path = path.strip('/')
            
            # Calculate depth based on path segments
            if not path or path == '':
                # Root level (like /index.html or just /)
                depth = 1
            else:
                # Count path segments separated by '/'
                segments = [seg for seg in path.split('/') if seg]
                depth = len(segments)
            
            # Limit depth to 9 for analysis
            if depth > 9:
                depth = 9
            
            depth_counts[depth] += 1
            
            # Store examples (max 3 per depth)
            if len(depth_examples[depth]) < 3:
                depth_examples[depth].append(url)
                
        except Exception as e:
            print(f"⚠️ Error parsing URL {url}: {e}")
            continue
    
    # Display results
    print(f"\n📊 URL DEPTH ANALYSIS RESULTS")
    print("=" * 60)
    print(f"{'Depth':>6} | {'Count':>6} | {'%':>6} | Example URLs")
    print("-" * 60)
    
    total_urls = len(html_urls)
    
    for depth in range(1, 10):  # Depths 1-9
        count = depth_counts[depth]
        percentage = (count / total_urls * 100) if total_urls > 0 else 0
        
        # Get example URL (shortened for display)
        example = ""
        if depth in depth_examples and depth_examples[depth]:
            example_url = depth_examples[depth][0]
            # Shorten URL for display
            if len(example_url) > 50:
                example = example_url[:47] + "..."
            else:
                example = example_url
        
        print(f"{depth:>6} | {count:>6} | {percentage:>5.1f}% | {example}")
    
    # Summary statistics
    print("\n" + "=" * 60)
    print("📈 SUMMARY STATISTICS")
    print("=" * 60)
    
    total_analyzed = sum(depth_counts.values())
    print(f"Total URLs analyzed: {total_analyzed}")
    print(f"Total in file: {total_urls}")
    
    if depth_counts:
        max_depth = max(depth_counts.keys())
        min_depth = min(depth_counts.keys())
        
        # Calculate average depth
        total_depth_sum = sum(depth * count for depth, count in depth_counts.items())
        avg_depth = total_depth_sum / total_analyzed if total_analyzed > 0 else 0
        
        print(f"Minimum depth: {min_depth}")
        print(f"Maximum depth: {max_depth}")
        print(f"Average depth: {avg_depth:.2f}")
        
        # Find most common depth
        most_common_depth = max(depth_counts.keys(), key=lambda x: depth_counts[x])
        print(f"Most common depth: {most_common_depth} ({depth_counts[most_common_depth]} URLs)")
    
    # Show examples for each depth
    print(f"\n📋 EXAMPLE URLs BY DEPTH")
    print("=" * 60)
    
    for depth in range(1, 10):
        if depth in depth_examples and depth_examples[depth]:
            print(f"\nDepth {depth} examples:")
            for i, url in enumerate(depth_examples[depth], 1):
                print(f"  {i}. {url}")
    
    # Save detailed analysis
    analysis_data = {
        "analysis_timestamp": json.loads(json.dumps(data.get("created_at_utc", ""), default=str)),
        "total_urls_analyzed": total_analyzed,
        "depth_distribution": dict(depth_counts),
        "depth_percentages": {str(depth): round(count/total_analyzed*100, 2) 
                            for depth, count in depth_counts.items()},
        "examples_by_depth": {str(depth): urls for depth, urls in depth_examples.items()},
        "statistics": {
            "min_depth": min(depth_counts.keys()) if depth_counts else 0,
            "max_depth": max(depth_counts.keys()) if depth_counts else 0,
            "average_depth": round(avg_depth, 2) if depth_counts else 0,
            "most_common_depth": most_common_depth if depth_counts else 0
        }
    }
    
    # Save analysis results
    try:
        with open('url_depth_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Detailed analysis saved to: url_depth_analysis.json")
    except Exception as e:
        print(f"⚠️ Could not save analysis file: {e}")
    
    print(f"\n🎯 DEPTH ANALYSIS COMPLETE")

if __name__ == "__main__":
    analyze_url_depths()
