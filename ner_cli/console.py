import datetime
import os
import re
import time

import tqdm

from logger import logger, file_logger
from typing import Dict
from containers import File

from util import get_xml_title, report_error

TITLE_CLEAN_REGEXP = re.compile(r"\s+")
ANNOTATION_EXCEPTION = "Annotation caused exception"
DIFF_ERROR = "Diff check failed: XML has been modified during annotation."
EXPORT_ERROR = "Export caused exception"

# Source: https://gist.github.com/borgstrom/936ca741e885a1438c374824efb038b3
TIME_DURATION_UNITS = (
    ("week", 60 * 60 * 24 * 7),
    ("day", 60 * 60 * 24),
    ("hour", 60 * 60),
    ("min", 60),
    ("sec", 1),
)

def human_time_duration(seconds: float) -> str:
    """
    Compute human-readable duration up to weeks from seconds.
    """
    if seconds == 0:
        return "inf"
    parts = []
    for unit, div in TIME_DURATION_UNITS:
        amount, seconds = divmod(int(seconds), div)
        if amount > 0:
            parts.append("{} {}{}".format(amount, unit, "" if amount == 1 else "s"))
    return ", ".join(parts)


def print_ner_header() -> None:
    """
    Prints header at the beginning
    """
    print()
    print("\033[1mKtZH/StAZH TEI XML Named Entity Recognition CLI client\033[0m")
    print("\033[1m======================================================\033[0m")
    print(f'{datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S")}\n')


def log_time_projection(
    progress_dict: Dict
) -> None:
    """
    Print estimated duration and projected end date and time based on it.
    """
    total_est_duration = human_time_duration(progress_dict["total_estimated"])
    projected_end_time = (
        datetime.datetime.now()
        + datetime.timedelta(seconds=progress_dict["total_estimated"])
    ).strftime("%a, %d %b %Y %H:%M:%S")
    logger.info(
        f"Total estimated duration: \033[1m{total_est_duration}\033[0m | "
        f"Projected end time: \033[1m{projected_end_time}\033[0m"
    )


def get_row_strs(file: File) -> None:
    """
    Truncate and pad file and title strings to fit table
    """
    file_str = file.file
    if len(file_str) > 29:
        file_str = file_str[:10] + "..." + file_str[-16:]

    title_str = get_xml_title(file.p_in / file.file)
    title_str = TITLE_CLEAN_REGEXP.sub(" ", title_str)[:37]
    if len(title_str) == 37:
        title_str = title_str.ljust(40, ".")
    file.file_str = file_str
    file.title_str = title_str


def print_table_header() -> None:
    """
    Print table header unless debug mode is enabled
    """
    title_row_str = (
        "\033[1m"
        + "Timestamp               "
        + "| File".ljust(33, " ")
        + "| Title"
        + " " * 36
        + "| # Token  | t est. / act.   | URL"
        + "\033[0m"
    )
    separator_str = (len(title_row_str) + 50) * "-"
    if not bool(int(os.environ["DEBUG"])):
        tqdm.tqdm.write(separator_str)
        tqdm.tqdm.write(title_row_str)
        tqdm.tqdm.write(separator_str)


def pb_logging(message):
    """
    Whilst iterating over files during processing, log everything to both screen and file if debug mode is enabled.
    Otherwise, log to file only.,
    """
    if bool(int(os.environ["DEBUG"])):
        logger.error(message)
    else:
        file_logger.error(message)


def print_table_row(
    progress_dict: Dict,
    file: File,
    start_time_doc: float,
) -> None:
    """
    Print table row for correctly processed files.
    """
    tqdm.tqdm.write(
        f"{datetime.datetime.now().isoformat(timespec='milliseconds')} | "
        f"{file.file_str:<30} | "
        f"{file.title_str:<40} | "
        f'{str(progress_dict["estimates"][file.file]["token_count"]):<8} | '
        f'{progress_dict["estimates"][file.file]["estimated_time"]:<6.2f} / {time.time()-start_time_doc:<6.2f} | '
        f"{file.tp_url}"
    )


def report_annotation_error(collection, file, e):
    """
    Report annotation error and print corresponding table row.
    """
    error_str = f"{ANNOTATION_EXCEPTION}: {e}"
    report_error(collection, file, cause=error_str)
    if not bool(int(os.environ["DEBUG"])):
        tqdm.tqdm.write(
            f"{datetime.datetime.now().isoformat(timespec='milliseconds')} | "
            f"{file.file_str:<30} | "
            f"\x1b[31;1m{error_str}\033[0m"
            )
    pb_logging(f"{error_str} ({file.p_in / file.file})")


def report_diff_error(collection, file, xml_texts_diff):
    """
    Report diff error and print corresponding table row.
    """
    report_error(collection, file, cause=DIFF_ERROR, diff=xml_texts_diff)
    if not bool(int(os.environ["DEBUG"])):
        tqdm.tqdm.write(
            f"{datetime.datetime.now().isoformat(timespec='milliseconds')} | "
            f"{file.file_str:<30} | "
            f"\033[5m\x1b[31;1m{DIFF_ERROR}\033[0m "
            f"          | "
            f"{file.tp_url}"
        )
    pb_logging(f"{DIFF_ERROR} ({file.p_in / file.file})")


def report_export_error(collection, file, e):
    """
    Report export error and print corresponding table row.
    """
    error_str = f"{EXPORT_ERROR}: {e}"
    report_error(collection, file, cause=error_str)
    if not bool(int(os.environ["DEBUG"])):
        tqdm.tqdm.write(
            f"{datetime.datetime.now().isoformat(timespec='milliseconds')} | "
            f"{file.file_str:<30} | " 
            f"\033[5m\x1b[31;1m{error_str}033[0m"
        )
    pb_logging(f"{EXPORT_ERROR} ({file.p_in / file.file})")
