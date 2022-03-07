"""Logging Configuration"""
__docformat__ = "numpy"
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import re
from pathlib import Path
import sys
import time
import uuid
from math import floor, ceil

import git
import boto3
from botocore.exceptions import ClientError

import gamestonk_terminal.config_terminal as cfg
from gamestonk_terminal import feature_flags as gtff

logger = logging.getLogger(__name__)
LOGFORMAT = "%(asctime)s|%(name)s|%(funcName)s|%(lineno)s|%(message)s"
LOGPREFIXFORMAT = "%(levelname)s|%(version)s|%(loggingId)s|%(sessionId)s|"
DATEFORMAT = "%Y-%m-%dT%H:%M:%S%z"
BUCKET = "gst-restrictions"
FOLDER_NAME = "gst-app/logs"


def library_loggers(verbosity: int = 0) -> None:
    """Setup library logging

    Parameters
    ----------
    verbosity : int, optional
        Log level verbosity, by default 0
    """

    logging.getLogger("requests").setLevel(verbosity)
    logging.getLogger("urllib3").setLevel(verbosity)


def get_log_dir() -> Path:
    file_path = Path(__file__)
    logger.debug("Parent dir: %s", file_path.parent.parent.absolute())
    log_dir = file_path.parent.parent.absolute().joinpath("logs")
    logger.debug("Future logdir: %s", log_dir)

    if not os.path.isdir(log_dir.absolute()):
        logger.debug("Logdir does not exist. Creating.")
        os.mkdir(log_dir.absolute())

    log_id = log_dir.absolute().joinpath(".logid")

    if not os.path.isfile(log_id.absolute()):
        logger.debug("Log ID does not exist: %s", log_id.absolute())
        cfg.LOGGING_ID = f"{uuid.uuid4()}"
        with open(log_id.absolute(), "a") as a_file:
            a_file.write(f"{cfg.LOGGING_ID}\n")
    else:
        logger.debug("Log ID exists: %s", log_id.absolute())
        with open(log_id.absolute()) as a_file:
            cfg.LOGGING_ID = a_file.readline().rstrip()

    logger.debug("Log id: %s", cfg.LOGGING_ID)

    uuid_log_dir = log_dir.absolute().joinpath(cfg.LOGGING_ID)

    logger.debug("Current log dir: %s", uuid_log_dir)

    if not os.path.isdir(uuid_log_dir.absolute()):
        logger.debug(
            "UUID log dir does not exist: %s. Creating.", uuid_log_dir.absolute()
        )
        os.mkdir(uuid_log_dir.absolute())
    return uuid_log_dir


def setup_file_logger(session_id: str) -> None:
    """Setup File Logger"""

    uuid_log_dir = get_log_dir()

    upload_archive_logs_s3(directory_str=uuid_log_dir, log_filter=r"\.log")

    start_time = int(time.time())
    cfg.LOGGING_FILE = uuid_log_dir.absolute().joinpath(f"{start_time}.log")  # type: ignore

    logger.debug("Current log file: %s", cfg.LOGGING_FILE)

    handler = TimedRotatingFileHandler(cfg.LOGGING_FILE)
    formatter = CustomFormatterWithExceptions(
        uuid_log_dir.stem, session_id, fmt=LOGFORMAT, datefmt=DATEFORMAT
    )
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)


class CustomFormatterWithExceptions(logging.Formatter):
    """Custom Logging Formatter that includes formatting of Exceptions"""

    def __init__(
        self,
        logging_id: str,
        session_id: str,
        fmt=None,
        datefmt=None,
        style="%",
        validate=True,
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate)
        self.logPrefixDict = {
            "loggingId": logging_id,
            "sessionId": session_id,
            "version": cfg.LOGGING_VERSION,
        }

    def formatException(self, ei) -> str:
        """Exception formatting handler

        Parameters
        ----------
        ei : logging._SysExcInfoType
            Exception to be logged

        Returns
        -------
        str
            Formatted exception
        """
        result = super().formatException(ei)
        return repr(result)

    def format(self, record: logging.LogRecord) -> str:
        """Log formatter

        Parameters
        ----------
        record : logging.LogRecord
            Logging record

        Returns
        -------
        str
            Formatted log message
        """
        if hasattr(record, "func_name_override"):
            record.funcName = record.func_name_override  # type: ignore
            record.lineno = 0
        s = super().format(record)
        if record.levelname:
            self.logPrefixDict["levelname"] = record.levelname[0]
        else:
            self.logPrefixDict["levelname"] = "U"

        if record.exc_text:
            self.logPrefixDict["levelname"] = "X"
            logPrefix = LOGPREFIXFORMAT % self.logPrefixDict
            s = (
                s.replace("\n", " - ")
                .replace("\t", " ")
                .replace("\r", "")
                .replace("'", "`")
                .replace('"', "`")
            )

        else:
            logPrefix = LOGPREFIXFORMAT % self.logPrefixDict
        return f"{logPrefix}{s}"


