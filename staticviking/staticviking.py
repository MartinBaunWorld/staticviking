#!/usr/bin/env python3

from types import SimpleNamespace
from datetime import date, datetime
import re
import os
from pathlib import Path
import shutil
from dataclasses import dataclass
from traceback import format_exc
from htmlmin import minify as html_minify

from PIL import Image
from frontmatter import load
from markdown import markdown as _markdown
from slugify import slugify
from jinja2 import Environment, FileSystemLoader, select_autoescape, BaseLoader
from docopt import docopt

LIB_DIR = os.path.split(__file__)[0]


@dataclass
class Tag:
    title: str
    slug: str
    url: str

    def __hash__(self):
        return hash((self.title, self.slug, self.url))


class Page(SimpleNamespace):
    def __hash__(self):
        return hash((self.title, self.dst, self.url))


def mkdir(path):
    return Path(path).mkdir(parents=True, exist_ok=True)


def mkdir_parent(path):
    return Path(path).parent.mkdir(parents=True, exist_ok=True)


def read(path):
    with open(path, 'r') as f:
        return f.read()


def write(path, data):
    with open(path, 'w') as f:
        return f.write(data)


def read_page(path):
    defaults = dict(
        title="",
        description="",
        date="2023-02-23",
        draft=False,
        tags=[],
        body="",
    )
    data = load(path)
    if data.content:
        data['body'] = data.content
    defaults.update(data)
    defaults['date'] = datetime.strptime(defaults['date'], "%Y-%m-%d")
    return defaults


def markdown(text):
    return _markdown(
        text,
        extensions=[
            'fenced_code',
            'tables',
            'sane_lists',
            'markdown.extensions.toc',
        ],
    )


def tmplsOrFail(tmpls):
    if Path(tmpls).is_dir():
        return Environment(
            loader=FileSystemLoader([tmpls]),
            autoescape=select_autoescape(),
        )
    elif Path(f"{LIB_DIR}/templates"):
        return Environment(
            loader=FileSystemLoader([f"{LIB_DIR}/templates"]),
            autoescape=select_autoescape(),
        )

    raise Exception("Could not find templates directory")


def compress_image(path):
    max_img_size = 500  # KB
    min_width = 400
    min_height = 250
    attempts = 5
    img_size = os.path.getsize(path) / 1024

    if img_size <= max_img_size:
        return

    try:
        while attempts > 0:
            with Image.open(path) as img:
                if img_size <= max_img_size or all([img.width * 0.75 < min_width, img.height * 0.75 < min_height]):
                    break

                img = img.resize((round(img.width * 0.75), round(img.height * 0.75)))
                img.save(path, optimize=True, quality=80)

            img_size = os.path.getsize(path) / 1024
            attempts -= 1
    except: # noqa
        print(f"Exception while image '{path}' compression:\n{format_exc()}")


def get_pagination_amount(page_amount):
    if page_amount <= 6:
        return 1

    pagination_amount = page_amount // 6
    if page_amount % 6 != 0:
        return pagination_amount + 1

    return pagination_amount


