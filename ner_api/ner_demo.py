from typing import Optional

import spacy_streamlit
import typer
from pydantic_settings import BaseSettings, SettingsConfigDict
from spacy.lang.de import German

from app.spacy_integration import *
from app.util import *

cli = typer.Typer()


class Settings(BaseSettings):
    sm_model: str = None
    device: str = "cpu"
    ne_tags: list = None
    ne_thresholds: Optional[dict] = None
    additional_punctuation: list = None
    split_overlong_sentences: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


@cli.command()
def run(text: str):
    settings = Settings()

    nlp = German()
    sentencizer = nlp.add_pipe("sentencizer")

    # Add additional punctuation chars treated as sentences boundaries
    sentencizer.punct_chars = sentencizer.punct_chars | set(
        settings.additional_punctuation
    )

    nlp.add_pipe(
        "span_marker_tunable",
        config={
            "model": settings.sm_model,
            "device": settings.device,
            "ne_thresholds": settings.ne_thresholds,
        },
    )

    # Split overlong sentences to accommodate SpanMarker token limit
    if settings.split_overlong_sentences:
        nlp.add_pipe("max_sen_len_splitter", before="span_marker_tunable")

    doc = nlp(text)

    spacy_streamlit.visualize_ner(
        doc,
        labels=settings.ne_tags,
    )


if __name__ == "__main__":
    try:
        cli(standalone_mode=False)
    except SystemExit:
        pass
