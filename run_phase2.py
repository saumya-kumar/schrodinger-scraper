#!/usr/bin/env python3
"""Helper script to run ONLY Phase 2 (Robots.txt & LLM Analysis) and append results into all_urls.json.
Assumes Phase 1 already populated all_urls.json.
"""
import asyncio, json, os, time
from datetime import datetime
from master_url_discovery import ComprehensiveURLDiscoveryMaster

BASE_URL = "https://www.city.chiyoda.lg.jp"
API_KEY = os.environ.get("GEMINI_API_KEY")  # optional

ALL_URLS_FILE = "all_urls.json"

async def run_phase2():
    # Load existing Phase 1 data
    if not os.path.exists(ALL_URLS_FILE):
        raise SystemExit("all_urls.json not found. Run Phase 1 first.")
    with open(ALL_URLS_FILE, 'r', encoding='utf-8') as f:
        store = json.load(f)

    phase1_urls = set(store.get('phases', {}).get('1_sitemap', {}).get('urls', []))

    master = ComprehensiveURLDiscoveryMaster(BASE_URL, gemini_api_key=API_KEY)
    # Seed master with Phase 1 URLs so Phase 2 has context
    master.all_discovered_urls.update(phase1_urls)

    # Run only Phase 2 internal method
    result = await master._run_robots_llm_analysis()
    if not result.get('success'):
        print("Phase 2 failed:", result.get('error'))
        return

    phase2_urls = result.get('urls', [])

    # Update JSON structure
    store['phases']['2_robots']['raw_count'] = len(phase2_urls)
    store['phases']['2_robots']['urls'] = phase2_urls

    # Recompute aggregate
    all_unique = set()
    for phase_key, pdata in store['phases'].items():
        all_unique.update(pdata.get('urls', []))
    store['aggregate']['total_unique_urls'] = len(all_unique)
    store['aggregate']['by_phase_counts']['2_robots'] = len(phase2_urls)
    store['aggregate']['last_phase_completed'] = 2
    store['aggregate']['unique_urls'] = sorted(all_unique)
    store['updated_at_utc'] = datetime.utcnow().isoformat() + 'Z'

    with open(ALL_URLS_FILE, 'w', encoding='utf-8') as f:
        json.dump(store, f, indent=2, ensure_ascii=False)

    print(f"Phase 2 stored. New URLs: {len(phase2_urls)} | Total unique: {len(all_unique)}")

if __name__ == "__main__":
    asyncio.run(run_phase2())
