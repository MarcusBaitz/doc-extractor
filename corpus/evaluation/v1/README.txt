SUBSTRAKT / MISTRAL - SYNTHETISCHER TESTDATENSATZ V1
Erstellt am 14.10.2026. Keine echten Kundendokumente, keine API-Aufrufe.

UMFANG
84 PDF-Dokumente, 98 Seiten: 60 Grundbelege und 24 abgeleitete Scanvarianten.
Sechs Layoutfamilien, zehn Grundbelege je Familie:
A Klassische Rechnung
B Rechnung mit Seitenleiste
C Feldformular
D Mehrseitige Abrechnung (Endbetrag auf Seite 2)
E Gutschrift als Brief (negative Beträge, Bezug auf eine ältere Rechnung)
F Rechnung mit englischen Feldnamen (USD, englische Zahlenschreibweise)

Neun Sollfelder pro Dokument (756 Feldinstanzen, davon 18 ausdrücklich absent):
belegnummer, belegdatum, gesamtbetrag, nettobetrag, steuerbetrag,
waehrung, ust_idnr, dokumentart, absender.
Die vier Felder des bisherigen Benchmarks sind vollständig enthalten.

DATENSATZTEILE - VOR DEM TEST FESTLEGEN
setup:          24 Dateien / 18 Grundbelege, Familien A-C.
known_layout:   18 Dateien / 12 andere Grundbelege, dieselben Familien A-C.
unseen_layout:  42 Dateien / 30 Grundbelege, ausschließlich Familien D-F.

Nur setup zur Anpassung von Prompts, Regeln und Regionen verwenden.
known_layout misst Wiederverwendung bereits eingerichteter Vorlagen.
unseen_layout misst neue Layoutfamilien; hierfür keine Testvorlagen einrichten.
Ein Grundbeleg und ALLE seine Varianten bleiben in demselben Teil.
Gruppierungsschlüssel ist group_id. Ergebnisse auch je Grundbeleg und Familie
betrachten: Scanvarianten sind keine statistisch unabhängigen Beobachtungen.
Nach Optimierung anhand der Testergebnisse gilt dieser Testsatz als verbraucht.

EINGABEN UND ANTWORTEN STRIKT TRENNEN
inputs/ enthält ausschließlich die zu verarbeitenden PDFs.
ground_truth/expected.jsonl enthält die Sollwerte und Fundstellen.
manifest.json enthält IDs, Dateipfade, Hashes, Gruppierung und Varianten.
field-schema.json ist das gemeinsame Extraktionsschema für beide Verfahren.
Keine Sollwerte, Generatorparameter oder Musterantworten an Modelle senden.
Nur Dokumentdatei, vereinbartes Feldschema und einen festen Prompt übergeben.

SOLLDATEN
Jede Zeile von expected.jsonl gehört zu genau einem Dokument.
fields.<name>.value: normalisierter Sollwert als String oder null.
fields.<name>.printed: tatsächlich gedruckte Schreibweise oder null.
fields.<name>.status: present oder absent.
fields.<name>.locators: Seite (0-basiert), bbox=[x0,y0,x1,y1], Punkte,
Ursprung oben links. Mehrfach gedruckte Werte können mehrere Fundstellen haben.
Die Boxen sind Schrift-/Layoutboxen, keine pixelgenauen Glyphenmasken.
Bei gedrehten Scans wurden die Boxen geometrisch mitgedreht; durch Rasterrundung
sind kleine Abweichungen möglich. Sie sind nicht aus einem OCR-Modell abgeleitet.

Die Sollwerte kommen direkt aus den Quelldaten. Geldbeträge werden mit Decimal
berechnet; Steuer wird je Dokument auf Cent gerundet. Negative Endbeträge und
Steuerbeträge der Gutschriften sind ausdrücklich so gedruckt.
Alle Firmen, Adressen und Kennungen sind synthetisch. Die USt-IDs müssen nicht
die Prüfzifferregeln erfüllen: hier zählt Lesen, nicht steuerliche Validierung.
Absender statt Empfänger; Belegdatum statt Lieferdatum; Endbetrag statt
Einzelpreis, Steuer oder Zwischensumme. Fehlende Werte müssen null bleiben.
Die Gutschrift-Belegnummer darf nicht durch die Nummer der alten Rechnung
ersetzt werden. Dokumentart wird als Rechnung oder Gutschrift normalisiert.

