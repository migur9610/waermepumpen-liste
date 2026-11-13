"""Abholdienst Herstellerdaten: zertifizierte Datenblattwerte der Luft/Wasser-Wärmepumpen aus der öffentlichen
Heat-Pump-KEYMARK-Datenbank (https://keymark.eu/en/products/heatpumps/certified-products, eingebettet von heatpumpkeymark.com).

Ablauf: Liste der Zertifikatsinhaber → je Inhaber (nur große, in Deutschland verbreitete Hersteller, siehe HERSTELLER) die Untertypen →
je Untertyp die Seite (Wärmequelle, Kältemittel, Füllmenge, Zertifizierungsdatum) und der CSV-Export aller Modelle.
Nur Außenluft/Wasser. Schon geholte Untertypen werden erst nach ALTER_TAGE neu geholt (das Portal schonen, Lauf kurz halten).

Werte je Modell (Kurzname → Bedeutung, Codes aus dem Keymark-CSV):
  EN 14511-2, Prüfpunkt A7 (Klima-Code 10), Vorlauf 35 °C (Temperatur-Code 4) bzw. 55 °C (Code 5): Heizleistung _001, COP _003
  EN 14825, mittleres Klima (Code 2): ηs _001, Prated _002, SCOP _003, Tbiv _004, TOL _005,
     Teillastpunkte A−7/+2/+7/+12: Pdh _008/_010/_012/_014, COPd _009/_011/_013/_015
  EN 12102-1: Schallleistung außen _002 (mittleres Klima, 35 °C)
Ergebnis: daten/keymark_lw.json (felder + zeilen, wie die BAFA-Liste) und daten/keymark_stand.json (Prüfsumme)."""
import csv, datetime, hashlib, html, io, json, os, re, subprocess, sys, time

B = 'https://www.heatpumpkeymark.com'
ZIEL = 'daten'
DATEI = f'{ZIEL}/keymark_lw.json'
STAND = f'{ZIEL}/keymark_stand.json'
ALTER_TAGE = 60                      # Untertypen nach so vielen Tagen neu holen (Änderungen, neue Modelle)
ZEIT_MAX = int(os.environ.get('KM_ZEIT', 40 * 60))   # höchstens so lange je Lauf, Rest beim nächsten Lauf
UT_MAX = int(os.environ.get('KM_MAX', 100000))       # zum Erproben: höchstens so viele Untertypen
# Zertifikatsinhaber (Teil des Namens, klein) – große, in Deutschland verbreitete Hersteller
HERSTELLER = ['vaillant', 'viessmann', 'stiebel', 'bosch thermotechnik', 'buderus', 'wolf gmbh', 'nibe', 'daikin', 'mitsubishi electric',
              'panasonic', 'samsung', 'lg electronics', 'fujitsu', 'toshiba', 'hitachi', 'johnson controls', 'weishaupt', 'ait-deutschland',
              'glen dimplex', 'remeha', 'brötje', 'de dietrich', 'kermi', 'lambda', 'ochsner', 'hoval', 'waterkotte', 'wolf', 'haier', 'midea',
              'gree', 'ariston', 'elco', 'idm', 'heliotherm', 'windhager', 'tecalor', 'oventrop', 'rotex', 'bosch home comfort', 'junkers']
FELDER = ['ut', 'inhaber', 'serie', 'modell', 'km', 'kmMenge', 'zert',
          'p7_35', 'cop7_35', 'p7_55', 'cop7_55',
          'etas35', 'prated35', 'scop35', 'tbiv35', 'tol35', 'pdhM7_35', 'copdM7_35', 'pdh2_35', 'copd2_35', 'pdh7_35', 'copd7_35', 'pdh12_35', 'copd12_35',
          'etas55', 'prated55', 'scop55', 'tbiv55', 'tol55', 'pdhM7_55', 'copdM7_55', 'pdh2_55', 'copd2_55', 'pdh7_55', 'copd7_55', 'pdh12_55', 'copd12_55',
          'lwa']
