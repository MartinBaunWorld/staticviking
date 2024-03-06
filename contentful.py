#!/usr/bin/env python3

from json import loads
from datetime import datetime
from pathlib import Path

from requests import get
from docopt import docopt


def get_media_data(assets, media_id, url):
    if not assets:
        link_part = url.split('/entries')[0]
        access_token = url.split("?access_token=")[-1]
        media_url = f"{link_part}/assets/{media_id}?access_token={access_token}"
        response = get(media_url)
        data = loads(response.text)
        return data.get("fields", {}).get("file", {})

    for asset in assets:
        sys_id = asset.get("sys", {}).get("id", "")
        if sys_id != media_id:
            continue

        return asset.get("fields", {}).get("file", {})

    return {}


def parse_entry(entry, assets, url):
    fields = entry.get("fields", {})
    created_at = entry.get("sys", {}).get("createdAt", "")

    date = created_at.split("T")[0] if created_at and "T" in created_at else datetime.now().strftime("%Y-%m-%d")
    title = fields.get("title", "No title")
    slug = fields.get("slug", "no_title")
    lang = fields.get("language", "en")
    description = fields.get("meta", "")
    body = fields.get("body", "")
    media_id = fields.get("image", {}).get("sys", {}).get("id", "")
    media_data = get_media_data(assets, media_id, url)
    img_filename = media_data.get("fileName", "")
    image = f'image: "{img_filename}"' if img_filename else ""

    data = f"""---
title: "{title}"
date: "{date}"
description: "{description}"
tags: []
{image}
---

{body}

"""

    return data, slug, lang, media_data


def run(content_path, input_url):
    response = get(input_url)

    try:
        data = loads(response.text)
    except: # noqa
        print(f"Can't parse data from the provided link.\nResponse: {response.status_code}\n{response.text}")
        exit(0)

    items = data.get("items", [data])
    assets = data.get("includes", {}).get("Asset", [])

    for item in items:
        content_type = item.get("sys", {}).get("contentType", {}).get("sys", {}).get("id", "")
        if content_type != "post":
            continue

        content, slug, lang, media_data = parse_entry(item, assets, url)

        post_path = f"{content_path}/{slug}"
        img_filename = media_data.get("fileName", "")
        img_url = media_data.get("url", "")
        Path(post_path).mkdir(parents=True, exist_ok=True)

        with open(f"{post_path}/index.md", "w") as f:
            f.write(content)

        if not img_url:
            continue

        with open(f"{post_path}/{img_filename}", "wb") as f:
            response = get(f"https:{img_url}")
            f.write(response.content)


doc = """ttcore

Usage:
  contentful.py <url> <content_path>

Options:
  <content_path> Path where to save contentful posts [default: content/blog]
  <url>          Contentful url
  -h --help      Show this screen.
  
"""

if __name__ == '__main__':
    arguments = docopt(doc)

    content_path = arguments['<content_path>']
    url = arguments['<url>']
    run(content_path, url)

