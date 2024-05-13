---
license: mit
library_name: span-marker
base_model: stefan-it/span-marker-gelectra-large-germeval14
tags:
- span-marker
- token-classification
- ner
- named-entity-recognition
pipeline_tag: token-classification
widget:
- text: "Konstruiertes Beispiel: Hans Meier besitzt eine Firma im zürcherischen Wil. Die Meier AG war Thema einer kantonsrätlichen Sitzung. Im Meierschen Besitz ist auch ein Anwesen, das sich in unmittelbarer Nachbarschaft zu Liegenschaften des Kantons befindet und unweit der Grenze zum Kanton Aargau gelegen ist."
  example_title: "Test sentence with all labels"
- text: "Böckli - Zürich erklärt, daß die Sozialdemokratische Fraktion bei allem Verständnis für die Kritik Winigers der Vorlage mit großer Mehrheit zustimmt. Das ungeschickte Vorgehen der «Swissair» bei der Kapitalerhöhung ist zu bedauern. Es war unglücklich, daß keine öffentliche Auflage der neuen Aktien durchgeführt wurde. Für die Stellungnahme der Zürcher Kantonalbank war ausschlaggebend, daß das Bankgesetz solche Beteiligungen ablehnt."
  example_title: "Cantonal council meeting notes"
language:
- de
---

# SpanMarker KtZH StAZH

