from typing import Any, Callable, Dict, List, Optional, Tuple
from span_marker.label_normalizer import AutoLabelNormalizer, LabelNormalizer
from span_marker.tokenizer import SpanMarkerTokenizer
from torch.utils.data import DataLoader
from datasets import Dataset

from span_marker import Trainer

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

REQUIRED_COLUMNS: Tuple[str] = ("tokens", "ner_tags")
OPTIONAL_COLUMNS: Tuple[str] = ("document_id", "sentence_id")


# Adapted from https://github.com/tomaarsen/SpanMarkerNER/blob/main/span_marker/trainer.py
def preprocess_dataset(
    model,
    dataset: Dataset,
    label_normalizer: LabelNormalizer,
    tokenizer: SpanMarkerTokenizer,
    dataset_name: str = "train",
    is_evaluate: bool = False,
) -> Dataset:
    """Normalize the ``ner_tags`` labels and call tokenizer on ``tokens``.

    Args:
        dataset (~datasets.Dataset): A Hugging Face dataset with ``tokens`` and ``ner_tags`` columns.
        label_normalizer (LabelNormalizer): A callable that normalizes ``ner_tags`` into start-end-label tuples.
        tokenizer (SpanMarkerTokenizer): The tokenizer responsible for tokenizing ``tokens`` into input IDs,
            and adding start and end markers.
        dataset_name (str, optional): The name of the dataset. Defaults to "train".
        is_evaluate (bool, optional): Whether to return the number of words for each sample.
            Required for evaluation. Defaults to False.

    Raises:
        ValueError: If the ``dataset`` does not contain ``tokens`` and ``ner_tags`` columns.

    Returns:
        Dataset: The normalized and tokenized version of the input dataset.
    """
    for column in REQUIRED_COLUMNS:
        if column not in dataset.column_names:
            raise ValueError(f"The {dataset_name} dataset must contain a {column!r} column.")

    # Drop all unused columns, only keep "tokens", "ner_tags", "document_id", "sentence_id"
    dataset = dataset.remove_columns(
        set(dataset.column_names) - set(OPTIONAL_COLUMNS) - set(REQUIRED_COLUMNS)
    )
    # Normalize the labels to a common format (list of label-start-end tuples)
    # Also add "entity_count" and "word_count" labels
    dataset = dataset.map(
        label_normalizer,
        input_columns=("tokens", "ner_tags"),
        desc=f"Label normalizing the {dataset_name} dataset",
        batched=True,
    )

    # Remove dataset columns that are only used for model card
    dataset = dataset.remove_columns(("entity_count", "word_count"))

    # Tokenize and add start/end markers
    with tokenizer.entity_tracker(split=dataset_name):
        dataset = dataset.map(
            tokenizer,
            batched=True,
            remove_columns=set(dataset.column_names) - set(OPTIONAL_COLUMNS),
            desc=f"Tokenizing the {dataset_name} dataset",
            fn_kwargs={"return_num_words": is_evaluate},
        )

    # Spread between multiple samples where needed
    original_length = len(dataset)
    dataset = dataset.map(
        Trainer.spread_sample,
        batched=True,
        desc="Spreading data between multiple samples",
        fn_kwargs={
            "model_max_length": tokenizer.model_max_length,
            "marker_max_length": model.config.marker_max_length,
        },
    )
    new_length = len(dataset)
    logger.info(
        f"Spread {original_length} sentences across {new_length} samples, "
        f"a {(new_length / original_length) - 1:%} increase. You can increase "
        "`model_max_length` or `marker_max_length` to decrease the number of samples, "
        "but recognize that longer samples are slower."
    )
    return dataset


class NoTrainPreprocTrainer(Trainer):
    def get_train_dataloader(self) -> DataLoader:
        return super(Trainer, self).get_train_dataloader()