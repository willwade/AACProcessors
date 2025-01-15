import json
import os
import shutil
import tempfile
import zipfile
from collections.abc import Generator
from typing import Optional

import pytest

from aac_processors.file_processor import FileProcessor
from aac_processors.tree_structure import AACTree


@pytest.fixture
def test_processor() -> FileProcessor:
    """Create test processor."""

    class TestFileProcessor(FileProcessor):
        """Test implementation of FileProcessor."""

        def __init__(self) -> None:
            """Initialize test processor."""
            super().__init__()
            self.messages: list[str] = []

        def debug(self, message: str) -> None:
            """Test implementation."""
            if self._debug_output:
                self._debug_output(message)

        def can_process(self, file_path: str) -> bool:
            """Test implementation."""
            return True

        def load_into_tree(self, file_path: str) -> AACTree:
            """Test implementation."""
            return AACTree()

        def save_from_tree(self, tree: AACTree, output_path: str) -> None:
            """Test implementation."""
            pass

        def extract_texts(self, file_path: str) -> list[str]:
            """Test implementation."""
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    return [data.get("text", "test")]
            except json.JSONDecodeError:
                return ["test"]

        def create_translated_file(
            self, file_path: str, translations: dict[str, str]
        ) -> Optional[str]:
            """Test implementation."""
            return "translated.test"

        def process_files(
            self, directory: str, translations: Optional[dict[str, str]] = None
        ) -> Optional[str]:
            """Test implementation."""
            if translations:
                # Create a new file with translations
                if self.check_is_archive(self.file_path):
                    # For zip files, create a new zip with translated content
                    output_file = os.path.join(directory, "translated.zip")
                    with zipfile.ZipFile(output_file, "w") as zf:
                        # Add translated test.test file
                        with tempfile.NamedTemporaryFile(mode="w", suffix=".test") as f:
                            f.write(translations.get("test content", ""))
                            f.flush()
                            zf.write(f.name, "test.test")
                        # Add unchanged test.txt file
                        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as f:
                            f.write("test content")
                            f.flush()
                            zf.write(f.name, "test.txt")
                    return output_file
                else:
                    # For regular files, create JSON with translations
                    output_file = os.path.join(directory, "translated.test")
                    with open(output_file, "w") as f:
                        json.dump({"text": translations.get("test", "")}, f)
                    return output_file
            return None

        def cleanup_temp_files(self) -> None:
            """Test implementation."""
            for temp_dir in self._temp_dirs:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            self._temp_dirs = []

    return TestFileProcessor()


@pytest.fixture
def temp_test_file() -> Generator[str, None, None]:
    """Create temporary test file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".test", delete=False) as f:
        json.dump({"text": "test"}, f)
        yield f.name
    if os.path.exists(f.name):
        os.remove(f.name)


@pytest.fixture
def temp_zip_file() -> Generator[str, None, None]:
    """Create temporary zip file."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
        with zipfile.ZipFile(temp_zip.name, "w") as zf:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".test") as f:
                f.write("test content")
                f.flush()
                zf.write(f.name, "test.test")
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as f:
                f.write("test content")
                f.flush()
                zf.write(f.name, "test.txt")
        yield temp_zip.name
    if os.path.exists(temp_zip.name):
        os.remove(temp_zip.name)


def test_init(test_processor: FileProcessor) -> None:
    """Test initialization"""
    assert test_processor._temp_dirs == []
    assert test_processor._debug_output is not None
    assert test_processor.collected_texts == []
    assert test_processor.file_path is None
    assert test_processor.original_filename is None


def test_debug_output(test_processor: FileProcessor) -> None:
    """Test debug output functionality"""
    messages: list[str] = []
    test_processor._debug_output = messages.append
    test_processor.debug("test message")
    assert len(messages) == 1
    assert messages[0] == "test message"


def test_create_and_cleanup_temp_dir(test_processor: FileProcessor) -> None:
    """Test temporary directory creation and cleanup"""
    temp_dir = test_processor.create_temp_dir()
    assert os.path.exists(temp_dir)
    assert temp_dir in test_processor._temp_dirs
    test_processor.cleanup_temp_files()
    assert not os.path.exists(temp_dir)
    assert test_processor._temp_dirs == []


