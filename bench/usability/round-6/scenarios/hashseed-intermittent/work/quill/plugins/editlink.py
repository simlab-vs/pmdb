"""Add an "Edit this page" link pointing to the site's repository."""


def add_edit_link(page, site):
    options = site["plugin_options"].get("editlink", {})
    repo = options.get("repository")
    if not repo:
        return
    branch = options.get("branch", "main")
    prefix = str(options.get("path", site["content_dir"])).strip("/")
    page["extra"]["edit_url"] = f"{str(repo).rstrip('/')}/edit/{branch}/{prefix}/{page['source']}"
