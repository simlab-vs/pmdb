"""Use a leading "TL;DR:" paragraph as the page summary."""


def take_lead(page, site):
    for block in page["blocks"]:
        if block["kind"] == "paragraph" and block["text"].startswith("TL;DR:"):
            page["meta"]["summary"] = block["text"][len("TL;DR:"):].strip()
            return