def test_get_output_path(test_processor: FileProcessor, temp_test_file: str) -> None:
    """Test output path generation"""
    test_processor.set_source_file(temp_test_file)
    output_path = test_processor.get_output_path("es")
    assert output_path.endswith("_es.test")
    assert os.path.dirname(output_path) == os.path.dirname(temp_test_file)


def test_get_output_path_with_existing_lang(test_processor: FileProcessor) -> None:
    """Test output path generation with existing language code"""
    test_processor.file_path = "/path/to/file_en.test"
    test_processor.original_filename = "file_en"
    output_path = test_processor.get_output_path("es")
    assert output_path.endswith("file_es.test")
    assert "_en_es" not in output_path


def test_check_is_archive(
    test_processor: FileProcessor, temp_zip_file: str, temp_test_file: str
) -> None:
    """Test archive detection"""
    assert test_processor.check_is_archive(temp_zip_file) is True
    assert test_processor.check_is_archive(temp_test_file) is False
    assert test_processor.check_is_archive(None) is False


def test_extract_archive(test_processor: FileProcessor, temp_zip_file: str) -> None:
    """Test archive extraction"""
    temp_dir = test_processor.create_temp_dir()
    test_processor.extract_archive(temp_zip_file, temp_dir)
    assert "test.txt" in os.listdir(temp_dir)
    assert "test.test" in os.listdir(temp_dir)


def test_create_archive(test_processor: FileProcessor) -> None:
    """Test archive creation"""
    temp_dir = test_processor.create_temp_dir()
    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test content")

    output_zip = os.path.join(temp_dir, "output.zip")
    test_processor.create_archive(temp_dir, output_zip)

    assert os.path.exists(output_zip)
    with zipfile.ZipFile(output_zip, "r") as zf:
        assert "test.txt" in zf.namelist()


def test_process_texts_extract(
    test_processor: FileProcessor, temp_test_file: str
) -> None:
    """Test text extraction mode"""
    result = test_processor.process_texts(temp_test_file)
    assert isinstance(result, list)
    assert result == ["test"]


def test_process_texts_translate(
    test_processor: FileProcessor, temp_test_file: str
) -> None:
    """Test translation mode"""
    translations = {"test": "prueba"}
    output_path = os.path.join(os.path.dirname(temp_test_file), "output.test")
    result = test_processor.process_texts(temp_test_file, translations, output_path)
    assert result == output_path
    with open(output_path) as f:
        saved = json.load(f)
    assert saved["text"] == "prueba"
    os.remove(output_path)


def test_process_texts_archive(
    test_processor: FileProcessor, temp_zip_file: str
) -> None:
    """Test processing archive file"""
    translations = {"test content": "prueba"}
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as output:
        result = test_processor.process_texts(temp_zip_file, translations, output.name)
        assert result == output.name

        # Verify the translated content
        with zipfile.ZipFile(output.name, "r") as zf:
            # Check test.test file
            with zf.open("test.test") as f:
                content = f.read().decode("utf-8")
                assert content == "prueba"
            # Check that test.txt is unchanged
            with zf.open("test.txt") as f:
                content = f.read().decode("utf-8")
                assert content == "test content"
        os.remove(output.name)


def test_sanitize_name(test_processor: FileProcessor) -> None:
    """Test name sanitization"""
    assert test_processor._sanitize_name("Hello World!") == "hello_world"
    assert test_processor._sanitize_name("Test-123") == "test_123"
    assert test_processor._sanitize_name("___test___") == "test"
    assert test_processor._sanitize_name("") == ""
    assert test_processor._sanitize_name(None) == ""


def test_cleanup_temp_files(test_processor: FileProcessor) -> None:
    """Test cleanup of temporary files"""
    temp_dir = test_processor.create_temp_dir()
    assert os.path.exists(temp_dir)
    test_processor.cleanup_temp_files()
    assert not os.path.exists(temp_dir)
