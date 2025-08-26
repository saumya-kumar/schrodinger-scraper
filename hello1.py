#!/usr/bin/env python3
"""
Hello1.py - Single webpage to English markdown converter using Crawl4AI

This script focuses on converting a single webpage to clean English markdown format.
Part of the modular website scraping system.

Block 1: Single Page Translation & Content Extraction
- Input: Single URL
- Output: Clean English markdown content
- Features: Google Translate integration, force English content
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import re

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")


def convert_url_to_english(url: str) -> str:
    """
    Currently returns the original URL. Logic for handling translated content
    is now within the core crawling strategy.
    """
    return url


async def convert_webpage_to_markdown(url: str, output_file: str = "crawled_content.txt", force_english: bool = False, original_url: str = None):
    """
    Convert a webpage to markdown and save it to a text file.
    
    Args:
        url (str): The URL of the webpage to convert
        output_file (str): The output file name (default: crawled_content.txt)
        force_english (bool): Whether to force English language content (default: False)
        original_url (str): The original URL before translation (for fallback)
    """
    try:
        print(f"🚀 Starting to crawl: {url}")
        print(f"📝 Output will be saved to: {output_file}")
        
        # Configure the browser with language preferences
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            # Set Accept-Language header for English preference
            headers={
                "Accept-Language": "en-US,en;q=0.9" if force_english else "en-US,en;q=0.9,ja;q=0.8"
            } if force_english else {},
            # Additional settings for better language handling
            java_script_enabled=True,  # Required for dynamic content
            ignore_https_errors=True,   # Handle any SSL issues
            # Increase viewport for better content rendering
            viewport_width=1920 if force_english else 1080,
            viewport_height=1080 if force_english else 600,
            # Additional browser arguments for language preference
            extra_args=[
                "--lang=en-US" if force_english else None,
                "--accept-lang=en-US" if force_english else None
            ] if force_english else None
        )
        
        # Configure the crawler with markdown generation
        crawler_config = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator(),
            verbose=True,
            # Wait for page to fully load (important for translated content)
            wait_for=None, # Removed 'domcontentloaded' as it's a load state, not a selector
            # Much longer timeout for Google Translate (in milliseconds)
            page_timeout=(30000 if force_english else 10000),  # 30s for English, 10s for regular
            # Wait for images to load (helps with translation completion)
            wait_for_images=True if force_english else False,
            # Enable iframe processing in the core crawler
            process_iframes=True if "translate.goog" in url else False
        )
        
        # Use the crawler with context manager for automatic cleanup
        async with AsyncWebCrawler(config=browser_config) as crawler:
            print("🌐 Browser started successfully")
            
            # Show configuration details
            if force_english:
                print("🔧 Browser configured with English language preferences")
                print(f"🔧 Accept-Language: {browser_config.headers.get('Accept-Language', 'Not set')}")
                print(f"🔧 Page timeout: {crawler_config.page_timeout}ms")
                print(f"🔧 Wait strategy: {crawler_config.wait_for}")
            
            # Crawl the webpage
            print("📖 Crawling webpage...")
            result_container = await crawler.arun(url=url, config=crawler_config)
            
            # Get the first result from the container
            if result_container and len(result_container._results) > 0:
                result = result_container._results[0]
            else:
                print("❌ No results returned from crawler")
                return False
            
            if result.success:
                print("✅ Webpage crawled successfully!")
                
                # Debug: Print available attributes
                print(f"🔍 Available result attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
                
                # Debug the markdown content
                print(f"🔍 Markdown type: {type(result.markdown)}")
                print(f"🔍 Markdown repr: {repr(result.markdown)}")
                
                # Get the markdown content - result.markdown is the actual string content
                markdown_content = str(result.markdown) if result.markdown else ""
                
                # Also try alternative content sources if markdown is empty
                if not markdown_content or len(markdown_content.strip()) < 10:
                    print("⚠️ Markdown content is empty or very short, trying alternative sources...")
                    
                    # Try cleaned HTML content
                    if hasattr(result, 'cleaned_html') and result.cleaned_html:
                        print("🔍 Trying cleaned_html...")
                        md_gen = DefaultMarkdownGenerator()
                        try:
                            md_result = md_gen.generate_markdown(result.cleaned_html)
                            # Extract the actual markdown string from the result
                            if hasattr(md_result, 'raw_markdown'):
                                markdown_content = md_result.raw_markdown
                            elif hasattr(md_result, 'markdown'):
                                markdown_content = str(md_result.markdown)
                            else:
                                markdown_content = str(md_result)
                            print(f"📝 Generated markdown from cleaned_html: {len(markdown_content)} chars")
                        except Exception as e:
                            print(f"❌ Failed to generate markdown from cleaned_html: {e}")
                    
                    # Try fit_html if available
                    if (not markdown_content or len(markdown_content.strip()) < 10) and hasattr(result, 'fit_html') and result.fit_html:
                        print("🔍 Trying fit_html...")
                        try:
                            md_result = md_gen.generate_markdown(result.fit_html)
                            if hasattr(md_result, 'raw_markdown'):
                                markdown_content = md_result.raw_markdown
                            elif hasattr(md_result, 'markdown'):
                                markdown_content = str(md_result.markdown)
                            else:
                                markdown_content = str(md_result)
                            print(f"📝 Generated markdown from fit_html: {len(markdown_content)} chars")
                        except Exception as e:
                            print(f"❌ Failed to generate markdown from fit_html: {e}")
                    
                    # Last resort: use raw HTML
                    if (not markdown_content or len(markdown_content.strip()) < 10) and hasattr(result, 'html') and result.html:
                        print("🔍 Trying raw html...")
                        try:
                            md_result = md_gen.generate_markdown(result.html)
                            if hasattr(md_result, 'raw_markdown'):
                                markdown_content = md_result.raw_markdown
                            elif hasattr(md_result, 'markdown'):
                                markdown_content = str(md_result.markdown)
                            else:
                                markdown_content = str(md_result)
                            print(f"📝 Generated markdown from raw html: {len(markdown_content)} chars")
                        except Exception as e:
                            print(f"❌ Failed to generate markdown from raw html: {e}")
                
                # Save to file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Crawled Content from: {url}\n\n")
                    f.write(f"**Crawl Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(f"**Page Title:** {getattr(result, 'title', 'N/A') or 'N/A'}\n\n")
                    if force_english:
                        f.write(f"**Language:** English (translated)\n\n")
                    f.write("---\n\n")
                    f.write(markdown_content)
                
                print(f"💾 Content saved to {output_file}")
                print(f"📊 Content length: {len(markdown_content)} characters")
                print(f"🔗 Page title: {getattr(result, 'title', 'N/A') or 'N/A'}")
                
                # Show a preview of the content
                preview = markdown_content[:200].replace('\n', ' ')
                if len(markdown_content) > 200:
                    preview += "..."
                print(f"\n📖 Content preview: {preview}")
                
            else:
                print(f"❌ Failed to crawl webpage: {result.error_message}")
                return False
                
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        return False
    
    return True


async def main():
    """Main function to handle user input and execute the conversion."""
    print("🤖 Crawl4AI Webpage to Markdown Converter")
    print("=" * 50)
    
    # Get URL from user input
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("🌐 Enter the webpage URL to convert: ").strip()
    
    # Validate URL
    if not url:
        print("❌ No URL provided. Exiting.")
        return
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Check if URL is already translated
    is_already_translated = "translate.goog" in url or "translate.google.com" in url
    original_url = url
    
    # Ask if user wants English content
    force_english = input("🌍 Force English content? (y/n, press Enter for 'y'): ").strip().lower()
    if force_english == "" or force_english.startswith('y'):
        force_english = True
        if is_already_translated:
            print("✅ URL is already translated to English")
        else:
            print("🌍 Will attempt to get English content via Google Translate.")
            # Use the proper Google Translate URL format
            encoded_url = url.replace('https://', '').replace('http://', '')
            url = f"https://translate.google.com/translate?hl=en&sl=auto&tl=en&u=https://{encoded_url}"
            print(f"🔄 Converted URL to Google Translate: {url}")
    else:
        force_english = False
    
    print(f"\n🎯 Target URL: {url}")
    print(f"🌐 Final URL to be crawled: {url}") # Add this line for debugging

    # Get output filename (optional)
    output_file = input("📁 Output filename (press Enter for 'crawled_content.txt'): ").strip()
    if not output_file:
        output_file = "crawled_content.txt"
    
    # Ensure .txt extension
    if not output_file.endswith('.txt'):
        output_file += '.txt'
    
    print(f"\n🚀 Starting conversion process...")
    
    # Convert the webpage
    success = await convert_webpage_to_markdown(url, output_file, force_english)
    
    if success:
        print(f"\n🎉 Conversion completed successfully!")
        print(f"📁 Check your file: {Path(output_file).absolute()}")
    else:
        print(f"\n💥 Conversion failed. Please check the error messages above.")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
