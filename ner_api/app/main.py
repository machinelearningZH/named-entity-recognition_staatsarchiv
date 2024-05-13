import json
import logging
import re
import sys
from typing import List
from typing import Optional
from typing import Tuple

import spacy
from fastapi import Body
from fastapi import FastAPI
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import PlainTextResponse
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from span_marker import SpanMarkerModel
from torch import mps

from .cache import Cache
from .cache import convert_size


class Settings(BaseSettings):
    pipeline_name: str = "span_marker_spacy_sentencizer"
    spacy_pipeline: Optional[str] = None
    sm_model: Optional[str] = None
    device: str = "cpu"
    ne_tags: list = []
    ne_thresholds: Optional[dict] = None
    tag_with_sm: bool = True
    tag_locs_within_orgs: bool = False
    tag_dates: bool = False
    locs_within_orgs_regex_path: Optional[str] = None
    date_regex_path: Optional[str] = None
    tagset_mapping_path: Optional[str] = None
    tagset_mapping: Optional[str] = None
    additional_punctuation: Optional[list] = None
    split_overlong_sentences: bool = False
    teipublisher_address: Optional[str] = None
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env")


class TrainingRequest(BaseModel):
    """Expected request body for training a model"""

    # Not implemented
    pass


class PatternRequest(BaseModel):
    lang: Optional[str] = "de"
    text: str
    patterns: List


class SetTaggingRequest(BaseModel):
    tag_with_sm: Optional[bool] = None
    tag_dates: Optional[bool] = None
    tag_locs_within_orgs: Optional[bool] = None


class Entity(BaseModel):
    """A single entity"""

    text: str
    type: str
    start: int


logger = logging.getLogger('uvicorn.error')
logger.setLevel(logging.DEBUG)

settings = Settings()

if settings.debug:
    logger.info(f"Settings: {repr(settings.__dict__)}")

app = FastAPI(
    title="StAZH NER API",
    description="This API exposes endpoints for named entity recognition powered by "
    "Python, spaCy and SpanMarker. It can be accessed directly or via TEI Publisher."
)
app.add_middleware(CORSMiddleware, allow_origins=["*"])

cache = Cache(logger, settings)


def load_tag_set_mapping():
    # Mapping of NER pipeline labels to TEI Publisher labels
    try:
        with open(settings.tagset_mapping_path) as f:
            settings.tagset_mapping = json.load(f)
    except FileNotFoundError:
        print("Cannot find tagset mapping, exiting ...")
        sys.exit(1)

load_tag_set_mapping()


def get_label_mapping(nerLabels):
    """
    Returns a dictionary containing all pipeline entity labels which should be mapped to
    TEI Publisher annotation labels.
    """
    labels = {}
    for key in settings.tagset_mapping:
        for nerLabel in nerLabels:
            if nerLabel in settings.tagset_mapping[key]:
                labels[nerLabel] = key
    return labels


# Provide a redirection route to TEI Publisher's annotate collection for URL shorting
@app.get("/d/{rest_of_path:path}")
async def url_redirect(rest_of_path: str):
    # Redirect to /docs (relative URL)
    return RedirectResponse(
        url=f"{settings.teipublisher_address}/exist/apps/tei-publisher/annotate/{rest_of_path}",
        status_code=302,
    )


@app.head("/health")
@app.get("/health")
def health():
    """
    Returns health status.
    """
    return JSONResponse({"status": "ok"})


