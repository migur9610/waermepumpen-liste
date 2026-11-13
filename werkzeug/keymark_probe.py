"""Einmalige Erkundung der Keymark-Datenbank (wird nach der Auswertung wieder gelöscht)."""
import re, subprocess, sys
def get(u):
    r = subprocess.run(['curl', '-sSL', '--max-time', '60', '-A', 'Mozilla/5.0', '-w', '\n%{http_code} %{url_effective} %{content_type}', u], capture_output=True, text=True)
    body, _, kopf = r.stdout.rpartition('\n'); return body, kopf
for u in sys.argv[1:]:
    b, k = get(u)
    print('=====', u, '→', k, len(b))
    links = sorted(set(re.findall(r'(?:href|src|action|data-[a-z-]+)="([^"]+)"', b)))
    for l in links:
        if any(x in l.lower() for x in ('certified', 'export', 'csv', 'xls', 'api', 'json', 'download', 'manufacturer', 'product', 'heatpump', '.js')): print('  L', l[:200])
    for m in re.findall(r'(?:fetch|axios\.[a-z]+|\$\.(?:get|post|ajax))\(\s*[\'"`]([^\'"`]+)', b): print('  F', m[:200])
    for m in re.findall(r'https?://[a-z0-9.-]+/[^\s"\'<>]*', b):
        if 'api' in m or 'json' in m or 'export' in m: print('  U', m[:200])
    print(b[:1500].replace('\n', ' ')[:1500])