class Blog:
    def __init__(self, content, dist, tmpls, host, markdown=markdown):
        self.content = content
        self.dist = dist
        self.tmpls = tmpls
        self.markdown = markdown
        self.env = tmplsOrFail(self.tmpls)
        self.set_host(host)

        def words(txt):
            return len(re.findall(r'\w+', txt))

        self.env.filters['words'] = words

        self.tags = []
        self.files = [
            os.path.join(dp, f)
            for dp, dn, filenames in os.walk(self.content)
            for f in filenames
        ]

        self.pages = []

    def set_host(self, host):
        if not host.startswith("http://") and not host.startswith("https://"):
            raise Exception("Wrong host name")

        self.host = host[:-1] if host[-1] == "/" else host  # http://localhost.com/blog
        init_host = "/".join(self.host.split("/")[0:3])  # http://localhost.com
        dirpath = self.host.replace(init_host, "")  # /blog

        if dirpath == "":
            return

        if self.dist.endswith(dirpath) or self.dist.endswith(dirpath + "/"):
            self.host = init_host
            return

        self.dist = (self.dist + dirpath).replace("//", "/")  # dist + /blog = dist/blog

    def handle_files(self):
        print("Handle files..")
        shutil.copytree(self.tmpls + "/to_copy/", self.dist + "/")
        for fn in self.files:
            file_ext = fn.split(".")[-1]
            if not fn.endswith('.md') and file_ext in ["jpg", "jpeg", "png"]:
                dst = self.dist + fn[len(self.content):]
                print(f' - {dst} - compress image and copy')
                mkdir_parent(dst)
                shutil.copy2(fn, dst)
                compress_image(dst)
                continue
            if not fn.endswith('.md'):
                dst = self.dist + fn[len(self.content):]
                print(f' - {dst} - copy')
                mkdir_parent(dst)
                shutil.copy2(fn, dst)
                continue

            page_data = read_page(fn)
            tags = []
            for tag in page_data['tags']:
                tags.append(Tag(
                    title=tag,
                    slug=f'tags/{slugify(tag)}',
                    url=f"{self.host}/tags/{slugify(tag)}/"),
                )

            path = fn[len(self.content):]

            if path.endswith("index.md"):
                # if path is of format /my-blog-post/index.md
                path = path[:-9]
            else:
                # if path is of format /my-blog-post.md
                path = path[0:-3]

            dst = self.dist + path
            print(f' - {dst} - handle as page')
            if page_data['date'] and page_data['date'] > datetime.today():
                continue

            image = page_data.get("image", "")
            if image != '' and not (image.startswith("https://") or image.startswith("http://")):
                # TODO: also make this image with my-blog-post.md
                post_path = (
                    fn[len(self.content):].
                    replace('index.md', '')) # /posts/cool-blog-post/

                image = f"{self.host}{post_path}{image}"

            page_data.update(dict(
                nolist=page_data.get('nolist', False),
                template=page_data.get('template', "post.html"),
                related=[],
                tags=tags,
                image=image,
                dst=dst,
                url=f"{self.host}{path}/",
                description=page_data['description'],
                author=page_data.get('author', ''),
                aliases=page_data.get('aliases', []),
                faq=page_data.get('faq', []),
            ))
            self.pages.append(Page(**page_data))

        print("Sorting pages..")
        self.pages = sorted(self.pages, key=lambda o: o.date, reverse=True)

        print("Organizing tags..")
        from collections import Counter
        for page in self.pages:
            # TODO maybe make this scored with amount of tags in common
            # But for now it is good and fast
            page.related = [
                p
                for p in self.pages
                # common tags > 0 (relevancy by tag amount)
                if len(Counter(page.tags) & Counter(p.tags)) > 0
                and p != page
            ]
            for tag in page.tags:
                self.tags.append(tag)

        self.tags = list(set(self.tags))

    def get_pages_with_tag(self, tag):
        return list(set([
            page
            for page
            in self.pages if tag.slug in [t.slug for t in page.tags]
        ]))

    def get_template(self, name):
        return self.env.get_template(name)

    def write_listing(self, path, pages, tag, url):
        pages = [page for page in pages if not page.nolist]
        page_amount = get_pagination_amount(len(pages))
        mkdir_parent(path)
        pages_set = pages[0:6]
        context = dict(
            tag=tag,
            blog=self,
            pages=[p for p in pages_set],
            page_amount=page_amount,
            current_page=1,
            prev_page=1,
            next_page=2 if page_amount >= 2 else 1,
            pages_urls=[f"{url}{p}/" for p in range(1, page_amount + 1)],
            url=f"{url}1/",
            blog_url=f"{self.host}/",
        )
        write(
            path,
            html_minify(self.get_template("listing.html").render(**context)),
        )
        for page_num in range(page_amount):
            page_path = path.replace("index.html", str(page_num + 1) + "/index.html")
            mkdir_parent(page_path)

            pages_set = pages[page_num*6:page_num*6+6]
            prev_page = page_num if page_num >= 1 else 1
            next_page = page_num + 2 if page_num + 2 <= page_amount else page_num + 1

            context = dict(
                tag=tag,
                blog=self,
                pages=[p for p in pages_set],
                page_amount=page_amount,
                current_page=page_num + 1,
                prev_page=prev_page,
                next_page=next_page,
                pages_urls=[f"{url}{p}/" for p in range(1, page_amount + 1)],
                url=f"{url}{page_num + 1}/",
                blog_url=f"{self.host}/",
            )
            write(
                page_path,
                html_minify(self.get_template("listing.html").render(**context)),
            )

    def write_pages(self):
        print("Writing pages..")
        for page in self.pages:
            page.body_html = self.markdown(page.body)
            print(page.dst)
            mkdir(page.dst)
            template = self.get_template(page.template)
            write(
                f'{page.dst}/index.html',
                html_minify(template.render(
                    blog=self,
                    page=page,
                    url=page.url,
                    blog_url=f"{self.host}/",
                )),
            )

            self.write_page_aliases(page)

    def write_page_aliases(self, page):
        for alias in page.aliases:
            alias_path = alias.strip().lower()
            if not alias_path:
                continue

            print(f"Writing '{alias_path}' alias..")
            mkdir(f"{self.dist}/{alias_path}")

            template = self.get_template("redirect.html")
            write(
                f'{self.dist}/{alias_path}/index.html',
                html_minify(template.render(
                    blog=self,
                    url=page.url,
                )),
            )

    def write_sitemap(self, extra_sitemaps=[]):
        print("Writing sitemap..")
        pages = list(self.pages) + extra_sitemaps
        template = self.get_template("sitemap.xml")
        write(
            f"{self.dist}/sitemap.xml",
            template.render(
                blog=self,
                pages=pages,
                tags=self.tags,
                today=datetime.today(),
                blog_url=f"{self.host}/",
                url=f"{self.host}/",
            ),
        )


