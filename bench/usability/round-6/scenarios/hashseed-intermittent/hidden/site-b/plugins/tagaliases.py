"""Rename tags according to [plugin:tagaliases] in site.ini."""


def alias_tags(page, site):
    aliases = site["plugin_options"].get("tagaliases", {})
    tags = page["extra"].get("tags")
    if tags:
        page["extra"]["tags"] = sorted({str(aliases.get(tag, tag)) for tag in tags})
