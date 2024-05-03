import os
import sys
from argparse import Namespace
from typing import Dict, List, Optional, Tuple, Union

import requests
from containers import File
from dotenv import load_dotenv
from logger import logger
from requests.sessions import Session

load_dotenv()

REQUEST_TIMEOUT = int(os.environ["REQUEST_TIMEOUT"])
XML_PROLOG = '<?xml version="1.0" encoding="UTF-8"?>'


def get_tp_servers_availability() -> bool:
    """
    Check that *both* TEI Publisher and TEI Publisher NER API are available.
    """
    try:
        requests.head(f'{os.environ["TEIPUBLISHER_ADDRESS"]}', timeout=REQUEST_TIMEOUT)
        requests.head(
            f'{os.environ["TP_NER_API_ADDRESS"]}/health', timeout=REQUEST_TIMEOUT
        )
    except (requests.exceptions.ConnectionError, requests.ReadTimeout):
        return False
    except KeyError:
        logger.error(
            "TEI Publisher and/or TEI Publisher NER API address not set in .env!"
        )
        return False
    return True


def reset_api():
    """
    Reset NER API to settings specified in its .env file.
    """
    try:
        result = requests.post(
            f'{os.environ["TP_NER_API_ADDRESS"]}/reset_api',
            timeout=REQUEST_TIMEOUT,
        )
        if not result.status_code == 200:
            logger.error(f"NER API reports:\n{result.text}\n")
            raise RuntimeError
    except (requests.exceptions.ConnectionError, requests.ReadTimeout) as e:
        logger.error(f"NER API connection error: {e}")
        raise RuntimeError


def set_sm_model(model):
    """
    Set SpanMarker model for TEI Publisher NER API.
    """
    try:
        result = requests.post(
            f'{os.environ["TP_NER_API_ADDRESS"]}/set_sm_model/{model}',
            timeout=REQUEST_TIMEOUT,
        )
        if not result.status_code == 200:
            logger.error(f"NER API reports:\n{result.text}\n")
            raise RuntimeError
    except (requests.exceptions.ConnectionError, requests.ReadTimeout) as e:
        logger.error(f"NER API connection error: {e}")
        raise RuntimeError


def get_sm_model() -> Union[str, None]:
    """
    Get SpanMarker model from TEI Publisher NER API.
    """
    try:
        result = requests.get(
            f'{os.environ["TP_NER_API_ADDRESS"]}/get_sm_model', timeout=REQUEST_TIMEOUT
        )
        return result.json()
    except (requests.exceptions.ConnectionError, requests.ReadTimeout) as e:
        logger.error(f"NER API connection error: {e}")
        return None


def get_pipeline() -> Union[str, None]:
    """
    Get name by which TEI Publisher addresses the spaCy pipeline of the TEI Publisher
    NER API. Internally referred to as 'model' by TEI Publisher.
    """
    try:
        result = requests.get(
            f'{os.environ["TP_NER_API_ADDRESS"]}/model', timeout=REQUEST_TIMEOUT
        )
        return result.json()[0]
    except (requests.exceptions.ConnectionError, requests.ReadTimeout) as e:
        logger.error(f"NER API connection error: {e}")
        return None


def get_ner_params() -> Union[Tuple[bool, bool, bool], Tuple[None, None, None]]:
    """
    Get NER params from TEI Publisher NER API.
    """
    try:
        result = requests.get(
            f'{os.environ["TP_NER_API_ADDRESS"]}/get_tagging', timeout=REQUEST_TIMEOUT
        ).json()
        return (
            result["tag_with_sm"],
            result["tag_locs_within_orgs"],
            result["tag_dates"],
        )
    except (requests.exceptions.ConnectionError, requests.ReadTimeout) as e:
        logger.error(f"NER API connection error: {e}")
        return None, None, None


def set_ner_params(setting: str, value: Union[str, bool, None]) -> None:
    """
    Set NER params for TEI Publisher NER API.
    """
    try:
        result = requests.post(
            f'{os.environ["TP_NER_API_ADDRESS"]}/set_tagging',
            json={setting: value},
            timeout=REQUEST_TIMEOUT,
        )
        if not result.status_code == 200:
            logger.error(f"NER API reports:\n{result.text}\n")
            raise RuntimeError
    except (requests.exceptions.ConnectionError, requests.ReadTimeout) as e:
        logger.error(f"NER API connection error: {e}")
        raise RuntimeError


def tei_publisher_login(session: Session, user: str, password: str) -> None:
    """
    Log into TEI Publisher to access eXist DB.
    """
    try:
        login_return = session.post(
            f'{os.environ["TEIPUBLISHER_ADDRESS"]}/exist/apps/tei-publisher/api/login',
            data={"user": user, "password": password},
        ).json()
        logger.info(
            f'Logged into TEI Publisher as user "{login_return["user"]}", '
            f'member of groups: {", ".join(login_return["groups"])}'
        )
        print()
    except KeyError:
        logger.error(
            f'Failed to log into TEI Publisher as user "{user}" with password "{password}", please check credentials. Exiting ...'
        )
        sys.exit(1)
    except (requests.exceptions.ConnectionError, requests.ReadTimeout) as e:
        logger.error(f"NER API connection error: {e}")
        raise RuntimeError


