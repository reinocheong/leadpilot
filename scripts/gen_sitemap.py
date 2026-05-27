#!/usr/bin/env python3
"""Generate sitemap.xml and JSON-LD dataset from rentals data.

Reads rentals.json, produces:
  - sitemap.xml  → Google/AI crawler index
  - dataset.json → JSON-LD for main page (injected into index.html)
"""
import json, os
from datetime import datetime

BASE_URL = 'https://leadpilot.dpdns.org'
DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'rentals.json')
SITEMAP_PATH = os.path.join(os.path.dirname(__file__), '..', 'sitemap.xml')

def load_data():
    with open(DATA_PATH) as f:
        raw = json.load(f)
    if isinstance(raw, dict):
        return raw.get('listings', [])
    return raw

def gen_sitemap(listings):
    pages = []
    # Main page
    pages.append({
        'loc': BASE_URL,
        'changefreq': 'daily',
        'priority': '1.0',
    })
    # Crawler page (all listings in one table)
    pages.append({
        'loc': BASE_URL + '/crawler-listings.html',
        'changefreq': 'daily',
        'priority': '0.9',
    })
    # Each listing as a filterable URL
    for i, l in enumerate(listings):
        prop = l.get('property') or l.get('property_name') or ''
        slug = prop.lower().replace(' ', '-')[:50]
        slug = ''.join(c for c in slug if c.isalnum() or c == '-') or f'listing-{i}'
        pages.append({
            'loc': f'{BASE_URL}/?id={i}',
            'changefreq': 'weekly',
            'priority': '0.6',
            'lastmod': (l.get('scraped_at') or '')[:10],
        })
    return pages

def write_sitemap(pages):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for p in pages:
        lines.append('  <url>')
        lines.append(f'    <loc>{p["loc"]}</loc>')
        lines.append(f'    <changefreq>{p["changefreq"]}</changefreq>')
        lines.append(f'    <priority>{p["priority"]}</priority>')
        if p.get('lastmod'):
            lines.append(f'    <lastmod>{p["lastmod"]}</lastmod>')
        lines.append('  </url>')
    lines.append('</urlset>')
    with open(SITEMAP_PATH, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    return len(pages)

def gen_dataset_json(listings):
    """Generate JSON-LD dataset schema for the main page."""
    areas = set()
    types = set()
    for l in listings:
        if l.get('property'): areas.add(l['property'])
        if l.get('property_type'): types.add(l['property_type'])
    return {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "LeadPilot - JB Rental Listings",
        "description": f"Johor Bahru rental property database with {len(listings)} listings across {len(areas)} properties. Updated daily from Facebook rental groups.",
        "url": BASE_URL,
        "dateModified": datetime.now().isoformat()[:10],
        "keywords": ["Johor Bahru", "JB rental", "property", "real estate", "Malaysia"],
        "variableMeasured": [
            {"@type": "PropertyValue", "name": "Rent (RM)", "description": "Monthly rental price in Malaysian Ringgit"},
            {"@type": "PropertyValue", "name": "Property Type", "description": "Condo, apartment, landed, room"},
            {"@type": "PropertyValue", "name": "Furnishing", "description": "Fully furnished, partially furnished, unfurnished"},
            {"@type": "PropertyValue", "name": "Rooms", "description": "Number of bedrooms"},
        ],
        "about": {
            "@type": "Thing",
            "name": "Johor Bahru Rental Properties",
            "sameAs": "https://en.wikipedia.org/wiki/Johor_Bahru"
        },
        "isAccessibleForFree": True,
        "distributor": {
            "@type": "Organization",
            "name": "LeadPilot",
            "url": BASE_URL
        }
    }

if __name__ == '__main__':
    listings = load_data()
    pages = gen_sitemap(listings)
    count = write_sitemap(pages)
    dataset = gen_dataset_json(listings)
    print(json.dumps(dataset, indent=2))
    print(f'\n✅ sitemap.xml generated: {count} URLs')
    print(f'📊 Dataset: {len(listings)} listings')
