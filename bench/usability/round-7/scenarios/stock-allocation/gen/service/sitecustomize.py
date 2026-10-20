"""Stand-in for the production inventory service, for record.sh and validate.sh.

Put this directory on PYTHONPATH and set INVENTORY_SNAPSHOT to a levels dump:
every HTTPS request to inventory.prod.internal is answered from the dump, with
the service's paging (``?warehouse=..&page=..&page_size=..`` ->
``{"levels": [...], "next_page": n or null}``). Nothing in this directory is
recorded: pmdb-record only records the job's own files.
"""

import io
import json
import os
import urllib.parse
import urllib.request
from email.message import Message

_SNAPSHOT = os.environ.get("INVENTORY_SNAPSHOT")


class _InventoryHandler(urllib.request.HTTPSHandler):
    _levels = None

    def https_open(self, req):
        url = urllib.parse.urlsplit(req.full_url)
        if url.hostname != "inventory.prod.internal":
            return super().https_open(req)
        if _InventoryHandler._levels is None:
            with open(_SNAPSHOT, encoding="utf-8") as handle:
                _InventoryHandler._levels = json.load(handle)["levels"]
        query = urllib.parse.parse_qs(url.query)
        warehouse = query["warehouse"][0]
        page = int(query.get("page", ["1"])[0])
        size = int(query.get("page_size", ["500"])[0])
        rows = [r for r in _InventoryHandler._levels if r["warehouse"] == warehouse]
        chunk = rows[(page - 1) * size: page * size]
        body = {"warehouse": warehouse, "page": page, "levels": chunk,
                "next_page": page + 1 if page * size < len(rows) else None}
        data = json.dumps(body).encode()
        headers = Message()
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(data))
        response = urllib.response.addinfourl(io.BytesIO(data), headers, req.full_url, 200)
        response.msg = "OK"
        return response


if _SNAPSHOT:
    import urllib.response  # noqa: E402

    urllib.request.install_opener(urllib.request.build_opener(_InventoryHandler()))