def delete_existing_documents(session: Session) -> None:
    """
    Clear existing documents from collection /data/annotate.
    """
    params = {"id": "annotate", "nav": "children", "per-page": 10000000}
    headers = {"Content-type": "application/json"}

    try:
        r = session.get(
            f'{os.environ["TEIPUBLISHER_ADDRESS"]}/exist/apps/tei-publisher/api/dts/collection',
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        dataset = [t["@id"] for t in r.json()["member"]]

        for doc in dataset:
            r = session.delete(
                f'{os.environ["TEIPUBLISHER_ADDRESS"]}/exist/apps/tei-publisher/api/document/{doc}',
                timeout=REQUEST_TIMEOUT,
            )
            if r.status_code == 405:
                raise RuntimeError(f"Could not delete document {doc}")
            r = session.get(
                f'{os.environ["TEIPUBLISHER_ADDRESS"]}/exist/apps/tei-publisher/api/dts/collection',
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
    except Exception as e:
        e.args = (f"Deleting existing documents: {e.args[0]}",) + e.args[1:]
        raise

    if len(r.json()["member"]):
        raise RuntimeError("Collection not empty after deleting all documents.")


def upload_documents(session: Session, files: List[File]) -> None:
    """
    Upload passed files to collection /data/annotate.
    """
    file_tuples = []
    for file in files:
        with open(file.p_in / file.file, "r") as f:
            file.xml = f.read()
            file_tuples.append(("files[]", (file.file, file.xml, "text/xml")))
    try:
        r = session.post(
            f'{os.environ["TEIPUBLISHER_ADDRESS"]}/exist/apps/tei-publisher/api/upload/annotate',
            files=file_tuples,
            timeout=REQUEST_TIMEOUT,
        )
    except Exception as e:
        e.args = (f"Uploading documents: {e.args[0]}",) + e.args[1:]
        raise

    if r.status_code != 200:
        raise RuntimeError("Could not upload documents")


def verify_upload(session: Session, files: List[File]) -> bool:
    """
    Verify that all files have been uploaded to collection /data/annotate.
    """
    params = {"id": "annotate", "nav": "children", "per-page": 10000000}
    headers = {"Content-type": "application/json"}

    try:
        r = session.get(
            f'{os.environ["TEIPUBLISHER_ADDRESS"]}/exist/apps/tei-publisher/api/dts/collection',
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
    except Exception as e:
        e.args = (f"Verifying upload: {e.args[0]}",) + e.args[1:]
        raise

    collection_set = set([t["@id"] for t in r.json()["member"]])
    files_set = set([file.id for file in files])

    return collection_set == files_set


def annotate(session: Session, file: File, pipeline: str) -> None:
    """
    Trigger NER through TEI Publisher, obtain entity span annotations and merge annotations with documents.
    Note: spaCy pipeline is referred to as "model" by TEI Publisher.
    """
    params = {"model": pipeline}
    headers = {"Content-type": "application/json"}

    try:
        r = session.get(
            f'{os.environ["TEIPUBLISHER_ADDRESS"]}/exist/apps/tei-publisher/api/nlp/entities/{file.id}',
            params=params,
            headers=headers,
            timeout=1800,
        )
    except Exception as e:
        e.args = (f"Extracting entity annotations: {e.args[0]}",) + e.args[1:]
        raise

    annotations = r.json()
    try:
        put_result = session.put(
            f'{os.environ["TEIPUBLISHER_ADDRESS"]}/exist/apps/tei-publisher/api/annotations/merge/{file.id}',
            json=annotations,
            timeout=REQUEST_TIMEOUT,
        )
    except Exception as e:
        e.args = (f"Merging annotations: {e.args[0]}",) + e.args[1:]
        raise

    if put_result.status_code != 200:
        raise RuntimeError(put_result.status_code, put_result.reason, put_result.text)


def get_xml(session: Session, file: File) -> None:
    """
    Write document XML string to file object and return URL in TEI Publisher for manual viewing.
    """
    params = {"type": "application/xml"}
    api_url = f'{os.environ["TEIPUBLISHER_ADDRESS"]}/exist/apps/tei-publisher/api/document/{file.id}'
    # NER API handles URL redirectin to obtain a shorter URL
    tp_url = f'{os.environ["TP_NER_API_ADDRESS"]}/d/{file.file}'
    try:
        document_xml = session.get(
            api_url, params=params, timeout=REQUEST_TIMEOUT
        ).content.decode("utf-8")
    except Exception as e:
        e.args = (f"Downloading document: {e.args[0]}",) + e.args[1:]
        raise

    # Add XML prolog if missing
    if not document_xml.startswith(XML_PROLOG):
        document_xml = XML_PROLOG + document_xml

    file.xml_annotated = document_xml
    file.tp_url = tp_url


def process_ner_params(
    args: Namespace, args_dict: Dict[str, Optional[Union[str, bool]]]
) -> Tuple:
    """
    Process SM model and NER parameters (if provided, set for NER API and retrieve
    params from NER API for validation.
    """
    has_ner_params = False

    if args.reset_api:
        reset_api()
    else:
        try:
            if args.sm_model is not None:
                set_sm_model(args.sm_model)
                has_ner_params = True
            for ner_param in ["tag_with_sm", "tag_locs_within_orgs", "tag_dates"]:
                if args_dict[ner_param] is not None:
                    has_ner_params = True
                    set_ner_params(ner_param, args_dict[ner_param])
        except RuntimeError:
            logger.error("Could not set model or NER params, quitting ...")
            sys.exit(1)

    sm_model = get_sm_model()
    tag_with_sm, tag_locs_within_orgs, tag_dates = get_ner_params()
    return has_ner_params, sm_model, tag_with_sm, tag_locs_within_orgs, tag_dates