def get_commit_hash() -> None:
    """Get Commit Short Hash"""

    file_path = Path(__file__)
    git_dir = file_path.parent.parent.absolute().joinpath(".git")

    if os.path.isdir(git_dir.absolute()):
        repo = git.Repo(search_parent_directories=True)
        sha = repo.head.object.hexsha
        short_sha = repo.git.rev_parse(sha, short=8)
        cfg.LOGGING_VERSION = f"sha:{short_sha}"


def setup_logging() -> None:
    """Setup Logging"""

    START_TIME = int(time.time())
    LOGGING_ID = cfg.LOGGING_ID if cfg.LOGGING_ID else ""

    verbosity_terminal = floor(cfg.LOGGING_VERBOSITY / 10) * 10
    verbosity_libraries = ceil(cfg.LOGGING_VERBOSITY / 10) * 10
    logging.basicConfig(
        level=verbosity_terminal, format=LOGFORMAT, datefmt=DATEFORMAT, handlers=[]
    )

    get_commit_hash()

    for a_handler in cfg.LOGGING_HANDLERS.split(","):
        if a_handler == "stdout":
            handler = logging.StreamHandler(sys.stdout)
            formatter = CustomFormatterWithExceptions(
                LOGGING_ID, str(START_TIME), fmt=LOGFORMAT, datefmt=DATEFORMAT
            )
            handler.setFormatter(formatter)
            logging.getLogger().addHandler(handler)
        elif a_handler == "stderr":
            handler = logging.StreamHandler(sys.stderr)
            formatter = CustomFormatterWithExceptions(
                LOGGING_ID, str(START_TIME), fmt=LOGFORMAT, datefmt=DATEFORMAT
            )
            handler.setFormatter(formatter)
            logging.getLogger().addHandler(handler)
        elif a_handler == "noop":
            handler = logging.NullHandler()  # type: ignore
            formatter = CustomFormatterWithExceptions(
                LOGGING_ID, str(START_TIME), fmt=LOGFORMAT, datefmt=DATEFORMAT
            )
            handler.setFormatter(formatter)
            logging.getLogger().addHandler(handler)
        elif a_handler == "file":
            setup_file_logger(str(START_TIME))
        else:
            logger.debug("Unknown loghandler")

    library_loggers(verbosity_libraries)

    logger.info("Logging configuration finished")
    logger.info("Logging set to %s", cfg.LOGGING_HANDLERS)
    logger.info("Verbosity set to %s", verbosity_libraries)
    logger.info(
        "FORMAT: %s%s", LOGPREFIXFORMAT.replace("|", "-"), LOGFORMAT.replace("|", "-")
    )


def upload_file_to_s3(
    file: Path, bucket: str, object_name=None, folder_name=None
) -> None:
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file.name
    # If folder_name was specified, upload in the folder
    if folder_name is not None:
        object_name = f"{folder_name}/{object_name}"

    # Upload the file
    try:
        s3_client = boto3.client(
            service_name="s3",
            aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=cfg.AWS_ACCESS_KEY,
        )
        s3_client.upload_file(str(file), bucket, object_name)
    except ClientError as e:
        logger.exception(str(e))


def upload_archive_logs_s3(
    directory_str=None,
    log_filter=r"\.log\.20[2-3][0-9]-[0-2][0-9]-[0-3][0-9]_[0-2][0-9]*",
) -> None:
    if gtff.ALLOW_LOG_COLLECTION:
        if directory_str is None:
            directory = get_log_dir()
        else:
            directory = Path(directory_str)
        archive = directory / "archive"

        if not archive.exists():
            # Create a new directory because it does not exist
            archive.mkdir()
            logger.debug("The new archive directory is created!")

        log_files = {}

        for file in directory.iterdir():
            regexp = re.compile(log_filter)
            if regexp.search(str(file)):
                log_files[str(file)] = file, (archive / file.name)
        logger.info("Start uploading Logs")
        for log_file, archived_file in log_files.values():
            upload_file_to_s3(file=log_file, bucket=BUCKET, folder_name=FOLDER_NAME)
            try:
                log_file.rename(archived_file)
            except Exception as e:
                logger.exception("Cannot archive file: %s", str(e))
        logger.info("Logs uploaded")
    else:
        logger.info("Logs not allowed to be collected")
