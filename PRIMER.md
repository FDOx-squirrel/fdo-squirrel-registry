# Primer — Aufbau der FDOx-Registry

Arbeitsplan für `fdo-squirrel-registry`: eine Registry, die auf Zenodo
publizierte FDOx-Pakete erntet, ihre RDF-Beschreibungen zu einem DCAT-Katalog
bündelt, den Bundle an CIDOC CRM verankert und SHACL-validiert, und ihn als
Filter- und SPARQL-Seite über GitHub Pages ausliefert.

**Ort.** <https://github.com/Research-Squirrel-Engineers/fdo-squirrel-registry/blob/main/PRIMER.md>

**So wird es benutzt.** Es wird in jedem Chat vollständig hochgeladen. Danach
genügt ein Satz: „Wir machen S3." Teil A gilt immer, Teil B ist die Übersicht,
Teil C beschreibt den einzelnen Schritt. Die Statusspalte in Teil B und die
Beschlusslage in A4 werden nach jedem Chat nachgeführt, damit spätere Chats den
aktuellen Stand sehen.

---

# Teil A — Immer gültig

## A1. Ausgangslage

**Zwei Repos, eine Kette.** `fdo-squirrel` macht *ein* Paket maschinenlesbar,
`fdo-squirrel-registry` macht *viele* auffindbar.

| Repo | Rolle | Stand |
|---|---|---|
| `Research-Squirrel-Engineers/fdo-squirrel` | FDOx-Referenzimplementierung, ZIP → `fdo-metadata.ttl` | v0.1, publiziert (Squirrel Papers 8(1) §4, DOI 10.5281/zenodo.18441772) |
| `Research-Squirrel-Engineers/fdo-squirrel-registry` | dieses Repo: Ernte, Bundle, Gate, Seite | leer, beginnt mit S1 |
| `SquirrelBase` (Wikibase) | semantischer Meta-Hub für 3D-Objekte, hält die FDO-URL je Objekt | produktiv, außerhalb dieses Plans |

**Was `fdo-squirrel` heute erzeugt** (geprüft am Repo-Stand und an
`fdo/fdo-metadata.ttl`, 2026-09-03):

- Das FDO ist Subjekt unter seiner DOI, typisiert als `dcat:Dataset` **und**
  `fdo:3DDataFDO` bzw. `fdo:SoftwareFDO`.
- Jede Datei im ZIP wird eine `dcat:Distribution` mit `dcat:byteSize`,
  `dcat:mediaType`, `fdo:sha256`, `fdo:path` und `fdo:role`
  (`model` | `metadata` | `documentation`).
- Namensräume: `dcat:`, `dct:`, `schema:`, `xsd:`, `fdo:` =
  `https://w3id.org/fdo-squirrel/`.
- Nebenausgaben je Paket: `rdf_modelling_report.json` und `.html`.

**Befunde am echten Paket** (geprüft 2026-09-03 an `fdo-metadata.ttl` aus
Record 18724635, 163 Tripel, aus `CO074-148----.zip`). Drei der vier Befunde
des Auftaktchats stammten aus dem Demo-TTL in `fdo-squirrel/fdo/` und waren
falsch — sie sind hier korrigiert, nicht gelöscht:

1. **Das TTL liegt *im* ZIP, nicht neben ihm.** Ein FDOx-Paket ist genau eine
   Datei im Record: das ZIP mit Daten *und* Metadaten (hier ≈ 300 MB, das TTL
   darin 10 073 Byte). Ein Ernter, der nur die Dateiliste des Records nach
   `fdo-metadata.ttl` durchsucht, findet nichts und meldet den ganzen Bestand
   als „übersprungen". Das ist der Grund für die vier Bezugswege in S2.
2. **Paketrelative `urn:`-IRIs — bestätigt, und eine Familie mehr.**
   11 × `urn:fdo-squirrel:dist/<sha-prefix>`, 11 × `urn:fdo-squirrel:content/<pfad>`
   als `dcat:accessURL`, dazu 2 × `urn:fdo-squirrel:person/<16 hex>`. Alle drei
   sind innerhalb eines Pakets eindeutig und über Pakete hinweg nicht: zwei FDOs
   mit einer Datei `CITATION.cff` kollidieren im accessURL. Ein Bundle, das die
   TTL nur aneinanderhängt, verschmilzt fremde Dateien zu einem Knoten. Das ist
   der Grund für die IRI-Umschreibung in S4 — die einzige erlaubte.
3. **~~Kein CIDOC CRM.~~ Korrigiert 2026-09-03: CRM ist da, aber mit
   abgekürzten Klassen-IRIs.** Das FDO trägt `crm:E73` und `crmdig:D1`, jede
   Distribution `crmdig:D9`. Die offiziellen IRIs heissen
   `E73_Information_Object`, `D1_Digital_Object`, `D9_Data_Object`; die
   verkürzten Formen lösen nicht auf und treffen kein Vokabular. S3 ist damit
   nicht mehr „CRM einführen", sondern „IRIs geradeziehen und die Abbildung
   vervollständigen" — die kleinere, aber unangenehmere Aufgabe, weil ein
   falscher Anker wie ein vorhandener aussieht.
4. **~~Blank Nodes für Personen.~~ Korrigiert 2026-09-03: es gibt im ganzen
   TTL keinen einzigen Blank Node.** Personen sind
   `urn:fdo-squirrel:person/<16 hex>` mit `schema:name "Nachname, Vorname"`.
   Skolemisierung entfällt also; stattdessen ist die Personen-URN die dritte
   Familie in Befund 2. Offen: ob derselbe Mensch in zwei Paketen denselben
   Hash bekommt — dann führt eine reine Umschreibung je Record dieselbe Person
   n-fach; ist zu prüfen, sobald ein zweites TTL vorliegt (S3).
5. **Doppelte Aussagen aus mehreren Quellen — bestätigt, und breiter als
   gedacht.** Die Lizenz steht 11-mal da, über sechs Prädikate (`dct:license`,
   `cff:license`, `cff:license-url`, `codemeta:license`, `schema:license`,
   `wdt:P275`), jeweils als IRI *und* als Zeichenkette `"CC-BY-NC-SA-4.0"` —
   auch `cff:license-url`, wo die Zeichenkette keine URL ist. Keywords: 13
   Aussagen über sechs Prädikate. `dct:description` steht viermal, mit
   `"make 3d model available"`, `"good"` und `"low"` — das sind erkennbar
   andere `MD.cff`-Felder (Zweck, Qualität, Auflösung), die in die Beschreibung
   gelaufen sind. Die Registry entscheidet, welche Aussage sie liest, und
   berichtet den Rest (A3).
6. **Der Generator prägt IRIs in einem fremden Namensraum.** Geometrie und
   Zeitraum hängen als `<DOI>_geom` und `<DOI>_temporal` unter `doi.org`,
   gebildet durch Anhängen an die DOI-IRI. Sie sind eindeutig, aber sie
   behaupten DOIs, die es nicht gibt. A3 erlaubt nur die Umschreibung von
   `urn:` — ob diese beiden dazukommen, ist in S4 zu entscheiden.
7. **`fdo:role` hat vier Werte, nicht drei:** `model` (4), `documentation` (3),
   `metadata` (2), `data` (2). Das SKOS-Vokabular in S3 braucht vier Konzepte.

**Was schon da ist und wiederverwendet wird.** `fdox_sparql_explorer/` in
`fdo-squirrel` ist ein nbconvert-Export eines Notebooks mit rdflib in Python,
also keine Browser-Lösung, aber eine gute Vorlage für die Fragen, die die
Registry-Seite beantworten soll. Die CSV-Crosswalks (`cwreference--cff.csv`,
`schema-org--codemeta.csv`) sind das Muster, dem `crosswalks/fdo--crm.csv` in
S3 folgt.

8. **Die Kandidatenliste aus den Papieren besteht aus Concept-DOIs.**
   `10.5281/zenodo.18724635` löst auf Record **18744133** auf, `…18732892` auf
   `…18732893` (geprüft 2026-09-03 im ersten echten Lauf). Zenodo beantwortet
   eine Concept-ID stillschweigend mit der neuesten Version — wer das nicht
   prüft, pinnt nichts, sondern folgt einem beweglichen Ziel. Zwei Folgen:
   Erstens muss die Liste einmal aufgelöst werden (`--resolve`). Zweitens ist
   sie kürzer als sie aussieht: die für den Vortrag ergänzten DOIs sind zum
   Teil genau die Versionen, auf die ältere Einträge zeigen — 18744133 steht in
   der Liste und ist zugleich das Ziel von 18724635.

