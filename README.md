# Wärmepumpen-Liste (BAFA)

Automatisch abgeholte Kopie der öffentlichen **Wärmeerzeugerliste „Wärmepumpen“** aus dem
[BAFA-Wärmeerzeuger-Portal](https://elan1.bafa.bund.de/zvi-ui/wep/waermepumpen) – alle Geräte, die am Abrufdatum als förderfähig gelistet sind.

- `daten/waermepumpen.json` – die Liste (Spaltennamen in `felder`, Werte je Gerät in `zeilen`); wird nur bei Änderungen neu geschrieben
- `daten/stand.json` – letzter Abruf, Anzahl, Prüfsumme (wird täglich aktualisiert)
- Abruf täglich nachts über GitHub Actions (`.github/workflows/abholen.yml`, Skript `werkzeug/abholen.py`)

Verbindlich ist allein die Liste im BAFA-Portal zum Zeitpunkt der Antragstellung.

## Keymark-Herstellerdaten (Luft/Wasser)

Zertifizierte Datenblattwerte aus der öffentlichen [Heat-Pump-KEYMARK-Datenbank](https://keymark.eu/en/products/heatpumps/certified-products)
für die großen, in Deutschland verbreiteten Hersteller (Liste `HERSTELLER` in `werkzeug/keymark.py`), nur Außenluft/Wasser.

- `daten/keymark_lw.json` – je Modell: Kältemittel und Füllmenge, EN 14511 A7/W35 und A7/W55 (Leistung, COP), EN 14825 mittleres Klima
  (ηs, Prated, SCOP, Tbiv, TOL, Teillastpunkte A−7/+2/+7/+12) bei 35 und 55 °C, Schallleistung außen
- `daten/keymark_stand.json` – letzter Abruf, Anzahl, Prüfsumme, ob der Durchlauf vollständig war
- Abruf täglich nachts (`.github/workflows/keymark.yml`), je Lauf höchstens 40 min; schon geholte Baureihen erst nach 60 Tagen neu.
  Der erste vollständige Durchlauf braucht deshalb einige Nächte.

