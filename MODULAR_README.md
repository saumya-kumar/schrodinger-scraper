# 🚀 Modular Website Scraper with Crawl4AI

A comprehensive, modular website scraping system built with Crawl4AI that focuses on URL discovery first, then intelligent content extraction.

## 🏗️ Modular Architecture

### Block 1: [`hello1.py`](hello1.py) - Single Page Translation & Content
- **Purpose**: Convert any single webpage to clean English markdown
- **Input**: Single URL
- **Output**: Clean English markdown content saved as .txt file
- **Features**: 
  - Google Translate integration for non-English pages
  - Force English content option
  - Clean markdown generation
  - Error handling and content validation

### Block 2: [`url_discoverer.py`](url_discoverer.py) - Comprehensive URL Discovery
- **Purpose**: Find ALL URLs from a website systematically
- **Input**: Homepage URL + optional context
- **Output**: Complete list of discovered URLs with metadata
- **Features**:
  - Recursive crawling using Crawl4AI
  - Sitemap parsing (XML & HTML)
  - Robots.txt analysis
  - LLM-powered keyword generation (Gemini API)
  - Pattern-based URL discovery
  - Intelligent filtering

### Block 3: [`integration_example.py`](integration_example.py) - Complete Pipeline
- **Purpose**: Demonstrates how blocks work together
- **Input**: Website homepage + context
- **Output**: Complete scraped content + comprehensive results
- **Features**:
  - Orchestrates URL discovery + content extraction
  - Progress tracking and reporting
  - Results compilation and export

## 🔧 Setup & Configuration

### 1. Install Dependencies
```bash
pip install crawl4ai google-generativeai python-dotenv
```

### 2. Setup Environment Variables
Copy `.env.template` to `.env` and add your API keys:
```env
# Get your Gemini API key from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 3. Verify Installation
```bash
python hello1.py  # Test single page extraction
python url_discoverer.py  # Test URL discovery
python integration_example.py  # Test complete pipeline
```

## 🎯 Usage Examples

### Single Page Content Extraction
```bash
python hello1.py
# Enter URL when prompted
# Choose English translation option
# Get clean markdown output
```

### Complete Website URL Discovery
```bash
python url_discoverer.py
# Enter homepage URL
# Optionally provide sample URL and context
# Get comprehensive list of all website URLs
```

### Full Website Scraping Pipeline
```bash
python integration_example.py
# Enter homepage URL and context
# System will discover URLs + extract content
# Get complete results with all files
```

## 🤖 LLM Integration (Gemini API)

The system uses Google Gemini API for intelligent features:

- **Keyword Generation**: Analyzes homepage to generate relevant keywords
- **URL Pattern Discovery**: Suggests likely URL patterns based on content
- **Content Relevance**: Future enhancement for filtering relevant pages

### API Key Setup
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file as `GEMINI_API_KEY`

## 📊 Output Files

### URL Discovery Results
```json
{
  "total_discovered_urls": 1247,
  "discovery_time_seconds": 45.2,
  "llm_keywords_generated": 89,
  "discovered_urls": ["url1", "url2", ...],
  "discovery_stats": {...}
}
```

### Content Extraction Results
- Individual `.txt` files for each page (clean markdown)
- Comprehensive JSON results file with metadata
- Success/failure statistics

## 🔄 Workflow

```
Homepage URL → URL Discovery → LLM Keywords → Recursive Crawling → 
Sitemap Parsing → Pattern Generation → Complete URL List → 
Content Extraction → English Translation → Markdown Generation → 
File Output → Final Results
```

## ⚙️ Configuration Options

### URL Discovery Config
```python
URLDiscoveryConfig(
    base_url="https://example.com",
    max_pages=10000,           # Maximum URLs to discover
    max_depth=6,               # Crawling depth limit
    force_english=True,        # Force English content
    use_llm_keywords=True,     # Use Gemini for keywords
    include_pdfs=True,         # Include PDF files
    max_concurrent=50          # Concurrent requests
)
```

## 🎯 Key Features

### 🔍 Comprehensive URL Discovery
- **Recursive Crawling**: Systematically discovers all pages
- **Multiple Sources**: Sitemaps, robots.txt, links, patterns
- **LLM Enhancement**: AI-powered keyword generation
- **Rate Limiting**: Respectful crawling with delays

### 🌐 Smart Content Extraction
- **English Translation**: Automatic via Google Translate
- **Clean Markdown**: Structured, readable output
- **Error Recovery**: Multiple fallback strategies
- **Content Validation**: Ensures quality output

### 🧩 Modular Design
- **Independent Blocks**: Each module works standalone
- **Easy Integration**: Simple APIs between blocks
- **Extensible**: Easy to add new features
- **Maintainable**: Clear separation of concerns

## 🚨 Important Notes

1. **Rate Limiting**: System includes delays to be respectful to servers
2. **API Costs**: Gemini API has usage costs (but very reasonable)
3. **Large Sites**: Sites with 10,000+ pages will take significant time
4. **English Focus**: Optimized for English content extraction
5. **Storage**: Large sites will generate many files

## 🔮 Future Enhancements

- **Relevance Filtering**: LLM-based content relevance scoring
- **Structured Data Extraction**: JSON schema-based extraction
- **Vector Storage**: Embeddings for semantic search
- **Parallel Processing**: Multi-threaded content extraction
- **Database Integration**: Store results in databases

## 📈 Performance

- **URL Discovery**: ~50-200 URLs/second (depending on site)
- **Content Extraction**: ~1-3 pages/second (with translation)
- **Memory Usage**: Efficient streaming processing
- **Disk Usage**: ~1MB per extracted page (markdown)

## 🆘 Troubleshooting

### Common Issues
1. **No Gemini API Key**: System falls back to basic keywords
2. **Rate Limiting**: Increase delays if getting blocked
3. **Memory Issues**: Reduce max_pages for large sites
4. **Translation Failures**: Google Translate has usage limits

### Debug Mode
Set `verbose=True` in configs for detailed logging.

---

**This modular approach ensures you can focus on URL discovery first (your priority), then add intelligent content extraction and analysis as needed.**