9. **Ein Paket im Bestand hat keine `fdo-metadata.ttl`.** Record 18740524
   („Heinz Eau", SquirrelBase Q55) liefert `Q55.zip` ohne TTL darin und ohne
   Namensvariante. Der Ernter überspringt ihn mit Begründung — das ist der
   erste echte Eintrag für den Qualitätsbericht aus S5 und eine Rückmeldung an
   den Paketautor, keine Aufgabe der Registry (A3).

**Zenodo ist nicht immer da.** Am 2026-09-03 antwortete `zenodo.org/api/` über
Stunden mit `504 Gateway Time-out`, der Dateipfad mit `404`. Ein Ernter ohne
Wiederholung und ohne lokalen Bezugsweg macht daraus einen leeren Bestand und
eine kaputte Seite. Beides ist deshalb in S2 eingebaut, nicht nachgerüstet.

**Erste Kandidaten für `registry/sources.json`** (aus den Papieren; nach
Befund 8 sind das Concept-DOIs, die vor dem Pinnen aufzulösen sind):

Aufgelöst am 2026-09-03 (`--resolve --write`): aus zehn Einträgen wurden
**acht** Records, zwei waren Dubletten — `18369866` ist die Version von
`18369865`, `18744133` die von `18724635`. Der gepinnte Stand steht in
`registry/sources.json`; die Tabelle hier bleibt als Herkunftsnachweis stehen.

| DOI | Was | Typ |
|---|---|---|
| 10.5281/zenodo.18724635 | CIIC 81, KIRI-Engine-Scan, Ogham-Stein | `fdo:3DDataFDO` |
| 10.5281/zenodo.18732892 | Lago di Anterselva, Steinmännchen (Q60) | `fdo:3DDataFDO` |
| 10.5281/zenodo.18740523 | Köln, Heinzelmännchen „Heinz Eau" (Q55) | `fdo:3DDataFDO` |
| 10.5281/zenodo.18742693 | Kassel, Beuys-Stele B 1036 (Q56) | `fdo:3DDataFDO` |
| 10.5281/zenodo.18369125 | o3d-epidoc-extractor | `fdo:SoftwareFDO` |
| 10.5281/zenodo.18369156 | ogham-analysis | `fdo:AnalysisFDO` |
| 10.5281/zenodo.18369865 | GEARS/1 | `fdo:3DDataFDO` |

## A2. Zielbild

Eine statische Seite unter
`https://research-squirrel-engineers.github.io/fdo-squirrel-registry/`, die drei
Dinge kann: **blättern**, **filtern**, **abfragen** — ohne Server, ohne
Endpoint, ohne Datenbank.

```
registry/sources.json            kuratierte DOI-Liste (A4)
        │  py/harvest_zenodo.py  Zenodo-REST: record → files → fdo-metadata.ttl
        ▼
data/raw/fdo/<record-id>/        fdo-metadata.ttl + record.json, unverändert, nur lesend
        │  py/build_bundle.py    Katalog bauen, IRIs vereindeutigen, CRM-Anker setzen
        ▼
dist/fdo-registry.ttl            DCAT + FDOx + CRM/CRMdig + GeoSPARQL + SKOS
        │  py/validate_bundle.py pyshacl gegen metadata/shapes.ttl  → Abbruch bei Verstoss
        ▼
docs/                            index.html (Facetten) · sparql.html (Pyodide) · fdo-registry.ttl
```

Vier Eigenschaften, an denen sich alles Weitere messen lassen muss:

- **Der Bundle ist ein Katalog, kein Konkatenat.** Jedes geerntete FDO bleibt
  als `dcat:Dataset` erhalten, wie `fdo-squirrel` es geschrieben hat. Die
  Registry legt einen `dcat:Catalog` darüber und je Eintrag einen
  `dcat:CatalogRecord`, der die Registry-Sicht trägt: Quell-DOI,
  Zenodo-Record-ID, Prüfsumme des geernteten TTL, Herkunft. An jedem Tripel ist
  ablesbar, ob es aus dem FDO stammt oder aus der Registry.
- **Jede Klasse im Bundle hat einen CRM-Anker.** Nicht als Absichtserklärung,
  sondern als Prüfung: eine SHACL-Shape läuft über alle vorkommenden Klassen und
  meldet jede ohne Anker. Sonst wächst die Registry und die Konformität rutscht
  unbemerkt weg.
- **Der Bundle ist N4O-anschlussfähig.** Zielbild ist ein Eintrag in
  `n4o-collections.json` und damit ein eigener Named Graph unter
  `https://graph.nfdi4objects.net/collection/<n>` (S9). Dafür genügt CRM nicht,
  es muss das Anwendungsprofil sein (A3).
- **Die Registry ist selbst ein FDO.** `MD.cff` + `CITATION.cff` im Repo,
  `dist/fdo-registry.ttl` als Inhalt, Zenodo-Release. Dann ist der Katalog nach
  denselben Regeln zitierbar wie das, was er katalogisiert — und der erste
  Eintrag der Registry kann die Registry sein.

## A3. Querschnittsregeln

- **Die Registry liest, sie korrigiert nicht.** Ein geerntetes
  `fdo-metadata.ttl` wird nie inhaltlich verändert. Was schief ist — fehlende
  Lizenz, Literal statt IRI, kein CRM-Typ — landet in `dist/quality_report.md`
  und geht als Rückmeldung an `fdo-squirrel` oder an den Paketautor. Das ist die
  Rückkopplung, die den Bestand über die Zeit besser macht; stilles Reparieren
  im Bundle würde sie abschalten.
- **Genau eine Ausnahme davon:** die Umschreibung der paketrelativen
  `urn:fdo-squirrel:*`-IRIs in Registry-IRIs (A1, Befund 2) und die
  Skolemisierung der Blank Nodes (Befund 3). Beides ist mechanisch, beides wird
  in `prov:`-Aussagen am `dcat:CatalogRecord` festgehalten, beides steht in S4.
- **Fremde Namensräume werden nicht axiomatisiert.** `fdo:`-Terme dürfen
  `rdfs:subClassOf` auf CRM bekommen — der Namensraum gehört uns. `dcat:`,
  `schema:` und `dct:` bekommen keine Axiome von uns; wo dort ein CRM-Anker
  nötig ist, wird er **je Instanz materialisiert**, nicht global behauptet. Die
  wenigen Brückenaxiome, die das Anwendungsprofil selbst vorschlägt
  (`crm:E39_Actor rdfs:subClassOf foaf:Agent` usw.), werden zitiert, nicht
  neu erfunden.
- **CRM heisst hier CRM nach dem N4O-Anwendungsprofil**
  (<https://nfdi4objects.github.io/crm-rdf-ap/>), nicht CRM nach Lehrbuch. Das
  Profil verbietet Konstrukte, die eine naive Abbildung zuerst wählen würde;
  die Liste steht in S3 und wird im SHACL-Gate erzwungen. Wer hier „richtig nach
  CRM" modelliert, ohne das Profil zu lesen, baut den Bundle N4O-untauglich.
- **Keine Uhr im Output.** Kein Generator liest `datetime.now()`. Zeitangaben im
  Bundle stammen aus dem Zenodo-Record (`created`, `updated`) oder aus
  `REGISTRY_RELEASE` in `py/registry_utils.py`. Ein Erntedatum ist keine
  Ausnahme: es wird beim Ernten in `data/raw/.../harvest.json` geschrieben und
  von dort gelesen. Damit ändert sich der Bundle genau dann, wenn sich Quellen
  oder Modell ändern.
- **Zweimal laufen lassen, `git status` muss sauber bleiben.** Kanonische
  Ausgabe: sortierte N-Triples als Zwischenstand, daraus die Turtle-Datei; keine
  zufälligen Blank-Node-IDs, keine Zeitstempel, sortierte JSON-Schlüssel.
- **Netz nur in S2.** `py/harvest_zenodo.py` ist der einzige Schritt, der ins
  Netz geht. Alle anderen laufen offline gegen `data/raw/`. `main.py` ohne
  Argumente erntet **nicht** — es baut aus dem, was da ist. Ernten ist ein
  bewusster Aufruf. Sonst ist kein Lauf reproduzierbar und keine
  Netzwerkstörung von einem Datenfehler zu unterscheiden.
- **Maschinenlokale Pfade stehen in `config.local.json`**, nie in einer
  versionierten Datei. `sources.json` ist kuratierter Bestand und muss auf
  jedem Rechner gleich sein; wo die ZIP-Pakete zufällig liegen, geht nur den
  einen Rechner etwas an. Die Datei ist in `.gitignore` und darf fehlen.
- **Windows ist die Referenzplattform.** Alle Kommandos werden für `cmd`
  angegeben, jeder Befehl auf **einer** Zeile, keine Fortsetzungszeichen. Pfade
  über `pathlib`, keine Shell-Pipes im Python-Code, keine Abhängigkeit von
  `make`.
- **Ein Thema pro Chat.** Ergebnisse kommen als Patch-ZIP nach dem
  Patch-Skill: nur Quellen, keine Erzeugnisse — `dist/` und `docs/` werden
  nachgebaut, nicht geliefert.
- **Offene Entscheidungen werden als interaktives Formular gestellt**, nicht als
  Aufzählung im Fliesstext, und **jedes Formular hat ein freies Kommentarfeld**.
  Die wichtigsten Antworten sind regelmässig die, an die beim Formulieren der
  Frage niemand gedacht hat.
- Sprache: Konversation deutsch, Code/Ontologie/Dokumentation englisch.
  Ausnahme: dieses `PRIMER.md` bleibt deutsch — internes Arbeitsdokument.

## A4. Beschlusslage

Beschlüsse aus dem Auftaktchat stehen mit Datum; was als **Vorschlag** markiert
ist, gilt bis zum Widerspruch und wird spätestens in dem Schritt bestätigt, in
dem es zum ersten Mal wirkt.

| Frage | Beschluss | seit |
|---|---|---|
| Woher kommt die FDO-Liste | kuratiertes `registry/sources.json` mit DOIs. Keine Community-Abfrage | 2026-09-03 |
| Wo entsteht der CRM-Anker | zuerst in der Registry als Brückendatei, `fdo-squirrel` bleibt unangetastet; Übernahme upstream später, wenn die Abbildung steht | 2026-09-03 |
| Browser-SPARQL | Pyodide + rdflib, wie in der `wdt-*`-Familie | 2026-09-03 |
| Orchestrator | `main.py` im Repo-Wurzelverzeichnis, Schritte einzeln aufrufbar, Windows-`cmd` als Referenz | 2026-09-03 |
| Registry-Namensraum | `https://w3id.org/fdo-squirrel/registry/`, Präfix `fdoreg:` — hängt unter den bestehenden FDOx-Namensraum | Vorschlag |
| DOI-Pinning | `sources.json` hält Concept-DOI **und** gepinnte Versions-DOI; geerntet wird die gepinnte. `main.py check-updates` meldet neuere Versionen, ändert aber nichts | Vorschlag |
| Records ohne `fdo-metadata.ttl` | werden übersprungen und im Qualitätsbericht genannt; das ZIP wird **nicht** durch `fdo-squirrel` gejagt (Aufgabe des Autors, nicht der Registry) | Vorschlag |
| IRI-Umschreibung | `urn:fdo-squirrel:dist/<sha>` → `<record-IRI>/dist/<sha>`, `urn:fdo-squirrel:content/<pfad>` → `<record-IRI>/content/<pfad>`; die Originale bleiben als `dct:identifier` erhalten | Vorschlag |
| Personenknoten | ORCID-IRI, wo vorhanden; sonst skolemisiert aus Nachname+Vorname unter `<record-IRI>/agent/<slug>` | Vorschlag |
| CRM-Profil | N4O-Anwendungsprofil (crm-rdf-ap), nicht die offizielle RDF-Kodierung. Abweichungen in S3 tabelliert | Vorschlag |
| Facettenseite | eigenes `dist/registry-index.json`, beim Build erzeugt; SPARQL bleibt der zweiten Seite vorbehalten. Niemand soll auf eine WASM-Runtime warten, um nach „3D" zu filtern | Vorschlag |
| Bundle im Repo | ja, `dist/fdo-registry.ttl` ist versioniert — er ist das zitierbare Erzeugnis und Eingabe der Seite | Vorschlag |
| Lizenz | Code MIT wie `fdo-squirrel`; der Bundle CC BY 4.0, Lizenzen der geernteten FDOs bleiben je Eintrag erhalten | Vorschlag |
| Schrittvertrag | jedes Schrittmodul bietet `main(strict=False)`, prüft seine eigene Vorbedingung und meldet `skipped (no input): <Grund>`, statt zu scheitern oder still durchzulaufen. Damit ist `python main.py` von Anfang an ein Rauchtest | 2026-09-03 |
| Orchestrator-Flags | `--list`, `--only`, `--from`, `--skip`, `--dry-run`, `--strict`; Schrittmodule werden faul importiert und bleiben einzeln lauffähig | 2026-09-03 |
| Netzschritt im Standardlauf | nein — `harvest` trägt `network=True` und wird von `select()` aus dem Standardlauf herausgefiltert. Nur `python main.py --only harvest` holt | 2026-09-03 |
| `dist/` in `.gitignore` | **nicht** ignoriert — es hält die zitierbaren Erzeugnisse. Ausgenommen `dist/pipeline_report.txt`: das Log trägt Laufzeiten und wäre bei jedem Lauf verändert | 2026-09-03 |
| PRIMER-Sprache | deutsch — internes Arbeitsdokument | 2026-09-03 |
| Bezugsweg für das TTL | vier Wege in fester Reihenfolge: Einzeldatei im Record → lokales ZIP → HTTP-Range in das ZIP auf Zenodo → Volldownload. Das TTL liegt im ZIP (A1, Befund 1), und 300 MB je Eintrag zu ziehen, um 10 kB zu lesen, ist keine Ernte | 2026-09-03 |
| Prüfung des Geernteten | was prüfbar ist, wird geprüft und in `harvest.json` protokolliert: MD5 des ZIP gegen den Record, wo das ganze ZIP gelesen wurde; sonst CRC-32 des Members aus dem ZIP-Verzeichnis. `harvest.json` sagt, welches von beiden | 2026-09-03 |
| Records ohne `fdo-metadata.ttl` | wie beschlossen übersprungen — und der Übersprung wird gemerkt: ein publizierter Zenodo-Record ist unveränderlich, ein zweiter Lauf fragt ihn nicht erneut. `--force` prüft trotzdem nach | 2026-09-03 |
| Offline-Betrieb | `--offline` erntet ohne Netz aus lokalen ZIPs; ohne `record.json` wird der Eintrag mit leeren Record-Feldern und Warnung angelegt, damit S3/S4 weiterlaufen. Ein späterer Online-Lauf vervollständigt ihn und gilt bis dahin nie als „up to date" | 2026-09-03 |
| Concept-DOI | bleibt kuratiert in `sources.json`; der Ernter prüft sie gegen den Record und meldet Abweichung oder Fehlen, überschreibt aber nichts | 2026-09-03 |
| Concept-DOI statt Versions-DOI in `sources.json` | harter Fehler vor dem ersten Schreibzugriff. Zenodo löst eine Concept-ID auf die neueste Version auf; eine gepinnte Registry darf nicht stillschweigend einen Record aufnehmen, den sie nicht angefragt hat | 2026-09-03 |
| Concept-DOI statt Versions-DOI beim Ernten | kein Abbruch: der Eintrag wird übersprungen, die aufgelöste Versions-DOI in `harvest.json` genannt, die Ernte läuft weiter. Ein falscher Pin unter zehn darf nicht neun andere verhindern | 2026-09-03, ersetzt den harten Fehler vom selben Tag |
| Auflösen der Liste | `--resolve` fragt Zenodo, was jede DOI wirklich ist, und **schlägt** die korrigierte `sources.json` vor; erst `--resolve --write` schreibt. Doppelte, die dabei sichtbar werden, werden gemeldet und beim Schreiben zusammengeführt — der Kommentar des ersten Eintrags gewinnt | 2026-09-03 |
| Netzausfall | ein nicht erreichbarer Record ist eine Aussage über Zenodo, nicht über den Record: nichts wird geschrieben, nichts gemerkt, der Lauf geht weiter. Nach drei Ausfällen in Folge bricht er ab und sagt, dass Zenodo nicht antwortet. Exitcode ≠ 0, damit die CI es merkt | 2026-09-03 |
| Zenodo-Endpunkte | Zenodo läuft auf InvenioRDM; die Community-Suche liegt unter `/api/communities/<slug>/records`, die alte `?communities=`-Form antwortet mit 400. `check-updates` probiert die bekannten Formen der Reihe nach und schreibt in den Bericht, welche geantwortet hat. Ein Bericht ist keinen kaputten Build wert | 2026-09-03 |
| `check-updates` | eigener Netzschritt, ändert nichts. Meldet neuere Versionen gepinnter Records *und* Records der Zenodo-Community `squirrel-fdo`, die nicht in `sources.json` stehen | 2026-09-03 |

## A5. Was in welchem Chat hochgeladen wird

Die Zeile **Uploads** bei jedem Schritt in Teil C nennt, was zusätzlich
gebraucht wird. Grundregel: lieber das Bundle als einzelne Dateien.

Das Repo bleibt klein — die Binärdaten liegen auf Zenodo, nicht hier. Ein
Grössenfilter genügt trotzdem, weil `data/raw/` mit der Zahl der Einträge
wächst:

```cmd
cd /d C:\git
robocopy fdo-squirrel-registry bundle\fdo-registry /E /MAX:2000000 /XD .git .venv __pycache__ /XF *.zip
powershell -NoProfile -Command "Compress-Archive -Path 'bundle\fdo-registry' -DestinationPath 'fdo-registry_bundle.zip' -Force"
```

Robocopy meldet Exitcode 1 bei Erfolg.

**Für S3 und S4:** ein echtes `fdo-metadata.ttl`, nicht das Demo-TTL aus
`fdo-squirrel/fdo/` — das Demo hat drei der vier Befunde in A1 falsch
suggeriert. Am besten zwei aus verschiedenen Paketen, weil erst der Vergleich
zeigt, ob die Personen-URN über Pakete hinweg stabil ist (A1, Befund 4).

Nach einer lokalen Ernte liegen sie ohnehin unter `data/raw/fdo/<id>/` und
kommen mit dem Bundle mit; `data/raw/` ist klein, weil dort nur TTL und
`record.json` landen, nie die Pakete selbst.

**Nicht hochladen:** `.venv/`, `.git/`, heruntergeladene ZIP-Pakete,
`config.local.json`.

## A6. IRI-Landkarte unter `https://w3id.org/fdo-squirrel/`

Die Registry hängt unter den bestehenden FDOx-Namensraum, statt einen zweiten
aufzumachen. Was davon bei w3id eingetragen werden muss, ist in S1 zu prüfen —
unbekannt ist derzeit, ob für `fdo-squirrel` überhaupt schon ein Eintrag
existiert oder ob die IRI bisher nur als Präfix benutzt wird.

| Pfad | Inhalt | Ziel des Redirects | Status |
|---|---|---|---|
| `/fdo-squirrel/` | FDOx-Vokabular: `fdo:3DDataFDO`, `fdo:role`, `fdo:sha256` … | `fdo-squirrel`, Datei noch zu bestimmen | in Benutzung, Eintrag ungeprüft |
| `/fdo-squirrel/crm/` | Brücke FDOx → CIDOC CRM | `metadata/crm_bridge.ttl` | geplant (S3) |
| `/fdo-squirrel/registry/` | Registry-Vokabular `fdoreg:` | `metadata/registry_ontology.ttl` | geplant (S1) |
| `/fdo-squirrel/registry/catalog` | der Katalogknoten selbst | `dist/fdo-registry.ttl` | geplant (S4) |
| `/fdo-squirrel/registry/record/{id}` | ein `dcat:CatalogRecord` je Eintrag | Detailansicht auf Pages | geplant (S6) |
| `/fdo-squirrel/registry/role/` | SKOS-Vokabular zu `fdo:role` | `metadata/vocab/role.ttl` | geplant (S3) |
| `/fdo-squirrel/registry/shapes/` | SHACL-Gate | `metadata/shapes.ttl` | geplant (S5) |

**Zu klären beim Eintragen.** Ein Redirect auf GitHub Pages liefert genau eine
Repräsentation aus. Für echte Content Negotiation braucht es w3id-seitige
`Accept`-Regeln oder je Pfad einen `.ttl`- und einen `.html`-Eintrag.

---

# Teil B — Schrittübersicht

| ID | Schritt | hängt ab von | Status |
|---|---|---|---|
| S0 | Festlegungen, kein Code | — | teilweise erledigt 2026-09-03 |
| S1 | Repo-Skelett und Orchestrator | S0 | erledigt 2026-09-03 |
| S2 | Ernte aus Zenodo | S1 | erledigt 2026-09-03 |
| S3 | Crosswalk FDOx → CIDOC CRM | S0, S2 (ein echtes TTL) | offen |
| S4 | Bundle-Build als DCAT-Katalog | S2, S3 | offen |
| S5 | SHACL-Gate und Qualitätsbericht | S4 | offen |
| S6 | Registry-Index und Facettenseite | S4 | offen |
| S7 | SPARQL-Seite | S4, S6 | offen |
| S8 | Registry als FDO, Release und CI | S5, S7 | offen |
| S9 | N4O-Andockung | S5, S8 | offen |

S3 lässt sich fachlich schon vor S2 beginnen, braucht für die Abnahme aber ein
echtes geerntetes TTL — deshalb die Abhängigkeit. S6 und S7 hängen beide an S4
und nicht aneinander; S6 zuerst, weil die Facettenseite den kürzeren Weg zu
etwas Vorzeigbarem ist. S5 steht vor S8, weil kein Release ohne grünes Gate
herausgeht.

---

# Teil C — Die Schritte

## S0 — Festlegungen (kein Code)

**Ziel:** die Entscheidungen treffen, die IRIs und Klassenidentität betreffen.
Werden sie später getroffen, müssen erzeugte Tripel neu geschrieben werden.

**Erledigt 2026-09-03:** Quelle der FDO-Liste, Ort des CRM-Ankers,
Browser-Engine (A4).

**Noch offen, spätestens in S1 bzw. S3 zu klären:**

- Registry-Namensraum bestätigen und w3id-Lage klären (A6).
- Versions- vs. Concept-DOI: der Vorschlag in A4 pinnt die Version. Die
  Alternative wäre, immer die neueste Version zu ziehen — dann ist der Bundle
  aber nicht mehr reproduzierbar, ohne das Datum mitzuführen.
- Umgang mit mehreren Versionen desselben Objekts: ein Eintrag je Version oder
  ein Eintrag mit Versionsgeschichte. Betrifft die Zählung auf der Seite und die
  `dcat:CatalogRecord`-Identität.

## S1 — Repo-Skelett und Orchestrator

**Ziel:** ein leeres, aber vollständiges Repo, in dem `python main.py` läuft und
„nichts zu tun" sagt.

**Uploads:** keine.

**Layout.** Es folgt der `wdt-*`-Familie, wo es passt, und `fdo-squirrel`, wo
das näher liegt:

```
fdo-squirrel-registry/
├── PRIMER.md              dieses Dokument
├── README.md              englisch, für aussen
├── LICENSE                MIT
├── CITATION.cff           Registry als zitierbare Software
├── MD.cff                 Registry als FDO (S8)
├── requirements.txt
├── .gitignore
├── main.py                Orchestrator
├── registry/
│   └── sources.json       kuratierte DOI-Liste
├── py/
│   ├── registry_utils.py  REGISTRY_RELEASE, IRI-Bau, kanonische Serialisierung
│   ├── harvest_zenodo.py  S2
│   ├── build_bridge.py    S3
│   ├── build_bundle.py    S4
│   ├── validate_bundle.py S5
│   ├── build_index.py     S6
│   ├── build_sparql.py    S7
│   └── templates/         index.html.j2, sparql.html.j2, style.css
├── crosswalks/
│   └── fdo--crm.csv       S3, Quelle der Brücke
├── metadata/
│   ├── registry_ontology.ttl
│   ├── crm_bridge.ttl     generiert aus der CSV
│   ├── shapes.ttl         SHACL-Gate
│   └── vocab/role.ttl     SKOS zu fdo:role
├── queries.yaml           S7
├── data/raw/fdo/<id>/     geerntet, nur lesend
├── dist/                  fdo-registry.ttl, registry-index.json, Berichte
└── docs/                  GitHub Pages
```

**`main.py`.** Ein Orchestrator, keine Bibliothek. Er ruft die Schritte in
fester Reihenfolge auf, fängt deren Ausgabe zeilenweise ein und schreibt sie
zugleich ins Terminal und nach `dist/pipeline_report.txt`. Aufrufe:

```cmd
python main.py
python main.py --only bundle
python main.py --from bundle
python main.py harvest
python main.py check-updates
python main.py --strict
```

`python main.py` ohne Argumente läuft `bridge → bundle → validate → index →
sparql → site`, ohne Netz (A3). `harvest` ist der einzige Schritt, der ins Netz
geht, und wird nur explizit aufgerufen. `--strict` macht Warnungen zu Fehlern —
so läuft die CI.

`PYTHONIOENCODING=utf-8` im Kindprozess setzen, sonst scheitern Umlaute und ✓ an
der Pipe unter Windows.

**`py/registry_utils.py`** hält von Anfang an: `REGISTRY_RELEASE` (Datum als
Konstante), `record_iri(record_id)`, `dist_iri(...)`, `agent_iri(...)`,
`write_canonical_turtle(graph, path)` (sortierte N-Triples → Turtle) und
`content_fingerprint(...)`. Wenn diese Funktionen erst in S4 entstehen, sind
sie bis dahin dreimal verschieden geschrieben worden.

**Abnahme:** `python main.py` läuft durch, meldet für jeden Schritt „skipped
(no input)", `git status` bleibt sauber. `pip install -r requirements.txt` in
einem frischen venv reicht aus — `rdflib`, `pyshacl`, `pyyaml`, `jinja2`,
`requests`.

### Erledigt 2026-09-03

Skelett steht, gegen einen frischen Klon des leeren Repos geprüft: `python
main.py` läuft alle sechs Nicht-Netz-Schritte durch, jeder meldet seine eigene
fehlende Vorbedingung, Exitcode 0.

Drei Dinge, die beim Bauen aufgefallen sind:

- **Das Laufzeitprotokoll darf nicht versioniert werden.** `main.py` schreibt
  `dist/pipeline_report.txt` mit der Laufzeittabelle, und die ändert sich bei
  jedem Lauf. Bei versioniertem `dist/` heisst das dauerhaft schmutziges `git
  status` — also genau der Zustand, den A3 verhindern soll. Die Datei ist jetzt
  einzeln ignoriert; `dist/` als Ganzes bleibt versioniert.
- **`urn:`-Umschreibung und Skolemisierung sind schon im Code angelegt.**
  `registry_utils.record_iri()`, `distribution_iri()`, `content_iri()` und
  `agent_iri()` stehen bereit, damit S4 sie nicht drei Mal verschieden erfindet.
  Sie erzeugen den in A4 vorgeschlagenen Namensraum; ist der Vorschlag falsch,
  ist es eine Zeile in `registry_utils.py`.
- **`registry/sources.json` bleibt leer.** Die Kandidaten aus A1 sind bekannt,
  aber ihre Concept-DOIs nicht — die stehen erst nach dem ersten Zenodo-Abruf
  fest. Sie zu erraten, wäre eine erfundene Angabe im kuratierten Kern der
  Registry. S2 füllt die Datei, nachdem die Records tatsächlich abgefragt sind.

Nicht geprüft: `pip install -r requirements.txt` in einem frischen venv. Der
Sandkasten hatte `rdflib` bereits, die übrigen vier sind nur deklariert.

## S2 — Ernte aus Zenodo

**Ziel:** aus einer DOI-Liste ein lokales, unverändertes Abbild der
FDO-Metadaten.

**Uploads:** keine, aber Netz — oder die Pakete lokal (`--offline`).

**`registry/sources.json`.** Bewusst schmal — alles Beschreibende steht im
FDO selbst und wird nicht doppelt gepflegt:

```json
{
  "schema_version": "1",
  "sources": [
    {
      "concept_doi": "10.5281/zenodo.18724634",
      "version_doi": "10.5281/zenodo.18724635",
      "note": "CIIC 81, KIRI Engine SfM scan",
      "added": "2026-09-03"
    }
  ]
}
```

`note` ist für Menschen und geht **nicht** in den Bundle — sonst konkurriert sie
mit `dct:description` aus dem FDO.

**Vier Bezugswege für das TTL, in dieser Reihenfolge** (A4). Das TTL liegt im
Paket-ZIP, nicht daneben (A1, Befund 1):

| # | Weg | wann | Prüfung |
|---|---|---|---|
| a | Einzeldatei `fdo-metadata.ttl` im Record | wenn der Autor sie zusätzlich hochlädt | MD5 gegen den Record |
| b | lokales Paket-ZIP (`--zip <id>=<pfad>`, oder `package_dir` aus `config.local.json`) | wenn das Paket schon auf der Platte liegt | MD5 des ZIP gegen den Record, CRC-32 des Members |
| c | HTTP-Range in das ZIP auf Zenodo | Regelfall | CRC-32 des Members aus dem ZIP-Verzeichnis |
| d | Volldownload des ZIP (`--full`, oder wenn der Server keine Ranges liefert) | Notnagel | MD5 des ZIP, CRC-32 des Members |

Weg c ist der Grund, warum die Ernte praktikabel ist: `zipfile` parst
Zentralverzeichnis und Eintrag, `py/package_zip.py` macht eine URL über
Range-Requests seekbar. Gemessen: **ein bis zwei Requests und 10 kB statt
300 MB je Paket.** Die MD5, die Zenodo veröffentlicht, gilt für das ganze ZIP
und kann auf diesem Weg nicht geprüft werden — dafür prüft das ZIP-Format den
Member selbst per CRC-32, und `harvest.json` schreibt hin, welche der beiden
Prüfungen gelaufen ist. Eine Prüfsumme, von der man nicht weiss, was sie
abdeckt, ist keine.

**Ablauf je Eintrag.**

1. Record-ID aus der Versions-DOI, `https://zenodo.org/api/records/<id>`
   abrufen, `record.json` unverändert nach `data/raw/fdo/<id>/`.
2. Löst Zenodo auf eine andere ID auf, war es eine Concept-DOI: **harter
   Fehler vor dem ersten Schreibzugriff** (A4).
3. TTL über die Wege a–d beziehen. Namensvarianten werden protokolliert, nicht
   geraten. Fehlt es: Eintrag überspringen, Grund in `harvest.json`, Ernte
   fortsetzen. Ein fehlendes TTL ist ein Befund, kein Abbruch.
4. `harvest.json` schreiben: beide DOIs, Titel, `created`/`updated`, Paketname,
   Weg, was geprüft wurde, SHA-256 des Members, Bezugsdatum.

**Vor dem ersten Ernten: auflösen.** Eine frisch zusammengetragene Liste
enthält Concept-DOIs (A1, Befund 8). `python py\step_harvest.py --resolve`
fragt für jeden Eintrag nach, was Zenodo daraus macht, meldet Doppelte und
schlägt die korrigierte Datei vor; `--write` schreibt sie. Danach steht in
`sources.json` je Eintrag die Versions-DOI im Pin und die Concept-DOI daneben,
und beide sind geprüft statt geraten.

**Wiederholte Läufe holen nichts.** Liegt das TTL mit passender SHA-256 vor,
wird übersprungen; ein einmal übersprungener Record wird nicht erneut
angefragt, weil ein publizierter Zenodo-Record unveränderlich ist. `--force`
prüft trotzdem nach. Ein offline ohne `record.json` angelegter Eintrag gilt nie
als „up to date".

**Netzverhalten.** Fünf Versuche mit 2/5/10/20 s Pause bei 5xx und Timeouts;
4xx wird nicht wiederholt, weil ein 404 eine Aussage über den Record ist und
keine über das Netz. Bleibt ein Record unerreichbar, wird für ihn nichts
geschrieben und nichts gemerkt, und der Lauf geht zum nächsten; nach drei
Ausfällen in Folge bricht er mit einer Erklärung ab (A4). Lange Wartezeiten
sind hier kein Vorteil: wenn Zenodo einen Tag lang steht, verzögert jede
Sekunde Backoff nur die Meldung, die das sagt.

**`check-updates`** ist ein eigener Netzschritt und ändert nichts: er meldet
neuere Versionen der gepinnten Records (über `/versions/latest`, also ohne
Concept-DOI) und Records der Community `squirrel-fdo`, die nicht in
`sources.json` stehen. Bericht nach `data/raw/check-updates.json`. Das
Nachziehen einer Version ist eine kuratorische Entscheidung.

**Abnahme:** alle Einträge aus A1 geerntet oder mit Grund übersprungen; zweiter
Lauf holt nichts nach und lässt `git status` sauber.

### Erledigt 2026-09-03

Ernter und `check-updates` stehen, geprüft gegen einen lokalen HTTP-Server mit
echtem 3-MB-ZIP und dem echten `fdo-metadata.ttl` aus Record 18724635. Zehn
Fälle: Range-Weg, TTL im Unterordner, ZIP ohne TTL, Einzeldatei im Record,
zweiter Lauf ohne Request, lokales ZIP über `package_dir`, `--offline --zip`
ohne `record.json` mit anschliessendem Online-Lauf, Server ohne Range-Unterstützung,
`--full`, falsche MD5.

Was beim Bauen herauskam:

- **Der Anlass für den Range-Weg war ein Ausfall.** Zenodo antwortete den
  ganzen Tag mit 504, und der Versuch, das TTL über den Dateipfad des Records
  zu ziehen, lieferte 404 — weil es diesen Pfad nicht gibt (A1, Befund 1). Der
  Ausfall hat den Entwurfsfehler sichtbar gemacht, den ein guter Tag verdeckt
  hätte.
- **CRC-32 als Gegenprobe funktioniert.** Der aus dem entfernten ZIP gelesene
  Member hat `b7d449a9` — dieselbe Prüfsumme, die 7-Zip für die Datei im
  lokalen Paket anzeigt. Damit ist der Range-Weg nicht nur schnell, sondern
  gegen eine unabhängige Angabe geprüft.
- **Ein übersprungener Record muss gemerkt werden.** Ohne das fragt jeder Lauf
  alle TTL-losen Records erneut an — bei einem Bestand, der wächst, der
  teuerste Teil der Ernte, und der einzige ohne Ertrag.
- **`registry/sources.json` ist mit zehn Einträgen gefüllt**, Concept-DOIs
  noch `null`. Der erste Online-Lauf meldet je Record die Concept-DOI aus dem
  Record als Warnung; sie wandert von Hand in die Datei, statt geraten zu
  werden.
### Nachtrag 2026-09-03, erster echter Lauf

Der erste Lauf auf der Zielmaschine hat zwei Dinge erledigt, die im Sandkasten
nicht zu sehen waren:

- **Die Kandidatenliste besteht aus Concept-DOIs** (A1, Befund 8). Der harte
  Fehler, den S2 dafür ursprünglich vorsah, war die falsche Reaktion: er hat
  den Lauf beim ersten Eintrag beendet und die neun anderen nie erreicht. Jetzt
  wird übersprungen, benannt und weitergemacht, und `--resolve` macht aus dem
  Befund eine Änderung an `sources.json`, die man vorher liest.
- **Ein Ausfall darf nicht als Abbruch enden.** `check-updates` lief in einen
  Traceback und dann in ein Ctrl-C, weil jeder Record einzeln fünfmal auf ein
  totes Zenodo wartete. Beide Netzschritte fangen den Ausfall jetzt je Eintrag
  ab, melden ihn im Bericht als „unerreichbar" — was etwas anderes ist als „es
  gibt nichts Neues" — und halten nach drei Fehlschlägen an.

### Nachtrag 2026-09-03, zweiter echter Lauf

Die Ernte läuft. **Acht Records, sieben geerntet, einer übersprungen, 5,5
Sekunden** — alle sieben über den Range-Weg. Damit ist der teuerste Teil des
Entwurfs auch der schnellste: sieben Pakete mit zusammen mehreren Gigabyte
kosten so viel wie ein paar Dutzend HTTP-Requests.

- **`--resolve` hat die Liste halbiert, wo sie doppelt war** (A1, Befund 8).
  Zehn Einträge, acht Records, zwei Dubletten benannt und beim Schreiben
  zusammengeführt.
- **Record 18740524 hat kein TTL** (A1, Befund 9). Der erste Eintrag für den
  Qualitätsbericht — genau der Fall, für den „übersprungen mit Grund" statt
  „Abbruch" gebaut wurde.
- **Die Community-Suche lief auf 400.** Die benutzte URL war die alte
  Zenodo-Form; Zenodo ist inzwischen InvenioRDM. Jetzt werden die bekannten
  Endpunkte der Reihe nach probiert, und ein Fehlschlag aller drei macht den
  Bericht unvollständig statt den Schritt kaputt. Ein 4xx ist seitdem ein
  eigener Fehlertyp: der Server hat verstanden und nein gesagt, das ist etwas
  anderes als ein Ausfall.

**Die Community-Suche findet ihren Endpunkt noch nicht.** Alle bekannten Formen
antworten mit **400**, auch die InvenioRDM-Pfadform — und 400 heisst, dass der
Pfad abgelehnt wird, nicht die Community, sonst käme 404. Der Schritt läuft
korrekt weiter und meldet den Bericht als unvollständig; das ist das gewünschte
Verhalten, aber es ist noch nicht die Antwort. Sie steht in Teil D, weil sie mit
Ausprobieren an einer Zenodo-URL zu klären ist und nicht am Quelltext.

**Offen aus diesem Lauf:** die Kommentare in `sources.json` stammen noch aus
der Kandidatenliste; für `18744583` steht dort „added for the talk", während
der Record `CHUIS/1` heisst. Kosmetik, aber sie steht im kuratierten Kern.

- **Nicht geprüft:** ein echter Lauf gegen zenodo.org. Der Sandkasten darf
  nicht ins Netz, und Zenodo war ohnehin nicht erreichbar. Was hier gegen einen
  lokalen Server läuft, kann an einer Eigenheit der echten API noch scheitern —
  der erste Lauf auf deiner Maschine ist die eigentliche Abnahme.

## S3 — Crosswalk FDOx → CIDOC CRM

**Ziel:** eine Tabelle, aus der die Brückendatei *und* die Dokumentation
entstehen, und die dem N4O-Anwendungsprofil folgt.

**Uploads:** ein echtes `fdo-metadata.ttl` aus S2.

**`crosswalks/fdo--crm.csv`** im Stil der vorhandenen Crosswalk-CSVs:

| Spalte | Inhalt |
|---|---|
| `fdo_term` | Term aus `fdo:` oder Feldpfad aus `MD.cff` |
| `kind` | `class` \| `property` \| `field` |
| `target` | CRM/CRMdig/GeoSPARQL/SKOS-Term |
| `mechanism` | `axiom` (nur für `fdo:`-Terme) \| `instance` (materialisiert in S4) |
| `ap_rule` | Verweis auf die Regel im Anwendungsprofil, wo einschlägig |
| `note` | Begründung, besonders bei „kein Anker" |

**Was das Anwendungsprofil verbietet.** Das ist der Teil, den eine naive
CRM-Abbildung zuerst falsch macht. Aus
<https://nfdi4objects.github.io/crm-rdf-ap/>:

| Naheliegend | Im Profil | Stattdessen |
|---|---|---|
| `crm:E55_Type` für Keywords und Rollen | MUST NOT | `skos:Concept`, `skos:broader`/`narrower` |
| `crm:E32_Authority_Document`, `P71 lists` | MUST NOT | `skos:ConceptScheme`, `skos:inScheme` |
| `crm:E52_Time-Span` mit `P82a`/`P82b` | ausdrücklich nicht erwünscht | typisierte Literale (`xsd:date`, `xsd:gYear`, `edtf:EDTF`) an `crm:P4_has_time-span`; komplexe Fälle als `time:Interval` |
| `crm:E94_Space_Primitive`, `P168 place is defined by` | ersetzt | `geo:hasGeometry` auf `geo:Geometry` mit `geo:asWKT` |
| `crm:E95_Spacetime_Primitive`, `P169i` | MUST NOT | `P4` für Zeit + `geo:hasGeometry` für Ort |
| `crm:E41/E35/E42` für Titel und Identifier | zu vermeiden | Literale, `skos:prefLabel`/`altLabel`, Identifier als IRI + `owl:sameAs` |
| eigene Klassen für Literaturangaben | MUST NOT | BIBO |

Die MD.cff-Felder `spatial.wkt`, `spatial.lat/lon` und `temporal.start/end`
treffen davon gleich drei Regeln — die Abbildung wird also nicht schematisch,
sondern feldweise begründet.

**Der Kern der Abbildung** (Arbeitsstand, in S3 gegen CRMdig 3.2.2 zu prüfen;
die CRMdig-Property-Namen sind zwischen den Versionen gewandert, hier wird
nichts aus dem Gedächtnis übernommen):

| FDOx | CRM-Anker | Mechanismus |
|---|---|---|
| `fdo:3DDataFDO` | `crmdig:D1_Digital_Object` | Axiom |
| `fdo:SoftwareFDO` | `crmdig:D14_Software` | Axiom |
| `fdo:AnalysisFDO` | `crmdig:D1_Digital_Object` | Axiom |
| `dcat:Distribution` (im Bundle) | `crmdig:D1_Digital_Object` | Instanz |
| `heritage_object` | `crm:E22_Human-Made_Object`, mit dem FDO verbunden über den Digitalisierungsvorgang | Instanz |
| `technique.acquisition` | `crmdig:D2_Digitization_Process`, Gerät und Software als `crm:P16_used_specific_object` | Instanz |
| `creators`, `publishers` | `crm:E39_Actor` (ORCID/ROR als IRI) | Instanz |
| `keywords` | `skos:Concept`, verknüpft über `crm:P2_has_type` | Instanz |
| `spatial` | `crm:E53_Place` + `geo:hasGeometry` | Instanz |
| `temporal` | `crm:P4_has_time-span` mit typisiertem Literal | Instanz |
| `license`, `version`, `sha256` | kein Anker, begründet — bleiben bei `dct:`/`fdo:` | — |

**`py/build_bridge.py`** erzeugt aus der CSV `metadata/crm_bridge.ttl` (nur die
`axiom`-Zeilen) und einen Abschnitt in `docs/crosswalk.html`. Die `instance`-
Zeilen liest S4.

**Abnahme:** jede Zeile der CSV hat entweder ein Ziel oder eine Begründung in
`note`; `crm_bridge.ttl` parst; keine Aussage über einen fremden Namensraum, die
nicht im Anwendungsprofil steht.

## S4 — Bundle-Build als DCAT-Katalog

**Ziel:** `dist/fdo-registry.ttl` — ein Graph, byte-gleich bei gleicher Eingabe.

**Uploads:** Bundle nach A5.

**Reihenfolge im Skript.** Sie ist nicht beliebig; die Vereindeutigung muss vor
dem Zusammenführen passieren, sonst ist die Kollision schon eingetreten:

1. Je Eintrag das TTL **in einen eigenen Graph** parsen.
2. Blank Nodes skolemisieren (A4): Personen auf ORCID, sonst auf
   `<record-IRI>/agent/<slug>`.
3. `urn:fdo-squirrel:*` umschreiben auf `<record-IRI>/dist/<sha>` bzw.
   `<record-IRI>/content/<pfad>`; die Original-URN als `dct:identifier` erhalten.
4. CRM-Anker je Instanz materialisieren, nach den `instance`-Zeilen aus S3.
5. In den Katalog hängen:

```turtle
<https://w3id.org/fdo-squirrel/registry/catalog> a dcat:Catalog ;
    dct:title "FDOx Registry"@en ;
    dct:license <https://spdx.org/licenses/CC-BY-4.0.html> ;
    dcat:record   <…/record/18724635> ;
    dcat:dataset  <https://doi.org/10.5281/zenodo.18724635> .

<…/record/18724635> a dcat:CatalogRecord ;
    foaf:primaryTopic <https://doi.org/10.5281/zenodo.18724635> ;
    dct:issued        "2026-06-14"^^xsd:date ;      # aus dem Zenodo-Record
    dct:source        <https://zenodo.org/records/18724635> ;
    fdoreg:conceptDoi <https://doi.org/10.5281/zenodo.18724634> ;
    fdoreg:sha256     "…" ;                          # des geernteten TTL
    prov:wasDerivedFrom <https://zenodo.org/api/records/18724635/files/fdo-metadata.ttl> .
```

6. Kanonisch serialisieren: sortierte N-Triples nach `dist/fdo-registry.nt`,
   daraus `dist/fdo-registry.ttl`.

**Was der Bundle nicht tut.** Er zieht keine Wikidata- oder OSM-Daten nach. Der
Bundle enthält die IRIs; wer mehr will, föderiert. Ein Registry, die fremde
Bestände mitkopiert, ist beim nächsten Lauf veraltet und beim übernächsten
falsch.

**Abnahme:** zwei Läufe hintereinander, `git status` sauber; Tripelzahl im
Bericht; keine `urn:`-IRI und kein Blank Node mehr im Ergebnis.

## S5 — SHACL-Gate und Qualitätsbericht

**Ziel:** ein Bundle, der entweder konform ist oder den Build anhält.

**Uploads:** Bundle nach A5.

**Drei Sorten Shapes in `metadata/shapes.ttl`:**

- **Vollständigkeit.** Jedes `dcat:Dataset` im Katalog braucht Titel, Lizenz,
  Identifier, mindestens eine Distribution und genau einen FDO-Typ. Jeder
  `dcat:CatalogRecord` braucht `foaf:primaryTopic`, `dct:source` und
  `fdoreg:sha256`.
- **Ankerprüfung.** Eine `sh:SPARQLConstraint`, die `SELECT DISTINCT ?class`
  über alle `rdf:type`-Objekte im Bundle bildet und jede Klasse meldet, für die
  weder ein Axiom in `crm_bridge.ttl` noch eine materialisierte CRM-Typisierung
  vorliegt. Das ist die Shape, die den Anspruch aus A2 prüfbar macht — alle
  anderen prüfen Felder.
- **Profilverbote.** Je eine Shape gegen die MUST-NOT-Konstrukte aus S3:
  `crm:E55_Type`, `crm:E32_Authority_Document`, `crm:E95_Spacetime_Primitive`,
  `P169i`, `P82a`/`P82b`, `crm:E41`-Instanzen. Sie werden nicht bei uns
  entstehen — sie entstehen, wenn jemand später eine Abbildung „verbessert".

`inference="none"` in pyshacl; SHACL folgt `rdfs:subClassOf` bei `sh:targetClass`
und `sh:class` selbst, die Axiome liegen im Bundle.

**`dist/quality_report.md`** ist der zweite Ausgang und der eigentliche Ertrag
für die Autoren: je Eintrag, was fehlt oder unsauber ist — Lizenz nur als
String, kein `dct:spatial`-IRI, Distribution ohne Rolle, `fdo:title` weicht von
`dct:title` ab. Das sind Warnungen, keine Fehler; erst `--strict` macht sie
tödlich.

**Abnahme:** `conforms = true` für den vollen Bestand, Bericht liegt vor, und
ein absichtlich kaputt gemachtes Eingabe-TTL bringt das Gate zum Anschlagen.
Eine Shape, die nie ausgelöst hat, ist ungeprüft.

## S6 — Registry-Index und Facettenseite

**Ziel:** eine Seite, die sofort da ist und auf der man in fünf Sekunden vom
Katalog zum Objekt kommt.

**Uploads:** Bundle nach A5.

`py/build_index.py` fragt den Bundle mit SPARQL ab und schreibt
`dist/registry-index.json`: je Eintrag Titel, FDO-Typ, Lizenz, Creator,
Keywords (Label + IRI), Ort (Label + WKT), Zeitraum, DOI, Dateizahl,
Gesamtgrösse, Rollenverteilung. Sortierte Schlüssel, keine Zeitstempel.

`docs/index.html` ist statisch, ohne Framework: Facetten links (Typ, Lizenz,
Keyword, Ort, Jahr, Creator), Kachelliste rechts, Detailansicht je Eintrag mit
Link auf Zenodo, auf die SquirrelBase-Q-ID, wo vorhanden, und auf das
FDO-Metadaten-TTL. Ein Facettenklick, der über die Facetten hinausgeht, springt
mit vorbelegter Query auf `sparql.html`.

**Abnahme:** die Seite lädt ohne Netz aus dem Repo heraus (`file://` genügt für
den Test), jeder Eintrag ist über mindestens eine Facette erreichbar, und die
Zahl der Kacheln stimmt mit `dcat:record` im Bundle überein.

## S7 — SPARQL-Seite

**Ziel:** dieselbe Frage im Browser stellen können, die man sonst gegen einen
Endpoint stellen würde — ohne Endpoint.

**Uploads:** Bundle nach A5.

Das Muster kommt aus der `wdt-*`-Familie und wird übernommen, nicht neu
erfunden: `queries.yaml` als einzige Quelle, daraus erzeugt
`py/build_sparql.py` die Seite `docs/sparql.html` (rdflib unter Pyodide) und die
Abfragen als `.rq` unter `docs/downloads/queries/`. Präfixe stehen in einem
Block, nicht in jeder Abfrage.

**Jede Abfrage wird beim Build gegen den echten Bundle ausgeführt, und eine
Abfrage ohne Ergebniszeilen bricht den Build ab.** SPARQL scheitert nicht an
einer falsch geschriebenen IRI, es liefert nichts — ein leeres Ergebnis ist
also das übliche Symptom eines kaputten Graphen, nicht einer langweiligen Frage.

**Startsatz an Abfragen**, aus dem, was die Papiere über den Bestand behaupten:

- alle FDOs mit Typ, Lizenz und Dateizahl
- alle 3D-Modelle mit Koordinate, als WKT für den Export nach QGIS
- alle Distributionen mit `fdo:role = model` samt Format und Grösse
- alle Objekte, die auf dasselbe Wikidata-Konzept zeigen
- alle FDOs eines Creators über alle Pakete hinweg
- Bestand je Lizenz und je Jahr
- alle Klassen im Bundle mit ihrem CRM-Anker — die Abfrage, die den Anspruch
  aus A2 auch für Leser sichtbar macht

**Abnahme:** die Seite antwortet auf allen Abfragen im Browser; die `.rq`-Dateien
liefern gegen `dist/fdo-registry.ttl` dieselben Ergebnisse.

## S8 — Registry als FDO, Release und CI

**Ziel:** der Katalog wird nach denselben Regeln zitierbar wie sein Inhalt.

`MD.cff` und `CITATION.cff` fürs Repo, `fdo_type: fdo:AnalysisFDO` (oder ein
neuer `fdo:RegistryFDO` — in S8 zu entscheiden, betrifft `fdo-squirrel`). Der
Bundle plus Index plus Shapes werden als ZIP durch `fdo-squirrel` geschickt und
nach Zenodo publiziert. Der so entstehende DOI kann in `sources.json` — die
Registry katalogisiert sich selbst, und der Rundlauf ist zugleich der beste
Integrationstest.

Zwei GitHub Actions: eine baut bei jedem Push `main.py --strict` und schlägt bei
rotem Gate fehl, eine deployt `docs/` nach Pages.

## S9 — N4O-Andockung

**Ziel:** aus dem Bundle wird ein Named Graph im NFDI4Objects Knowledge Graph.

Der Weg dorthin ist ein Eintrag in `n4o-collections.json`
(<https://github.com/nfdi4objects/n4o-databases>), der dem `collection-schema.json`
des `n4o-graph-importer` entspricht; die Daten landen dann in einem eigenen
Graphen unter `https://graph.nfdi4objects.net/collection/<n>`.

**Vor dem Antrag zu klären:**

- Welche Lieferform der Importer erwartet (Dump-URL, Format, Aktualisierung) und
  ob eine GitHub-Pages-URL als Quelle taugt.
- Ob die Registry als eigene *Collection* geführt wird oder als Datenbank in
  `n4o-databases.csv` — sie ist beides ein bisschen: ein Repositorium von
  Verweisen auf Zenodo.
- Ob eine Wikidata-Item für die Registry angelegt werden soll; `n4o-databases`
  zieht Zusatzangaben von dort.
- Verhältnis zur N4O Objects Ontology und zu MaCHeCO: die Anker in S3 zeigen auf
  CRM direkt. Ob N4O stattdessen die Verknüpfung über die Anwendungsontologie
  erwartet, ist mit A. Noback und A. Gerber zu klären — das ist eine Frage an
  Menschen, keine an die Dokumentation.

---

# Teil D — Offene Punkte

- **Verhältnis zur SquirrelBase.** Die SquirrelBase hält je Objekt die FDO-URL,
  die Registry hält je FDO die Metadaten. Beide könnten voneinander lesen. Der
  saubere Schnitt wäre: die Registry nimmt die Q-ID aus dem FDO auf, wenn sie
  dort steht, und fragt die SquirrelBase sonst nicht. Zu entscheiden, wenn die
  ersten Einträge stehen — vermutlich in S6.
- **Wer darf einreichen.** Bislang kuratiert (A4). Sobald Dritte FDOs beitragen
  wollen, braucht es einen Weg: Pull Request auf `sources.json` mit
  CI-Prüfung wäre der billigste. Erst relevant, wenn es Dritte gibt.
- **Zenodo als einzige Quelle.** Der Ernter kennt heute nur die Zenodo-API. Ein
  FDO auf einem anderen Repositorium wäre über eine direkte TTL-URL im
  `sources.json` einzubinden; das würde die Prüfsummen-Logik ändern.
- **`fdo:RegistryFDO`.** Falls S8 einen neuen FDO-Typ braucht, gehört er nach
  `fdo-squirrel`, nicht hierher — und dann ist die Beschlusslage in A4 zum
  Ort des Ankers ohnehin nochmal zu betrachten.
- **Endpunkt der Community-Suche.** Vier Formen, alle 400 (Stand 2026-09-03).
  Zu klären mit drei Aufrufen, jeder auf einer Zeile:

  ```cmd
  curl -s -o nul -w "%{http_code} communities/slug\n" https://zenodo.org/api/communities/squirrel-fdo
  curl -s -o nul -w "%{http_code} communities/slug/records\n" https://zenodo.org/api/communities/squirrel-fdo/records
  curl -s -o nul -w "%{http_code} records?q=slug\n" "https://zenodo.org/api/records?q=parent.communities.entries.slug:%22squirrel-fdo%22"
  ```

  Antwortet die erste Zeile mit 200 und die zweite mit 400, liegt es am
  Unterpfad; antwortet auch die erste nicht, stimmt der Slug nicht — die
  Community-URL im Browser sagt dann, wie er wirklich heisst. Was 200 liefert,
  wandert als erster Eintrag in `COMMUNITY_SEARCH`. Bis dahin ist die Ernte
  davon unberührt: die Suche ergänzt `sources.json` um Vorschläge, sie füttert
  sie nicht.
- **Personen-URN über Paketgrenzen.** Ist `urn:fdo-squirrel:person/<hash>` für
  denselben Menschen in zwei Paketen gleich, wäre eine Umschreibung je Record
  falsch — sie würde eine Person vervielfachen, die die Quelle bereits
  zusammengeführt hat. Entscheidet sich an einem zweiten TTL, spätestens in S3.
- **`<DOI>_geom` und `<DOI>_temporal`.** Vom Generator geprägte IRIs in einem
  fremden Namensraum (A1, Befund 6). Umschreiben verletzt A3, Stehenlassen
  veröffentlicht DOI-artige IRIs, die nicht auflösen. In S4 zu entscheiden;
  die saubere Lösung liegt upstream.
- **Rückfluss nach `fdo-squirrel`.** Der Beschluss lautet „Registry zuerst,
  upstream später". Wann später ist, hängt an S3: sobald die Abbildung ein
  echtes Paket unbeanstandet durchs Gate bringt, ist sie reif für den
  Generator. Der Qualitätsbericht aus S5 sagt, was dabei zuerst zu reparieren
  ist.
