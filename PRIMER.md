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
7. **~~`fdo:role` hat vier Werte, nicht drei.~~ Korrigiert 2026-09-03 in S3:
   sechs Werte über den ganzen Bestand.** `software` (311), `documentation`
   (123), `script` (28), `model` (12), `data` (9), `metadata` (8). Die vier aus
   dem Auftaktchat stammten aus einem einzigen 3D-Paket; die Software-Pakete
   bringen `software` und `script` mit. Das SKOS-Vokabular hat sechs Konzepte,
   flach — die Quelle kennt keine Hierarchie zwischen den Werten, und eine hier
   erfundene wäre Struktur, die in keinem Paket steht.

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

**Befunde am vollen geernteten Bestand** (geprüft 2026-09-03 in S3 an allen
sieben `fdo-metadata.ttl` unter `data/raw/fdo/`, zusammen 4845 Tripel):

10. **Vier von sieben TTL sind kein gültiges Turtle.** Zwei Defektklassen:
    `18369126`, `18369157` und `18369866` benutzen `crm:` und `crmdig:`, ohne
    die Präfixe je zu deklarieren; `18369866` und `18732893` haben unescapte
    Anführungszeichen im JSON-Literal an `dct:provenance`. Beides sind
    Generator-Jahrgänge, beides ist upstream repariert worden — die neueren
    Pakete (`18742694`, `18744133`, `18744583`) sind sauber. Unter A3 hat die
    Registry damit heute **drei** lesbare Einträge, nicht sieben. Wer die
    Zahlen auf der Seite mit den Papieren vergleicht, muss das wissen.
11. **Die Personen-URN ist über Paketgrenzen hinweg stabil.**
    `urn:fdo-squirrel:person/8e916ce55425de21` ist in vier verschiedenen
    Records dieselbe Person (Thiery, Florian). Damit ist der offene Punkt aus
    Teil D entschieden und der Beschluss in A4 war falsch: eine Umschreibung je
    Record würde dieselbe Person vervierfachen. Die Umschreibung muss
    registry-global sein.
12. **Zwei Personendialekte.** Die älteren Pakete tragen ORCID-IRIs direkt
    (`18369126`, `18369157`, `18369866`), die neueren die Personen-URN — der
    Generator hat unterwegs aufgehört, ORCIDs zu benutzen. Das
    Anwendungsprofil will ausdrücklich die etablierte IRI (DOI, ORCID, ROR).
    Rückmeldung an `fdo-squirrel`. **Ergänzt 2026-09-03 in S4:** die beiden
    Dialekte treffen sich in derselben Person. „Thiery, Florian" steht in den
    älteren Paketen als `orcid.org/0000-0002-3246-3531` und in den neueren als
    `urn:fdo-squirrel:person/8e916ce55425de21`. Vier Menschen im Bestand, fünf
    Knoten. Zusammenführen darf das nur ein Mensch (A4).
13. **Drei Zeilen der Entwurfsabbildung haben keine Quelle in den Daten.** Es
    gibt keinen Knoten für das physische Objekt — FDO und Objekt sind derselbe
    Knoten, `crm:E22` lässt sich also nicht verankern, ohne einen Knoten zu
    erfinden. `technique.acquisition` überlebt nur als undurchsichtiges
    JSON-Literal an `dct:provenance` (`{"software": "KIRI Engine", …}`), also
    haben `crmdig:D2`, `D8` und `crm:P16` keine strukturierte Quelle. Und
    `fdo:AnalysisFDO` kommt im Bestand nicht vor: beide „Analyse"-Pakete sind
    `fdo:SoftwareFDO`. Die Entwurfstabelle war aus `MD.cff` gedacht — die
    Registry sieht aber nur das TTL.
14. **Das Subjekt im TTL ist die Concept-DOI, nicht die Versions-DOI.**
    Record `18744133` beschreibt `zenodo.18724635`, Record `18744583`
    beschreibt `zenodo.18369720`. Der Dataset-Knoten des Bundles trägt damit
    eine IRI, die auf ein bewegliches Ziel zeigt; die feste Kennung sitzt am
    `dcat:CatalogRecord`. **Bestätigt 2026-09-03 in S4** an allen sieben
    lesbaren Paketen: das Subjekt ist ausnahmslos die Concept-DOI aus
    `harvest.json`. Der Build prüft das je Paket und meldet jede Abweichung;
    genau darauf ruht die Katalogidentität in A4.
15. **Zeiten stehen als `xsd:integer`.** `dcat:startDate "300"^^xsd:integer`
    am `dct:PeriodOfTime`-Knoten. Das Profil listet für Zeitwerte nur
    `xsd:*`-Datumstypen und EDTF; `xsd:integer` ist keiner davon.
16. **`dcat:bbox` gibt es auch**, in zwei Paketen, als DCAT-Zeichenkette. Das
    Profil bevorzugt `geo:hasBoundingBox`. Wird gemeldet, nicht umgeschrieben.

**Befunde aus dem ersten Gate-Lauf** (geprüft 2026-09-03 in S5 gegen den
Bundle aus S4, 6582 Tripel):

17. **Die Ankerprüfung „pro Klasse" widerspricht A3.** Als `SELECT DISTINCT
    ?class` ausgeführt meldet sie 11 Klassen ohne Anker, darunter
    `schema:Person`, `dcat:Distribution` und `dct:PeriodOfTime` — also genau
    die, deren Anker A3 ausdrücklich je Instanz materialisiert, statt ein
    Klassenaxiom über einen fremden Namensraum zu behaupten. Die Shape hätte
    bemängelt, dass die Regel eingehalten wurde. Pro Knoten gefragt blieben
    vier Sorten ohne CRM-Typ: 7 `dcat:CatalogRecord`, 1 `dcat:Catalog`, 7
    `sf:Point` und die 6 Rollenkonzepte. Die richtige Frage ist, ob jedes
    beschriebene Ding CRM erreicht, nicht ob jede Klasse es tut.
18. **Die Axiome lagen nicht im Bundle**, anders als die Planung in S5
    annahm. `metadata/crm_bridge.ttl` ist eine eigene Datei, und der Bundle
    trägt nur `dct:conformsTo` darauf. Gegen pyshacl 0.40 geprüft: `sh:targetClass`
    und `sh:class` folgen `rdfs:subClassOf` tatsächlich ohne Inferenz, aber nur
    für Axiome im validierten Graphen. Ohne die Brücke verlieren `skos:Concept`,
    `sf:Point` und der ganze `D14`-Weg ihren Anker.
19. **Das Profil verbot, was S4 baute.** Der Bundle trug 7 ×
    `crm:P82a_begin_of_the_begin` und 7 × `crm:P82b_end_of_the_end`. Das Profil
    sagt zu diesen Properties wörtlich, sie sollten zugunsten von EDTF und Time
    Ontology *nicht* benutzt werden, und führt `E52 Time-Span` in RDF als
    „Literal oder `time:Interval`". Härtegrad beachten: `E55`, `E32`, `E95`,
    `P169i` sind MUST NOT, die Zeitgrenzen nur ein SHOULD NOT.
20. **Kein `dcat:Dataset` trägt `dct:identifier`.** Die geplante
    Vollständigkeits-Shape hätte auf allen sieben angeschlagen. Die DOI *ist*
    die Knoten-IRI, und das Profil will Identifier ausdrücklich als IRI — hier
    gehörte die Shape korrigiert, nicht der Bundle.
21. **Die MUST-NOT-Konstrukte kommen im Bestand null mal vor.** Fünf der 38
    Regeln können gegen den heutigen Bestand gar nicht auslösen. Ohne
    absichtlich kaputte Eingabe wäre ihr Grün bedeutungslos; das ist der Grund
    für `metadata/shapes_selftest.ttl`.
22. **`dct:spatial`-Objekte trugen kein `crm:E53_Place`**, obwohl die Notiz in
    `fdo--crm.csv` das behauptete. Eine Abbildung, die in der CSV steht und im
    Code fehlt, ist schlimmer als eine, die fehlt: sie sieht erfüllt aus.
    Seit S5 typisiert die Zeile `dct:spatial@object` die sieben
    OpenStreetMap-IRIs je Instanz.
23. **Die Ankerprüfung je Fokusknoten kostete 18 Sekunden, als SPARQL-Target
    0,9.** `sh:targetSubjectsOf rdf:type` führt die Constraint für jeden der
    rund 1100 typisierten Knoten einzeln aus. Dieselbe Frage als
    `sh:SPARQLTarget` ist eine Abfrage. Bei sechs Paketen ist das Bequemlichkeit,
    bei sechzig wäre es der Unterschied zwischen einem Gate im Standardlauf und
    einem, das jemand herausnimmt.

**Befunde aus dem Seitenbau** (geprüft 2026-09-03 in S6 am Bundle mit 6584
Tripeln):

24. **Die IRIs, auf die die Pakete zeigen, tragen keine Labels.** Sieben
    Wikidata-Konzepte und sieben OpenStreetMap-Objekte stehen im Bundle mit
    genau einem Tripel — ihrem `rdf:type` aus der Instanz-Verankerung. Kein
    `rdfs:label`, kein `schema:name`. Die Facette „Ort" heisst damit ohne
    Zutun „OSM relation 62273". Auflösen darf die Registry sie nicht (A3, Netz
    nur in S2), erfinden erst recht nicht — deshalb die kuratierte Tabelle in
    A4. Gegenbeispiel im selben Bundle: die `dct:PeriodOfTime`-Knoten *haben*
    `rdfs:label` („Ogham stone inscriptions (ca. 4th–7th century CE)") und
    `owl:sameAs` auf ChronOntology. Der Generator kann es also, er tut es nur
    für Orte und Konzepte nicht — Rückmeldung an `fdo-squirrel`.
25. **`file://` und `fetch()` vertragen sich nicht.** Eine Seite, die ihren
    Index per `fetch()` nachlädt, scheitert lokal geöffnet an der
    Same-Origin-Regel (Origin `null`) — in Chrome und seit Firefox 68 auch
    dort. Die Abnahme von S6 verlangt genau diesen Test, also ist der Index in
    `docs/index.html` eingebettet und liegt zusätzlich als eigene Datei
    daneben. Das kostet 34 KB doppelt und ist der Preis dafür, dass die Seite
    ohne Server funktioniert.
26. **`prov:wasDerivedFrom` zeigt auf das ZIP, nicht auf das TTL.** Der
    Katalogeintrag trägt die Zenodo-Content-URL des Pakets (196 MB bei
    18744133); der Membername steht nur in `harvest.json`, nicht im Graphen.
    Eine Detailseite, die den Link mit „fdo-metadata.ttl" beschriftet, lügt um
    zwei Grössenordnungen. Sie beschriftet ihn jetzt als Paket.
27. **Die Ausgabe war plattformabhängig.** `dist/quality_report.md` nennt
    seine Eingaben über `Path.relative_to()` und schrieb damit unter Windows
    `dist\fdo-registry.ttl`, unter Linux `dist/fdo-registry.ttl`. Zwei
    Rechner, dieselben Daten, verschiedene Bytes. Seit S6 geht alles, was in
    eine Datei geschrieben wird, durch `registry_utils.rel()`. Determinismus
    je Rechner reicht nicht, sobald mehr als ein Rechner baut.

**Befunde aus dem ersten Lauf auf einem echten Rechner** (2026-09-03, Windows,
Browser):

