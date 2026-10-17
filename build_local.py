"""Build local/before and local/after from v1: served at a host root, same URLs, obviously different content."""
import os
import re
import shutil
import sys
from urllib.parse import urljoin

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = f"{HERE}/v1"
OUT = f"{HERE}/local"

BANNER_RE = re.compile(r'<div style="background:#ffeb3b.*?</div></div>', re.S)


def banner(version):
    colour, label = ("#ffeb3b", "BEFORE (version 1)") if version == "before" else ("#d5281b", "AFTER (version 2)")
    text = "#212b32" if version == "before" else "#ffffff"
    return (
        f'<div style="background:{colour};color:{text};padding:16px 0;border-bottom:4px solid #212b32">'
        f'<div class="nhsuk-width-container"><div style="font-size:32px;font-weight:700;line-height:1.2">{label}</div>'
        "Test fixture, not the NHS website.</div></div>"
    )


CHANGE_CARD = (
    '<div style="background:#d5281b;color:#fff;border:6px solid #8a1538;padding:24px;margin:16px 0 24px">'
    '<p style="font-size:44px;font-weight:700;line-height:1.1;margin:0 0 12px;color:#fff">DO NOT TAKE THIS MEDICINE</p>'
    '<p style="font-size:20px;margin:0 0 8px;color:#fff">This warning was added in version 2 of the test site. '
    "The version 1 page does not have it.</p>"
    '<p style="font-size:14px;margin:0;color:#fff">Test fixture for a scraping exercise, not real medical advice.</p></div>'
)
NEW_SECTION = (
    "<section><h2>New in version 2</h2>"
    "<p>This whole section was added in version 2 of the test site. Version 1 has no section with this heading.</p>"
    "</section>"
)


def to_root_relative(html, page_path):
    def fix(m):
        href = m.group(1)
        if href.startswith(("http://", "https://", "#", "mailto:")):
            return m.group(0)
        return f'href="{urljoin("http://x" + page_path, href).removeprefix("http://x")}"'

    return re.sub(r'href="([^"]*)"', fix, html)


def change(html, rel):
    if rel == "acrivastine/":
        html = html.replace("Acrivastine <span", "Acrivastine (CHANGED PAGE) <span", 1)
        assert "(CHANGED PAGE)" in html, "hub h1 not found"
        html, n = re.subn(r"(<article>)", r"\1" + CHANGE_CARD, html, count=1)
        assert n == 1, "hub article not found"
    if rel == "acrivastine/taking-acrivastine-with-other-medicines-and-herbal-supplements/":
        html, n = re.subn(r"(<article>)", r"\1" + CHANGE_CARD + NEW_SECTION, html, count=1)
        assert n == 1, "article not found"
        html, n = re.subn(r"Page last reviewed: [^<]*", "Page last reviewed: 17 October 2026", html, count=1)
        assert n == 1, "review date not found"
    return html


def build():
    shutil.rmtree(OUT, ignore_errors=True)
    for version in ("before", "after"):
        root = f"{OUT}/{version}"
        for dirpath, _, names in os.walk(SRC):
            for name in names:
                src = os.path.join(dirpath, name)
                rel = os.path.relpath(dirpath, f"{SRC}/medicines")
                rel = "" if rel == "." else rel + "/"
                html = open(src).read()
                html = to_root_relative(html, f"/medicines/{rel}")
                html, n = BANNER_RE.subn(banner(version), html, count=1)
                assert n == 1, f"banner not found in {src}"
                if version == "after":
                    html = change(html, rel)
                dst = f"{root}/medicines/{rel}{name}"
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                open(dst, "w").write(html)
        shutil.copy(f"{HERE}/nhsuk.css", f"{root}/nhsuk.css")
        open(f"{root}/robots.txt", "w").write("User-agent: *\nAllow: /\n")


LIVE_PREFIX = "/nhs-scraper-fixture/live"


def build_live(version):
    """Copy local/<version> into live/, served by GitHub Pages under the repo prefix."""
    live = f"{HERE}/live"
    shutil.rmtree(live, ignore_errors=True)
    shutil.copytree(f"{OUT}/{version}", live)
    for dirpath, _, names in os.walk(live):
        for name in names:
            if name.endswith(".html"):
                path = os.path.join(dirpath, name)
                html = open(path).read()
                html = re.sub(r'href="(/[^/][^"]*)"', rf'href="{LIVE_PREFIX}\1"', html)
                open(path, "w").write(html)


if __name__ == "__main__":
    build()
    if len(sys.argv) == 3 and sys.argv[1] == "live":
        build_live(sys.argv[2])
