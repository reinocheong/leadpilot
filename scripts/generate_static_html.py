#!/usr/bin/env python3
"""Pre-render first N property cards into index.html for AI crawlers (GPT, etc.).
JS still fetches full data from API for interactive users."""

import json, os, re, html as html_mod
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, 'data', 'rentals.json')
INDEX_PATH = os.path.join(ROOT, 'index.html')
PRERENDER_COUNT = 50

def esc(s):
    return html_mod.escape(str(s or ''), quote=True)

def fmt_rent(r):
    if not r:
        return ''
    n = re.sub(r'[^0-9]', '', str(r))
    if not n:
        return ''
    n = int(n)
    if n >= 1000:
        val = '%.1f' % (n / 1000)
        val = val.replace('.0', '')
        return 'RM' + val
    return 'RM' + str(n)

def time_ago(ts):
    if not ts:
        return ''
    try:
        d = datetime.strptime(str(ts)[:19], '%Y-%m-%d %H:%M:%S')
        mins = int((datetime.now() - d).total_seconds() / 60)
        if mins < 1: return '刚刚'
        if mins < 60: return '%d 分钟前' % mins
        if mins < 1440: return '%d 小时前' % (mins // 60)
        return '%d 天前' % (mins // 1440)
    except:
        return ''

def is_today(ts):
    if not ts:
        return False
    try:
        d = datetime.strptime(str(ts)[:19], '%Y-%m-%d %H:%M:%S')
        return d.date() == date.today()
    except:
        return False

def accent_class(prop_type, ptype):
    t = (prop_type or ptype or '').lower()
    if any(x in t for x in ['condo', 'apartment', 'studio']):
        return 'accent-condo'
    if any(x in t for x in ['landed', 'terrace', 'bungalow', 'semi']):
        return 'accent-landed'
    if 'room' in t:
        return 'accent-room'
    return 'accent-default'

def build_card(l):
    is_new = is_today(l.get('scraped_at'))
    post_text = l.get('post_text') or ''
    short = len(post_text) <= 80
    post_cls = '' if short else 'collapsed'
    post_click = '' if short else ' onclick="togglePost(this)"'

    chips = []
    if l.get('type'):
        chips.append('<span class="chip type-chip">%s</span>' % esc(l['type']))
    if l.get('property_type'):
        chips.append('<span class="chip">%s</span>' % esc(l['property_type']))
    if l.get('rooms'):
        chips.append('<span class="chip">%s</span>' % esc(l['rooms']))
    if l.get('furnishing'):
        chips.append('<span class="chip furnish-chip">%s</span>' % esc(l['furnishing']))
    if l.get('remark'):
        chips.append('<span class="chip">%s</span>' % esc(l['remark']))
    chips_html = '<div class="info-chips">%s</div>' % ''.join(chips) if chips else ''

    rent = fmt_rent(l.get('rent'))
    rent_tag = '<span class="rent-tag">%s</span>' % esc(rent) if rent else ''

    new_badge = '<span class="badge-new">NEW</span>' if is_new else ''

    initial = (l.get('agent') or '?')[0]
    phone_masked = l.get('phone') or ''

    agent_html = ''
    if l.get('agent') or phone_masked:
        phone_part = '<span class="agent-phone agent-phone-locked">\U0001f512 <span>%s</span></span>' % esc(phone_masked) if phone_masked else ''
        agent_name = '<span>%s</span>' % esc(l['agent']) if l.get('agent') else ''
        agent_html = ('<div class="agent-row">'
            '<span class="agent-avatar">%s</span>%s%s</div>') % (esc(initial), agent_name, phone_part)

    post_html = ''
    if post_text:
        post_html = '<div class="post-block %s"%s>%s</div>' % (post_cls, post_click, esc(post_text))

    accent = accent_class(l.get('property_type'), l.get('type'))
    prop_name = esc(l.get('property') or '(未识别)')

    return ('<div class="card %s">'
        '<div class="card-body">'
        '<div class="card-name">%s%s%s</div>%s%s%s'
        '<div class="card-foot"><span class="time">%s</span><span></span></div>'
        '</div></div>') % (
        accent, new_badge, prop_name, rent_tag,
        chips_html, agent_html, post_html,
        time_ago(l.get('scraped_at')))


def build_html():
    with open(DATA_PATH) as f:
        raw = json.load(f)

    listings = raw.get('listings', [])
    total = raw.get('total', len(listings))

    prerender = listings[:PRERENDER_COUNT]
    cards_html = '\n'.join(build_card(l) for l in prerender)

    with open(INDEX_PATH) as f:
        original = f.read()

    modified = original

    # Update JSON-LD dateModified
    modified = re.sub(
        r'"dateModified":\s*"[^"]*"',
        '"dateModified": "%s"' % date.today().isoformat(),
        modified
    )

    # Replace listings div content
    listings_start = '<div class="listings" id="listings">'
    listings_end = '</div>\n\n<p class="footnote"'
    start_idx = modified.find(listings_start)
    end_idx = modified.find(listings_end, start_idx)

    if start_idx != -1 and end_idx != -1:
        before = modified[:start_idx + len(listings_start)]
        after = modified[end_idx:]
        new_section = '%s\n<style>.skeleton{display:none!important}</style>\n%s' % (before, cards_html)
        modified = new_section + after

    with open(INDEX_PATH, 'w') as f:
        f.write(modified)

    print('Generated %s' % INDEX_PATH)
    print('  Pre-rendered: %d cards, Total in data: %d' % (PRERENDER_COUNT, total))

if __name__ == '__main__':
    build_html()
