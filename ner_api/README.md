### Projekt «Named Entity Recognition Zentrale Serien Staatsarchiv Kanton Zürich»

# NER API

Dieses Werkzeug ist Teil des Projekts **«Named Entity Recognition für die zentralen Serien des Staatsarchivs Kanton Zürich».**

Das Projekt hat die [Abteilung «Data» des Statistischen Amts](https://www.zh.ch/de/direktion-der-justiz-und-des-innern/statistisches-amt/data.html) des Kantons Zürich gemeinsam mit dem [Staatsarchiv](https://www.zh.ch/de/direktion-der-justiz-und-des-innern/staatsarchiv.html) entwickelt.
-   Verantwortlich: **Adrian van der Lek, Rebekka Plüss**
-   Softwareentwicklung: **Adrian van der Lek**
-   Mitarbeit (Dokumentation, Organisation): Patrick Arnecke, Dominik Frefel

## Übersicht

Die API kann eingesetzt werden **alleinstehend** als Plaintext-verarbeitender NER-Server (siehe API-Dokumentation) oder **in Zusammenhang mit dem TEI Publisher** und **wahlweise** dem NER-CLI-Tool für gestützte manuelle Annotation und automatisierte Batchannotation respektive.

-   Die API ist nur mit der im Repository TODO hinterlegten TEI Publisher-Version kompatibel.
-   Im Gegensatz zur ursprünglichen Version ist es nicht möglich, ein Modell via TEI Publisher zu trainieren.
-   Die spaCy-Pipeline wird architekturbedingt zur Laufzeit erzeugt (es können keine anderen spaCy-Pipelines geladen werden) und es kann nur ein SpanMarker-Modell auf einmal geladen werden.
-   Einstellungen werden über die API bzw. via NER CLI-Tool gesteuert.
-   Codebasis der API: <https://github.com/eeditiones/tei-publisher-ner>

## Voraussetzungen

Erfordert pip.

```         
pip install -r requirements.txt
```

## Server starten

Hinweis: Wird die API in Zusammenhang mit dem TEI-Publisher eingesetzt und ein alternativer Port verwendet, muss das Dockerfile des TEI-Publishers angepasst und ein neues Image erzeugt werden.

```         
python -m uvicorn app.main:app --reload --host localhost --port 8001 &
```

## NER-Demo

Streamlit-Applikation für die manuelle Evaluation der Pipeline anhand beliebigen Plaintexts, ohne Regex-Matching. Hinweis: Es dauert einige Sekunden, bis im Browser eine Ausgabe erfolgt.

```         
streamlit run ner_demo.py -- "$(cat samples/lokalbahn_gmunden.txt)"
```

## Dateistruktur

```         
├── .env                                Konfiguration via Umgebungsvariablen
├── README.md
├── app
│   ├── cache.py                        Cache- und Modellobjekte
│   ├── main.py                         Applikation
│   ├── spacy_integration.py            Modifizierte Spacy-Integration des SpanMarkers
│   └── util.py
├── ner_demo.py                         NER-Demo (streamlit)
├── requirements.txt
├── resources
│   ├── date_regex.txt                  Datums-Regex
│   ├── locs_within_orgs_regex.txt      Regex für in Organisationen eingebettete Ortschaften
│   ├── log_conf.yaml                   Logging-Konfiguration
│   └── tagset_mapping.json             Mapping von TEI-Publisher NE-Tags zu NER NE-Tags
└── samples
   └── lokalbahn_gmunden.txt
```

## Einstellungen

Sämtliche Defaulteinstellungen werden via Umgebungsvariablen in `.env` spezifiziert. Taggingeinstellungen und geladenes SpanMarker-Modell lassen sich zur Laufzeit via API verändern (siehe API-Dokumentation und Aufrufparameter des NER-CLI-Tools).

| **Parameter**               | **Defaultwert**                                        | **Beschreibung**                                                                                                                                                                                                                                       |
|-------------------------------|--------------------|---------------------|
| PIPELINE_NAME               | span_marker_spacy_sentencizer                          | Name der Pipeline, wie er im TEI Publisher angezeigt und auf der CLI geloggt wird. (Anm.: Im TEI Publisher ist stets von "Modell" die Rede, es handelt sich jedoch um die spaCy-Pipeline, in die das Modell eingebettet wird).                         |
| SM_MODEL                    | TODO                                                   | Pfad zum SpanMarker-Modell.                                                                                                                                                                                                                            |
| DEVICE                      | mps                                                    | Inferenz-Device. Apple Mx GPU: "mps".                                                                                                                                                                                                                  |
| NE_TAGS                     | \["LOC","ORG","PER","LOCderiv","ORGderiv","PERderiv"\] | Liste der zu berücksichtigenden NE tags.                                                                                                                                                                                                               |
| NE_THRESHOLDS               | {"LOCderiv":0.08, "ORGderiv":0.9, "PERderiv":0.87}     | Nachgeschalteter Schwellenwert pro NE-Tag. Die Standardwerte wurden grob anhand der Precision-Recall-Kurven einer 5-CV in Hinblick auf eine Precision von 0.8 geschätzt. Wenn leer oder fehlend, greift nur der interne Schwellenwert des SpanMarkers. |
| TAG_WITH_SM                 | true                                                   | Text mit SpanMarker auszeichnen.                                                                                                                                                                                                                       |
| TAG_LOCS_WITHIN_ORGS        | true                                                   | In Organisationen eingebettete Orte per RegEx auszeichnen. Setzt TAG_WITH_SM nicht voraus, da die SpanMarker-Auszeichnung intern immer ausgeführt wird.                                                                                                |
| TAG_DATES                   | true                                                   | Datumsausdrücke per RegEx auszeichnen.                                                                                                                                                                                                                 |
| LOCS_WITHIN_ORGS_REGEX_PATH | resources/locs_within_orgs_regex.txt                   | Pfad zum RegEx für in Organisationen eingeschachtelte Orte.                                                                                                                                                                                            |
| DATE_REGEX_PATH             | resources/date_regex.txt                               | Pfad zum RegEx für Datumsausdrücke. Kann mit Zeilenumbrüchen formatiert werden.                                                                                                                                                                        |
| TAGSET_MAPPING_PATH         | resources/tagset_mapping.json                          | Pfad zum Mapping von TEI-Publisher NE-Tags zu NER NE-Tags.                                                                                                                                                                                             |
| ADDITIONAL_PUNCTUATION      | \[";", ":"\]                                           | Liste zusätzlicher Interpunktionszeichen, die als Satzgrenzen behandelt werden.                                                                                                                                                                        |
| SPLIT_OVERLONG_SENTENCES    | true                                                   | Sätze, welche die Tokenlimite des SpanMarkers überschreiten, aufteilen. Hinweis: Die Aufteilung erfolgt nach der Trennung an zusätzlichen Interpunktionszeichen.                                                                                       |
| DEBUG                       | false                                                  | Debuginformationen zu spaCy-Pipeline, Einstellungen und Speicherauslastung des Modells ausgeben.                                                                                                                                                       |
| TEI_PUBLISHER_ADDRESS       | http://localhost:8080                                  | Addresse des TEI-Publishers. Wird für URL-Kürzung benötigt (`<TEI publisher URL>/exist/apps/tei-publisher/annotate/*.xml -> <NER API URL>/d/*.xml`), die vom CLI-Tool verwendet wird.                                                                  |

## API-Dokumentation

Automatisch erzeugte FastAPI-Doku: <http://localhost:8001/docs>

## Quellenangaben

Regex für Orte innerhalb von Named Entities: Ortschaften und Gemeinden aus dem Amtlichen Ortschaftenverzeichnis extrahiert (Release 2023, ©swisstopo). Der Regex kann mit dem Jupyternotebook `notebooks/extract_locs_for_regex.ipynb` neu erzeugt werden.
