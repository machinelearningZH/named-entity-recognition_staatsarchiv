## Postprocessing

In einem weiteren Schritt werden alle NE aus den TEI-XML für die Nachbearbeitung extrahiert. Bei Ausführung der Python-Skripte werden pro NE-Typ ein csv mit folgenden Feldern erstellt:

- *FilePath* (Pfad und Dateiname des TEI-XML)
- Das extrahierte NE (*persName*, *orgName* oder *placeName*)
- *documentDate* (Die Datierung des Dokuments, beispielsweise für Statistiken zu Entwicklungen über einen Zeitraum)
- *n* (Die eindeutige ID des NE für die Rücküberführung ins TEI-XML)
- *Context* (Einige Zeichen vor und nach dem NE, um Kontext zu erhalten. So wird die Identifikation des NE bei der Verknüpfung mit Normdaten einfacher.)
<br/>

### Verwendung

<br/>

```
python extract_persname.py /path/to/your/folder /path/to/your/output.csv
```

<br/>

### Beispielauswertung

<br/>

![Beispiel Organisation Bund](assets/example_orgName_Bund.png)


