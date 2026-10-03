"""Access to the card-events queue.

In production the job talks to the queue gateway (a thin HTTP front of the
message queue): ``POST <queue>/receive`` returns up to ``max`` messages, and
``POST <queue>/delete`` acknowledges them by receipt handle. The queue is a
standard queue: delivery is at least once, and messages are not ordered.

For tests and incident replays the job can read a queue dump instead (the
DLQ tooling's ``queue-dump --keep`` writes one): JSON Lines, optionally
gzip-compressed, one received message per line, in the order received, with
the gateway's fields (``MessageId``, ``ReceiptHandle``, ``Attributes``,
``Body``). Pass it with ``--spool`` or ``CARDLEDGER_SPOOL``.
"""

import gzip
import json
import logging
import urllib.request

log = logging.getLogger(__name__)


class QueueError(RuntimeError):
    pass


class GatewayQueue:
    """The production queue, through the queue gateway."""

    def __init__(self, url, timeout=20):
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.name = self.url.rsplit("/", 1)[-1]

    def _post(self, action, payload):
        request = urllib.request.Request(
            f"{self.url}/{action}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode() or "{}")
        except OSError as exc:
            raise QueueError(f"{self.url}/{action}: {exc}") from exc

    def receive(self, max_messages):
        reply = self._post("receive", {"max": max_messages, "wait_seconds": 5})
        return reply.get("Messages", [])

    def delete(self, handles):
        if handles:
            self._post("delete", {"ReceiptHandles": list(handles)})

    def close(self):
        pass


class SpoolQueue:
    """A queue dump read back in the order it was received."""

    def __init__(self, path, name):
        self.path = str(path)
        self.name = name
        opener = gzip.open if self.path.endswith(".gz") else open
        self._handle = opener(self.path, "rt", encoding="utf-8")
        self.deleted = 0

    def receive(self, max_messages):
        batch = []
        for line in self._handle:
            line = line.strip()
            if line:
                batch.append(json.loads(line))
                if len(batch) == max_messages:
                    break
        return batch

    def delete(self, handles):
        self.deleted += len(handles)

    def close(self):
        self._handle.close()


def open_queue(url, spool=None):
    if spool:
        name = url.rstrip("/").rsplit("/", 1)[-1]
        log.info("reading queue %s from dump %s", name, spool)
        return SpoolQueue(spool, name)
    return GatewayQueue(url)


def drain(queue, batch_size, stats):
    """Yield received batches until the queue is empty.

    The caller processes a batch before asking for the next one; the batch is
    then acknowledged, so a crash leaves unprocessed messages on the queue.
    """
    while True:
        batch = queue.receive(batch_size)
        if not batch:
            return
        stats["batches"] += 1
        stats["received"] += len(batch)
        yield batch
        queue.delete([message["ReceiptHandle"] for message in batch])