@app.post("/entities/{model:path}")
def ner(
    model: str, response: Response, text: str = Body(..., media_type="text/text")
) -> List[Entity]:
    """
    Run entity recognition on the text using the given model.
    """
    pipeline = cache.get_pipeline(settings)
    nlp = pipeline.nlp
    if nlp is None:
        response.status_code = 500
        return

    normText, normOffsets, leading_spaces_offset = normalize_offsets(text)
    entities = []

    # Disable SpanMarker if neither SM NEs nor LOCs within ORGs are annotated
    if settings.tag_with_sm or settings.tag_locs_within_orgs:
        try:
            doc = nlp(normText)
        except Exception as e:
            logger.error(f"spaCy processing raised exception: {e}")
            response.status_code = 500
            return []

        cache.inference_counter += 1

        if settings.debug:
            logger.info(
                f"GPU memory stats after inference #{cache.inference_counter} \
                            - tensors: {convert_size(mps.current_allocated_memory())} | \
                                total: {convert_size(mps.driver_allocated_memory())}"
            )

        labels = get_label_mapping(settings.ne_tags)
        logger.info(f"Extracting entities using model {pipeline.sm_model}")
        for ent in doc.ents:
            if ent.label_ in labels:
                # Tag with SpanMarker
                if settings.tag_with_sm:
                    adjOffset = adjust_offset(
                        normOffsets, ent.start_char, ent.end_char, leading_spaces_offset
                    )
                    adjText = text[adjOffset[0] : adjOffset[1]]
                    entities.append(
                        Entity(text=adjText, type=labels[ent.label_], start=adjOffset[0])
                    )

                # Tagging LOCs nested in ORGs
                if settings.tag_locs_within_orgs and ent.label_ == "ORG":
                    for subent_match in pipeline.loc_within_org_matcher(ent):
                        subent = ent[subent_match[1] : subent_match[2]]
                        adjOffset = adjust_offset(
                            normOffsets,
                            subent.start_char,
                            subent.end_char,
                            leading_spaces_offset,
                        )
                        adjText = text[adjOffset[0] : adjOffset[1]]
                        entities.append(
                            Entity(text=adjText, type="place", start=adjOffset[0])
                        )

    if settings.tag_dates:
        # match dates with date regex
        for match in pipeline.date_regex.finditer(normText):
            span = match.span()
            adjOffset = adjust_offset(
                normOffsets, span[0], span[1], leading_spaces_offset
            )
            adjText = text[adjOffset[0] : adjOffset[1]]
            entities.append(Entity(text=adjText, type="date", start=adjOffset[0]))

    return entities


@app.post("/patterns/")
def entity_ruler(data: PatternRequest) -> List[Entity]:
    """Use rule-based matching to expand entities."""
    nlp = spacy.blank(data.lang)
    ruler = nlp.add_pipe("entity_ruler", config={"validate": True})
    ruler.add_patterns(data.patterns)

    (normText, normOffsets) = normalize_offsets(data.text)

    doc = nlp(normText)

    labels = get_label_mapping(settings.ne_tags)
    entities = []
    for ent in doc.ents:
        if ent.label_ in labels:
            adjOffset = adjust_offset(normOffsets, ent.start_char, ent.end_char)
            adjText = data.text[adjOffset[0] : adjOffset[1]]
            entities.append(
                Entity(text=adjText, type=labels[ent.label_], start=adjOffset[0])
            )
    return entities


def normalize_offsets(text: str) -> List:
    """
    Normalize the text by replacing sequences of 2 or more whitespace characters
    as well as non-space whitespace characters with a single space. Remove leading and
    trailing spaces to avoid sentence segmentation artifacts.

    Returns a tuple with 1) the normalized text and 2) a list of pairs, each
    containing a) the offset into the normalized text, b) the number of whitespace
    characters replaced up to the current offset.
    """
    offsets = []
    offset = 0

    # Substitute non-breaking spaces with normal ones
    text = re.sub(r'\xa0', ' ', text)
    # Replace non-space whitespace characters with spaces and remove trailing whitespace
    text = re.sub(r'\s', ' ', text)
    text = text.rstrip()

    leading_spaces = re.match(r"^\s+", text, flags=re.UNICODE)
    leading_spaces_offset = leading_spaces.span()[1] if leading_spaces else 0
    offset += leading_spaces_offset

    # SpanMarker can't handle empty sentences only consisting of whitespace;
    # also stripping leading whitespace
    text = text.strip()

    for match in re.finditer(r"\s{2,}", text, flags=re.UNICODE):
        span = match.span()
        start = span[0] - offset
        offset += span[1] - span[0] - 1
        offsets.append((start, offset))

    return (
        re.sub(r"\s{2,}", " ", text, flags=re.UNICODE),
        offsets,
        leading_spaces_offset
    )


