import datetime
import difflib
import json
import os.path
import shutil
import xml.etree.ElementTree as ET

from io import StringIO
from pathlib import Path
from dotenv import load_dotenv

from containers import Collection, File
from typing import Dict, List, Tuple, Union

load_dotenv()


class ContinueException(Exception):
    pass


ERRORS: List[Dict] = []
# Defaults to duration for SpanMarker Gelectra observed on Apple M2 Max (~5 seconds per 1000 tokens)
PER_1000_TOKEN_DURATION: int = int(os.environ.get("PER_1000_TOKEN_DURATION", 5))


def get_xml_text(xml: Union[StringIO, Path]) -> str:
    """
    Extract plaintext from body of XML file
    """
    try:
        tree = ET.parse(xml)
        root = tree.getroot()
    except ET.ParseError as e:
        raise RuntimeError(e)
    body = root.findall(
        "./xmlns:text/xmlns:body", namespaces={"xmlns": "http://www.tei-c.org/ns/1.0"}
    )[0]

    return "".join(body.itertext())


def get_xml_title(xml: Path) -> str:
    """
    Extract title from XML (./teiHeader/fileDesc/titleStmt/title)
    """
    try:
        tree = ET.parse(xml)
        root = tree.getroot()
    except ET.ParseError:
        return "(kein Titel)"
    title = root.findall(
        "./xmlns:teiHeader/xmlns:fileDesc/xmlns:titleStmt/xmlns:title",
        namespaces={"xmlns": "http://www.tei-c.org/ns/1.0"},
    )[0]
    return "".join(title.itertext())


def get_length(file: File) -> int:
    """
    Get (rough) token length of XML body plaintext by whitespace splitting
    """
    text = get_xml_text(file.p_in / file.file)
    tokens = text.split()
    return len(tokens)


def time_estimate(file: File) -> Tuple[float, int]:
    """
    Estimate processing time
    """
    token_count = get_length(file)
    return (token_count / 1000) * PER_1000_TOKEN_DURATION, token_count


def diff_xml_texts(file: File) -> Union[str, bool]:
    """
    Check if XML body plaintext is identical between original and annotated XML.
    """
    xml_text = get_xml_text(StringIO(file.xml))
    xml_annotated_text = get_xml_text(StringIO(file.xml_annotated))
    # Surrounding whitespace gets stripped during processing
    if xml_text != xml_annotated_text:
        return "\n".join(
            list(difflib.context_diff(xml_text.split(), xml_annotated_text.split()))
        )
    return False


def report_error(collection, file, cause, diff=None):
    """
    Report error and copy XML to error paths
    """
    os.makedirs(collection.p_error, exist_ok=True)
    os.makedirs(file.p_error, exist_ok=True)

    error_json = {
        "cause": cause,
        "path": str(file.p_in / file.file),
        "time": datetime.datetime.isoformat(datetime.datetime.now()),
        "input": file.xml,
    }

    if file.xml_annotated:
        error_json["output"] = file.xml_annotated

    if diff:
        # In case of a diff error, move annotated XML from output to error directory.
        error_json["diff"] = diff
        shutil.move(file.p_out / file.file, file.p_error / file.file)
    else:
        # Otherwise, copy original XML from input to error directory.
        try:
            shutil.copy(file.p_in / file.file, file.p_error / file.file)
        except shutil.SameFileError:
            pass

    ERRORS.append(error_json)

    collection.error_count += 1


def log_errors(collection: Collection) -> None:
    """
    Store reported errors as JSON
    """
    if ERRORS:
        output_file = collection.p_log / f"errors-{collection.time_stamp}.json"
        with open(output_file, "w") as f:
            json.dump(ERRORS, f, ensure_ascii=False, indent=4)