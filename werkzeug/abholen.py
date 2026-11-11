"""Abholdienst: holt die Wärmeerzeugerliste „Wärmepumpen“ aus dem öffentlichen BAFA-Wärmeerzeuger-Portal (WEP)
und legt sie kompakt unter daten/ ab. Läuft nachts über GitHub Actions (.github/workflows/abholen.yml).

Schnittstelle (vom Portal selbst genutzt, nicht offiziell dokumentiert):
  GET https://elan1.bafa.bund.de/zvi-api/wep/waermepumpen
      ?filter=foerderungAb=le="JJJJ-MM-TT";foerderungBis=ge="JJJJ-MM-TT"   (= „förderfähig am“ heute)
      &sortierung=markeHersteller,asc;uuid,asc&seite=N&anzahl=100            (anzahl höchstens 100)
Abruf mit curl (Python-urllib wird vom Portal nicht beantwortet)."""
import json, subprocess, time, datetime, hashlib, os, sys, urllib.parse

URL = 'https://elan1.bafa.bund.de/zvi-api/wep/waermepumpen'
PRO_SEITE = 100
ZIEL = 'daten'
# Felder in fester Reihenfolge (Kurzname für die Datei, Feld der BAFA-Antwort)
FELDER = [
    ('nr', 'anlagennummer'), ('id', 'uuid'), ('hersteller', 'markeHersteller'), ('geraet', 'geraetebezeichnung'),
    ('typ', 'pumpentyp'), ('quelle', 'waermequelle'), ('antrieb', 'antriebsart'), ('regelung', 'leistungsregelungArt'),
    ('verdichter', 'anzahlVerdichter'), ('km1', 'kaeltemittel1'), ('kmMenge1', 'mengeKaeltemittel1'),
    ('km2', 'kaeltemittel2'), ('kmMenge2', 'mengeKaeltemittel2'),
    ('etas35', 'etas35C'), ('prated35', 'heizleistungPrated35C'), ('pdesign35', 'heizleistungPdesignh35C'),
    ('etas55', 'etas55C'), ('prated55', 'heizleistungPrated55C'), ('pdesign55', 'heizleistungPdesignh55C'),
    ('scop', 'scop'), ('copAm7', 'copBeiAMinus7W35'), ('copA2', 'copBeiA2W35B0W35W10W35'), ('copA7', 'copBeiA7W35'),
    ('copA10', 'copBeiA10W35'), ('pElMax', 'maxElektrischeLeistungsaufnahme'), ('dT', 'temperaturdifferenz'),
    ('lwaAussen', 'schallemissionAussen'), ('lwaInnen', 'schallemissionInnen'),
    ('kuehlen', 'effizienzKuehlen'), ('pKuehl', 'kuehlleistung'), ('seer', 'seer'),
    ('netz', 'netzdienlichkeit'), ('netzArt', 'netzdienlichkeitArt'), ('abtauGeprueft', 'abtauungGeprueft'), ('abtauArt', 'abtauungArt'),
    ('einzelabnahme', 'einzelabnahme'), ('eeAnzeige', 'eeAnzeige'), ('wmz', 'waermemengenzaehler'),
    ('gtin', 'gtinEan'), ('artikel', 'artikelnummer'), ('web', 'webseite'),
]

def seite(nr, heute, versuche=4):
    filt = f'foerderungAb=le="{heute}";foerderungBis=ge="{heute}"'
    q = urllib.parse.urlencode({'filter': filt, 'sortierung': 'markeHersteller,asc;uuid,asc', 'seite': nr, 'anzahl': PRO_SEITE})
    for v in range(versuche):
        r = subprocess.run(['curl', '-4', '-sS', '--max-time', '60', '-H', 'Accept: application/json',
                            '-w', '\n%{http_code}', f'{URL}?{q}'], capture_output=True, text=True)
        rumpf, _, code = r.stdout.rpartition('\n')
        if code == '200':
            return json.loads(rumpf)
        print(f'Seite {nr}: HTTP {code or r.stderr.strip()} – Versuch {v + 1}', file=sys.stderr)
        time.sleep(10 * (v + 1))
    raise SystemExit(f'Seite {nr} nicht abrufbar – Abbruch, alte Daten bleiben stehen')

def main():
    heute = datetime.date.today().isoformat()
    erste = seite(0, heute)
    gesamt = erste['total']
    alle = list(erste['inhalt'])
    for n in range(1, (gesamt + PRO_SEITE - 1) // PRO_SEITE):
        time.sleep(1.0)  # das Portal schonen
        alle += seite(n, heute)['inhalt']
    # Plausibilität: Liste darf nicht plötzlich fast leer sein
    if len(alle) < 1000 or len(alle) < 0.95 * gesamt:
        raise SystemExit(f'Nur {len(alle)} von {gesamt} Einträgen – Abbruch, alte Daten bleiben stehen')
    neu_felder = sorted(set().union(*(a.keys() for a in alle)) - {f for _, f in FELDER})
    zeilen = [[a.get(f) for _, f in FELDER] for a in alle]
    inhalt = json.dumps(zeilen, ensure_ascii=False, separators=(',', ':'))
    pruef = hashlib.sha256(inhalt.encode()).hexdigest()[:16]
    os.makedirs(ZIEL, exist_ok=True)
    pfad_stand = f'{ZIEL}/stand.json'
    alt = json.load(open(pfad_stand)) if os.path.exists(pfad_stand) else {}
    geaendert = alt.get('pruefsumme') != pruef
    stand = {
        'quelle': 'BAFA Wärmeerzeuger-Portal (WEP), Liste Wärmepumpen – https://elan1.bafa.bund.de/zvi-ui/wep/waermepumpen',
        'foerderfaehigAm': heute,
        'abgerufen': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'datenStand': heute if geaendert else alt.get('datenStand', heute),
        'anzahl': len(zeilen),
        'pruefsumme': pruef,
        'unbekannteFelder': neu_felder,
    }
    if geaendert:
        daten = {k: stand[k] for k in ('quelle', 'foerderfaehigAm', 'datenStand', 'anzahl', 'pruefsumme')}
        daten['felder'] = [k for k, _ in FELDER]
        with open(f'{ZIEL}/waermepumpen.json', 'w', encoding='utf8') as f:
            f.write(json.dumps(daten, ensure_ascii=False, separators=(',', ':'))[:-1] + ',"zeilen":' + inhalt + '}')
    with open(pfad_stand, 'w', encoding='utf8') as f:
        json.dump(stand, f, ensure_ascii=False, indent=1)
    print(f'{len(zeilen)} Wärmepumpen, {"geändert" if geaendert else "unverändert"}, Prüfsumme {pruef}')
    if neu_felder:
        print('Neue Felder in der BAFA-Antwort:', neu_felder)

if __name__ == '__main__':
    main()