def adjust_offset(
    offsets: List, start: int, end: int, leading_spaces_offset: int
) -> Tuple:
    """
    Recompute offsets into the normalized text to be relative to the original text.
    """
    i = 0
    # computed adjusted start
    while i < len(offsets) and offsets[i][0] < start:
        i += 1
    adjStart = start + leading_spaces_offset if i == 0 else offsets[i - 1][1] + start

    # computed adjusted end: entities may span across whitespace
    while i < len(offsets) and offsets[i][0] < end:
        i += 1
    adjEnd = end + leading_spaces_offset if i == 0 else offsets[i - 1][1] + end
    return (adjStart, adjEnd)


@app.get("/status")
def status():
    """Return status information about the spaCy installation."""
    return spacy.info()


# Route /model is retained for TEI Publisher compatibility, even though "model" refers to the entire spaCy pipeline
@app.get("/model")
def get_spacy_pipeline() -> List[str]:
    """Get name of spaCy pipeline as used in TEI Publisher."""
    return [settings.pipeline_name]


@app.get("/model/{model:path}")
def get_metadata(model: str, response: Response):
    """Retrieve metadata about the selected model."""
    nlp = cache.get_pipeline(settings).nlp
    if nlp is None:
        response.status_code = 500
        return
    return nlp.meta


@app.post("/train/")
def training(data: TrainingRequest, response: Response):
    """Not implemented."""
    # Not implemented
    response.status_code = 404
    return


@app.get("/train/{pid}", response_class=PlainTextResponse)
def poll_training_log(pid: int, response: Response):
    """Not implemented."""
    # Not implemented
    response.status_code = 404
    return


@app.get("/get_tagging")
def get_tagging():
    """Get tagging settings."""
    return JSONResponse(
        {
            "tag_with_sm": settings.tag_with_sm,
            "tag_dates": settings.tag_dates,
            "tag_locs_within_orgs": settings.tag_locs_within_orgs,
        }
    )


@app.post("/reset_api")
def reset_api(response: Response):
    """Reset tagging settings and SpanMarker model to parameters of .env"""
    global settings
    settings = Settings()
    load_tag_set_mapping()
    logger.info(f"Resetting tagging settings and using model {settings.sm_model} as per .env ...")


@app.post("/set_tagging")
def set_tagging(data: SetTaggingRequest, response: Response):
    """Enabling or disabling tagging."""
    if data.tag_with_sm is not None:
        logger.info(f"Setting SpanMarker tagging to {data.tag_with_sm}")
        settings.tag_with_sm = data.tag_with_sm
    if data.tag_dates is not None:
        logger.info(f"Setting date tagging to {data.tag_dates}")
        settings.tag_dates = data.tag_dates
    if data.tag_locs_within_orgs is not None:
        logger.info(f"Setting LOC within ORG tagging to {data.tag_locs_within_orgs}")
        settings.tag_locs_within_orgs = data.tag_locs_within_orgs


@app.post("/set_sm_model/{model:path}")
def set_sm_model(model: str, response: Response):
    """Switch SpanMarker model on the fly."""
    try:
        SpanMarkerModel.from_pretrained(model)
    except OSError as e:
        return Response(f"Error: {str(e)}", status_code=400)
    if model != settings.sm_model:
        logger.info(f'Setting SpanMarker model to "{model}"')
        settings.sm_model = model
        # Deleting cached model to trigger recreation
        del cache[settings.pipeline_name]
        cache.get_pipeline(settings)



@app.get("/get_sm_model")
def get_metadata():
    """Get currently loaded (or to be loaded) SpanMarker model."""
    return settings.sm_model
