"""Mirror a few nhs.uk medicine pages into v1/ (as-is) and v2/ (one div -> section)."""
import os
import re
import shutil
import urllib.request

NHS = "https://www.nhs.uk"
MEDS = ("acrivastine", "amlodipine")
HERE = os.path.dirname(os.path.abspath(__file__))

BANNER = (
    '<div style="background:#ffeb3b;padding:12px 0;border-bottom:4px solid #212b32">'
    '<div class="nhsuk-width-container"><strong>Test fixture, not the NHS website.</strong> '
    "Pages copied from nhs.uk for a scraping exercise; content may be altered.</div></div>"
)
FOOTER = (
    '<div class="nhsuk-width-container"><p class="nhsuk-body-s">Content from the '
    '<a href="https://www.nhs.uk/medicines/">NHS website</a>, used under the '
    '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">'
    "Open Government Licence v3.0</a>. Not medical advice.</p></div>"
)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req).read().decode()


def main_of(html):
    return re.search(r"<main.*?</main>", html, re.S).group(0)


def rewrite_links(html, depth):
    up = "../" * depth

    def fix(m):
        href = m.group(1)
        path = href.removeprefix(NHS)
        med = re.match(r"/medicines/((?:%s)/.*)" % "|".join(MEDS), path)
        if med:
            return f'href="{up}{med.group(1)}"'
        if path.startswith("/medicines/#") or path == "/medicines/":
            return f'href="{up}{path.removeprefix("/medicines/")}"'
        if path.startswith("/"):
            return f'href="{NHS}{path}"'
        return m.group(0)

    return re.sub(r'href="([^"]*)"', fix, html)


def page(title, main, depth):
    css = "../" * (depth + 2) + "nhsuk.css"
    return (
        f'<!doctype html>\n<html lang="en-GB">\n<head>\n<meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta name="robots" content="noindex">\n<title>{title}</title>\n'
        f'<link rel="stylesheet" href="{css}">\n</head>\n<body>\n{BANNER}\n'
        f'<div class="nhsuk-width-container">\n{main}\n</div>\n{FOOTER}\n</body>\n</html>\n'
    )


def write(path, html):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(html)


def only_meds(index_main):
    def keep(m):
        return m.group(0) if any(f"/medicines/{med}/" in m.group(0) for med in MEDS) else ""

    return re.sub(r"<li>\s*<a href=\"/medicines/[^\"]+\">.*?</a>\s*</li>", keep, index_main, flags=re.S)


def wrap_related_in_section(hub_main):
    out, n = re.subn(
        r'<div class="nhsuk-u-margin-top-6 ">(\s*<div class="beta-hub-related-links-title">\s*'
        r"<h2[^>]*>Related conditions</h2>.*?</ul>\s*)</div>",
        r'<section class="nhsuk-u-margin-top-6 ">\1</section>',
        hub_main,
        count=1,
        flags=re.S,
    )
    assert n == 1, "Related conditions block not found"
    return out


def build():
    pages = {"": only_meds(main_of(fetch(f"{NHS}/medicines/")))}
    for med in MEDS:
        main = main_of(fetch(f"{NHS}/medicines/{med}/"))
        pages[f"{med}/"] = main
        subs = re.findall(rf'href="(?:{NHS})?/medicines/{med}/([^"/#]+)/"', main)
        for sub in dict.fromkeys(subs):
            pages[f"{med}/{sub}/"] = main_of(fetch(f"{NHS}/medicines/{med}/{sub}/"))

    css = re.search(r'href="(/static/nhsuk/css/main\.[^"]+\.css)"', fetch(f"{NHS}/medicines/")).group(1)
    write(f"{HERE}/nhsuk.css", fetch(NHS + css))

    for version in ("v1", "v2"):
        shutil.rmtree(f"{HERE}/{version}", ignore_errors=True)
        for rel, main in pages.items():
            if version == "v2" and rel == "acrivastine/":
                main = wrap_related_in_section(main)
            depth = rel.count("/")
            title = re.sub(r"<[^>]+>|\s+", " ", re.search(r"<h1.*?</h1>", main, re.S).group(0)).strip()
            write(f"{HERE}/{version}/medicines/{rel}index.html", page(title, rewrite_links(main, depth), depth))

    write(
        f"{HERE}/index.html",
        page(
            "NHS medicines fixture",
            '<main class="nhsuk-main-wrapper"><h1>NHS medicines fixture</h1><ul>'
            '<li><a href="v1/medicines/">v1</a></li><li><a href="v2/medicines/">v2</a></li></ul></main>',
            -2,
        ),
    )


if __name__ == "__main__":
    build()