This is a [SpanMarker](https://github.com/tomaarsen/SpanMarkerNER) model that is based on the [GELECTRA Large](https://huggingface.co/stefan-it/span-marker-gelectra-large-germeval14) variant of the **SpanMarker for GermEval 2014 NER** and further fine-tuned on meeting notes from the cantonal council, resolutions of the governing council and law text from the corpus juris of the Canton of Zurich. The documents span the 19th and 20th century, covering both historical language with varying degrees of standardization and contemporary language. Distinguished are `PER`son, `LOC`ation, `ORG`anisation, as well as derivations of Named Entities (tag suffix `-deriv`).

The `ORG`anisation class has been extended to encompass institutions that have been deemed to be reasonably unambiguous in isolation or by virtue of their usage in the training data. Purely abstract/prototypical uses of institutions are generally out of scope (the model does not perform concept classification), can however occasionally arise.

## Usage

The fine-tuned model can be used like:

```python
from span_marker import SpanMarkerModel

# Download from the 🤗 Hub
model = SpanMarkerModel.from_pretrained("team-data-ktzh/span-marker-ktzh-stazh")

# Run inference
entities = model.predict("Hans Meier aus Dielsdorf vertritt im Kantonsrat die FDP.")
```

## Model Details

### Model Description
- **Model Type:** SpanMarker
- **Encoder:** [deepset/gelectra-large](https://huggingface.co/deepset/gelectra-large) (ELECTRA Large)
- **Maximum Sequence Length:** 256 tokens
- **Maximum Entity Length:** 8 words
- **Training Dataset:** see https:// TODO
- **Language:** de
- **License:** MIT

### Model Sources
- **Training repository (TODO):** []()
- **SpanMarker:** [SpanMarker on GitHub](https://github.com/tomaarsen/SpanMarkerNER)

### Model Labels
| Label | Examples                                                                                              |
|:------|:------------------------------------------------------------------------------------------------------|
| PER      | Hans Müller   | 
| LOC      | Zürich    | 
| ORG      | SBB, Swissair, Kantonsrat, Bundesgericht | 
| PERderiv | Müllersche   | 
| LOCderiv | zürcherische    |
| ORGderiv | bundesgerichtlicher    | 

## Cross-validation evaluation

Evaluation relies on SpanMarker's internal evaluation code, which is based on `seqeval`.

### Average per-label metrics
| Label    |    P |    R |   F1 |
|:---------|-----:|-----:|-----:|
| PER      | 0.97 | 0.97 | 0.97 |
| LOC      | 0.95 | 0.96 | 0.96 |
| ORG      | 0.92 | 0.95 | 0.93 |
| PERderiv | 0.40 | 0.30 | 0.33 |
| LOCderiv | 0.86 | 0.85 | 0.85 |
| ORGderiv | 0.73 | 0.76 | 0.74 |

### Overall per-fold validation metrics
| Fold  |  Precision |  Recall  | F1 | Accuracy |
|:-----:|:---------------------:|:------------------:|:-------------:|:-------------------:|
| 0     |  0.927                | 0.952              | 0.939         |  0.992              |  
| 1     |  0.942                | 0.957              | 0.949         |  0.993              | 
| 2     |  0.938                | 0.946              | 0.942         |  0.992              | 
| 3     |  0.921                | 0.951              | 0.936         |  0.992              | 
| 4     |  0.945                | 0.949              | 0.947         |  0.993              |

### Confusion matrix
![Confusion matrix](confusion_matrix.png)

(Note that the confusion matrix also lists other labels from the GermEval 2014 dataset which are ignored in the context of this model.)

## Bias, Risks and Limitations

Please note that this is released strictly as a task-bound model for the purpose of annotating historical and future documents from the collections it was trained on, as well as the official gazette of the Canton of Zurich. No claims of generalization are made outside of the specific use case it was developed for. The training data was annotated according to a specific but informal annotation scheme and the bias of the original model has been retained where it was found not to interfere with the use case. Be mindful of idiosyncrasies when applying to other documents.

### Recommendations

The original XML documents of the training set can be found here: TODO. The annotations may be freely modified to tailor the model to an alternative use case. Note that the modified TEI Publisher version in TODO and the notebook at TODO are required to generate a Huggingface Dataset.

## Training Details

### Training Hyperparameters
- learning_rate: Decay from 1e-05 to 5e-07 
- train_batch_size: 4
- seed: 42
- optimizer: AdamW with betas=(0.9,0.999), epsilon=1e-08, weight_decay=0.01
- lr_scheduler_type: Polynomial (cubic)
- lr_scheduler_warmup_ratio: 0.05
- num_epochs: 10
- gradient_accumulation_steps: 2
- steps: 16000

## Training data sources

The training data was sampled from the following collections from the [data catalog of the Canton of Zurich](https://www.zh.ch/de/politik-staat/statistik-daten/datenkatalog.html#/), curated by the [Staatsarchiv des Kantons Zürich (state archives of the Canton of Zurich)](https://www.zh.ch/de/direktion-der-justiz-und-des-innern/staatsarchiv.html):

* **Meeting notes of the cantonal council**: [Zürcher Kantonsratsprotokolle des 19. und 20. Jahrhunderts](https://www.zh.ch/de/politik-staat/statistik-daten/datenkatalog.html#/datasets/732@staatsarchiv-kanton-zuerich)
* **Resolutions of the governing council**: [Zürcher Regierungsratsbeschlüsse des 19. und 20. Jahrhunderts](https://www.zh.ch/de/politik-staat/statistik-daten/datenkatalog.html#/datasets/466@staatsarchiv-kanton-zuerich)
* **Corpus juris**: [Erlasse der Zürcher Gesetzessammlung ab 1803](https://www.zh.ch/de/politik-staat/statistik-daten/datenkatalog.html#/datasets/712@staatsarchiv-kanton-zuerich)

## Bibliography

This work builds upon:
```
@software{Aarsen_SpanMarker,
    author = {Aarsen, Tom},
    license = {Apache-2.0},
    title = {{SpanMarker for Named Entity Recognition}},
    url = {https://github.com/tomaarsen/SpanMarkerNER}
}

@article{aarsenspanmarker,
  title={SpanMarker for Named Entity Recognition},
  author={Aarsen, Tom and del Prado Martin, Fermin Moscoso and Suero, Daniel Vila and Oosterhuis, Harrie}
}

@inproceedings{ye-etal-2022-packed,
    title = "Packed Levitated Marker for Entity and Relation Extraction",
    author = "Ye, Deming  and
      Lin, Yankai  and
      Li, Peng  and
      Sun, Maosong",
    editor = "Muresan, Smaranda  and
      Nakov, Preslav  and
      Villavicencio, Aline",
    booktitle = "Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)",
    month = may,
    year = "2022",
    address = "Dublin, Ireland",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2022.acl-long.337",
    doi = "10.18653/v1/2022.acl-long.337",
    pages = "4904--4917"}",
}

@misc{chan2020germans,
  author = {Chan, Branden and Schweter, Stefan and Möller, Timo},
  description = {German's Next Language Model},
  keywords = {bert gbert languagemodel lm},
  title = {German's Next Language Model},
  url = {http://arxiv.org/abs/2010.10906},
  year = 2020
}

@inproceedings{benikova-etal-2014-nosta,
    title = {NoSta-D Named Entity Annotation for German: Guidelines and Dataset},
    author = {Benikova, Darina  and
      Biemann, Chris  and
      Reznicek, Marc},
    booktitle = {Proceedings of the Ninth International Conference on Language Resources and Evaluation ({LREC}'14)},
    month = {may},
    year = {2014},
    address = {Reykjavik, Iceland},
    publisher = {European Language Resources Association (ELRA)},
    url = {http://www.lrec-conf.org/proceedings/lrec2014/pdf/276_Paper.pdf},
    pages = {2524--2531},
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->