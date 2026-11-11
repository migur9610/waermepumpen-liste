# Wärmepumpen-Liste (BAFA)

Automatisch abgeholte Kopie der öffentlichen **Wärmeerzeugerliste „Wärmepumpen“** aus dem
[BAFA-Wärmeerzeuger-Portal](https://elan1.bafa.bund.de/zvi-ui/wep/waermepumpen) – alle Geräte, die am Abrufdatum als förderfähig gelistet sind.

- `daten/waermepumpen.json` – die Liste (Spaltennamen in `felder`, Werte je Gerät in `zeilen`); wird nur bei Änderungen neu geschrieben
- `daten/stand.json` – letzter Abruf, Anzahl, Prüfsumme (wird täglich aktualisiert)
- Abruf täglich nachts über GitHub Actions (`.github/workflows/abholen.yml`, Skript `werkzeug/abholen.py`)

Verbindlich ist allein die Liste im BAFA-Portal zum Zeitpunkt der Antragstellung.
