import numexpr

# Enable usage of all cores
numexpr.set_num_threads(numexpr.detect_number_of_cores())

import math
import re

import spacy
from . import spacy_integration
from . import util

from spacy.lang.de import German
from spacy.matcher import Matcher
from torch import mps

# https://stackoverflow.com/a/14822210
def convert_size(size_bytes):
    """Convert bytes to a human-readable size."""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


class CachedPipeline:
    def __init__(self, nlp, sm_model, loc_within_org_matcher, date_regex, device):
        self.nlp = nlp
        self.sm_model = sm_model
        self.loc_within_org_matcher = loc_within_org_matcher
        self.date_regex = date_regex
        self.device = device


class Cache:
    """Cache spaCy pipelines across API calls"""
    pipelines = {}
    inference_counter = 0

    def __init__(self, logger, settings):
        self.logger = logger
        self.get_pipeline(settings)

    def __delitem__(self, key):
        del self.pipelines[key]

    def get_pipeline(self, settings):
        if settings.pipeline_name not in self.pipelines:            
            # GPU-specific setup
            if settings.device != 'cpu':
                spacy.require_gpu()
            # Clear cache if using MPS (Apple) GPU
            if settings.device == 'mps':
                total_memory_before_release = mps.driver_allocated_memory()
                mps.empty_cache()
                total_memory_after_release = mps.driver_allocated_memory()
                if settings.debug:
                    self.logger.info(
                        f"Released unoccupied cached GPU memory - before: "
                        f"{convert_size(total_memory_before_release)} | "
                        f"after: {convert_size(total_memory_after_release)}"
                    )
            if settings.sm_model:
                self.logger.info(
                    f"Instantiating spaCy pipeline '{settings.pipeline_name}' using SpanMarker model '{settings.sm_model}' ..."
                )
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
            else:
                self.logger.error("Must specify SpanMarker model.")
                raise RuntimeError

            loc_within_org_matcher = None
            # Matcher for LOCs within ORGs
            try:
                with open(settings.locs_within_orgs_regex_path) as f:
                    loc_within_org_matcher = Matcher(nlp.vocab)
                    pattern = [{"TEXT": {"REGEX": f.read()}}]
                    loc_within_org_matcher.add("Nested_LOC", [pattern])
            except Exception:
                self.logger.error("Could not create LOC within ORG regex matcher")
                raise

            try:
                with open(settings.date_regex_path) as f:
                    # Load as verbose (ignoring newlines used for formatting)
                    date_regex = re.compile(f.read(), flags=re.VERBOSE)
            except Exception:
                self.logger.error("Could not compile date regex!")
                raise

            self.pipelines[settings.pipeline_name] = CachedPipeline(
                nlp,
                settings.sm_model,
                loc_within_org_matcher,
                date_regex,
                settings.device,
            )

            if settings.debug:
                self.logger.info(f"spaCy pipeline: {', '.join(nlp.pipe_names)}")
                self.logger.info(
                    f"GPU memory stats upon initialization - tensors: "
                    f"{convert_size(mps.current_allocated_memory())} | "
                    f"total: {convert_size(mps.driver_allocated_memory())}"
                )
            return self.pipelines[settings.pipeline_name]
        else:
            return self.pipelines[settings.pipeline_name]
