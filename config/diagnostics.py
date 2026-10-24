import logging

from django.core.signals import got_request_exception

logger = logging.getLogger("tafita.members_500")


def log_members_exception(sender, request, **kwargs):
    if request.path.rstrip("/") == "/members":
        logger.error(
            "TAFITA_MEMBERS_500 method=%s path=%s",
            request.method,
            request.path,
            exc_info=True,
        )


got_request_exception.connect(
    log_members_exception,
    dispatch_uid="tafita_members_500_diagnostic",
    weak=False,
)
