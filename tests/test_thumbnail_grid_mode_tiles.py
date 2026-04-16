"""Tests for mode-aware tile behavior in thumbnail_grid."""

from pathlib import Path

from cerebro.v2.ui.widgets.thumbnail_grid import (
    _mode_placeholder,
    _should_decode_thumbnail,
)


def test_photos_mode_prefers_image_thumbnails():
    image = Path("sample.jpg")
    assert _should_decode_thumbnail("photos", image) is True
    assert _mode_placeholder("photos", image) == "Image preview"


def test_videos_mode_uses_placeholder_not_pil_decode():
    image = Path("sample.jpg")
    assert _should_decode_thumbnail("videos", image) is False
    assert _mode_placeholder("videos", image) == "Video preview"


def test_music_mode_uses_audio_placeholder():
    audio = Path("song.mp3")
    assert _should_decode_thumbnail("music", audio) is False
    assert _mode_placeholder("music", audio) == "Audio file"


def test_files_mode_decodes_only_images():
    image = Path("photo.png")
    video = Path("clip.mp4")
    assert _should_decode_thumbnail("files", image) is True
    assert _should_decode_thumbnail("files", video) is False
    assert _mode_placeholder("files", video) == "Video file"