28. **Die Facettenfilterung wählte richtig aus und blendete nichts aus.**
    Zähler und Facettenzahlen stimmten („1 of 7"), auf dem Schirm standen
    weiter alle sieben Kacheln. Ursache ist nicht JavaScript, sondern die
    Kaskade: `hidden` ist nur im *User-Agent*-Stylesheet `display: none`, und
    **jede** Autorenregel schlägt das User-Agent-Stylesheet — die eigene Regel
    `.card { display: flex }` hielt also genau die Kacheln sichtbar, die das
    Skript versteckt hatte. Behoben durch `.card[hidden] { display: none }`.
    Lehre für die Prüfung, nicht nur fürs CSS: die statische Kontrolle im
    Sandkasten (eingebettetes JSON parst, kein `fetch`, Skript
    syntaxgeprüft, Filterlogik ausserhalb des Browsers durchgerechnet) hat
    **jede** dieser Aussagen bestätigt und den Fehler trotzdem nicht gesehen,
    weil er im Rendern sitzt. Auch `jsdom` meldet hier fälschlich Erfolg — es
    gibt dem User-Agent-Stylesheet den Vorrang, den ein Browser ihm nicht
    gibt. Eine Seite ist erst geprüft, wenn ein Browser sie gezeichnet hat.
29. **Erzeugte Textdateien tragen unter Windows CRLF.** `Path.write_text()`
    übersetzt `\n` in `os.linesep`; dieselbe Zeile Python schreibt also unter
    Windows andere Bytes als unter Linux — in jeder erzeugten Datei, nicht nur
    im Bericht aus Befund 27. Git versteckt das beim Commit meist über
    `core.autocrlf`, was es gefährlicher macht statt harmloser: der
    Byte-Vergleich zweier Rechner wird dadurch bedeutungslos, ohne dass jemand
    etwas merkt. Seit S6a schreibt alles über `registry_utils.write_text()`
    mit `newline="\n"`. Nachtrag vom selben Tag: der Lauf auf dem Zielrechner
    hat `core.autocrlf=true` und meldete beim `git add` dreimal „LF will be
    replaced by CRLF the next time Git touches it". Harmlos, aber es zeigt,
    dass das Verhalten am Klon hängt und nicht am Repository — deshalb die
    `.gitattributes`. Geprüft: `git add --renormalize .` gegen den
    unveränderten Klon ändert nichts, die abgelegten Blobs sind bereits LF.

**Befunde aus dem Bau der Abfrageseite** (geprüft 2026-09-03 in S7 an denselben
6584 Tripeln):

30. **Die Templates werden nicht escaped, und niemand hat es gemerkt.**
    `select_autoescape(["html"])` vergleicht das Ende des Dateinamens; alle
    Templates hier heissen `*.html.j2` und enden auf `.j2`, also liefert der
    Helfer `False`. `step_site` und `step_bridge` glauben seit S6, sie escapen,
    und tun es nicht. **Nachtrag aus S6b, 2026-09-03: der Fehler war nicht
    folgenlos.** Das WKT-Literal beginnt mit
    `<http://www.opengis.net/def/crs/EPSG/0/4326>`; roh in ein `<code>`
    geschrieben nimmt der HTML-Parser das für ein unbekanntes Element und wirft
    es weg. Sieben Detailseiten zeigten ihre Koordinate ohne CRS, und niemand
    hat es gesehen, weil die Zeile plausibel aussieht. Behoben in S6b (A4).

31. **Zwei rdflib-Fallen in einer Abfrage.** `OPTIONAL { … UNION … }` bindet in
    rdflib nichts: die Anker-Abfrage lief durch, meldete 7 statt 24 Zeilen und
    liess die per Instanz verankerten Klassen leer aussehen — ein falsches
    Ergebnis, das wie ein Befund über den Graphen aussah. Und
    `GROUP_CONCAT(DISTINCT ?x)` wirft `NotBoundError`, sobald `?x` in einer
    Zeile ungebunden ist, statt sie zu überspringen. Beides umgangen: zwei
    getrennte `OPTIONAL`-Blöcke, `COALESCE(?x, "")` in der Aggregation. Die
    zwei Spalten sind ohnehin die bessere Auskunft, weil sie die beiden
    Ankermechanismen aus A3 trennen, statt sie zu einer Liste zu verrühren.
32. **Der Bundle allein beantwortet zwei der acht Fragen nicht.** Die
    Rollenkonzepte stehen darin mit genau einem Tripel — ihrem `rdf:type` —,
    die `skos:prefLabel` liegen in `vocab/role.ttl`, die Klassenaxiome in
    `crm_bridge.ttl`. Das ist Befund 18 aus Sicht eines Lesers und kein Mangel:
    A3 verbietet die Axiome im Bundle. Die Seite lädt die drei
    Vokabulardateien deshalb je Abfrage dazu (A4) — und macht damit sichtbar,
    wo diese Aussagen wirklich stehen.
33. **Die `content/`-IRIs sind doppelt prozentkodiert.** Die Quelle schreibt
    `urn:fdo-squirrel:content/docs%2Fjs%2Fjsts.js`, `content_iri()` quotet
    erneut, im Bundle steht `…/content/docs%252Fjs%252Fjsts.js`. Eindeutig ist
    das, auflösbar nicht: `%252F` dekodiert zu `%2F`, nicht zu `/`. Ein Fehler
    aus S4, den erst eine Abfrage über `dcat:accessURL` sichtbar gemacht hat.
    Nicht in S7 repariert — die Umschreibung zu ändern heisst Bundle, Gate und
    beide Seiten neu zu bauen; siehe Teil D.
34. **Die Personenabfrage zählt fünf, die Facette vier.** Kein Widerspruch,
    sondern Befund 12 an der Oberfläche: „Thiery, Florian" ist im Graphen zwei
    Knoten (ORCID und Registry-Agent), die Facettenseite führt sie unter einem
    Namen zusammen. Genau deshalb ist der Gegentest in A4 auf Lizenz, Jahr und
    Eintragszahl beschränkt und nicht auf die Creator-Facette: dort *müssen*
    beide verschieden zählen, und das steht in der Einleitung der Abfrage.

**Was das Anwendungsprofil nicht abdeckt** (geprüft 2026-09-03 an
<https://nfdi4objects.github.io/crm-rdf-ap/>, Fassung 2025-01-27, Jakob Voß):
Es behandelt CRM-Kern, SKOS, GeoSPARQL, Time Ontology und BIBO. Zu **CRMdig
sagt es kein Wort** — weder erlaubend noch verbietend. Genau dort sitzt aber
der Kern unserer Abbildung, das Digitalobjekt. Die Verbotsliste in S3 ist
gegen die Quelle geprüft und stimmt vollständig. Eine Unstimmigkeit im Profil
selbst: Abschnitt 3 nennt `skos:Concept` eine Unterklasse von „E27 Conceptual
Object", Abschnitt 7 von `E28 Conceptual Object`. E27 ist *Site*; E28 ist
gemeint. Die Brücke benutzt E28 und meldet es upstream.

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

**Befunde zur N4O-Andockung** (geprüft 2026-09-04, vor dem eigentlichen S9 —
Flo hat den Umfang korrigiert: kein Eintrag in `n4o-collections.json` durch
uns, das macht VZG von Hand; unsere Aufgabe endet bei einem Bundle, das durch
`n4o-rse/n4o-kg-profile` validiert):

35. **Der Selbsteintrag der Registry braucht keinen neuen Code — er ist
schon gebaut.** `python main.py --only release` (S8) tatsächlich laufen
lassen (nicht nur gelesen): `fdo-squirrel` staged `dist/fdo-registry.ttl` + `dist/registry-index.json` + `metadata/shapes.ttl` + `MD.cff` + `CITATION.cff`
zu einem ZIP und erzeugt daraus `dist/release/fdo-metadata.ttl` — Subjekt
`<https://github.com/FDOx-squirrel/fdo-squirrel-registry>`, typisiert
`a dcat:Dataset, crmdig:D1_Digital_Object, crm:E73_Information_Object, fdo:RegistryFDO`. A2s Versprechen „der erste Eintrag der Registry kann die Registry sein" ist
damit mechanisch eingelöst, sobald ein Mensch drei Dinge tut, die alle schon
vorgesehen sind: `dist/release/..-fdo-bundle.zip` auf Zenodo veröffentlichen,
die DOI als neunten Eintrag in `sources.json` eintragen (wie jeder andere),
`harvest` + `bundle` neu laufen lassen. Kein neuer Zweig in `step_bundle.py`.
36. **`n4o-rse/n4o-kg-profile` hat keinen `v1`-Tag.**
`git ls-remote --tags https://github.com/n4o-rse/n4o-kg-profile.git` liefert
nichts. Ein `uses: …@v1`, wie das Repo selbst es dokumentiert, hat also
aktuell nichts, worauf es auflösen könnte.
37. **`n4o-kg-profile`s eigene `action.yml` checkt einen Org-Pfad aus, der
404 gibt.** `actions/checkout` darin zeigt auf
`Research-Squirrel-Engineers/n4o-kg-profile` — die Org existiert (200), das
Repo liegt dort aber nicht (404, kein Redirect). Anders als bei Befund 38:
das ist keine stehen gebliebene Umbenennung mit funktionierendem Redirect,
sondern ein Pfad, der nie dorthin gezeigt hat. Betrifft jeden Aufruf der
Action, unabhängig davon, mit welchem Ref eine aufrufende Collection sie
einbindet — der kaputte Checkout sitzt in der Action selbst, S9 kann ihn
nicht von aussen umgehen. Browser-Beleg: `curl -w "%{http_code}"` auf
`.../Research-Squirrel-Engineers/n4o-kg-profile` → 404, auf
`.../n4o-rse/n4o-kg-profile` → 200.
38. **Nebenbefund, unkritisch:** `CITATION.cff` in diesem Repo trägt noch
`repository-code: https://github.com/Research-Squirrel-Engineers/fdo-squirrel-registry`. Anders als Befund 37 löst das auf — `fdo-squirrel-registry` und
`fdo-squirrel` sind tatsächlich von `Research-Squirrel-Engineers` zu
`FDOx-squirrel` transferiert worden, GitHub hält den Redirect (200, `curl -w "%{url_effective}"` zeigt die neue URL). Kosmetisch falsch, nicht blockierend;
Korrektur bei Gelegenheit.

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
- **Der Bundle ist N4O-anschlussfähig.** Zielbild ist ein Bundle, das alle
  geernteten FDO-TTL plus die Registry selbst als DCAT enthält, vollständig an
  CIDOC CRM verankert, und das durch `n4o-rse/n4o-kg-profile` SHACL-validiert
  in einem eigenen Collection-Repo liegt (S9). Der Eintrag in
  `n4o-collections.json` und damit der Named Graph unter
  `https://graph.nfdi4objects.net/collection/<n>` ist **nicht** unsere
  Aufgabe — das trägt VZG von Hand ein, sobald das Bundle steht (korrigiert
  2026-09-04, A4). Dafür genügt CRM nicht, es muss das Anwendungsprofil sein
  (A3).
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
- **Genau zwei Ausnahmen davon**, beide mechanisch, beide in `prov:`-Aussagen
  am `dcat:CatalogRecord` festgehalten, beide in S4: die Umschreibung der
  paketrelativen `urn:fdo-squirrel:*`-IRIs in Registry-IRIs (A1, Befund 2) und
  die Normalisierung der abgekürzten Klassen-IRIs `crm:E73`, `crmdig:D1`,
  `crmdig:D9` auf ihre offiziellen Formen (Befund 3, A4). Die zweite repariert
  eine Kodierung, keine Aussage: `crmdig:D1` löst nicht auf und trifft kein
  Vokabular, `crmdig:D1_Digital_Object` sagt dasselbe und tut es.
  Skolemisierung steht hier nicht mehr — es gibt im ganzen Bestand keinen
  einzigen Blank Node (Befund 4).
- **Nicht parsebares Turtle wird nicht zurechtgebogen.** Ein geerntetes TTL,
  das rdflib nicht liest, wird übersprungen, mit Grund und Zeilennummer
  gemeldet und geht in den Qualitätsbericht. Alle Schritte lesen den Bestand
  über `registry_utils.read_fdo_graph()`, damit sie sich nie darüber uneinig
  sind, welche Pakete drin sind.
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
| Registry-Namensraum | `https://w3id.org/fdo-squirrel/registry/`, Präfix `fdoreg:` — hängt unter den bestehenden FDOx-Namensraum | 2026-09-03, bestätigt in S3 (Rollen-Schema) |
| DOI-Pinning | `sources.json` hält Concept-DOI **und** gepinnte Versions-DOI; geerntet wird die gepinnte. `main.py check-updates` meldet neuere Versionen, ändert aber nichts | Vorschlag |
| Records ohne `fdo-metadata.ttl` | erscheinen **gar nicht** im Katalog — kein leerer `dcat:CatalogRecord` — und werden im Qualitätsbericht genannt; das ZIP wird nicht durch `fdo-squirrel` gejagt. Ein Eintrag, der nichts beschreibt, wäre auf der Facettenseite ein Treffer ohne Inhalt | 2026-09-03, bestätigt in S4 |
| IRI-Umschreibung | `urn:fdo-squirrel:dist/<sha>` → `<record-IRI>/dist/<sha>`, `urn:fdo-squirrel:content/<pfad>` → `<record-IRI>/content/<pfad>`; die Originale bleiben als `dct:identifier` erhalten | 2026-09-03, bestätigt in S4 |
| ~~Personenknoten je Record~~ | hinfällig: `<record-IRI>/agent/<slug>` hätte denselben Menschen je Paket einmal angelegt. Siehe die registry-globale Fassung weiter unten | hinfällig 2026-09-03 |
| CRM-Profil | N4O-Anwendungsprofil (crm-rdf-ap), nicht die offizielle RDF-Kodierung. Abweichungen in S3 tabelliert; die eine echte Lücke ist CRMdig, siehe unten | 2026-09-03, bestätigt in S3 |
| Facettenseite | eigenes `dist/registry-index.json`, beim Build erzeugt; SPARQL bleibt der zweiten Seite vorbehalten. Niemand soll auf eine WASM-Runtime warten, um nach „3D" zu filtern | Vorschlag |
| Bundle im Repo | ja, `dist/fdo-registry.ttl` ist versioniert — er ist das zitierbare Erzeugnis und Eingabe der Seite. `dist/fdo-registry.nt` liegt daneben: es ist die kanonische Form, und der Byte-Vergleich zweier Läufe geschieht an ihm | 2026-09-03, bestätigt in S4 |
| Lizenz | Code MIT wie `fdo-squirrel`; der Bundle CC BY 4.0 (`dct:license` am Katalogknoten), Lizenzen der geernteten FDOs bleiben je Eintrag erhalten | 2026-09-03, bestätigt in S4 |
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
| Was im Katalog landet | `registry/sources.json`, nicht der Inhalt von `data/raw/fdo/`. Verzeichnisse, die nicht mehr gepinnt sind, werden von späteren Schritten ignoriert, beim Ernten benannt und nur mit `--prune` entfernt | 2026-09-03 |
| Zurückziehen eines TTL | nur wenn das Paket wirklich gelesen wurde und die Datei nicht enthält. Ein Lauf, der nicht nachsehen konnte, ändert nichts auf der Platte und meldet `unchecked` | 2026-09-03 |
| Nicht implementierte Schritte | melden `pending`, sobald ihre Eingabe da ist, statt zu werfen. Sonst bricht der Rauchtest genau in dem Moment, in dem der vorige Schritt zu liefern beginnt | 2026-09-03 |
| Netzausfall | ein nicht erreichbarer Record ist eine Aussage über Zenodo, nicht über den Record: nichts wird geschrieben, nichts gemerkt, der Lauf geht weiter. Nach drei Ausfällen in Folge bricht er ab und sagt, dass Zenodo nicht antwortet. Exitcode ≠ 0, damit die CI es merkt | 2026-09-03 |
| Zenodo-Endpunkte | Community-Suche über `/api/communities/<slug>/records`, **ohne selbst gebaute Query-Parameter**: erste Seite nackt, danach `links.next` folgen. `size`/`page` anzuhängen quittiert Zenodo mit 400, der nackte Pfad mit 200 (geprüft 2026-09-03). `check-updates` probiert die bekannten Formen der Reihe nach und schreibt in den Bericht, welche geantwortet hat. Ein Bericht ist keinen kaputten Build wert | 2026-09-03 |
| ~~Nicht parsebare TTL~~ | ersetzt: das Überspringen kostete vier von acht FDOs **dauerhaft**, weil ein publizierter Zenodo-Record unveränderlich ist und eine Korrektur in `fdo-squirrel` diese vier nie erreicht. Siehe die Zeile darunter | ersetzt 2026-09-03 |
| Nicht parsende TTL | werden mit **deklarierten Reparaturen** gelesen (`py/repair.py`): fehlende `@prefix`-Zeile, unmaskiertes `\"` in einem einzeiligen Literal. Beide Defekte hat derselbe Generator später behoben, die Sollform steht also in einem Februarpaket und ist nicht erfunden. Jede Reparatur wird benannt — im Log, auf der Crosswalk-Seite und als `fdoreg:readRepair` am Katalogeintrag —, und `fdoreg:sha256` bleibt der Hash der **Originaldatei**. Was ohne Raten nicht zu reparieren ist, bleibt ungelesen | 2026-09-03, ersetzt den Beschluss vom selben Tag |
| Grenze der Reparatur | nur die **Kodierung**, nie die Aussage. Die drei widersprüchlichen `dct:description` in 18732893 („make 3d model available", „good", „low") werden nicht angefasst: welcher Wert wohin gehört, wüsste nur der Autor. Sie sind ein Datenfehler und gehören in den Qualitätsbericht (S5) | 2026-09-03 |
| Identität eines Katalogeintrags | DCAT trägt die in S0 offene Versionsfrage von selbst: `dcat:Dataset` ist das FDO, identifiziert durch die **Concept-DOI** — genau die IRI, die das geerntete TTL als eigenes Subjekt führt (Befund 14) —, `dcat:CatalogRecord` ist der Eintrag zu **einer gepinnten Version**. Zwei gepinnte Versionen desselben FDO geben zwei Records über einem Dataset, ohne Zusatzmodell und ohne Doppelzählung. Der Build prüft je Paket, dass Subjekt und Concept-DOI übereinstimmen | 2026-09-03 |
| Gleichnamige Personen | werden **nicht** zusammengeführt. „Thiery, Florian" trägt im Bestand zwei Knoten, einen mit ORCID (aus `CITATION.cff`) und einen aus der Personen-URN (aus dem Verzeichnisscan). `owl:sameAs` auf Namensgleichheit zu setzen, erfindet Identität; der Build meldet den Kandidaten und überlässt die Entscheidung einem Menschen | 2026-09-03 |
| `fdo:role` im Bundle | das Literal bleibt, daneben tritt `crm:P2_has_type` auf das SKOS-Konzept aus S3. Das Axiom `fdo:role ⊑ crm:P2_has_type` allein hätte einen String dorthin gesetzt, wo CRM einen Typ erwartet — genau das, was das SHACL-Gate in S5 zurückweisen soll | 2026-09-03 |
| Zeitspanne | `dct:temporal` → `crm:P4_has_time-span`, der Knoten wird `crm:E52_Time-Span`, die Grenzen `crm:P82a_begin_of_the_begin` / `crm:P82b_end_of_the_end` als `xsd:gYear` (`300` → `"0300"`). Die ursprünglichen `dcat:startDate`/`endDate` im `xsd:integer` bleiben unverändert daneben stehen. Die drei Zeilen stehen in `fdo--crm.csv`, damit der Anker dort dokumentiert ist wie jeder andere | 2026-09-03 |
| Präfixe im kanonischen Turtle | der Schreiber besitzt die Präfixtabelle, nicht der Graph: `bind_remaining()` bindet jeden ungebundenen Namensraum sortiert nach IRI. rdflib erfindet sonst `ns1`, `ns2`, … in der Reihenfolge, in der es ihnen begegnet, und die kommt aus einer Menge | 2026-09-03 |
| Bezug des Repos im Chat | Klon von GitHub statt Upload-Bundle, solange der Stand gepusht ist. Näher am Zustand, gegen den der Patch ohnehin geprüft wird — der Preis ist, dass lokal Ungepushtes für den Chat nicht existiert | 2026-09-03 |
| CRMdig trotz Profillücke | bleibt. `fdo:3DDataFDO` → `crmdig:D1_Digital_Object`, `fdo:SoftwareFDO` → `crmdig:D14_Software`, Distributionen → `crmdig:D9_Data_Object`; dazu die aus CRMdig **zitierten** Axiome `D1 ⊑ E73`, `D9 ⊑ D1`, `D14 ⊑ D1`. Damit sieht auch ein Konsument, der nur CRM-Kern liest, jedes FDO als `E73_Information_Object` | 2026-09-03 |
| Abgekürzte Klassen-IRIs | der Bundle soll korrekt sein: `crm:E73`, `crmdig:D1`, `crmdig:D9` werden in S4 durch die offiziellen IRIs ersetzt (`normalise`-Zeilen der Crosswalk-CSV). Das ist die **zweite** erlaubte Ausnahme zu A3 neben der `urn:`-Umschreibung — sie repariert die Kodierung, nicht die Aussage. Ziel bleibt, dass neu publizierte FDOs den aktuellen Stand von `fdo-squirrel` tragen und die Normalisierung leerläuft | 2026-09-03 |
| Fremde Namensräume im Brückenfile | drei Mechanismen statt zwei: `axiom` nur über `fdo:`/`fdoreg:`, `ext-axiom` **wörtlich zitiert** aus der eigenen Ontologie des Terms (CRMdig, GeoSPARQL, das Profil) mit Quellenangabe in der CSV, `instance` für alles andere. Beides wird beim Build geprüft; ein `axiom` über `dcat:` oder ein `ext-axiom` ohne Quelle bricht S3 ab | 2026-09-03 |
| Personenknoten | **registry-global**, nicht je Record: `<registry>/agent/<hash>` aus der Personen-URN, ORCID wo vorhanden. Ersetzt den Beschluss vom selben Tag, der je Record skolemisierte — A1, Befund 11 zeigt, dass die URN paketübergreifend stabil ist und eine Umschreibung je Record dieselbe Person vervielfacht hätte | 2026-09-03, ersetzt den Vorschlag vom selben Tag |
| Rollen-Vokabular | sechs SKOS-Konzepte, flach, unter `https://w3id.org/fdo-squirrel/registry/role/`; verknüpft über `crm:P2_has_type`, nicht über `crm:E55_Type`, das das Profil verbietet. Der Build meldet jeden `fdo:role`-Wert im lesbaren Bestand, der im Vokabular fehlt; unter `--strict` bricht er ab | 2026-09-03 |
| Zwei Crosswalk-CSV | `fdo--crm.csv` ist die Abbildung nach CRM, `fdo-role--skos.csv` das Rollenvokabular. Getrennt, weil das zweite kein Crosswalk ist, sondern eine Begriffsliste, und in `note` gepresste Definitionen später niemand pflegt | 2026-09-03 |
| Zeitspanne — ersetzt | die Zeilen `dcat:startDate → P82a` und `dcat:endDate → P82b` sind hinfällig. Das Anwendungsprofil rät von `P82a`/`P82b` ausdrücklich ab. Stattdessen trägt das FDO den Zeitwert als typisiertes Literal an `crm:P4_has_time-span`: `xsd:gYear` bei gleicher Ober- und Untergrenze, sonst ein EDTF-Level-0-Intervall (`0300/0699`). Der `dct:PeriodOfTime`-Knoten bleibt und wird weiterhin `crm:E52_Time-Span` — die Klasse ist nicht das Problem, die Ausdrucksform war es. Die geernteten `xsd:integer`-Grenzen bleiben unangetastet | 2026-09-03, ersetzt den Beschluss vom selben Tag |
| Wogegen das Gate validiert | Bundle **plus** `crm_bridge.ttl`, `vocab/role.ttl` und `registry_ontology.ttl` als ein Graph. Der publizierte `dist/fdo-registry.ttl` bleibt unverändert; SHACL folgt `rdfs:subClassOf` ohne Inferenz, aber nur für Axiome im validierten Graphen (Befund 18) | 2026-09-03 |
| Was N4O bekommt | genau der Graph, der geprüft wurde: `dist/fdo-registry-n4o.ttl` = Bundle + Brücke + Rollenvokabular + Registry-Vokabular, kanonisch geschrieben. Ein Wissensgraph soll den Graphen bekommen, der durchs Gate ging, und nicht eine Teilmenge davon | 2026-09-03 |
| Ankerprüfung | **je Knoten**, nicht je Klasse. Je Klasse gefragt widerspricht sie A3 und meldet die per Instanz verankerten Klassen als ankerlos (Befund 17). Ausgenommen sind terminologische Knoten (`owl:Ontology`, `owl:ObjectProperty`, `rdfs:Class` …): eine Ontologie-Kopfzeile beschreibt eine Datei, kein Ding im Katalog | 2026-09-03 |
| Katalograhmen im Anker | `dcat:Catalog` und `dcat:CatalogRecord` werden je Instanz `crm:E31_Document`, `foaf:primaryTopic` bekommt `crm:P70_documents` daneben. Der Rahmen ist Teil des Bundles und wird wie alles andere verankert, statt als Ausnahme geführt zu werden | 2026-09-03 |
| Geometrie im CRM | `sf:Point`-Knoten werden je Instanz `crmgeo:SP5_Geometric_Place_Expression`; das ext-Axiom `SP5 ⊑ crm:E73_Information_Object` ist aus CRMgeo v1.0 zitiert. CRMgeo ist die Extension, auf die das Profil in seiner Fußnote zur Geometrie selbst verweist. Über `geo:Geometry` im Allgemeinen wird nichts behauptet | 2026-09-03 |
| Identifier am Dataset | keine eigene `dct:identifier`-Pflicht. Die Concept-DOI ist die Knoten-IRI, das Profil will Identifier als IRI, und eine zweite Fassung derselben DOI als Zeichenkette wäre nur eine weitere Stelle, an der etwas auseinanderlaufen kann. Die Shape prüft stattdessen, dass die Dataset-IRI eine DOI ist | 2026-09-03 |
| Severity im Gate | spiegelt den Modalverb des Profils: MUST NOT und was die Registry über ihre eigenen Einträge verspricht → `sh:Violation`, Build hält an. SHOULD/SHOULD NOT und unsaubere Pakete → `sh:Warning`, Qualitätsbericht | 2026-09-03 |
| Warnungen unter `--strict` | **nicht** tödlich. Die 46 Warnungen betreffen publizierte Zenodo-Records, die unveränderlich sind; eine CI, die deswegen ein Jahr rot ist, liest niemand. Dieselbe Begründung wie bei der Personen-Kollision in S4. Ersetzt „erst `--strict` macht sie tödlich" aus der Planung von S5. `--strict` schlägt hier auf genau eine Sache an, und die ist unsere: eine Regel, die kein Fixture mehr auslöst | 2026-09-03, ersetzt die Planung in S5 |
| Selbsttest des Gates | `metadata/shapes_selftest.ttl` ist ein absichtlich kaputter Graph, gegen den **jede** `sh:message` aus `shapes.ttl` mindestens einmal anschlagen muss; geprüft bei jedem Lauf. Fünf Regeln können gegen den heutigen Bestand nie auslösen (Befund 21) — ohne Fixture wäre ihr Grün bedeutungslos | 2026-09-03 |
| `object-class` als sechster Mechanismus | eine Crosswalk-Zeile darf den **Objekten** einer Property eine Klasse geben (`dct:spatial@object → crm:E53_Place`). Nur als `instance` erlaubt: als Axiom wäre es ein `rdfs:range` auf einer fremden Property und damit eine Aussage über einen Namensraum, der uns nicht gehört | 2026-09-03 |
| `check-updates` | eigener Netzschritt, ändert nichts. Meldet neuere Versionen gepinnter Records *und* Records der Zenodo-Community `squirrel-fdo`, die nicht in `sources.json` stehen | 2026-09-03 |
| Labels für fremde IRIs | kuratierte `registry/labels.json`, von Hand gepflegt, mit Unterstützung: `python main.py --only index` schreibt jede IRI ohne Label nach `dist/labels_missing.json`, fertig zum Ausfüllen. Ein `null`-Label heisst „gesehen, noch nicht benannt"; die Seite zeigt dann die nackte Kennung und verlinkt zur Quelle. Labels sind reine Anzeige und kommen in keinen Graphen | 2026-09-03 |
| SquirrelBase-Q-ID | kuratiertes Feld `squirrelbase_item` in `registry/sources.json`, im Bundle als `fdoreg:squirrelbaseItem` am `dcat:CatalogRecord` (`rdfs:subPropertyOf crm:P67_refers_to`). Aus dem ZIP-Dateinamen *abgeleitet* wird sie nicht — die drei Zuordnungen Q55/Q56/Q60 stammen aus der Tabelle in A1 und sind vom Menschen zu bestätigen | 2026-09-03 |
| IRI-Form der SquirrelBase | eine Konstante `SQUIRRELBASE_ENTITY_NS` in `py/registry_utils.py`, nicht je Eintrag wiederholt. Steht auf `https://squirrelbase.wikibase.cloud/entity/`, **ungeprüft** gegen die laufende Instanz; jeder Bundle-Lauf sagt das dazu. Auf `None` gesetzt bleibt das Tripel ganz draussen | 2026-09-03, zu prüfen |
| Form der Seite | `docs/index.html` mit eingebettetem Index plus je Eintrag eine statische `docs/record/<id>.html`. Eingebettet, weil `fetch()` unter `file://` scheitert (Befund 25); je Eintrag eine Datei, weil A6 dem Record einen eigenen Pfad gibt und ein w3id-Redirect auf ein Fragment nicht zeigen kann | 2026-09-03 |
| Welches `dct:description` die Seite zeigt | das längste. Die kurzen Werte („good", „low") sind erkennbar andere `MD.cff`-Felder; welches wohin gehört, weiss nur der Autor (A4, Grenze der Reparatur). Die Detailseite nennt die übrigen und sagt, dass die Quelle mehrdeutig ist | 2026-09-03 |
| Facette „Jahr" | Erscheinungsjahr des FDO (`dct:issued`, ersatzweise `dct:created`), nicht der Zeitraum des Objekts. Der Zeitraum steht auf Kachel und Detailseite, ist aber als Facette wertlos: fünf der sieben Pakete tragen dieselbe Ogham-Spanne | 2026-09-03 |
| Personen-IRIs auf der Seite | nur ORCIDs werden verlinkt. Die registry-eigenen `agent/`-IRIs haben noch keine Seite, und ein Link ins Leere sieht aus wie ein Angebot. Stattdessen steht dort „no ORCID in the package" — dieselbe Aussage wie im Qualitätsbericht, nur dort, wo sie jemand liest | 2026-09-03 |
| Pfade in Erzeugnissen | über `registry_utils.rel()`, nie über `Path.relative_to()` direkt (Befund 27). Terminalausgabe darf plattformnativ bleiben, Dateiinhalt nicht | 2026-09-03 |
| Zeilenenden in Erzeugnissen | LF, immer, über `registry_utils.write_text()` mit `newline="\n"` (Befund 29). Kein Generator benutzt `Path.write_text()` direkt | 2026-09-03 |
| Zeilenenden im Repository | `.gitattributes` mit `* text=auto eol=lf`: LF im Repository **und** im Arbeitsverzeichnis, auf jeder Plattform. Sonst hängt es an `core.autocrlf` des jeweiligen Klons, und ein Byte-Vergleich zwischen zwei Rechnern sagt nichts mehr. Binärendungen sind dort deklariert statt geraten, und `dist/`, `docs/`, `data/raw/` sowie die erzeugten TTL unter `metadata/` tragen `linguist-generated=true` — ihre Diffs sind auf GitHub eingeklappt, nicht versteckt | 2026-09-03 |
| Seite ansehen | `python main.py --open` öffnet `docs/index.html` von der Platte — die Seite braucht keinen Server, deshalb bekommt sie auch keinen. `python main.py --serve [PORT]` liefert `docs/` auf `127.0.0.1:8000` aus und läuft bis Ctrl+C; es gibt keinen Modus zu verlassen, nur einen Prozess, der endet. Gedacht für S7, wo Pyodide einen `http://`-Origin verlangt | 2026-09-03 |
| Wann eine Seite geprüft ist | wenn ein Browser sie gezeichnet hat. Statische Prüfungen und `jsdom` haben die kaputte Filterung in Befund 28 beide bestanden; `jsdom` bildet die Kaskade zwischen Autor- und User-Agent-Stylesheet nicht korrekt ab. Im Chat wird deshalb gesagt, was nur am Rechner prüfbar ist, statt es als geprüft auszugeben | 2026-09-03 |
| Graph der Abfrageseite | Basisgraph ist der **publizierte** `docs/fdo-registry.ttl` — dieselbe Datei, die die Facettenseite zum Download anbietet, damit ein Leser jede Antwort mit der Datei in der Hand nachvollziehen kann. Brücke, Rollen- und Registry-Vokabular werden je Abfrage über `needs: vocab` dazugeladen und dafür nach `docs/vocab/` kopiert. Nicht der n4o-Bundle: der wäre eine zweite 380-KB-Kopie fast desselben Inhalts und würde die Trennung aus A3 gerade unsichtbar machen | 2026-09-03 |
| Leeres Ergebnis | bricht den Bau ab, immer, auch ohne `--strict`. SPARQL scheitert nicht an einer falsch geschriebenen IRI, es liefert nichts; null Zeilen sind also das übliche Symptom eines kaputten Graphen. Negativprobe gefahren: eine Abfrage auf eine erfundene Klasse beendet den Schritt mit Exitcode 1 und schreibt keine Datei | 2026-09-03 |
| Gegentest gegen den Index | eine Abfrage darf `crosscheck` deklarieren und wird dann gegen `dist/registry-index.json` gerechnet: `catalogue-overview` gegen die Eintragszahl, `holdings-by-licence` und `holdings-by-year` gegen die gleichnamige Facette. Abweichung bricht ab. Die Creator-Facette bleibt aussen vor, weil sie nach Namen zusammenführt und der Graph nach Knoten zählt (Befund 34) | 2026-09-03 |
| Gepinnte Laufzeit | Pyodide 0.26.4 und rdflib 7.1.1, beide als Konstante in `py/step_sparql.py`. Ein ungepinnter CDN-Pfad folgt dem, was als nächstes erscheint, und ein rdflib, das dieses Turtle nicht mehr liest, zerlegt die Seite lautlos. Alle acht Abfragen sind gegen genau diese rdflib-Fassung nachgerechnet, nicht nur gegen die des Bausystems | 2026-09-03 |
| Kein quarto-live-Notebook | die `wdt-*`-Familie erzeugt aus `queries.yaml` drei Erzeugnisse; hier sind es zwei. Ein Notebook ist ein Lehrmittel, und die Registry hat noch keinen Kurs. Kommt dazu, sobald es einen gibt — `queries.yaml` bleibt die Quelle, es ist eine Vorlage mehr | 2026-09-03 |
| Reihenfolge im Orchestrator | `sparql` läuft **nach** `site`: die Seite wird aus dem `docs/`-Baum bedient, den `site` anlegt, und liest den Bundle, den `site` dorthin publiziert. Läuft sie davor, meldet sie eine Warnung statt eine 404 zu erzeugen | 2026-09-03 |
| Autoescape in den Templates | `autoescape=True` ausdrücklich, nicht `select_autoescape(["html"])`: der Helfer prüft die Dateiendung, und alle Templates enden auf `.j2` (Befund 30). Die drei JSON-Blöcke im Skript sind einzeln mit `| safe` markiert — genau dort ist rohe Ausgabe gewollt und nirgends sonst | 2026-09-03 |
| Doppelt kodierte `content/`-IRIs | **upstream in `fdo-squirrel` lösen**, nicht in der Registry. Die Umschreibung so zu ändern, dass sie eine fremde Kodierung repariert, wäre eine dritte Ausnahme zu A3 — und die Registry korrigiert nicht, sie meldet. Sobald der Generator den Pfad unkodiert in die URN schreibt, liefert `content_iri()` von selbst die richtige Form; im Code hier ändert sich nichts. Bis dahin bleiben die publizierten Records und damit der Bundle so, wie sie sind | 2026-09-03 |
| Autoescape in `step_site` | erledigt in **S6b**. Nicht zwei Zeilen in zwei Schritten, sondern eine Funktion in `py/registry_utils.py`: `template_environment()` mit `autoescape=True`, benutzt von `step_site`, `step_bridge` und `step_sparql`. Ein Fehler, den zwei Generatoren unabhängig hatten, wird einmal repariert und nicht zweimal | 2026-09-03, ausgeführt in S6b |
| JSON in einem `<script>` | über `registry_utils.script_json()`: sortierte Schlüssel, `<`, `>` und `&` als `\uXXXX`, im Template roh ausgegeben. Autoescape würde die Anführungszeichen zu `&#34;` machen, und ein `<script>` ist Rohtext — der Browser dekodiert darin keine Entities, `JSON.parse` scheitert an der ersten. Roh muss es sein, unfähig das Element zu beenden auch | 2026-09-03 |
| Rohe Ausgabe im Template | nur ausdrücklich markiert und nur an einer Stelle, die man zeigen kann. Die Zelle `row.target or '&mdash;'` in der Crosswalk-Seite war das Gegenbeispiel: die Präzedenz von `or` machte allein den Ersatzwert roh, was aussieht wie eine Aussage über die ganze Zelle. Sie steht jetzt als Zeichen „—“ da und braucht keine Markierung mehr | 2026-09-03 |
| Kein quarto-live-Notebook | bestätigt: es bleibt bei zwei Erzeugnissen aus `queries.yaml`. Das Notebook kommt, wenn es einen Kurs gibt, der es braucht | bestätigt 2026-09-03 |
| `fdo_type` der Registry selbst | neuer `fdo:RegistryFDO` statt `fdo:AnalysisFDO` — die Registry ist kein Analyseergebnis. Braucht einen Patch in `fdo-squirrel` (Schema-Enum, Rollenklassifikation innerhalb des sechswertigen Vokabulars aus S3) | 2026-09-04 |
| Einbindung von `fdo-squirrel` in S8 | echter Schritt `step_release.py`, `fdo-squirrel` als `pip`-Abhängigkeit von GitHub (`requirements.txt`, auf Commit gepinnt statt `main` zu tracken — dieselbe Begründung wie bei Pyodide/rdflib in S7). Dieselbe Frage steht bei `fdo-3d-packager`/`fdo-git-packager` noch offen; dort noch zu übernehmen | 2026-09-04 |
| Umfang von S9 | **korrigiert:** kein Eintrag in `n4o-collections.json` durch die Registry — das übernimmt VZG von Hand, sobald ein Bundle vorliegt. S9 endet bei: alle geernteten FDO-TTL plus die Registry selbst als DCAT modelliert, vollständig an CIDOC CRM verankert, durch `n4o-rse/n4o-kg-profile` SHACL-validiert, in einem eigenen Repo, das per Hand mit Zenodo gesynct wird. Ersetzt den bisherigen A2-Absatz zum `n4o-collections.json`-Eintrag | 2026-09-04, ersetzt den Plan vom selben Tag |
| Selbsteintrag der Registry im Bundle | **kein neuer Code** — der Weg ist S8 (`step_release.py`, verifiziert lauffähig, A1 Befund 35) → Zenodo-Publish von Hand → DOI als Eintrag in `sources.json` (wie jeder andere) → normaler `harvest`+`bundle`-Lauf. Der nächste `fdo-registry-n4o.ttl`-Build enthält die Registry dann automatisch als achten `dcat:Dataset` | 2026-09-04 |
| Ort und Form des Collection-Repos | neues Repo `FDOx-squirrel/fdox-squirrel-n4o-collection`, **folgt nicht** dem `primer-repo`-Skelett (kein `main.py`, kein eigenes `PRIMER.md`) — `n4o-kg-profile`s eigene Konvention verlangt genau eine von Hand gepflegte `metadata.yaml`, alles andere kopiert die Action bei jedem Lauf hinein. `fdo-registry-n4o.ttl` wird per `source:`/`downloadURL` von `raw.githubusercontent.com` gezogen, nicht committet — der Selbsteintrag (Zeile darüber) landet damit ohne Änderung an diesem Repo automatisch im nächsten Collection-Build | 2026-09-04 |
| `n4o-kg-profile`-Version | `@v1` wie von `n4o-kg-profile` selbst dokumentiert — **aktuell nicht auflösbar**, kein Tag vorhanden (A1, Befund 36), und die Action checkt zusätzlich einen 404-Org-Pfad aus (Befund 37). Beides sind Upstream-Blocker, nicht durch Pinnen auf einen Commit statt eines Tags zu umgehen, weil der kaputte Checkout in der Action selbst sitzt. Workflow im Collection-Repo liegt bereit, aber vorerst nur `workflow_dispatch`, kein `push` — Issue-Entwurf liegt im Repo bei | 2026-09-04 |
| `schema:sameAs` (Wikidata-Item der Registry) | offen — `n4o-kg-profile`s SHACL-Gate verlangt zwingend ein Wikidata-Q-Item (`sh:Violation`); die Registry hat noch keins. `metadata.yaml` trägt einen sichtbaren `TODO`-Platzhalter statt eines erfundenen Items; ein `strict`-Build bleibt bis dahin absichtlich rot | 2026-09-04, offen |

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

**Seit S4 auch ohne Upload.** Solange der Stand auf GitHub gepusht ist, genügt
die Repo-URL: der Chat klont
`https://github.com/Research-Squirrel-Engineers/fdo-squirrel-registry` und sieht
damit genau den committeten Baum, gegen den der Patch am Ende ohnehin geprüft
wird. Der Preis ist, dass lokal Ungepushtes für den Chat nicht existiert — wer
im Arbeitsbaum etwas liegen hat, lädt weiter das Bundle hoch.

## A6. IRI-Landkarte unter `https://w3id.org/fdo-squirrel/`

Die Registry hängt unter den bestehenden FDOx-Namensraum, statt einen zweiten
aufzumachen. Was davon bei w3id eingetragen werden muss, ist in S1 zu prüfen —
unbekannt ist derzeit, ob für `fdo-squirrel` überhaupt schon ein Eintrag
existiert oder ob die IRI bisher nur als Präfix benutzt wird.

| Pfad | Inhalt | Ziel des Redirects | Status |
|---|---|---|---|
| `/fdo-squirrel/` | FDOx-Vokabular: `fdo:3DDataFDO`, `fdo:role`, `fdo:sha256` … | `fdo-squirrel`, Datei noch zu bestimmen | in Benutzung, Eintrag ungeprüft |
| `/fdo-squirrel/crm/` | Brücke FDOx → CIDOC CRM | `docs/vocab/crm_bridge.ttl` (Kopie aus `metadata/`, seit S7 auf Pages) | gebaut (S3), w3id-Eintrag offen |
| `/fdo-squirrel/registry/` | Registry-Vokabular `fdoreg:`, vier Terme | `docs/vocab/registry_ontology.ttl` (Kopie, seit S7 auf Pages) | gebaut (S4), w3id-Eintrag offen |
| `/fdo-squirrel/registry/catalog` | der Katalogknoten selbst | `dist/fdo-registry.ttl` | gebaut (S4), w3id-Eintrag offen |
| `/fdo-squirrel/registry/record/{id}` | ein `dcat:CatalogRecord` je gepinnter Version | `docs/record/{id}.html` | gebaut (S6), w3id-Eintrag offen |
| `/fdo-squirrel/registry/record/{id}/dist/{sha}` | eine `dcat:Distribution` | Detailansicht auf Pages | im Bundle vergeben (S4) |
| `/fdo-squirrel/registry/agent/{hash}` | eine Person ohne ORCID, registry-global | Detailansicht auf Pages | im Bundle vergeben (S4), keine Seite — die Detailseiten verlinken solche IRIs deshalb nicht (A4) |
| `/fdo-squirrel/registry/role/` | SKOS-Vokabular zu `fdo:role`, sechs Konzepte | `docs/vocab/role.ttl` (Kopie, seit S7 auf Pages) | gebaut (S3), w3id-Eintrag offen |
| `/fdo-squirrel/registry/shapes/` | SHACL-Gate, 38 Regeln | `metadata/shapes.ttl` | gebaut (S5), w3id-Eintrag offen |
| `/fdo-squirrel/registry/squirrelbaseItem` | Verweis auf das SquirrelBase-Item zum Objekt | `metadata/registry_ontology.ttl` | gebaut (S6), w3id-Eintrag offen |

**Zu klären beim Eintragen.** Ein Redirect auf GitHub Pages liefert genau eine
Repräsentation aus. Für echte Content Negotiation braucht es w3id-seitige
`Accept`-Regeln oder je Pfad einen `.ttl`- und einen `.html`-Eintrag.

---

# Teil B — Schrittübersicht

| ID | Schritt | hängt ab von | Status |
|---|---|---|---|
| S0 | Festlegungen, kein Code | — | erledigt 2026-09-03 |
| S1 | Repo-Skelett und Orchestrator | S0 | erledigt 2026-09-03 |
| S2 | Ernte aus Zenodo | S1 | erledigt 2026-09-03 |
| S3 | Crosswalk FDOx → CIDOC CRM | S0, S2 (ein echtes TTL) | erledigt 2026-09-03 |
| S4 | Bundle-Build als DCAT-Katalog | S2, S3 | erledigt 2026-09-03 |
| S5 | SHACL-Gate und Qualitätsbericht | S4 | erledigt 2026-09-03 |
| S6 | Registry-Index und Facettenseite | S4 | erledigt 2026-09-03 |
| S6b | Autoescape in den Seitentemplates | S6 | erledigt 2026-09-03 |
| S7 | SPARQL-Seite | S4, S6 | erledigt 2026-09-03 |
| S8 | Registry als FDO, Release und CI | S5, S7 | erledigt 2026-09-04 |
| S9 | N4O-Andockung | S5, S8 | begonnen 2026-09-04, blockiert bei `n4o-kg-profile` |

S3 lässt sich fachlich schon vor S2 beginnen, braucht für die Abnahme aber ein
echtes geerntetes TTL — deshalb die Abhängigkeit. S6 und S7 hängen beide an S4
und nicht aneinander; S6 zuerst, weil die Facettenseite den kürzeren Weg zu
etwas Vorzeigbarem ist. S5 steht vor S8, weil kein Release ohne grünes Gate
herausgeht. S6b hängt nur an S6 und blockiert nichts; es sollte trotzdem vor S8
laufen, weil ein Release Seiten publiziert, die dann fest sind.

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
- ~~Umgang mit mehreren Versionen desselben Objekts~~ — **erledigt in S4**: ein
  `dcat:CatalogRecord` je gepinnter Version, ein `dcat:Dataset` je Concept-DOI.
  Die Trennung steckt schon in DCAT und musste nicht erfunden werden; siehe A4
  und Befund 14.

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

**`check-updates` fragt einmal, nicht achtmal.** Die Community-Liste liefert je
Concept die neueste Version — damit ist die Frage „gibt es etwas Neueres" für
jeden gepinnten Record beantwortet, dessen Concept darin vorkommt, ohne eine
eigene Abfrage. Nur was die Liste nicht abdeckt, kostet einen Request. Der
Unterschied ist nicht kosmetisch: mit einer Abfrage je Record dauerte der
Schritt 335 Sekunden, weil zwei davon in 504-Wiederholungen liefen (gemessen
2026-09-03). Dazu ist das Wiederholungsbudget hier kleiner als beim Ernten —
ein etwas älterer Bericht kostet weniger als eine lange Wartezeit, eine
ausgefallene Ernte dagegen kostet die Daten selbst.

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

**Ein Record ohne ZIP ist kein leerer Record.** Von den sieben ungelisteten
Community-Einträgen sind mehrere Papiere und Vorträge — sie haben ein PDF, kein
FDOx-Paket, und gehören nicht in `sources.json`. Der Bericht sagt das jetzt
(„no package — a paper or slides") statt „no files", was nach einem defekten
Record aussah.

**Die Community-Suche scheiterte nicht am Pfad, sondern an meinen Parametern.**
Vier Formen antworteten mit 400. Drei `curl`-Proben zeigten dann, dass genau
dieselben Pfade **ohne Query-Parameter mit 200 antworten** — es lag an
`size=100&page=1`, nicht am Endpunkt. Die Lehre ist allgemeiner als der Bug:
ein Client, der sich seine Seiten-URLs selbst zusammenbaut, rät an einem
Vertrag herum, den der Server bereits ausspricht. Die Suche holt jetzt die
erste Seite nackt und folgt danach `links.next`; die Seitengrösse bestimmt
Zenodo. Eine Schleife in den Links wird nach 50 Seiten abgebrochen.

Wert der Fehlersuche für später: der Unterschied zwischen 400 und 404 war der
Hinweis. 404 hätte geheissen „diesen Pfad gibt es nicht", 400 heisst „den Pfad
gibt es, aber so nicht" — und danach war die richtige Frage nicht mehr *welche
URL*, sondern *welcher Parameter*.

### Nachtrag 2026-09-03, nach dem Commit

Der erste frische Klon des committeten Repos hat drei Fehler gezeigt, die
vorher keiner sehen konnte, weil `data/` erst mit dem Commit existierte:

- **`python main.py` brach ab.** Die Schrittrümpfe warfen `NotImplementedError`,
  sobald ihre Vorbedingung erfüllt war — und S2 erfüllt die Vorbedingung von S4.
  Ein Rauchtest, der genau dann kaputtgeht, wenn der erste Schritt liefert, ist
  keiner. Die Rümpfe melden jetzt `pending: input is ready; implemented in S4`
  und geben zurück (A4, Schrittvertrag).
- **Sieben verwaiste Verzeichnisse unter `data/raw/fdo/`.** Rückstände der Läufe
  vor `--resolve`; eines davon, `18724635`, hält ein echtes TTL — dasselbe FDO
  wie der gepinnte Record 18744133. Ein ungefilterter Glob hätte es in S4
  mitgebündelt und den Ogham-Stein zweimal in den Katalog geschrieben, unter
  zwei Record-IRIs, ohne eine Aussage im Graphen, dass es eine Sache ist.
  `harvested_records()` liest jetzt nur noch, was in `sources.json` steht;
  `step_harvest` benennt die Waisen, `--prune` entfernt sie. Was im Katalog
  steht, entscheidet die kuratierte Liste, nicht der Inhalt eines Ordners.
- **Ein Offline-Lauf löschte geerntete TTLs.** Er fand die Datei nicht — weil er
  offline gar nicht ins ZIP schauen konnte — und behandelte das wie „im Record
  nicht mehr vorhanden". Die Unterscheidung ist jetzt explizit: nur ein
  tatsächlich gelesenes Paket darf ein TTL zurückziehen, und ein Lauf, der
  nichts prüfen konnte, lässt auch die `harvest.json` unangetastet und meldet
  `unchecked`. „Ich konnte nicht nachsehen" ist etwas anderes als „da ist
  nichts" — diese Verwechslung ist der teuerste Fehler, den ein Ernter machen
  kann, weil sie Daten vernichtet, die er selbst nicht zurückholen kann.

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

**Zwei CSV.** `crosswalks/fdo--crm.csv` ist die Abbildung nach CRM,
`crosswalks/fdo-role--skos.csv` das Rollenvokabular — getrennt, weil das zweite
kein Crosswalk ist, sondern eine Begriffsliste mit Definitionen, und in eine
`note`-Spalte gequetschte Definitionen später niemand pflegt.

| Spalte | Inhalt |
|---|---|
| `fdo_term` | Term aus `fdo:`, fremder Term, oder Feldpfad aus `MD.cff`. Ein Suffix `@iri`/`@literal` unterscheidet zwei Zeilen zum selben Prädikat |
| `kind` | `class` \| `property` \| `field` |
| `target` | CRM/CRMdig/GeoSPARQL/SKOS-Term |
| `mechanism` | `axiom` \| `ext-axiom` \| `normalise` \| `instance` \| `none` |
| `ap_rule` | Verweis auf die Regel im Anwendungsprofil, wo einschlägig |
| `source` | wörtlich zitierte Quelle — Pflicht bei `ext-axiom` |
| `note` | Begründung, besonders bei „kein Anker" |

**Fünf Mechanismen, nicht zwei.** Das ist der Kern des Schritts, und er kommt
aus A3: über fremde Namensräume wird nichts behauptet.

- `axiom` — Aussage über einen Term aus `fdo:`/`fdoreg:`, geht nach
  `metadata/crm_bridge.ttl`.
- `ext-axiom` — Aussage über einen fremden Term, **wörtlich zitiert** aus dessen
  eigener Ontologie oder aus dem Profil, mit Quellenangabe. Ohne diese Kategorie
  gäbe es keinen Weg von `crmdig:D1` nach `crm:E73`, ohne etwas zu erfinden.
- `normalise` — abgekürzte Klassen-IRI, die S4 ersetzt (A4).
- `instance` — Anker, den S4 je Objekt materialisiert, weil das Subjekt in einem
  fremden Namensraum liegt.
- `none` — bewusst ohne Anker, mit Begründung daneben.

Beides wird beim Build geprüft und bricht S3 ab: ein `axiom` über `dcat:`, ein
`ext-axiom` ohne Quelle, ein unbekanntes Präfix, eine Zeile ohne Ziel *und* ohne
Begründung.

**Was das Anwendungsprofil verbietet.** Das ist der Teil, den eine naive
CRM-Abbildung zuerst falsch macht. Gegen
<https://nfdi4objects.github.io/crm-rdf-ap/> geprüft am 2026-09-03; die Liste
stimmt vollständig:

| Naheliegend | Im Profil | Stattdessen |
|---|---|---|
| `crm:E55_Type` für Keywords und Rollen | MUST NOT | `skos:Concept`, `skos:broader`/`narrower`; `crm:P2_has_type` bleibt erlaubt und wird im Profil selbst so benutzt |
| `crm:E32_Authority_Document`, `P71 lists` | MUST NOT | `skos:ConceptScheme`, `skos:inScheme` |
| `crm:E52_Time-Span` mit `P82a`/`P82b` | ausdrücklich nicht erwünscht | typisierte Literale (`xsd:date`, `xsd:gYear`, `edtf:EDTF`) an `crm:P4_has_time-span`; komplexe Fälle als `time:Interval` |
| `crm:E94_Space_Primitive`, `P168 place is defined by` | ersetzt | `geo:hasGeometry` auf `geo:Geometry` mit `geo:asWKT` |
| `crm:E95_Spacetime_Primitive`, `P169i` | MUST NOT | `P4` für Zeit + `geo:hasGeometry` für Ort |
| `crm:E41/E35/E42` für Titel und Identifier | zu vermeiden | Literale, `skos:prefLabel`/`altLabel`, Identifier als IRI + `owl:sameAs` |
| `crm:E58_Measurement_Unit` selbst prägen | zu vermeiden | QUDT oder UCUM-Datentyp |
| eigene Klassen für Literaturangaben | MUST NOT | BIBO |

**Was das Profil *nicht* sagt.** Es kennt CRM-Kern, SKOS, GeoSPARQL, Time
Ontology und BIBO — und schweigt zu CRMdig. Genau dort sitzt aber der Kern
dieser Registry: das Digitalobjekt. Beschluss (A4): CRMdig bleibt, und die drei
Unterklassenaxiome aus CRMdig werden zitiert, damit jedes FDO auch für einen
Konsumenten, der nur CRM-Kern liest, ein `E73_Information_Object` ist.

**Der Kern der Abbildung**, gegen den echten Bestand geprüft:

| FDOx | CRM-Anker | Mechanismus |
|---|---|---|
| `fdo:3DDataFDO` | `crmdig:D1_Digital_Object` | Axiom |
| `fdo:SoftwareFDO` | `crmdig:D14_Software` | Axiom |
| `fdo:AnalysisFDO` | `crmdig:D1_Digital_Object` | Axiom (im Bestand nicht vorhanden, A1 Befund 13) |
| `crmdig:D1` ⊑ `crm:E73_Information_Object` | — | ext-Axiom, zitiert aus CRMdig 3.2.1 |
| `sf:Point` ⊑ `geosparql:Geometry` | — | ext-Axiom, zitiert aus GeoSPARQL |
| `skos:Concept` ⊑ `crm:E28_Conceptual_Object` | — | ext-Axiom, zitiert aus dem Profil |
| `dcat:Distribution` | `crmdig:D9_Data_Object` | Instanz |
| `schema:Person` / `schema:Organization` | `crm:E21_Person` / `crm:E74_Group` | Instanz |
| `dct:title` | `crm:P102_has_title` mit Literal | Instanz |
| `dct:description`, `dct:provenance`, `fdo:context` | `crm:P3_has_note` | Instanz bzw. Axiom |
| `dct:type`, `dcat:keyword` (IRI), `dct:subject`, `fdo:role` | `crm:P2_has_type` | Instanz bzw. Axiom |
| `dct:spatial` | `crm:P67_refers_to` auf `crm:E53_Place` | Instanz |
| `dct:temporal` | `crm:P4_has_time-span` mit typisiertem Literal | Instanz |
| `dct:creator`, `dct:publisher` | kein Anker, begründet: bräuchte ein `E65`-Ereignis, das im FDO nicht steht | — |
| `heritage_object`, `technique.acquisition` | kein Anker, begründet: im geernteten TTL nicht vorhanden | — |
| `dct:license`, `dct:hasVersion`, `fdo:sha256`, `dcat:byteSize`, `dcat:mediaType` | kein Anker, begründet | — |

**`py/step_bridge.py`** erzeugt `metadata/crm_bridge.ttl` (nur `axiom` und
`ext-axiom`), `metadata/vocab/role.ttl` und `docs/crosswalk.html`. Die
`instance`- und `normalise`-Zeilen liest S4 aus derselben CSV.

**Abnahme:** jede Zeile der CSV hat entweder ein Ziel oder eine Begründung in
`note`; `crm_bridge.ttl` parst; keine Aussage über einen fremden Namensraum, die
nicht zitiert und mit Quelle belegt ist.

### Erledigt 2026-09-03

42 Zeilen: 5 `axiom`, 5 `ext-axiom`, 3 `normalise`, 11 `instance`, 18 `none`.
`crm_bridge.ttl` hat 17 Tripel, `role.ttl` 39 bei sechs Konzepten. Zwei Läufe
hintereinander sind byte-gleich.

Was anders kam als gedacht:

- Die Hälfte des Schritts war **nicht** Abbilden, sondern Streichen. 18 von 42
  Zeilen haben keinen Anker, und die drei interessantesten davon —
  `heritage_object`, `technique.acquisition`, `dct:creator` — scheitern nicht am
  Profil, sondern daran, dass die Quelle die Information gar nicht führt. Eine
  Abbildung, die aus `MD.cff` gedacht ist, verspricht Anker, die das TTL nicht
  einlösen kann.
- Die Prüfungen wurden gegen absichtlich kaputte Zeilen getestet und schlagen
  alle an (Axiom über `dcat:`, `ext-axiom` ohne Quelle, unbekanntes Präfix,
  unbekannter Mechanismus, Zeile ohne Ziel und ohne Begründung). Eine Prüfung,
  die nie ausgelöst hat, ist ungeprüft.
- Der Rollenzähler sieht im lesbaren Bestand nur `documentation` 48, `model` 9,
  `metadata` 6, `data` 5 — `software` und `script` stecken in den vier Paketen,
  die nicht parsen. Das Vokabular hat trotzdem sechs Konzepte: die Zahlen aus
  Befund 7 stammen aus dem vollständigen Bestand, den S3 einmal von Hand
  repariert gelesen hat, um überhaupt zu wissen, was es zu modellieren gibt.
- `registry_utils.read_fdo_graph()` ist in S3 entstanden, gehört aber S4 und S5
  genauso. Der Grund steht in A4: drei Schritte, die sich uneinig sind, welche
  Pakete im Katalog stehen, sind schlimmer als drei Schritte, die alle dasselbe
  auslassen.

## S4 — Bundle-Build als DCAT-Katalog

**Ziel:** `dist/fdo-registry.ttl` — ein Graph, byte-gleich bei gleicher Eingabe.

**Uploads:** Bundle nach A5.

**Reihenfolge im Skript.** Sie ist nicht beliebig; die Vereindeutigung muss vor
dem Zusammenführen passieren, sonst ist die Kollision schon eingetreten:

1. Je Eintrag das TTL über `registry_utils.read_fdo_graph()` **in einen eigenen
   Graph** parsen. Was nicht parst, wird übersprungen und gemeldet (A3, A4).
2. Personen vereinheitlichen: ORCID, wo vorhanden; sonst
   `urn:fdo-squirrel:person/<hash>` → `<registry>/agent/<hash>`,
   **registry-global**, nicht je Record (A1, Befund 11). Skolemisierung
   entfällt, es gibt keine Blank Nodes.
3. `urn:fdo-squirrel:*` umschreiben auf `<record-IRI>/dist/<sha>` bzw.
   `<record-IRI>/content/<pfad>`; die Original-URN als `dct:identifier` erhalten.
4. Abgekürzte Klassen-IRIs normalisieren, nach den `normalise`-Zeilen der
   Crosswalk-CSV: `crm:E73` → `crm:E73_Information_Object` usw.
5. CRM-Anker je Instanz materialisieren, nach den `instance`-Zeilen aus S3.
   `dct:temporal` wird dabei zu `crm:P4_has_time-span` mit `xsd:gYear`, wo
   `dcat:startDate` und `dcat:endDate` gleich sind, sonst zu `time:Interval` —
   die Quelle schreibt `xsd:integer`, was das Profil nicht führt (Befund 15).
6. In den Katalog hängen:

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

7. Kanonisch serialisieren: sortierte N-Triples nach `dist/fdo-registry.nt`,
   daraus `dist/fdo-registry.ttl`.

**Was der Bundle nicht tut.** Er zieht keine Wikidata- oder OSM-Daten nach. Der
Bundle enthält die IRIs; wer mehr will, föderiert. Ein Registry, die fremde
Bestände mitkopiert, ist beim nächsten Lauf veraltet und beim übernächsten
falsch.

**Abnahme:** zwei Läufe hintereinander, `git status` sauber; Tripelzahl im
Bericht; keine `urn:`-IRI und kein Blank Node mehr im Ergebnis.

### Erledigt 2026-09-03

`dist/fdo-registry.ttl` hat **6552 Tripel** aus **7 der 8 gepinnten Records**,
0 `urn:`-IRIs, 0 Blank Nodes. Vier Pakete wurden mit deklarierten Reparaturen
gelesen, 21 abgekürzte Klassen-IRIs normalisiert, 633 CRM-Anker materialisiert.
Abnahme erfüllt: vier weitere Läufe mit wechselndem `PYTHONHASHSEED` liefern
byte-gleiche Dateien, `python main.py --strict` endet mit Exitcode 0.

Was anders kam als geplant:

- **Die Reparatur war billiger als befürchtet und gleich doppelt wertvoll.**
  Zwei fehlende `@prefix`-Zeilen und ein maskiertes Anführungszeichen je Datei —
  sechs veränderte Zeilen im ganzen Bestand. Der Gewinn geht über S4 hinaus:
  S3 zählte `fdo:role` vorher nur über drei Pakete und sah vier Werte, jetzt
  über sieben und sieht alle sechs (`software` 312, `documentation` 123,
  `script` 28, `model` 12, `data` 9, `metadata` 8). Das Vokabular aus S3 ist
  damit zum ersten Mal gegen den **vollen** Bestand geprüft statt gegen den
  von Hand reparierten.
- **Das Bundle war nicht reproduzierbar, und die Abnahme von S1 und S3 hatte
  das nicht gemerkt.** Zwei Läufe unterschieden sich in 84 Zeilen, ohne dass
  ein Tripel anders gewesen wäre: rdflib erfindet für ungebundene Namensräume
  `ns1`, `ns2`, … in der Reihenfolge, in der es ihnen begegnet, und die kommt
  aus einer Menge. `codemeta:` war einmal `ns2` und einmal `ns3`. Die kleinen
  Graphen aus S1 und S3 hatten schlicht keinen ungebundenen Namensraum, die
  Prüfung „zwei Läufe byte-gleich" ging also durch, ohne etwas zu prüfen.
  `write_canonical_turtle` bindet jetzt selbst (`bind_remaining`), und
  `cff:`, `codemeta:`, `wd:`, `wdt:`, `role:` stehen in `PREFIXES`. Der
  N-Triples-Zwischenstand war die ganze Zeit stabil — er ist das eigentliche
  kanonische Erzeugnis und der Ort, an dem zwei Läufe zu vergleichen sind.
- **`fdo:role` hätte einen String dorthin gesetzt, wo CRM einen Typ erwartet.**
  Das Axiom aus S3 (`fdo:role ⊑ crm:P2_has_type`) ist nur zusammen mit einer
  Auflösung des Literals gegen das SKOS-Vokabular tragfähig. 516 Anker; ohne
  sie wäre das SHACL-Gate in S5 sofort rot geworden, mit einem Fehler, dessen
  Ursache zwei Schritte zurückliegt.
- **Die Versionsfrage aus S0 hat sich nicht gestellt.** DCAT trennt Dataset und
  CatalogRecord bereits so, wie es hier gebraucht wird, und Befund 14 liefert
  die Concept-DOI als Dataset-IRI frei Haus. Der Build prüft die Zuordnung je
  Paket; alle sieben stimmen.
- **`crmdig:D14_Software` steht im Bundle nirgends.** Zwei Pakete sind
  `fdo:SoftwareFDO`, und der Weg zu D14 führt über ein Axiom in
  `metadata/crm_bridge.ttl` — eine Datei, die der Bundle nicht mitbringt. Der
  Katalogknoten trägt `dct:conformsTo` auf die Brücke, aber ein Konsument, der
  nur `fdo-registry.ttl` lädt, sieht die Software-Klasse nicht. Ob das Gate in
  S5 gegen Bundle + Brücke prüft oder der Bundle die Brücke importiert, ist in
  S5 zu entscheiden.

Offen aus diesem Lauf: der Präfixkopf des Bundles trägt rund dreissig
generierte `nsNN:`-Zeilen, je eine für die `content/`- und `dist/`-Namensräume
der sieben Records. Deterministisch, aber unschön; ob das die Lesbarkeit einer
publizierten Datei genug stört, um die IRI-Form zu ändern, gehört zu S6.

## S5 — SHACL-Gate und Qualitätsbericht

**Ziel:** ein Bundle, der entweder konform ist oder den Build anhält.

**Uploads:** Bundle nach A5.

**Drei Sorten Shapes in `metadata/shapes.ttl`:**

- **Vollständigkeit.** Jedes `dcat:Dataset` im Katalog braucht Titel, Lizenz,
  ~~Identifier~~ (korrigiert 2026-09-03: eine DOI-IRI als Knoten, siehe A1
  Befund 20), mindestens eine Distribution und genau einen FDO-Typ. Jeder
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
  Korrigiert 2026-09-03: die Liste wirft zwei Härtegrade zusammen. `E55`, `E32`,
  `E95` und `P169i` sind MUST NOT und damit `sh:Violation`; `P82a`/`P82b`,
  `E41` und `E94` sind SHOULD NOT und damit `sh:Warning`. Und `P82a`/`P82b`
  standen bis zu diesem Schritt im eigenen Bundle (A1, Befund 19).

`inference="none"` in pyshacl; SHACL folgt `rdfs:subClassOf` bei `sh:targetClass`
und `sh:class` selbst — ~~die Axiome liegen im Bundle~~. Korrigiert 2026-09-03:
sie liegen in `metadata/crm_bridge.ttl`, und das Gate validiert deshalb Bundle
plus Brücke plus Vokabulare als einen Graphen (A1, Befund 18; A4).

**`dist/quality_report.md`** ist der zweite Ausgang und der eigentliche Ertrag
für die Autoren: je Eintrag, was fehlt oder unsauber ist — Lizenz nur als
String, kein `dct:spatial`-IRI, Distribution ohne Rolle, `fdo:title` weicht von
`dct:title` ab. Das sind Warnungen, keine Fehler; ~~erst `--strict` macht sie
tödlich~~. Korrigiert 2026-09-03: sie sind auch unter `--strict` nicht tödlich,
weil sie unveränderliche Zenodo-Records betreffen (A4). `--strict` schlägt hier
nur auf eine Regel an, die kein Fixture mehr auslöst.

**Abnahme:** `conforms = true` für den vollen Bestand, Bericht liegt vor, und
ein absichtlich kaputt gemachtes Eingabe-TTL bringt das Gate zum Anschlagen.
Eine Shape, die nie ausgelöst hat, ist ungeprüft.

### Erledigt 2026-09-03

`metadata/shapes.ttl` hat **38 Regeln** in fünf Gruppen. Der Bundle ist
konform: 0 Verstöße, 46 Warnungen über 9 Regeln, alle 38 Regeln lösen gegen
`metadata/shapes_selftest.ttl` aus. `dist/quality_report.md` und
`dist/fdo-registry-n4o.ttl` (6665 Tripel) liegen vor. Vier Läufe mit
wechselndem `PYTHONHASHSEED` liefern byte-gleiche Dateien, `python main.py
--strict` endet mit Exitcode 0. Das Gate kostet 2,1 s von 3,6 s Gesamtlauf.

Der Schritt begann mit einer Vorprüfung der geplanten Shapes gegen den echten
Bundle, und die hat mehr verändert als das Schreiben danach. Die Befunde 17–23
in A1 stammen von dort; zwei davon haben die Planung des Schritts widerlegt:

- **Die Ankerprüfung war falsch herum gedacht.** „Pro Klasse" meldet genau die
  Klassen, deren Anker A3 vorschreibt (Befund 17). Sie fragt jetzt pro Knoten,
  und die vier ankerlosen Sorten sind verschwunden, weil sie einen Anker
  bekommen haben statt einer Ausnahme: Katalog und Katalogeintrag als
  `crm:E31_Document`, die Geometrie über `crmgeo:SP5_Geometric_Place_Expression`,
  die Rollenkonzepte über das Profilzitat `skos:ConceptScheme ⊑ crm:E31_Document`.
  Übrig bleibt eine einzige, benannte Ausnahme: terminologische Knoten. Eine
  Ontologie-Kopfzeile beschreibt eine Datei, kein Ding im Katalog.
- **Das Gate hätte den eigenen Bundle beanstandet.** `P82a`/`P82b` standen in
  A4 als Beschluss und im Profil als Abrat (Befund 19). Aufgelöst zugunsten des
  Profils, weil der Bundle in den N4O-Graphen soll: der Zeitwert ist jetzt ein
  typisiertes Literal an `crm:P4_has_time-span`, `0300/0699`^^`edtf:EDTF` bei
  einer Spanne, `1982`^^`xsd:gYear` bei einem Jahr. Das kostete 14 Tripel und
  brachte 7 dazu.

Was sonst anders kam als geplant:

- **`--strict` macht die Warnungen nicht tödlich**, anders als hier geplant.
  Die 46 Warnungen betreffen unveränderliche Zenodo-Records; eine CI, die
  deswegen dauerhaft rot ist, liest niemand. Dieselbe Überlegung stand schon in
  S4 bei der Personen-Kollision. `--strict` schlägt jetzt auf genau eine Sache
  an, und die können wir beheben: eine Regel, die kein Fixture mehr auslöst.
- **Der Selbsttest hat sich sofort bezahlt gemacht.** Beim ersten Lauf meldete
  er „The distribution has no fdo:role" als nie ausgelöst — das Fixture hatte
  nur eine Distribution, und die trug eine Rolle. Genau so verschwindet eine
  Regel unbemerkt aus einem Gate.
- **Laufzeit ist hier eine Entwurfsfrage, keine Optimierung.** Die
  Ankerprüfung je Fokusknoten brauchte 18 Sekunden, als `sh:SPARQLTarget` 0,9
  (Befund 23). Ein Gate, das den Standardlauf um das Sechsfache verlängert,
  wird herausgenommen, und dann prüft es nichts mehr.
- **Der Qualitätsbericht ist das eigentliche Ergebnis für die Autoren.** 46
  Warnungen, gleichmäßig über die sieben Pakete verteilt (6 je Paket, 4
  paketübergreifend): Lizenz und Keywords als Zeichenkette, vier
  `dct:description` je Paket, `schema:funding` ohne Förderer-IRI,
  `dcat:startDate` als `xsd:integer`, `geo:hasGeometry` am FDO statt am Ort,
  Personen ohne ORCID. Nichts davon kann die Registry reparieren, alles davon
  kann `fdo-squirrel` beim nächsten Paket besser machen.

Offen aus diesem Lauf und an S6 weitergegeben: der Bericht nennt Knoten-IRIs,
keine Dateinamen. Wer wissen will, welche Datei in Paket 18744133 keine Rolle
trägt, muss die IRI von Hand auflösen. Die Facettenseite hat diese Zuordnung
ohnehin und kann den Bericht verlinken.

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

### Erledigt 2026-09-03

`py/step_index.py` (nicht `build_index.py` — die Schrittmodule heissen im Repo
alle `step_*`) schreibt `dist/registry-index.json`: 7 Einträge, 510
Distributionen, 0,9 GB beschrieben. `py/step_site.py` rendert daraus
`docs/index.html` mit 7 Kacheln und 6 Facetten (FDO type 2, Licence 4, Keyword
14, Place 6, Published 5, Creator 4), je Eintrag eine `docs/record/<id>.html`
und daneben Kopien von Bundle und Index für Pages. Beide Abnahmeprüfungen
laufen im Schritt selbst: Eintragszahl gegen `dcat:record`, und jeder Eintrag
mit mindestens einem Facettenwert. Zwei Läufe mit wechselndem `PYTHONHASHSEED`
liefern byte-gleiche `dist/` und `docs/`.

Was anders kam als geplant:

- **Die Detailansicht ist keine Ansicht, sondern sieben Dateien.** Geplant war
  „Detailansicht je Eintrag" innerhalb der Facettenseite. A6 vergibt dem Record
  aber einen eigenen Pfad, und ein w3id-Redirect kann nicht auf ein Fragment
  zeigen, das erst JavaScript auflöst. Der Preis ist ein Verzeichnis, das beim
  Bauen aufgeräumt werden muss — eine Seite zu einem nicht mehr gepinnten
  Record wäre erreichbar, sähe aktuell aus und stünde in keinem Log.
- **Der Index steht zweimal da.** Einmal eingebettet in `index.html`, einmal
  als Datei daneben (Befund 25). Nicht schön, aber die Alternative ist eine
  Seite, die genau bei der Abnahme scheitert.
- **Die Facetten sind nur so gut wie die Labels** (Befund 24). Sieben Orte
  stehen heute als „OSM relation 62273" auf der Seite. Die sieben
  Wikidata-Konzepte sind in `registry/labels.json` benannt und gegen Wikidata
  geprüft; die OSM-Objekte sind offen und werden vom Lauf jedes Mal genannt.
  Ein geratener Ortsname wäre schlimmer als eine nackte Kennung: er sieht aus
  wie eine Aussage.
- **Zwei Beschriftungen waren Lügen.** Der Link auf das „FDO-Metadaten-TTL"
  zeigt auf ein 196-MB-ZIP (Befund 26), und die Personen-Links zeigten auf
  registry-eigene IRIs ohne Seite. Beides korrigiert; die zweite Korrektur
  bringt den Qualitätsbefund „keine ORCID" dorthin, wo ihn jemand sieht.
- **Der Sprung auf `sparql.html` fehlt noch**, weil es die Seite erst in S7
  gibt. Die Facettenseite ist ohne sie vollständig; der Link kommt in S7 dazu,
  und das ist die einzige Stelle, an der S7 auf S6 zurückgreift.

Offen und an S7 weitergegeben: `dist/registry-index.json` ist die zweite
Lesart des Bundles neben SPARQL. Wenn eine Abfrage in S7 etwas anderes zählt
als die Facette hier, ist eine von beiden falsch — das ist ein billiger
Gegentest und gehört in den Startsatz an Abfragen.

### Nachtrag 2026-09-03, erster Lauf im Browser

Die Filterung wählte richtig und blendete nichts aus (Befund 28): `.card`
setzt `display: flex`, und eine Autorenregel schlägt das
User-Agent-`[hidden]`. Eine Zeile CSS (`.card[hidden] { display: none }`).
Dabei fiel Befund 29 auf, die CRLF unter Windows.

Zwei Flags kamen dazu, weil die Frage „muss ich das auf localhost laufen
lassen?" nach dem Fehler naheliegend war und die Antwort nein lautet:
`--open` öffnet die gebaute Seite von der Platte, `--serve` liefert `docs/`
bis Ctrl+C aus. Die Facettenseite braucht `--serve` nicht; S7 wird es
brauchen, weil Pyodide seine Module nicht über `file://` nachlädt.

## S6b — Autoescape in den Seitentemplates

**Ziel:** die erzeugten Seiten escapen, was aus den Paketen kommt — heute tun
sie es nicht (A1, Befund 30).

**Uploads:** Bundle nach A5.

`step_site.environment()` setzt `select_autoescape(["html"])`. Der Helfer
vergleicht das Ende des Dateinamens, alle Templates hier enden auf `.j2`, also
liefert er `False`, und `docs/index.html`, `docs/record/*.html` und
`docs/crosswalk.html` werden seit S6 ungeschützt geschrieben. `step_sparql`
setzt seit S7 `autoescape=True` ausdrücklich; dieselbe Zeile fehlt in
`step_site`.

Der Umbau ist eine Zeile, die Prüfung ist die Arbeit: mit Autoescape werden
Werte escaped, die heute roh durchgehen, und die drei Templates schreiben an
etlichen Stellen Fragmente, die roh gemeint sind (`entry.geometry` in einem
`<a>`-Attribut, die eingebettete Index-JSON im `<script>`). Jede Stelle, die
danach `&lt;` zeigt, wo vorher ein Element stand, gehört mit `| safe` markiert
— und jede Stelle, an der man das tut, ist eine Entscheidung und kein
Automatismus.

Ein Fixture gehört dazu, sonst prüft man Abwesenheit: ein Paketwert mit `<`,
`&` und einem Anführungszeichen (etwa ein Titel `R&D <test> "x"`), einmal durch
den Seitenbau, und die Seite muss ihn anzeigen statt an ihm zu zerbrechen.

**Abnahme:** ~~`docs/` unterscheidet sich gegenüber dem Stand davor nicht~~ —
diese Erwartung war falsch, siehe unten. Statt dessen: `python main.py` läuft
durch, jede Änderung an `docs/` ist einzeln erklärt, die eingebettete Index-JSON
parst, und ein Fixture-Titel mit `<`, `&`, Anführungszeichen und `</script>`
steht vollständig auf Kachel und Detailseite, statt die Seite zu zerlegen.

### Erledigt 2026-09-03

Der Umbau ist nicht eine Zeile in `step_site`, sondern eine Funktion in
`registry_utils`: `template_environment()` mit `autoescape=True`, benutzt von
`step_site`, `step_bridge` und `step_sparql`. Beide Seitenbauer hatten den
Fehler, nicht einer; ihn zweimal zu reparieren hiesse, ihn beim dritten
Generator wieder zu machen. `step_sparql` hat seine eigene Fassung aus S7
abgegeben. Dazu `script_json()` an derselben Stelle: JSON, das in einem
`<script>` landet, escaped `<`, `>` und `&` als `\uXXXX` und wird im Template
mit `| safe` roh ausgegeben.

**Die Annahme in der Planung war falsch: `docs/` ändert sich, und zwar an einer
Stelle, an der die Seite bisher etwas Falsches zeigte.** Drei Klassen von
Änderung, alle nachgesehen:

1. **Sieben Detailseiten zeigten ihre Koordinate unvollständig.** Das WKT-Literal
   beginnt mit `<http://www.opengis.net/def/crs/EPSG/0/4326>`; roh in ein
   `<code>` geschrieben liest der HTML-Parser das als unbekanntes Element und
   wirft es weg. Gemessen am gerenderten Text: vorher `POINT(-8.0 53.0)`,
   nachher `<http://…/4326> POINT(-8.0 53.0)`. Der Befund 30 war also nicht
   theoretisch, er hat die CRS-Angabe auf jeder Detailseite verschluckt.
2. **Die eingebettete Index-JSON** wurde durch das Autoescape zu `&#34;` und
   damit unbrauchbar — ein `<script>`-Element ist Rohtext, der Browser
   dekodiert darin keine Entities. Genau deshalb `script_json()` und `| safe`:
   roh, aber unfähig, das Element zu beenden oder ein Tag zu öffnen.
3. **Apostrophe in den Notizen der Crosswalk-Seite** stehen jetzt als `&#39;`.
   Bytes anders, Anzeige gleich. Die eine Zelle mit `{{ row.target or '&mdash;'
   | safe }}` ist auf das Zeichen „—" umgestellt: die Präzedenz von `or` und
   `| safe` machte dort nur den Ersatzwert roh, was niemand mehr erraten muss.

Fixture zweimal gefahren, gegen den gepushten Stand und gegen diesen. Titel
`R&D <test> "x" — fixture`: vorher zeigt die Kachel `"x" — fixture`, das
`<test>` steht als erfundenes Element im DOM; nachher steht der Titel
vollständig da. Titel `closing </script> fixture`: vorher scheitert
`JSON.parse` auf der eingebetteten Index-JSON, womit Suche und Facetten der
ganzen Startseite tot sind; nachher parst sie. Das ist der Schaden, den der
Fehler angerichtet hätte, sobald ein Paket einen solchen Wert trägt — und
Paketautoren schreiben Titel, keine HTML-sicheren Zeichenketten.

Zwei Läufe hintereinander, `git status` sauber; `--strict` grün; alle Seiten
über `--serve` mit 200, eingebettete JSON parst auch über HTTP. Was auch hier
nicht geprüft werden konnte: ob ein Browser die Seiten zeichnet (A4).

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

### Erledigt 2026-09-03

Gebaut wie geplant, mit zwei Abweichungen vom Familienmuster: der Generator
heisst `py/step_sparql.py` statt `build_sparql.py` (Schrittvertrag dieses Repos)
und es entsteht kein quarto-live-Notebook (A4). Neu im Baum: `queries.yaml`,
`py/templates/sparql.html.j2`, `docs/sparql.html`, `docs/downloads/queries/*.rq`,
`docs/vocab/` mit den drei Vokabulardateien. Der Link von der Facettenseite auf
`sparql.html` ist gesetzt — die eine Stelle, an der S7 auf S6 zurückgreift.

Acht Abfragen statt sieben: „Bestand je Lizenz und je Jahr" ist zweigeteilt,
weil beide Hälften so einzeln gegen die Facette gerechnet werden können.
Zeilenzahlen im Bau: `catalogue-overview` 7, `models-with-coordinates` 5,
`model-files` 12, `shared-concepts` 2, `creators-across-packages` 5,
`holdings-by-licence` 4, `holdings-by-year` 5, `crm-anchors` 24.

Der Gegentest, den S6 weitergegeben hat, ist eingebaut und grün: sieben
Einträge wie im Index, vier Lizenzwerte und fünf Jahreswerte deckungsgleich mit
den Facetten. Negativproben gefahren — eine Abfrage auf eine erfundene Klasse
und eine künstlich verstimmte Lizenzabfrage beenden den Schritt mit Exitcode 1,
ohne eine Datei zu schreiben.

Zwei Dinge waren anders als gedacht. Die Anker-Abfrage lieferte zunächst 7
statt 24 Zeilen, weil rdflib in `OPTIONAL { … UNION … }` nichts bindet
(Befund 31) — ein falsches Ergebnis, das wie eine Aussage über den Graphen
aussah. Und die Templates escapen seit S6 nicht, was hier auffiel, weil die
Abfragen in ein `<textarea>` gehen (Befund 30). Dazu ein Fund, der nicht in
diesen Schritt gehört: die `content/`-IRIs sind doppelt prozentkodiert
(Befund 33, Teil D).

Alle acht Abfragen sind zusätzlich gegen rdflib 7.1.1 nachgerechnet — die
Fassung, die die Seite im Browser installiert, nicht die des Bausystems. Gleiche
Zeilenzahlen. Was hier **nicht** geprüft werden konnte, ist die Seite selbst:
Pyodide verlangt einen `http://`-Origin und einen Browser. Geprüft ist, dass
alle vierzehn URLs, die die Seite anfasst, über `python main.py --serve` mit 200
antworten, dass das Skript syntaktisch fehlerfrei ist und die drei JSON-Blöcke
parsen. Ob die Seite antwortet, sagt erst ein Browser (A4).

## S8 — Registry als FDO, Release und CI

**Ziel:** der Katalog wird nach denselben Regeln zitierbar wie sein Inhalt.

`MD.cff` und `CITATION.cff` liegen im Repo-Root. `fdo_type: fdo:RegistryFDO`
— neuer vierter Typ, entschieden statt des vorgeschlagenen `fdo:AnalysisFDO`:
die Registry ist kein Analyseergebnis, und ein eigener Typ hält das für
spätere N4O-Konsumenten unterscheidbar. Der Typ, die Rollenklassifikation
(innerhalb des festen sechswertigen Vokabulars aus S3) und die
Pip-Installierbarkeit von `fdo-squirrel` selbst sind in drei Patches dort
gelandet (Befund 33 vorweg, dann `fdo:RegistryFDO` + `pyproject.toml` +
`--outdir`, dann ein zweiter, unabhängiger `--outdir`-Leck in
`rdf_modelling_report.json`) — alle drei gegen frische Klone verifiziert und
gepusht: `4ca86ae`, `3593c9f`, `504b7af`. `requirements.txt` pinnt auf den
letzten davon, dieselbe Begründung wie bei Pyodide/rdflib in S7.

**`py/step_release.py`** (neuer Schritt, network=False): kopiert
`dist/fdo-registry.ttl`, `dist/registry-index.json`, `metadata/shapes.ttl`,
`MD.cff` und `CITATION.cff` in ein ZIP und schickt es durch das
pip-installierte `fdo-squirrel` — nicht über `$PATH`
(`shutil.which`, findet eine nicht aktivierte venv nicht) und nicht über
`-m main` (Namenskollision: `fdo-squirrel`s Einstiegsmodul heißt `main`,
genau wie der Orchestrator hier — `-m` stellt das Arbeitsverzeichnis vor die
Paketpfade und träfe dieses `main.py`, nicht das installierte). Stattdessen
das Konsolenskript direkt neben `sys.executable` gesucht, wie `pip` es dort
platziert. Ergebnis landet in `dist/release/` (gitignored — ein
rebuildbares Nebenprodukt aus bereits versionierten Quellen, keine zweite
zitierbare Fassung, siehe `.gitignore`).

**Eine zweite Namenskollision, hier statt in `fdo-squirrel`:** die neue
Pfadkonstante für `dist/release/` hieß zuerst `RELEASE` — und überschrieb
damit stillschweigend das schon vorhandene `RELEASE` (das Release-*Datum*
der Registry, `"2026-09-03"`, in `dct:issued`, dem User-Agent, den
Templates und dem Qualitätsbericht verwendet). Ein `python main.py
--strict` gegen einen frischen Klon hat es gezeigt: `dct:issued` bekam den
Dateipfad statt des Datums, `step_index` stürzte beim JSON-Schreiben eines
`Path`-Objekts ab. Umbenannt in `RELEASE_DIR`; derselbe Rundlauf danach
grün. Festhaltenswert, weil `u.RELEASE` als Name naheliegend war und der
Fehler erst beim vollen `--strict`-Lauf auffiel, nicht beim isolierten Test
von `step_release` allein.

**Bewusst nicht automatisiert:** der Zenodo-Publish. Braucht einen Menschen
mit Zugangsdaten, dieselbe Begründung wie bei `harvest` (A4,
„Netzschritt im Standardlauf"). `step_release` baut das fertige Bundle-ZIP
und sagt, dass es von Hand hochzuladen ist; die daraus entstehende DOI geht
danach von Hand in `registry/sources.json`, wie jeder andere Eintrag.

**Zwei GitHub Actions:** `build.yml` baut bei jedem Push/PR `main.py
--strict` (schließt `harvest`/`check-updates` automatisch aus, da
network=True); `pages.yml` deployt das bereits committete `docs/` nach
GitHub Pages, ohne selbst neu zu bauen — dieselbe Begründung wie bei
`dist/`: `docs/` ist versioniertes Erzeugnis, kein CI-Artefakt.

## S9 — N4O-Andockung

**Ziel — korrigiert 2026-09-04 (Flo):** kein Eintrag in `n4o-collections.json`
durch dieses Repo — das übernimmt VZG von Hand, sobald ein gültiges Bundle
vorliegt. Unsere Aufgabe endet hier: alle geernteten FDO-TTL plus die Registry
selbst als DCAT modelliert, vollständig an CIDOC CRM verankert (das ist,
wofür `dist/fdo-registry-n4o.ttl` seit S5 schon gebaut wird), durch
`n4o-rse/n4o-kg-profile` SHACL-validiert, in einem eigenen Repo, das per Hand
mit Zenodo gesynct wird.

**Drei-Repo-Muster von `n4o-kg-profile`**, gegen den echten Code geprüft
(nicht nur das README), 2026-09-04:

```
fdo-squirrel-registry            Quellrepo — baut das Bundle, kennt den KG nicht
    dist/fdo-registry-n4o.ttl    schon da, SHACL-gated seit S5
        │  raw.githubusercontent.com, je Build gezogen
        ▼
fdox-squirrel-n4o-collection      Collection-Repo, neu angelegt
    metadata.yaml                 die einzige von Hand gepflegte Datei
    .github/workflows/build.yml   ruft n4o-kg-profile als reusable workflow
        │  uses: n4o-rse/n4o-kg-profile/…/collection.yml@v1
        ▼
dist/n4o-collection.ttl           Registrierungssatz, das liest N4O
dist/metadata.ttl                 DCAT + VoID-Statistik + CRM-Alignment + Queries
```

**Was dafür *nicht* gebraucht wird — A1 Befund 35:** der Selbsteintrag der
Registry braucht keinen neuen Code in `step_bundle.py`. `python main.py --only release` (S8) tatsächlich laufen lassen bestätigt: die bestehende Kette
erzeugt schon `dist/release/fdo-metadata.ttl`, typisiert
`a dcat:Dataset, crmdig:D1_Digital_Object, crm:E73_Information_Object, fdo:RegistryFDO`. Was fehlt, sind drei von Hand zu tuende Schritte, alle schon in A4/S2/S8
vorgesehen: Zenodo-Publish, DOI in `sources.json`, `harvest`+`bundle` neu
laufen lassen. Danach steht die Registry im nächsten `fdo-registry-n4o.ttl`
als achter `dcat:Dataset` — ohne dass dieser Schritt hier etwas ändern
musste.

**Was `fdox-squirrel-n4o-collection` bekommen hat** (voller Baum, kein
`primer-repo`-Skelett — `n4o-kg-profile`s eigene Konvention verlangt genau
eine `metadata.yaml`):

- `metadata.yaml` — die vier N4O-Pflichtfakten (`title`, `homepage`,
  `sameAs`, `license`), NCMDP-Kern, `distributions` zeigt per `source:`/
  `downloadURL` auf `raw.githubusercontent.com/FDOx-squirrel/fdo-squirrel-registry/main/dist/fdo-registry-n4o.ttl` (nicht committet — jeder Build zieht frisch, der Selbsteintrag
  landet damit automatisch, ohne Änderung an diesem Repo), `model.classes`
  ordnet jede im Bundle vorkommende native Klasse ihrem CRM-Anker zu.
  `sameAs` trägt einen sichtbaren `TODO`-Platzhalter (kein Wikidata-Item
  vorhanden, A4) — ein `strict`-Build bleibt bis dahin absichtlich rot.
- `model.classes`, gegen den echten Bundle geprüft (`rdflib`, `SELECT DISTINCT ?class (COUNT(?s) AS ?n) WHERE { ?s a ?class }` gegen
  `dist/fdo-registry-n4o.ttl`, 2026-09-04): die meisten Klassen tragen ihren
  CRM-Anker schon direkt am Knoten (A3, „instance"-Mechanismus — z. B. jede
  `dcat:Distribution` ist zugleich `crmdig:D9_Data_Object`), die Zuordnung
  dokumentiert diese Paarung. Die einzige echte Ausnahme ist `skos:Concept`:
  die sechs Rollenkonzepte hängen nur über ein globales Ext-Axiom
  (`crm_bridge.ttl`, im n4o-Bundle enthalten) an `crm:E28_Conceptual_Object`,
  nicht je Instanz — deshalb steht diese Zeile explizit da. Terminologische
  Knoten (`owl:Ontology`, `owl:ObjectProperty`, `owl:DatatypeProperty`) und
  `skos:ConceptScheme` (das Profil selbst hat dafür bewusst keine
  CRM-Klasse) sind ausgelassen, aus denselben Gründen wie in unserer eigenen
  Ankerprüfung (A4).
- `.github/workflows/build.yml` — auf `@v1` gepinnt, wie `n4o-kg-profile`
  selbst dokumentiert (A4), aber **nur `workflow_dispatch`, kein `push`**:
  siehe die beiden Blocker unten. Sobald behoben, ist das Nachtragen von
  `push: {branches: [main]}` die einzige nötige Änderung.
- `ISSUE-DRAFT-n4o-kg-profile.md` — fertiger Text für ein Issue in
  `n4o-rse/n4o-kg-profile`, mit den Belegen aus den Befunden unten. Nicht
  automatisch eingereicht.
- `README.md`, `LICENSE` (MIT), `CITATION.cff`.

**Zwei Upstream-Blocker in `n4o-rse/n4o-kg-profile`, beide 2026-09-04 direkt
am Code geprüft, nicht nur am README** (A1, Befunde 36/37):

1. **Kein `v1`-Tag.** `git ls-remote --tags https://github.com/n4o-rse/n4o-kg-profile.git` liefert nichts — `uses: …@v1` hat aktuell nichts, worauf es
   auflösen könnte.
2. **`action.yml` checkt einen 404-Org-Pfad aus.** `actions/checkout` darin
   zeigt fest auf `repository: Research-Squirrel-Engineers/n4o-kg-profile` —
   die Org existiert (200), das Repo liegt dort nicht (404, kein Redirect,
   anders als bei `fdo-squirrel-registry` selbst, das tatsächlich
   transferiert wurde, A1 Befund 38). Das sitzt in der Action selbst und
   lässt sich von einer aufrufenden Collection nicht umgehen, auch nicht
   durch Pinnen auf einen Commit statt eines Tags.

Beides ist nicht durch dieses Repo oder das Collection-Repo zu beheben —
Issue-Entwurf liegt bereit, das Einreichen ist eine Entscheidung von Flo.

**Was danach noch fehlt, bevor ein `strict`-Build grün wird:**

- ein Wikidata-Q-Item für die Registry (`schema:sameAs`, `sh:Violation`,
  A4) — offen, absichtlich nicht erfunden;
- eine echte DOI für `homepage` (`foaf:homepage`, `sh:Violation`) — hängt an
  S8s Zenodo-Publish, siehe oben;
- der `v1`-Tag und der Checkout-Fix bei `n4o-rse/n4o-kg-profile`.

**Abnahme, sobald alle drei behoben sind:** `python build/make_metadata.py`
(bzw. der Workflow) läuft `strict`, `dist/n4o-collection.ttl` und
`dist/metadata.ttl` entstehen, keine Klasse im Bundle bleibt ohne
CRM-Alignment gemeldet, jede Beispielabfrage liefert Zeilen.

---

# Teil D — Offene Punkte

- ~~**Verhältnis zur SquirrelBase.**~~ Entschieden 2026-09-03 in S6: die
  Registry nimmt die Q-ID auf, wenn ein Mensch sie in `sources.json` einträgt,
  und fragt die SquirrelBase nie selbst. Offen bleibt nur die IRI-Form der
  Instanz (`SQUIRRELBASE_ENTITY_NS`, A4) und die Gegenrichtung: ob die
  SquirrelBase je Objekt auf den Katalogeintrag zeigen soll statt nur auf die
  FDO-URL. Das ist eine Frage an die SquirrelBase, nicht an dieses Repo.
- ~~**Doppelt kodierte `content/`-IRIs.**~~ Entschieden 2026-09-03 nach S7: der
  Fehler wird upstream in `fdo-squirrel` behoben, nicht in der Registry (A4,
  Befund 33). **Behoben 2026-09-04 in `fdo-squirrel`** (`fdo_rdf.py`, Commit
  „Stop double-percent-encoding content/ distribution IRIs"): der Generator
  schreibt den Pfad jetzt roh (Turtle-escaped, nicht prozentkodiert) in die
  URN, `content_iri()` hier kodiert ihn dadurch wie vorgesehen genau einmal.
  Gegen ein synthetisches Testpaket mit Leerzeichen/Kommas/Unterordnern im
  Dateinamen (der Härtefall für diesen Bug) end-to-end durch `term_map()` +
  `content_iri()` geprüft: einfach kodiert, kein `%25` mehr. Betrifft nur neu
  generierte Pakete — die sieben bereits publizierten Zenodo-Records tragen
  `%252F` weiterhin, das ist unveränderlich (A3).
- ~~**`select_autoescape` greift in `step_site` nicht.**~~ Ist seit 2026-09-03
  Schritt **S6b** in Teil B (A1, Befund 30).
- **Labels für fremde IRIs auf Dauer.** `registry/labels.json` ist von Hand
  gepflegt (A4) und wächst mit jedem Paket. Ab welcher Zahl das lästig wird,
  ist offen; der billigste Ausweg wäre ein Netzschritt neben `harvest`, der
  Labels holt und *vorschlägt*, wie `--resolve` es mit `sources.json` tut.
  Nicht vor S8 — heute sind es vierzehn IRIs.
- **Wer darf einreichen.** Bislang kuratiert (A4). Sobald Dritte FDOs beitragen
  wollen, braucht es einen Weg: Pull Request auf `sources.json` mit
  CI-Prüfung wäre der billigste. Erst relevant, wenn es Dritte gibt.
- **Zenodo als einzige Quelle.** Der Ernter kennt heute nur die Zenodo-API. Ein
  FDO auf einem anderen Repositorium wäre über eine direkte TTL-URL im
  `sources.json` einzubinden; das würde die Prüfsummen-Logik ändern.
- **`fdo:RegistryFDO`.** Falls S8 einen neuen FDO-Typ braucht, gehört er nach
  `fdo-squirrel`, nicht hierher — und dann ist die Beschlusslage in A4 zum
  Ort des Ankers ohnehin nochmal zu betrachten.
- **`fdo-squirrel`s Beispielpaket ist stehen geblieben.** Beim S8-Vorlauf
  geprüft (2026-09-04): `example_fdo/MD.cff` validiert nicht mehr gegen das
  aktuell geladene Schema (`schemas/md_cff/MD.cff-schema.yaml`) — es benutzt
  noch die Feldnamen einer älteren Fassung (`abstract`/`publisher` statt
  `description`/`publishers` u.a.). Dazu liegt am Repo-Root ein totes
  `MD.cff.schema.yaml`, das laut `main.py` gar nicht mehr geladen wird — zwei
  Schemadateien, eine davon Leiche. Reine Aufräumarbeit in `fdo-squirrel`,
  nichts, das S8 hier blockiert.
- ~~**Personen-URN über Paketgrenzen.**~~ Erledigt 2026-09-03 in S3: sie ist
  stabil (A1, Befund 11), die Umschreibung ist registry-global (A4).
- **Fehlerhafte Pakete im Bestand.** Vier von sieben TTL parsen nicht (A1,
  Befund 10); seit S4 werden sie mit deklarierten Reparaturen gelesen, stehen
  also im Katalog, aber der Defekt bleibt in den publizierten Records. Ob wir
  vor S6 einen Durchgang „upstream reparieren und neu publizieren" einschieben,
  ist eine Frage an den Zeitplan, nicht an die Technik — `dist/quality_report.md`
  aus S5 ist die Liste, aus der er gefahren wird: 46 Befunde über sieben
  Pakete, dazu Record 18740524 ganz ohne TTL.
- **`<DOI>_geom` und `<DOI>_temporal`.** Vom Generator geprägte IRIs in einem
  fremden Namensraum (A1, Befund 6). Umschreiben verletzt A3, Stehenlassen
  veröffentlicht DOI-artige IRIs, die nicht auflösen. In S4 zu entscheiden;
  die saubere Lösung liegt upstream.
- **Rückfluss nach `fdo-squirrel`.** Der Beschluss lautet „Registry zuerst,
  upstream später". Wann später ist, hängt an S3: sobald die Abbildung ein
  echtes Paket unbeanstandet durchs Gate bringt, ist sie reif für den
  Generator. Der Qualitätsbericht aus S5 sagt, was dabei zuerst zu reparieren
  ist. Die Liste ist inzwischen benannt: abgekürzte Klassen-IRIs (Befund 3),
  fehlende Labels an Orten und Konzepten (Befund 24), ORCID statt Personen-URN
  (Befund 12), `xsd:integer` an Zeitgrenzen (Befund 15), `dcat:bbox` statt
  `geo:hasBoundingBox` (Befund 16) und die doppelte Prozentkodierung in
  `urn:fdo-squirrel:content/…` (Befund 33, A4).
