import collections
import json
import os.path
import shutil
import sys
import time

from pathlib import Path

from containers import Collection, File
from logger import logger
from util import time_estimate, report_error, ContinueException
from typing import DefaultDict, Dict, List, Tuple


def get_file_dict(path_data_in: Path, recursive: bool) -> DefaultDict[str, List[str]]:
    """
    Generate dictionary of files, by flatly scanning current directory or walking it
    recursively.
    """
    file_dict = collections.defaultdict(list)

    if recursive:
        for subpath, dirs, files in os.walk(path_data_in):
            dirs.sort()
            for file in sorted(files):
                # Skip hidden files
                if file.startswith("."):
                    continue
                if not file.endswith(".xml"):
                    continue
                file_dict[os.path.relpath(subpath, path_data_in)].append(file)
    else:
        for file in os.listdir(path_data_in):
            # Skip hidden files
            if file.startswith("."):
                continue
            if not file.endswith(".xml"):
                continue
            if os.path.isfile(path_data_in / file):
                file_dict[""].append(file)
    return file_dict


def prepare_paths(collection: Collection) -> None:
    """
    Sanity checks, clear and recreate output paths as needed.
    """
    if os.path.isfile(collection.p_in):
        raise ContinueException

    try:
        if os.path.exists(collection.p_worker) and os.path.isdir(collection.p_worker):
            shutil.rmtree(collection.p_worker)
    except Exception:
        # we probably don't have enough permission in ROOT/data/
        logger.error(f"Could not remove folder: {collection.p_worker}")
        raise ContinueException

    if os.path.exists(collection.p_out):
        logger.warning(f"Output path ({collection.p_out}) already exists.")

    try:
        if not os.path.exists(collection.p_out):
            os.makedirs(collection.p_out)
    except Exception:
        # we probably don't have enough permission in ROOT/data/
        logger.error(f"Could not create output folder {collection.p_out}")
        raise ContinueException

    if not os.path.exists(collection.p_worker):
        os.makedirs(collection.p_worker)

    if collection.p_in == collection.p_error:
        logger.warning(
            "I have detected that you specified the error path of the export "
            "directory as input path, please check that this is intended!"
        )


def collate_files(collection: Collection, recursive: bool) -> Tuple[Dict, DefaultDict]:
    """
    Collate files, obtain file dictionary and estimate per-file processing time.
    """
    progress_file_name = collection.p_worker / "progress_file.json"
    Path(progress_file_name).touch()

    time_estimates = {}

    file_dict = get_file_dict(collection.p_in, recursive)
    if not file_dict:
        logger.error(
            "No files found, did you mean to seek the path recursively? (argument --recursive)"
        )
        print("Exiting ...")
        sys.exit(1)

    file_dict_filtered = collections.defaultdict(list)

    if collection.continue_from is not None:
        skip_path = True
    else:
        skip_path = False

    for subpath, files in file_dict.items():
        if skip_path:
            if collection.continue_from in subpath:
                logger.info(f"Skipped ahead to {collection.p_in / subpath} ...")
                skip_path = False
            else:
                continue
        for filename in files:
            # Create any subdirs
            os.makedirs(collection.p_out / subpath, exist_ok=True)
            os.makedirs(collection.p_error / subpath, exist_ok=True)

            file = File(
                filename,
                collection.p_in / subpath,
                None,
                collection.p_error / subpath,
                None,
            )

            collection.file_count += 1

            if " " in file.file:
                logger.warning(
                    f"File name of {file.p_in / file.file} contains a space, this is not allowed! Skipping ..."
                )
                report_error(collection, file, cause="File name contains space")
                continue

            try:
                estimated_time, token_count = time_estimate(file)
                time_estimates[file.file] = {
                    "estimated_time": estimated_time,
                    "token_count": token_count,
                }
                file_dict_filtered[subpath].append(file.file)
            except RuntimeError as e:
                logger.warning(
                    f"{file.p_in / file.file} empty or malformed, skipping: {e}"
                )
                report_error(collection, file, cause="File could not be read.")
                continue

    progress_dict = {
        "estimates": time_estimates,
        "start_time": time.time(),
        "total_estimated": sum(v["estimated_time"] for v in time_estimates.values()),
    }

    try:
        with open(progress_file_name, "w") as f:
            json.dump(progress_dict, f)
    except Exception:
        # we probably don't have enough permission in ROOT/data/
        logger.error("Could not write to progress_file")
        print("Exiting ...")
        sys.exit(1)

    return progress_dict, file_dict_filtered


def get_file_list(
    collection: Collection, file_dict: DefaultDict[str, List[str]], subpath: str
) -> List[File]:
    """
    Generate file paths per file in file dict.
    """
    files = []
    for file in file_dict[subpath]:
        file_path_in = collection.p_in / subpath
        file_path_error = collection.p_error / subpath
        file_path_out = collection.p_out / subpath

        # skip all files that have already been annotated.
        if os.path.isfile(file_path_out):
            continue

        files.append(
            File(
                file,
                file_path_in,
                file_path_out,
                file_path_error,
                id="annotate/" + file,
            )
        )
    return files