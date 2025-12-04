from __future__ import annotations

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT: float = 5.0
"""Default timeout in seconds."""


def mount_timeout_and_retries(
    client: Session,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = 8,
    retry_for_post=False,
) -> Session:
    retries = Retry(
        # retries up to 8 times
        total=max_retries,
        # which results in successive sleeps of 0.5, 1, 2, 4, 8, 16, 32, 64 seconds for total == 8
        backoff_factor=1,
        # do not retry on '500 Internal Server Error' (because it's longer-term error that we should investigate or file a bug at the API)
        status_forcelist=[429, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
        + (["POST"] if retry_for_post else []),
    )
    client.mount("http://", TimeoutHTTPAdapter(timeout=timeout, max_retries=retries))
    client.mount("https://", TimeoutHTTPAdapter(timeout=timeout, max_retries=retries))
    return client


class TimeoutHTTPAdapter(HTTPAdapter):
    """Mounted to a client, sets a default timeout to all requests if not set on request basis.

    Adapted from https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/#combining-timeouts-and-retries.
    """

    def __init__(self, *args, timeout: float = DEFAULT_TIMEOUT, **kwargs):
        self.timeout = timeout
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)