def build(blog):
    shutil.rmtree(blog.dist, ignore_errors=True, onerror=None)
    blog.handle_files()
    mkdir(blog.dist)

    blog.write_sitemap()
    blog.write_pages()
    blog.write_listing(
        f"{blog.dist}/index.html",
        blog.pages,
        None,
        f'{blog.host}/',
    )

    for tag in blog.tags:
        blog.write_listing(
            f"{blog.dist}/{tag.slug}/index.html",
            blog.get_pages_with_tag(tag),
            tag,
            tag.url,
        )


doc = """staticviking

Usage:
  staticviking.py new <host>
  staticviking.py build <content> <dist> [--tmpls=<tmpls>] [--host=<host>]
  staticviking.py buildserve <content> <dist> [--tmpls=<tmpls>] [--host=<host>]

Options:

  <dist>            destination of compiled. Warning folder will be overriden [default: dist]
  <content>         folder of content [default: content]
  -h --help         Show this screen.
  --tmpls=<tmpls>   What's the folder of your templates [default: templates]
  --host=<host>     the host where the file [default: http://localhost:8000]
"""


def add_execute_permission(filepath):
    current_permissions = os.stat(filepath).st_mode
    new_permissions = current_permissions | 0o111
    os.chmod(filepath, new_permissions)


def cli():
    a = docopt(doc, version='staticviking.py 0.1')
    print(a)
    if a['build']:
        build(Blog(a['<content>'], a['<dist>'], a['--tmpls'], a['--host']))
    elif a['buildserve']:
        build(Blog(a['<content>'], a['<dist>'], a['--tmpls'], a['--host']))
        os.system(f"cd {a['<dist>']} && python3 -m http.server -b localhost")
    elif a['new']:
        if not os.path.exists("staticviking.py"):
            shutil.copyfile(f"{LIB_DIR}/staticviking.py", "staticviking.py")

        if not os.path.exists("templates"):
            shutil.copytree(f"{LIB_DIR}/templates", "templates")

        if not os.path.exists("build_prod"):
            write("build_prod", f"#!/bin/sh\n\nstaticviking build content dist --host=\"{a['<host>']}\"")
            add_execute_permission("build_prod")

        if not os.path.exists("build"):
            write("build", "#!/bin/sh\n\nstaticviking build content dist --host=\"http://localhost:8000\"")
            add_execute_permission("build")

        if not os.path.exists("buildserve"):
            write("buildserve", "#!/bin/sh\n\nstaticviking buildserve content dist --host=\"http://localhost:8000\"")
            add_execute_permission("buildserve")


if __name__ == "__main__":
    cli()