EN14825 = {'001': 'etas', '002': 'prated', '003': 'scop', '004': 'tbiv', '005': 'tol', '008': 'pdhM7', '009': 'copdM7', '010': 'pdh2', '011': 'copd2',
           '012': 'pdh7', '013': 'copd7', '014': 'pdh12', '015': 'copd12'}
VL = {'4': '35', '5': '55'}


def hole(pfad, versuche=3):
    u = pfad if pfad.startswith('http') else B + '/' + html.unescape(pfad).lstrip('/')
    for v in range(versuche):
        r = subprocess.run(['curl', '-sSL', '--max-time', '90', '-A', 'Mozilla/5.0 (Abholdienst waermepumpen-liste)', '-w', '\n%{http_code}', u],
                           capture_output=True, text=True, errors='replace')
        rumpf, _, code = r.stdout.rpartition('\n')
        if code == '200' and rumpf:
            return rumpf
        print(f'HTTP {code or r.stderr.strip()[:80]} – Versuch {v + 1}: {u[:120]}', file=sys.stderr)
        time.sleep(5 * (v + 1))
    return None


def links(b):
    return [(h, html.unescape(re.sub(r'<[^>]+>', '', t)).strip()) for h, t in re.findall(r'<td[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', b or '', re.S)]


def zahl(x):
    try:
        return float(str(x).replace(',', '.'))
    except ValueError:
        return None


def untertyp(href, inhaber, serie):
    b = hole(href)
    if not b: return None
    info = {}
    for lab, dat in re.findall(r'class="info-label">\s*<span>(.*?)</span>.*?class="info-data">(.*?)</div>', b, re.S):
        lab = lab.strip()
        if lab not in info: info[lab] = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', dat))).strip()
    art = info.get('Heat Pump Type', '')
    if 'air/water' not in art.lower() or 'exhaust' in art.lower(): return {'zeilen': [], 'art': art}
    ex = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>\s*Export[^<]*CSV[^<]*</a>', b)
    if not ex: return None
    eb = hole(ex[0])
    dl = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>\s*Download\s*</a>', eb or '')
    c = hole(dl[0]) if dl else None
    if not c: return None
    km = info.get('Refrigerant', '').replace(' ', '')
    m = re.match(r'([\d.,]+)', info.get('Mass of Refrigerant', ''))
    menge = zahl(m.group(1)) if m else None
    zert = '-'.join(reversed(info.get('Certification Date', '').split('.'))) or None
    mod = {}
    for z in csv.DictReader(io.StringIO(c)):
        d = mod.setdefault(z['modelID'], {})
        n, w, t, k = z['varName'], z['value'], z['temperature'], z['climate']
        if n == 'title': d['modell'] = w.strip()
        elif n.startswith('EN14511_2_') and k == '10' and t in VL:
            if n.endswith('_001'): d['p7_' + VL[t]] = zahl(w)
            elif n.endswith('_003'): d['cop7_' + VL[t]] = zahl(w)
        elif n.startswith('EN14825_') and k == '2' and t in VL and n[-3:] in EN14825:
            d[EN14825[n[-3:]] + VL[t]] = zahl(w)
        elif n == 'EN12102_1_002' and k == '2' and t == '4': d['lwa'] = zahl(w)
    sid = re.search(r'subtype%5D=(\d+)', ex[0]).group(1)
    zeilen = []
    for d in mod.values():
        if not d.get('modell'): continue
        d.update(ut=sid, inhaber=inhaber, serie=serie, km=km, kmMenge=menge, zert=zert)
        zeilen.append([d.get(f) for f in FELDER])
    return {'zeilen': zeilen, 'art': art, 'sid': sid}


