import os
from typing import Optional
from typing import Union

import torch
from spacy.tokens import Doc
from span_marker.spacy_integration import SpacySpanMarkerWrapper


# Adapted from https://github.com/tomaarsen/SpanMarkerNER/blob/main/span_marker/spacy_integration.py
class SpacySpanMarkerWrapperTunable(SpacySpanMarkerWrapper):
    """This wrapper allows SpanMarker to be used as a drop-in replacement of the "ner" pipeline component.

    Usage:

    .. code-block:: diff

         import spacy

         nlp = spacy.load("en_core_web_sm")
       + nlp.add_pipe("span_marker", config={"model": "tomaarsen/span-marker-roberta-large-ontonotes5"})

         text = '''Cleopatra VII, also known as Cleopatra the Great, was the last active ruler of the
         Ptolemaic Kingdom of Egypt. She was born in 69 BCE and ruled Egypt from 51 BCE until her
         death in 30 BCE.'''
         doc = nlp(text)

    Example::

        >>> import spacy
        >>> import span_marker
        >>> nlp = spacy.load("en_core_web_sm", exclude=["ner"])
        >>> nlp.add_pipe("span_marker", config={"model": "tomaarsen/span-marker-roberta-large-ontonotes5"})
        >>> text = '''Cleopatra VII, also known as Cleopatra the Great, was the last active ruler of the
        ... Ptolemaic Kingdom of Egypt. She was born in 69 BCE and ruled Egypt from 51 BCE until her
        ... death in 30 BCE.'''
        >>> doc = nlp(text)
        >>> doc.ents
        (Cleopatra VII, Cleopatra the Great, 69 BCE, Egypt, 51 BCE, 30 BCE)
        >>> for span in doc.ents:
        ...     print((span, span.label_))
        (Cleopatra VII, 'PERSON')
        (Cleopatra the Great, 'PERSON')
        (69 BCE, 'DATE')
        (Egypt, 'GPE')
        (51 BCE, 'DATE')
        (30 BCE, 'DATE')
    """

    def __init__(
        self,
        pretrained_model_name_or_path: Union[str, os.PathLike],
        *args,
        batch_size: int = 4,
        device: Optional[Union[str, torch.device]] = None,
        overwrite_entities: bool = False,
        ne_thresholds: dict = None,
        **kwargs,
    ) -> None:
        """Initialize a SpanMarker wrapper for spaCy.

        Args:
            pretrained_model_name_or_path (Union[str, os.PathLike]): The path to a locally pretrained SpanMarker model
                or a model name from the Hugging Face hub, e.g. `tomaarsen/span-marker-roberta-large-ontonotes5`
            batch_size (int): The number of samples to include per batch. Higher is faster, but requires more memory.
                Defaults to 4.
            device (Optional[Union[str, torch.device]]): The device to place the model on. Defaults to None.
            overwrite_entities (bool): Whether to overwrite the existing entities in the `doc.ents` attribute.
                Defaults to False.
        """
        if ne_thresholds is not None:
            self.ne_thresholds = ne_thresholds
        else:
            self.ne_thresholds = {}
        super().__init__(
            pretrained_model_name_or_path,
            *args,
            batch_size=batch_size,
            device=device,
            overwrite_entities=overwrite_entities,
        )

    def __call__(self, doc: Doc) -> Doc:
        """Fill `doc.ents` and `span.label_` using the chosen SpanMarker model."""
        sents = list(doc.sents)
        inputs = [
            [token.text if not token.is_space else "" for token in sent]
            for sent in sents
        ]

        # use document-level context in the inference if the model was also trained that way
        if self.model.config.trained_with_document_context:
            inputs = self.convert_inputs_to_dataset(inputs)

        ents = []
        entities_list = self.model.predict(inputs, batch_size=self.batch_size)
        for sentence, entities in zip(sents, entities_list):
            for entity in entities:
                start = entity["word_start_index"]
                end = entity["word_end_index"]
                score = entity["score"]
                label = entity["label"]
                span = sentence[start:end]
                span.label_ = label
                if score > self.ne_thresholds.get(label, 0.0):
                    ents.append(span)

        self.set_ents(doc, ents)

        return doc


# Adapted from https://github.com/tomaarsen/SpanMarkerNER/blob/main/span_marker/__init__.py
# Set up for spaCy
try:
    from spacy.language import Language
except ImportError:
    pass
else:
    DEFAULT_SPACY_CONFIG = {
        "model": "stefan-it/span-marker-gelectra-large-germeval14",
        "batch_size": 4,
        "device": None,
        "overwrite_entities": False,
        "ne_thresholds": None,
    }

    @Language.factory(
        "span_marker_tunable",
        assigns=["doc.ents", "token.ent_iob", "token.ent_type"],
        default_config=DEFAULT_SPACY_CONFIG,
    )
    def _spacy_span_marker_factory(
        nlp: Language,  # pylint: disable=W0613
        name: str,  # pylint: disable=W0613
        model: str,
        batch_size: int,
        device: Optional[Union[str, torch.device]],
        overwrite_entities: bool,
        ne_thresholds: Optional[dict],
    ) -> SpacySpanMarkerWrapperTunable:
        if overwrite_entities:
            # Remove the existing NER component, if it exists,
            # to allow for SpanMarker to act as a drop-in replacement
            try:
                nlp.remove_pipe("ner")
            except ValueError:
                # The `ner` pipeline component was not found
                pass
        return SpacySpanMarkerWrapperTunable(
            model, batch_size=batch_size, device=device, ne_thresholds=ne_thresholds
        )
