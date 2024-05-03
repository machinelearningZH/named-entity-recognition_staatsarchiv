from itertools import chain
from typing import Collection, Dict, List, Sequence, Union

import spacy
from datasets import ClassLabel, Dataset
from datasets import Sequence as Sequence_DS
from spacy.training import biluo_to_iob, offsets_to_biluo_tags

spacy.require_gpu()

# Adapted from https://github.com/Ben-Epstein/spacy-to-hf (removed HF tokenization, as SpanMarker does not require subtoken-tokenized input)

def dict_to_dataset(hf_data: Dict[str, List[str]], label_to_idx) -> Dataset:
    """Converts a dictionary of huggingface data into a well-formed Dataset

    ex input:
        {
            "tokens": [["sentence", "1"], ["sentence", "Apple"]],
            "ner_tags": [["U-word", "O"], ["U-word", "U-ORG"]]
        }

    This will create a huggingface dataset from the input, and also map the `ner_tags`
    into a ClassLabel object which is required for training.
    """
    labels = sorted(set(chain.from_iterable(hf_data["ner_tags"])))
    # O is typically the first tag. Move it there
    if "O" in labels:
        labels.remove("O")
        labels.insert(0, "O")
    ds = Dataset.from_dict(hf_data)
    # https://github.com/python/mypy/issues/6239
    class_label = Sequence_DS(feature=ClassLabel(num_classes=len(labels), names=labels))
    # First need to string index the ner_tags. Map unknown tags to "O" (0)
    ds = ds.map(
        lambda row: {"ner_tags": [label_to_idx.get(tag, 0) for tag in row["ner_tags"]]}
    )
    # Then we can create the ClassLabel
    ds = ds.cast_column("ner_tags", class_label)
    return ds


def spacy_to_hf(
    spacy_data: List[Dict[str, Sequence[Collection[str]]]],
    label_to_idx: dict,
    exclusion_list: list = None,
) -> Union[Dataset, Dict[str, List[List[str]]]]:
    """Maps spacy formatted spans to HF tokens in BILOU format

    Input should be a list of dictionaries of 'text' and 'spans' keys
    Ex:
        spacy_data = [
            {
                "text": "I have a BSc (Bachelors of Computer Sciences) from NYU",
                "spans": [
                    {"start": 9, "end": 12, "label": "degree"},
                    {"start": 14, "end": 44, "label": "degree"},
                    {"start": 51, "end": 54, "label": "university"}
                ]
            },
            ...
        ]

    Returns a Dictionary with 2 keys: 'tokens', and 'ner_tags'.

    :param spacy_data: The spacy formatted span data. Must be a list containing
        "text" key and "spans" key. "spans" must be a list of dictionaries with
        "start", "end", and "label"
    """
    print("Misaligned entities:")
    exclusion_set = set(exclusion_list) if exclusion_list else set()
    nlp = spacy.load("de_dep_news_trf")
    hf_data: Dict[str, List] = {"tokens": [], "ner_tags": []}
    seen_tag_set = set()

    for row in spacy_data:
        spans = row["entities"]
        text = row["text"]

        # Tokenize text with spaCy and
        doc = nlp(text)
        spacy_tokens = [token.text for token in doc]
        entities = [(span[0], span[1], span[2]) for span in spans]

        # Convert entity-level spans and labels -> token-level BILUO tags -> token-level BIO/IOB tags
        spacy_tags = offsets_to_biluo_tags(doc, entities)
        spacy_tags = biluo_to_iob(spacy_tags)

        # Warn about BIO/IOB tags not defined in label_to_idx
        unseen_tag_set = set(spacy_tags) - seen_tag_set
        if unseen_tag_set:
            for tag in unseen_tag_set:
                if tag not in label_to_idx:
                    print(
                        f"Warning: Tag '{tag}' is not defined in label_to_idx, will be mapped to 'O' ..."
                    )
            seen_tag_set |= unseen_tag_set

        # Remove empty string tokens (spaces, tabs, \xa0), as these are stripped when predicting as well
        spacy_tokens_filtered = []
        spacy_tags_filtered = []

        length = len(spacy_tokens)

        # Process token - tag pairs
        for idx, (token, tag) in enumerate(zip(spacy_tokens, spacy_tags)):
            if token.strip():
                spacy_tokens_filtered.append(token)

                # Map misaligned entities to "O" and
                if tag == "-":
                    print(token, tag)
                    tag = "O"

                # Handle tokens from the exclusion list that are NOT part of a multi-token NE
                elif (
                    not (idx == (length - 1))
                    and (token in exclusion_set)
                    and tag.startswith("B")
                    and (spacy_tags[idx + 1] == "O")
                ):
                    print(token, tag, spacy_tokens[idx + 1], spacy_tags[idx + 1])
                    tag = "O"

                spacy_tags_filtered.append(tag)

        # Collect tokens and tags of current text
        hf_data["tokens"].append(spacy_tokens_filtered)
        hf_data["ner_tags"].append(spacy_tags_filtered)

    return dict_to_dataset(hf_data, label_to_idx)