def main():
    t0 = time.time(); heute = datetime.date.today().isoformat()
    alt = json.load(open(DATEI, encoding='utf8')) if os.path.exists(DATEI) else {}
    ut = alt.get('untertypen', {})           # Schlüssel = Link des Untertyps → {inhaber, serie, geholt, art, n}
    zeilen = {}
    for z in alt.get('zeilen', []): zeilen.setdefault(z[0], []).append(z)
    liste = links(hole('/?type=109126'))
    if len(liste) < 50: raise SystemExit(f'Nur {len(liste)} Zertifikatsinhaber gefunden – Seitenaufbau geändert? Alte Daten bleiben stehen')
    wahl = [(h, n) for h, n in liste if any(x in n.lower() for x in HERSTELLER)]
    print(f'{len(liste)} Zertifikatsinhaber, davon {len(wahl)} ausgewählt')
    neu = geholt = 0; gesehen = set()
    for h, inh in wahl:
        if time.time() - t0 > ZEIT_MAX or geholt >= UT_MAX: break
        for uh, serie in links(hole(h)):
            if serie == inh or not serie: continue
            key = re.sub(r'&(amp;)?cHash=[0-9a-f]+', '', html.unescape(uh)); gesehen.add(key)
            e = ut.get(key)
            if e and (datetime.date.fromisoformat(heute) - datetime.date.fromisoformat(e['geholt'])).days < ALTER_TAGE: continue
            if time.time() - t0 > ZEIT_MAX or geholt >= UT_MAX: break
            time.sleep(0.5); r = untertyp(uh, inh, serie); geholt += 1
            if r is None: print('nicht abrufbar:', inh, '|', serie, file=sys.stderr); continue
            if e and e.get('sid'): zeilen.pop(e['sid'], None)
            if r.get('sid'): zeilen[r['sid']] = r['zeilen']
            ut[key] = {'inhaber': inh, 'serie': serie, 'geholt': heute, 'art': r['art'], 'sid': r.get('sid'), 'n': len(r['zeilen'])}
            neu += len(r['zeilen'])
    fertig = time.time() - t0 <= ZEIT_MAX and geholt < UT_MAX
    if fertig:  # zurückgezogene Untertypen entfernen (nur nach vollständigem Durchlauf)
        for k in [k for k in ut if k not in gesehen and any(ut[k]['inhaber'] == n for _, n in wahl)]:
            zeilen.pop(ut[k].get('sid'), None); del ut[k]
    alle = sorted((z for zz in zeilen.values() for z in zz), key=lambda z: (z[1], z[2], z[3]))
    inhalt = json.dumps(alle, ensure_ascii=False, separators=(',', ':'))
    pruef = hashlib.sha256(inhalt.encode()).hexdigest()[:16]
    stand_alt = json.load(open(STAND)) if os.path.exists(STAND) else {}
    geaendert = stand_alt.get('pruefsumme') != pruef
    os.makedirs(ZIEL, exist_ok=True)
    stand = {'quelle': 'Heat Pump KEYMARK – zertifizierte Produkte, https://keymark.eu/en/products/heatpumps/certified-products',
             'abgerufen': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
             'datenStand': heute if geaendert else stand_alt.get('datenStand', heute), 'anzahl': len(alle), 'pruefsumme': pruef,
             'untertypen': len(ut), 'vollstaendig': fertig}
    daten = {k: stand[k] for k in ('quelle', 'datenStand', 'anzahl', 'pruefsumme')}
    daten.update(felder=FELDER, untertypen=ut)
    with open(DATEI, 'w', encoding='utf8') as f:
        f.write(json.dumps(daten, ensure_ascii=False, separators=(',', ':'))[:-1] + ',"zeilen":' + inhalt + '}')
    json.dump(stand, open(STAND, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print(f'{geholt} Untertypen geholt, {neu} Modelle neu/aktualisiert, gesamt {len(alle)} Modelle, {"vollständig" if fertig else "Fortsetzung beim nächsten Lauf"}, {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
