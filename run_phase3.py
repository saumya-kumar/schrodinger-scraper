#!/usr/bin/env python3
"""Run Phase 3 (URL Seeding) only and append results to all_urls.json.
Uses existing Phase 1 + 2 URLs for context. Relies on master_url_discovery internal method.
"""
import asyncio, json, os
from datetime import datetime
from master_url_discovery import ComprehensiveURLDiscoveryMaster

BASE_URL = "https://www.city.chiyoda.lg.jp"
API_KEY = os.environ.get("GEMINI_API_KEY")  # optional
STORE_FILE = "all_urls.json"
PHASE_KEY = "3_url_seeding"

async def run_phase3():
    if not os.path.exists(STORE_FILE):
        raise SystemExit("all_urls.json not found. Run prior phases first.")
    with open(STORE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Collect prior discovered URLs for context
    prior_urls = set()
    for k, v in data.get('phases', {}).items():
        prior_urls.update(v.get('urls', []))

    master = ComprehensiveURLDiscoveryMaster(BASE_URL, gemini_api_key=API_KEY)
    master.all_discovered_urls.update(prior_urls)

    result = await master._run_url_seeding()
    if not result.get('success'):
        print("Phase 3 failed:", result.get('error'))
        return

    urls = result.get('urls', [])

    # Update store
    data['phases'][PHASE_KEY]['raw_count'] = len(urls)
    data['phases'][PHASE_KEY]['urls'] = urls

    # Recompute aggregate
    all_unique = set()
    for phase_key, pdata in data['phases'].items():
        all_unique.update(pdata.get('urls', []))
    data['aggregate']['total_unique_urls'] = len(all_unique)
    data['aggregate']['by_phase_counts'][PHASE_KEY] = len(urls)
    data['aggregate']['last_phase_completed'] = 3
    data['aggregate']['unique_urls'] = sorted(all_unique)
    data['updated_at_utc'] = datetime.utcnow().isoformat() + 'Z'

    with open(STORE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Phase 3 stored. New seeded URLs: {len(urls)} | Total unique: {len(all_unique)}")

if __name__ == "__main__":
    asyncio.run(run_phase3())
