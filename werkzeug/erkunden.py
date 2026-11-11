"""Sucht im öffentlichen BAFA-Wärmeerzeuger-Portal (WEP) die Datenschnittstelle der Wärmepumpen-Liste.
Schreibt alle Funde nach erkundung/ (HTML, JS-Fundstellen, Antworten auf Probe-Aufrufe)."""
import re, json, os, urllib.request, urllib.parse
BASIS = 'https://elan1.bafa.bund.de'
SEITE = BASIS + '/zvi-ui/wep/waermepumpen'
OUT = 'erkundung'; os.makedirs(OUT, exist_ok=True)
H = {'User-Agent': 'Mozilla/5.0 (waermepumpen-liste; oeffentliche Liste)', 'Accept': '*/*'}
def hol(url, daten=None, typ=None):
    h = dict(H)
    if typ: h['Content-Type'] = typ
    r = urllib.request.Request(url, data=daten, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=60) as a:
            return a.status, a.headers.get('Content-Type', ''), a.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type', ''), e.read()
    except Exception as e:
        return 0, '', str(e).encode()
bericht = []
s, t, b = hol(SEITE); html = b.decode('utf8', 'replace')
open(f'{OUT}/seite.html', 'w').write(html); bericht.append(f'SEITE {s} {t} {len(b)}')
skripte = set(re.findall(r'(?:src|href)="([^"]+\.js[^"]*)"', html))
funde = set()
for sk in sorted(skripte):
    url = urllib.parse.urljoin(SEITE, sk)
    s, t, b = hol(url); js = b.decode('utf8', 'replace')
    bericht.append(f'JS {s} {len(b)} {url}')
    name = re.sub(r'[^A-Za-z0-9._-]', '_', sk)[-80:]
    open(f'{OUT}/{name}', 'w').write(js)
    for m in re.finditer(r'["\'`]([^"\'`\s]{0,80}(?:zvi-api|/api/|wep|waermepumpe|anlage)[^"\'`\s]{0,120})["\'`]', js, re.I):
        funde.add(m.group(1))
    for m in re.finditer(r'.{0,120}zvi-api.{0,200}', js):
        funde.add('KONTEXT: ' + m.group(0))
open(f'{OUT}/funde.txt', 'w').write('\n'.join(sorted(funde)))
# Probe-Aufrufe naheliegender Pfade
proben = ['/zvi-api', '/zvi-api/', '/zvi-api/wep/waermepumpen', '/zvi-api/api/wep/waermepumpen', '/zvi-api/public/wep/waermepumpen',
          '/zvi-api/wep/waermepumpen?page=0&size=5', '/zvi-api/v3/api-docs', '/zvi-api/v2/api-docs', '/zvi-api/swagger-ui/index.html',
          '/zvi-api/actuator', '/zvi-api/wep/anlagen', '/zvi-api/api/waermepumpen']
for p in proben:
    s, t, b = hol(BASIS + p)
    bericht.append(f'PROBE {s} {t} {len(b)} {p} :: {b[:300]!r}')
open(f'{OUT}/bericht.txt', 'w').write('\n'.join(bericht))
print('\n'.join(bericht)); print('---- FUNDE ----'); print('\n'.join(sorted(funde))[:20000])