VARIANTEN
digital: PDF mit auswählbarem Text.
scan: 150 dpi, 1,7 Grad Drehung, Rauschen und reduzierter Kontrast.
photo: 110 dpi, -2,6 Grad Drehung, stärkeres Rauschen, Schattenverlauf,
leichte Unschärfe. Trotz des Namens eine simulierte Verschlechterung, kein Foto.
scan und photo sind reine Bild-PDFs ohne versteckten Text.
Digital-PDFs und Scan-PDFs getrennt auswerten. Ein Gesamtergebnis vermischt
direktes Textlesen und OCR. Keine Behauptung über OCR aus Digital-PDFs ableiten.

VORHERSAGEN SPEICHERN
Eine JSON-Zeile je Dokument, zum Beispiel (Formatbeispiel, keine Sollantwort):
{"id":"A01_digital","fields":{"belegnummer":null,"belegdatum":null,"gesamtbetrag":null,"ust_idnr":null},"review_fields":["belegnummer","belegdatum","gesamtbetrag","ust_idnr"]}

Für Beträge Strings verwenden, z.B. "1234.56". Schema verlangt Strings/null.
review_fields enthält Felder, die tatsächlich zur Kontrolle vorgelegt würden.
Für jede Engine eine eigene predictions.jsonl erzeugen. Modellversion,
Commit, Prompt, Startzeit, Laufzeit und API-Verbrauch separat protokollieren.
Für den reinen Genauigkeitsvergleich sind review_fields optional. Die Metrik
incorrect_without_review unterstellt sonst, dass jeder nichtleere Wert ohne
Prüfmarkierung übernommen würde; sie ist keine gemessene menschliche Fehlerrate.

AUSWERTUNG - PYTHON, KEINE ZUSATZPAKETE ERFORDERLICH
python evaluate.py predictions.jsonl --split unseen_layout --output scores.json
Standard: die bisherigen vier Felder Belegnummer, Belegdatum, Gesamtbetrag, USt-ID.
Alle neun Felder:
python evaluate.py predictions.jsonl --fields belegnummer,belegdatum,gesamtbetrag,nettobetrag,steuerbetrag,waehrung,ust_idnr,dokumentart,absender --output scores-all.json

Das Skript zählt fehlende Dokumente und fehlende Feldschlüssel als Fehler.
Ein ausdrücklich geliefertes null ist nur bei einem fehlenden Sollwert richtig.
Datumsschreibweisen und Dezimal-/Tausendertrennzeichen werden vereinheitlicht.
Vorzeichen und abweichende Ziffern werden NICHT toleriert. Belegnummern werden
streng verglichen. Es gibt keine unscharfe Bewertung richtiger Feldwerte.
Ergebnisse: gesamt, je Split, Familie und Variante; vorhandene und fehlende
Felder separat; vollständig korrekte Dokumente und falsch ergänzte Angaben.

QUALITÄTSPRÜFUNG
validation.json enthält Umfang und Prüfergebnis.
Alle 84 Dateien: Hash, Seitenzahl, Betragsgleichung und Koordinatengrenzen geprüft.
Alle Digital-PDFs: gedruckte Sollwerte unabhängig mit pdfplumber ausgelesen.
Alle Bild-PDFs: fehlender Textlayer bestätigt.
Visuelle Stichprobe: jede Layoutfamilie, Folgeseite, fehlende Felder und Scan.
Evaluator-Tests: python -m unittest test_evaluate.py

REPRODUKTION
tools/generate.py erzeugt dieselben Dokumente mit Seed 20261014.
Python 3.12 und die Versionen in tools/requirements-generation.txt verwenden.
python tools/generate.py --output NEUER_LEERER_ORDNER
Der Generator erzeugt PDFs, Manifest, Sollwerte, Schema und Validierungsdatei;
Dokumentation, Vorschau und Evaluator werden nicht neu erzeugt.

GRENZEN
Dies ist ein synthetischer Regressionstest, keine repräsentative Feldstudie.
Ein gemeinsamer Generator, ähnliche Schrift und ähnliche Tabellenstruktur
begrenzen die Vielfalt auch zwischen den sechs Layoutfamilien.
Keine echte Handschrift, keine echten Kameraperspektiven, keine beschädigten
Dateien, keine verschachtelten Tabellen, keine Passwörter, keine realen Stempel.
Für einen Produktionseinsatz später separat echte freigegebene Belege ergänzen.
Dieser Datensatz ist größer und schwieriger als der erste Korpus, aber eine
100-Prozent-Quote wäre weiterhin kein Beweis für allgemeine Zuverlässigkeit.

HERKUNFT
Dokumente, Quelldaten und Generator wurden für diese Aufgabe neu erstellt.
Keine extern beschafften Dokumente und keine personenbezogenen Kundendaten.
Der Datensatz enthält keine Zugangsdaten. Es wurden keine Daten an Mistral gesendet.
