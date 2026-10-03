"""Client of the CRM's statement import API.

``POST <endpoint>`` with one statement per request (the CRM's import API
takes no batches). Failed requests are retried with exponential backoff.
For staging, ``spool:<dir>`` writes the requests to ``<dir>`` instead.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.request

from . import clock

log = logging.getLogger(__name__)


class CrmError(RuntimeError):
    pass


class CrmClient:
    def __init__(self, endpoint, timeout_s=10.0, retries=3):
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self.retries = retries
        self.sent = 0
        self.retried = 0

    def _post(self, body, headers):
        if self.endpoint.startswith("spool:"):
            directory = self.endpoint[len("spool:"):]
            os.makedirs(directory, exist_ok=True)
            with open(os.path.join(directory, "requests.jsonl"), "a", encoding="utf-8") as handle:
                handle.write(json.dumps({"headers": headers, "body": json.loads(body)}, sort_keys=True) + "\n")
            return 202
        request = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
            return response.status

    def push(self, statement):
        body = json.dumps(statement, sort_keys=True).encode("utf-8")
        for attempt in range(self.retries + 1):
            headers = {
                "Content-Type": "application/json",
                "X-Request-Time": clock.utc_stamp(),
                "Idempotency-Key": f"{statement['member_id']}:{statement['month']}",
            }
            try:
                status = self._post(body, headers)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                status, error = None, exc
            else:
                error = None
            if status is not None and 200 <= status < 300:
                self.sent += 1
                return
            if attempt < self.retries:
                self.retried += 1
                time.sleep(2 ** attempt)
        raise CrmError(f"statement of {statement['member_id']}: CRM import failed ({error or status})")

    def push_all(self, statements):
        for item in statements:
            self.push(item)
