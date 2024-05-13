### Projekt «Named Entity Recognition Zentrale Serien Staatsarchiv Kanton Zürich»

# NER CLI-Client

Dieses Werkzeug ist Teil des Projekts **«Named Entity Recognition für die zentralen Serien des Staatsarchivs Kanton Zürich».**

Das Projekt hat die [Abteilung «Data» des Statistischen Amts](https://www.zh.ch/de/direktion-der-justiz-und-des-innern/statistisches-amt/data.html) des Kantons Zürich gemeinsam mit dem [Staatsarchiv](https://www.zh.ch/de/direktion-der-justiz-und-des-innern/staatsarchiv.html) entwickelt.
-   Verantwortlich: **Adrian van der Lek, Rebekka Plüss**
-   Softwareentwicklung: **Adrian van der Lek**
-   Mitarbeit (Dokumentation, Organisation): Patrick Arnecke, Dominik Frefel

## Übersicht
Das Kommandozeilentool ermöglich eine automatisierte Eigennamenerkennung (Named Entity Recognition, NER) von TEI-XML-Korpora. 

- Named Entities werden mittels Tags ausgezeichnet, die Attribute aufweisen (UUIDv4, sowie `type="deriv"` im Falle derivierter NEs). - Dieses Werkzeug benötigt eine Instanz des im gleichen Repository hinterlegten modifizierten TEI Publishers (TODO Link) (typischerweise als Podman-Container), sowie der modifizierten TEI Publisher API (TODO Link). 
- Ordner mit Dokumenten lassen sich flach oder rekursiv verarbeiten, im zweiten Fall wird die Ordnerstruktur im Zielverzeichnis reproduziert. 
- Über einen Link lassen sich einzelne Dokumente während der Verarbeitung im TEI Publisher sichten.

Beim Start überprüft das Tool, ob der TEI Publisher und die NER API des TEI Publishers unter den in .env spezifzierten Adressen erreichbar sind. Zudem konfiguriert es die NER API mit allfällig spezifizierten Taggingoptionen und kontrolliert, dass diese korrekt gesetzt wurden. Falls eines dieser Kriterien nicht erfüllt ist, erfolgt ein Abbruch.

Nach erfolgter Annotation eines Dokuments erfolgt ein Sanitycheck, ob der Text des Dokumenten-Bodys und aller untergeordneten Knoten bei der Annotation verändert wurde. Fehlerhafte Dokumente werden gelogggt und ins Unterverzeichnis `error` des Exportpfads verschoben. 

**Wichtig**: Allfällige Änderungen an Tags und Attributen, sowie Metaden werden *nicht* überprüft.

## Voraussetzungen

Für Massenannotation wird eine schnelle GPU benötigt. Auf der GPU des Apple M2 Max können ca. 200 Token pro Sekunde verarbeitet werden.

Erfordert pip.

```         
pip install -r requirements.txt
```

## Aufruf

Aufruf mit aktuellen Parametern der NER API, rekursiver Suche im Inputverzeichnis und Standardexportverzeichnis gemäss `.env` (default: `$pwd/export`):

```         
./ner -r -i ~/path/to/input
```

Spult bis zum ersten Unterzeichnis vor, das den Substring `MM_01_010` enthält:

```         
./ner -r -i ~/path/to/input -cf MM_01_10
```

## Hinweise

-   Vor Bearbeitung jedes Verzeichnisses wird das Datenverzeichnis der NER-Collection (annotate) in der Datenbank des TEI-Publishers geleert, weshalb manuelle Änderungen nicht vorgesehen sind Während der Bearbeitung kann die Annotation von Dokumenten über den geloggten Link im TEI-Publisher verifiziert werden. Die Verarbeitung kann via SIGSTOP (Ctrl+Z) pausiert und mittels SIGCONT (`fg`) fortgesetzt werden. Nach Beendigung der Annotation verbleiben die Dokumente des zuletzt verarbeiteten Unterordners zwecks Analyse und allfälliger Fehlersuche in der Datenbank.
-   Änderungen an Taggingeinstellungen und SpanMarker-Modell sind **persistent**, werden also beim nächsten Aufruf ohne Tagging-/Modellparameter wiederverwendet. Die NER API kann via Kommandozeilentool mittels `--reset-api (-ra)` auf die Standardeinstellungen (.env der NER API) zurückgesetzt werden.
-   Es ist möglich, ausschliesslich in Organisationen enthaltene Orte zu taggen. Die SpanMarker-Annotation erfolgt in diesem Fall ebenfalls, wird jedoch nicht an den TEI Publisher übermittelt. **Achtung**: Der TEI Publisher unterstützt in der verwendeten Version keine nachträgliche Annotation von eingeschachtelten Entitäten! Umgebende und geschachtelte Entitäten müssen im selben Durchgang übermittelt werden.

## Sanity-Checks

Das Tool erkennt ungültige XMLs. Dateinamen, die Leerschläge enthalten, sind nicht erlaubt. Nach Annotation eines Dokuments erfolgt ein Plaintextabgleich, um unerwünschte Änderungen zu erkennen und auszuweisen.

## Logging

Fehler werden fortlaufend in `ROOT/log/run-*.log` geloggt. Fehlerhafte Dateien werden in `ROOT/error/` abgelegt, zudem wird nach Verarbeitung jedes Subpfades die Datei `ROOT/log/error-*.json` aktualisiert, die den Fehlergrund, den Inhalt der XML-Datei vor und nach der Annotation, sowie in Fällen von Diff-Fehlern einen Diff der Plaintext-Unterschiede aufführt.

## Caveat

Die verwendete Version des TEI Publishers verursacht in vereinzelten Fällen Diff-Fehler, zudem können bei der Rücküberführung der extrahierten Entities ins XML Timeoutfehler auftreten. Timeouts hängen nicht mit der Dokumentenlänge zusammen, können also auch bei sehr kurzen Dokumenten auftreten.

Es empfiehlt sich, nach Verarbeitung einer Sammlung das Log zu prüfen. Anhand der Angaben in ROOT/log/error\*.json lassen sich Diff-Fehler von Hand korrigieren.

## Umgebungsvariablen (.env)

| Parameter               | Standardwert        | Beschreibung                                                                                                                                                                 |
|---------------|---------------|-------------------------------------------|
| ROOT                    | export/             | Pfad des Exportverzeichnis.                                                                                                                                                  |
| TEIPUBLISHER_USER       | stazh               | TEI-Publisher-Nutzer.                                                                                                                                                        |
| TEIPUBLISHER_PASSWORD   | (nicht gesetzt)     | Passwort des TEI-Publisher Nutzers.                                                                                                                                          |
| TEIPUBLISHER_ADDRESS    | http://0.0.0.0:8080 | Adresse des TEI-Publishers.                                                                                                                                                  |
| TP_NER_API_ADDRESS      | http://0.0.0.0:8001 | Adresse der TEI Publisher NER API. Anmerkung: Wird die API mit einem anderen Port gestartet, muss das TEI Publisher Dockerfile angepasst und ein neues Image erzeugt werden. |
| PER_1000_TOKEN_DURATION | 5                   | Anzahl Sekunden pro 1000 Token. Wird für die Schätzung der Verarbeitungsdauer verwendet (Standardwert für M2 Max überschlagen).                                              |
| REQUEST_TIMEOUT         | 30                  | Timeout in Sekunden für sämtliche Requests ausser Entitätsextraktion. Fängt Fehler ab, die seitens TEI Publisher keine Response erzeugen.                                    |
| DEBUG                   | 0                   | Debugging-Modus mit ausführlichem Logging.                                                                                                                                   |

## Kommandozeilenparameter:

```         
usage: KtZH/StAZH TEI XML Named Entity Recognition CLI client [-h] -i INPUT_PATH [-o OUTPUT_PATH] [-cf CONTINUE_FROM] [-sm SM_MODEL]
                                                              [-r] [-tsm | --tag-with-sm | --no-tag-with-sm]
                                                              [-tlwo | --tag-locs-within-orgs | --no-tag-locs-within-orgs]
                                                              [-td | --tag-dates | --no-tag-dates] [-ra]

Supports SpanMarker NER, as well as regex-based tagging of LOCs nested in ORGs and dates.

options:
  -h, --help            show this help message and exit
  -i INPUT_PATH, --input-path INPUT_PATH
                        Input path
  -o OUTPUT_PATH, --output-path OUTPUT_PATH
                        Output path. If not specified, files are stored in the default output directory (see README)
  -cf CONTINUE_FROM, --continue-from CONTINUE_FROM
                        Skip directories up to one that matches the specified string. Note that strings are always matched as
                        substrings, specify full string for exact matching
  -sm SM_MODEL, --sm-model SM_MODEL
                        SpanMarker model. If not specified, the model currently set in the NER API server is used.
  -r, --recursive       Whether to walk the directory recusively. The directory structure is replicated in the output directory.
  -tsm, --tag-with-sm, --no-tag-with-sm
                        Tag persons, locations and organizations with SpanMarker
  -tlwo, --tag-locs-within-orgs, --no-tag-locs-within-orgs
                        Tag LOCs nested in ORGs using the corresponding regex of the NER service. Can be used independently from
                        "--tag-with-sm"
  -td, --tag-dates, --no-tag-dates
                        Tag date expressions using the corresponding regex of the NER service.
  -ra, --reset-api      Reset NER settings as defined in the .env of the NER API
```