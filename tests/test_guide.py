import json
import re
from html.parser import HTMLParser
from pathlib import Path

from flask import url_for

from app.models import User
from app.platform_guide import GUIDE_CHAPTERS


class GuidePage(HTMLParser):
    """Inspect the delivered page without adding a browser/parser dependency."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def handle_data(self, text):
        self.text.append(text)

    def tags(self, name):
        return [attrs for tag, attrs in self.elements if tag == name]


def test_video_guide_is_public_and_does_not_require_a_database(app, client, tmp_path):
    database = tmp_path / "unused-guide.sqlite3"
    app.config["DATABASE"] = str(database)
    response = client.get("/guide")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert not database.exists()


def test_video_guide_is_available_to_signed_in_students(app, client):
    with app.app_context():
        user = User.create("Guide Student", "guide@example.com", "unused-password-hash")
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True
    response = client.get("/guide")
    assert response.status_code == 200
    page = GuidePage(response.get_data(as_text=True))
    assert any(link.get("href") == "/dashboard" for link in page.tags("a"))


def test_guide_is_discoverable_in_header_and_footer(client):
    for path in ("/", "/auth/login", "/guide"):
        html = client.get(path).get_data(as_text=True)
        header = html.split("<header", 1)[1].split("</header>", 1)[0]
        footer = html.split("<footer", 1)[1].split("</footer>", 1)[0]
        assert any(link.get("href") == "/guide" for link in GuidePage(header).tags("a"))
        assert any(link.get("href") == "/guide" for link in GuidePage(footer).tags("a"))


def test_guide_has_playable_video_accessible_captions_and_written_steps(app, client):
    page = GuidePage(client.get("/guide").get_data(as_text=True))
    assert len(page.tags("video")) == 1
    video = page.tags("video")[0]
    assert "controls" in video and "playsinline" in video
    assert "autoplay" not in video
    assert video["preload"] == "metadata"
    assert video["poster"] == "/static/media/platform-guide-poster.jpg"
    assert any(source.get("src") == "/static/media/platform-guide.mp4" and source.get("type") == "video/mp4"
               for source in page.tags("source"))
    assert any(track.get("kind") == "captions" and track.get("srclang") == "en"
               and track.get("src") == "/static/media/platform-guide.en.vtt" and "default" in track
               for track in page.tags("track"))
    assert any(track.get("kind") == "chapters" and track.get("src") == "/static/media/platform-guide.chapters.vtt"
               for track in page.tags("track"))

    anchors = {link.get("href") for link in page.tags("a")}
    chapter_links = [link for link in page.tags("a") if "data-guide-chapter" in link]
    assert len(chapter_links) == len(GUIDE_CHAPTERS) == 6
    text = " ".join(" ".join(page.text).split())
    for chapter in GUIDE_CHAPTERS:
        assert f"#guide-chapter-{chapter['id']}" in anchors
        assert any(attrs.get("id") == f"guide-chapter-{chapter['id']}" for _, attrs in page.elements)
        for step in chapter["steps"]:
            assert " ".join(step.split()) in text
        with app.test_request_context():
            action = url_for(chapter["action_endpoint"], **chapter.get("action_values", {}))
        assert action in anchors


def test_guide_media_assets_are_served_with_correct_types(client):
    assets = {
        "platform-guide.mp4": "video/mp4",
        "platform-guide-poster.jpg": "image/jpeg",
        "platform-guide.en.vtt": "text/vtt",
        "platform-guide.chapters.vtt": "text/vtt",
    }
    for filename, mimetype in assets.items():
        with client.get("/static/media/" + filename) as response:
            assert response.status_code == 200, filename
            assert response.mimetype == mimetype, filename
            assert int(response.headers["Content-Length"]) > 0
            if filename.endswith(".vtt"):
                assert response.get_data(as_text=True).startswith("WEBVTT")


def test_guide_video_supports_byte_ranges_for_seeking(client):
    with client.get("/static/media/platform-guide.mp4", headers={"Range": "bytes=0-255"}) as response:
        assert response.status_code == 206
        assert response.headers["Accept-Ranges"] == "bytes"
        assert response.headers["Content-Range"].startswith("bytes 0-255/")
        assert len(response.data) == 256
        assert b"ftyp" in response.data[:64]


def test_video_timings_and_chapter_tracks_match_the_content(app):
    media = Path(app.static_folder) / "media"
    manifest = json.loads((media / "platform-guide.json").read_text())
    assert manifest["duration"] > 0
    assert len(manifest["chapters"]) == len(GUIDE_CHAPTERS) == 6
    assert (media / "platform-guide.mp4").stat().st_size > 100_000
    assert (media / "platform-guide-poster.jpg").stat().st_size > 1_000
    previous_end = 0
    for timing, chapter in zip(manifest["chapters"], GUIDE_CHAPTERS):
        assert timing["id"] == chapter["id"]
        assert timing["start"] >= previous_end - 0.01
        assert timing["end"] > timing["start"]
        assert timing["end"] <= manifest["duration"] + 0.1
        previous_end = timing["end"]
    assert manifest["chapters"][0]["start"] == 0
    assert abs(previous_end - manifest["duration"]) < 0.1
    timestamps = re.findall(r"\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}",
                            (media / "platform-guide.chapters.vtt").read_text())
    assert len(timestamps) == 6
