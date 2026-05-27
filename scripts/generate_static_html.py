#!/usr/bin/env python3
"""Pre-render all property cards into index.html for AI crawlers (GPT, etc.)."""

import json, os, re, html as html_mod
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, 'data', 'rentals.json')
INDEX_PATH = os.path.join(ROOT, 'index.html')

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
        now = datetime.now()
        mins = int((now - d).total_seconds() / 60)
        if mins < 1:
            return '刚刚'
        if mins < 60:
            return '%d 分钟前' % mins
        if mins < 1440:
            return '%d 小时前' % (mins // 60)
        return '%d 天前' % (mins // 1440)
    except Exception:
        return ''

def is_today(ts):
    if not ts:
        return False
    try:
        d = datetime.strptime(str(ts)[:19], '%Y-%m-%d %H:%M:%S')
        return d.date() == date.today()
    except Exception:
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

    chips_html = ''
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
    if chips:
        chips_html = '<div class="info-chips">' + ''.join(chips) + '</div>'

    rent = fmt_rent(l.get('rent'))
    rent_tag = ''
    if rent:
        rent_tag = '<span class="rent-tag">%s</span>' % esc(rent)

    new_badge = ''
    if is_new:
        new_badge = '<span class="badge-new">NEW</span>'

    initial = (l.get('agent') or '?')[0]

    agent_html = ''
    phone_masked = l.get('phone') or ''
    if l.get('agent') or phone_masked:
        phone_part = ''
        if phone_masked:
            phone_part = '<span class="agent-phone agent-phone-locked">\U0001f512 <span>%s</span></span>' % esc(phone_masked)
        agent_name = ''
        if l.get('agent'):
            agent_name = '<span>%s</span>' % esc(l['agent'])
        agent_html = '''<div class="agent-row">
        <span class="agent-avatar">%s</span>
        %s
        %s
      </div>''' % (esc(initial), agent_name, phone_part)

    post_html = ''
    if post_text:
        post_html = '<div class="post-block %s"%s>%s</div>' % (post_cls, post_click, esc(post_text))

    accent = accent_class(l.get('property_type'), l.get('type'))
    prop_name = esc(l.get('property') or '(未识别)')

    blob_parts = '|'.join(str(v or '') for v in [
        l.get('property'), l.get('agent'), l.get('property_type'),
        l.get('type'), l.get('remark'), l.get('furnishing'), l.get('post_text')
    ]).lower()
    search_attr = esc(blob_parts)
    tag_attr = esc(l.get('property') or '')

    card_css_cls = 'card ' + accent
    html = '''<div class="%s" data-search="%s" data-property="%s">
    <div class="card-body">
      <div class="card-name">
        %s
        %s
        %s
      </div>
      %s
      %s
      %s
      <div class="card-foot">
        <span class="time">%s</span>
        <span></span>
      </div>
    </div>
  </div>''' % (
        card_css_cls, search_attr, tag_attr,
        new_badge, prop_name, rent_tag,
        chips_html,
        agent_html,
        post_html,
        time_ago(l.get('scraped_at'))
    )
    return html


def build_html():
    with open(DATA_PATH) as f:
        raw = json.load(f)

    listings = raw.get('listings', [])
    total = raw.get('total', len(listings))
    today_new = raw.get('today_new', 0)
    top_properties = raw.get('top_properties', [])
    updated_at = raw.get('updated_at', '')

    cards_html = '\n'.join(build_card(l) for l in listings)

    data_json = json.dumps({
        'total': total,
        'today_new': today_new,
        'top_properties': top_properties,
        'listings': listings,
        'updated_at': updated_at
    }, ensure_ascii=False)

    with open(INDEX_PATH) as f:
        original = f.read()

    modified = original

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
        
        new_listings_section = '%s\n<style>.skeleton{display:none!important}</style>\n%s' % (before, cards_html)
        modified = new_listings_section + after
    
    # Add inline data script before </body>
    data_script = '<script id="__INITIAL_DATA__" type="application/json">%s</script>\n</body>' % data_json
    modified = modified.replace('</body>', data_script)

    # Replace loadPreview function
    old_lp = '''async function loadPreview() {
  const r = await fetch(AUTH_URL + '/preview');
  DATA = await r.json();
  if (DATA.error) throw new Error(DATA.error);
  DATA.preview = true;
  renderStats();
  renderTags();
  filter();
}'''
    
    new_lp = '''async function loadPreview() {
  const dataEl = document.getElementById('__INITIAL_DATA__');
  if (dataEl) {
    try {
      DATA = JSON.parse(dataEl.textContent);
      DATA.preview = true;
      document.querySelectorAll('.card').forEach(function(c) { c.style.display = ''; });
      document.getElementById('previewBar').classList.remove('hidden');
      document.getElementById('previewCount').textContent = DATA.total + ' \u5957\u623f\u6e90';
      renderStats();
      renderTags();
      filter();
      return;
    } catch(e) {}
  }
  const r = await fetch(AUTH_URL + '/preview');
  DATA = await r.json();
  if (DATA.error) throw new Error(DATA.error);
  DATA.preview = true;
  renderStats();
  renderTags();
  filter();
}'''
    modified = modified.replace(old_lp, new_lp)

    # Replace renderListings to add preview show/hide mode
    old_rl_start = '''function renderListings(q) {
  let items = DATA.listings;
  if (activeTag) items = items.filter(l => (l.property || '').includes(activeTag));
  if (q) {
    items = items.filter(l => {
      const blob = [l.property, l.agent, l.property_type, l.type, l.remark, l.furnishing, l.post_text].join('|').toLowerCase();
      return blob.includes(q);
    });
  }

  if (!items.length) {
    document.getElementById('listings').innerHTML = '<div class="empty">没有匹配的房源</div>';
    return;
  }

  const html = items.map(l => {'''

    new_rl_start = '''function renderListings(q) {
  // Preview mode with pre-rendered cards: use show/hide
  if (DATA.preview && document.querySelectorAll('.card').length > 0) {
    var cards = document.querySelectorAll('.card');
    var shown = 0;
    cards.forEach(function(c) {
      var blob = c.dataset.search || '';
      var prop = c.dataset.property || '';
      var match = true;
      if (activeTag && prop.indexOf(activeTag) === -1) match = false;
      if (q && blob.indexOf(q) === -1) match = false;
      c.style.display = match ? '' : 'none';
      if (match) shown++;
    });
    document.getElementById('previewCount').textContent = shown + ' \u5957\u623f\u6e90';
    return;
  }

  let items = DATA.listings;
  if (activeTag) items = items.filter(l => (l.property || '').includes(activeTag));
  if (q) {
    items = items.filter(l => {
      const blob = [l.property, l.agent, l.property_type, l.type, l.remark, l.furnishing, l.post_text].join('|').toLowerCase();
      return blob.includes(q);
    });
  }

  if (!items.length) {
    document.getElementById('listings').innerHTML = '<div class="empty">没有匹配的房源</div>';
    return;
  }

  const html = items.map(l => {'''

    modified = modified.replace(old_rl_start, new_rl_start)

    with open(INDEX_PATH, 'w') as f:
        f.write(modified)

    print('Generated %s' % INDEX_PATH)
    print('  Cards: %d, Total: %d, New: %d' % (len(listings), total, today_new))
    print('  Updated_at: %s' % updated_at)


if __name__ == '__main__':
    build_html()
