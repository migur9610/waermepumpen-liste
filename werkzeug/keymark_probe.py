"""Einmalige Erkundung der Keymark-Datenbank (wird nach der Auswertung wieder gelöscht)."""
import re, subprocess, html
B = 'https://www.heatpumpkeymark.com/'
def get(u):
    r = subprocess.run(['curl', '-sSL', '--max-time', '60', '-A', 'Mozilla/5.0', u if u.startswith('http') else B + u.lstrip('/')], capture_output=True, text=True)
    return r.stdout
def tds(b): return re.findall(r'<td[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)
h = get('?type=109126'); m = tds(h)
print('Hersteller', len(m)); print([html.unescape(re.sub('<[^>]+>', '', t)).strip() for _, t in m][:400])
ziel = [x for x in m if 'vaillant' in x[1].lower()][:1]
for href, name in ziel:
    print('HREF', href)
    hb = get(html.unescape(href)); mm = tds(hb); print('Modelle', len(mm), [re.sub('<[^>]+>', '', t).strip() for _, t in mm[:15]])
    mh = get(html.unescape(mm[0][0])); print('MODELL-SEITE', len(mh))
    for lab, dat in re.findall(r'class="info-label">\s*<span>(.*?)</span>.*?class="info-data">(.*?)</div>', mh, re.S)[:20]: print('  I', lab.strip(), '=', re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', dat)).strip()[:80])
    ex = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>\s*(Export[^<]*)</a>', mh); print('EXPORT', ex)
    if ex:
        eb = get(html.unescape(ex[0][0])); dl = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>\s*Download\s*</a>', eb); print('DL', dl)
        if dl: c = get(html.unescape(dl[0])); print('CSV', len(c)); print(c[:4000])
