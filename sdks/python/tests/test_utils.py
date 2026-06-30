import logging

import pytest

from imagen_sdk import UploadError, check_files_match_profile_type


class DummyProfile:
    def __init__(self, image_type):
        self.image_type = image_type
        self.profile_name = f"Dummy {image_type}"


@pytest.fixture
def logger():
    return logging.getLogger("test_utils")


def test_check_files_match_profile_type_raw_valid(tmp_path, logger):
    raw_file = tmp_path / "photo1.dng"
    raw_file.write_bytes(b"rawdata")
    profile = DummyProfile("RAW")
    # Should not raise
    check_files_match_profile_type([raw_file], profile, logger)


def test_check_files_match_profile_type_jpg_valid(tmp_path, logger):
    jpg_file = tmp_path / "photo1.jpg"
    jpg_file.write_bytes(b"jpgdata")
    profile = DummyProfile("JPG")
    # Should not raise
    check_files_match_profile_type([jpg_file], profile, logger)


def test_check_files_match_profile_type_raw_with_jpg_raises(tmp_path, logger):
    raw_file = tmp_path / "photo1.dng"
    jpg_file = tmp_path / "photo2.jpg"
    raw_file.write_bytes(b"rawdata")
    jpg_file.write_bytes(b"jpgdata")
    profile = DummyProfile("RAW")
    with pytest.raises(UploadError):
        check_files_match_profile_type([raw_file, jpg_file], profile, logger)


def test_check_files_match_profile_type_jpg_with_raw_raises(tmp_path, logger):
    raw_file = tmp_path / "photo1.dng"
    jpg_file = tmp_path / "photo2.jpg"
    raw_file.write_bytes(b"rawdata")
    jpg_file.write_bytes(b"jpgdata")
    profile = DummyProfile("JPG")
    with pytest.raises(UploadError):
        check_files_match_profile_type([jpg_file, raw_file], profile, logger)


def test_check_files_match_profile_type_invalid_file_raises(tmp_path, logger):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("not an image")
    profile = DummyProfile("RAW")
    with pytest.raises(UploadError):
        check_files_match_profile_type([txt_file], profile, logger)
