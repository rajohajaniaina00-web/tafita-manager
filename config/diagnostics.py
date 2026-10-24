import logging
import sys
import traceback
from pathlib import Path

logger = logging.getLogger("tafita.members_500")


def log_members_exception(sender, request, **kwargs):
    if request.path.rstrip("/") != "/members":
        return

    exc_type, exc_value, tb = sys.exc_info()

    if exc_type is None:
        detail = "Exception Python indisponible dans le contexte du signal"
        locations = "indisponibles"
    else:
        message = " ".join(str(exc_value).split())[:500]
        detail = f"{exc_type.__name__}: {message}"

        frames = traceback.extract_tb(tb) if tb else []
        locations = " > ".join(
            f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}"
            for frame in frames[-5:]
        )

    logger.error(
        "TAFITA_MEMBERS_500 method=%s path=%s detail=%s locations=%s",
        request.method,
        request.path,
        detail,
        locations,
    )


from django.core.signals import got_request_exception

got_request_exception.connect(
    log_members_exception,
    dispatch_uid="tafita_members_500_diagnostic",
    weak=False,
)
