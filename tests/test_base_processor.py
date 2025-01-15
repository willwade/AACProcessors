import json
import os
import tempfile
import zipfile
from collections.abc import Generator
from typing import Optional

import pytest

from aac_processors.base_processor import AACProcessor
from aac_processors.tree_structure import AACTree


@pytest.fixture
def test_processor() -> AACProcessor:
    """Create a test implementation of AACProcessor"""

    class TestProcessor(AACProcessor):
        """Test implementation of AACProcessor."""

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
            return ["test1", "test2"]

        def create_translated_file(
            self, file_path: str, translations: dict[str, str]
        ) -> Optional[str]:
            """Test implementation."""
            if translations:
                with open(file_path, "w") as f:
                    json.dump(translations, f)
                return file_path
            return None

    processor = TestProcessor()
    processor.collected_texts = []
    return processor


@pytest.fixture
def temp_test_file() -> Generator[str, None, None]:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".test", delete=False) as f:
        f.write("test content")
    yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_zip_file() -> Generator[str, None, None]:
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        with zipfile.ZipFile(f.name, "w") as zf:
            zf.writestr("test.txt", "test content")
    yield f.name
    os.unlink(f.name)


def test_session_workspace(test_processor: AACProcessor) -> None:
    """Test workspace creation and management"""
    workspace = test_processor.get_session_workspace()
    assert os.path.exists(workspace)
    assert (
        workspace == test_processor.get_session_workspace()
    )  # Should return same path
    test_processor.cleanup_temp_files()
    assert not os.path.exists(workspace)


def test_set_source_file(test_processor: AACProcessor, temp_test_file: str) -> None:
    """Test source file setting"""
    test_processor.set_source_file("/path/to/example.test")
    assert test_processor._original_filename == "example"


def test_prepare_workspace_normal_file(
    test_processor: AACProcessor, temp_test_file: str
) -> None:
    """Test workspace preparation with normal file"""
    test_processor.is_archive = False
    workspace = test_processor._prepare_workspace(temp_test_file)
    assert os.path.exists(workspace)
    assert len(os.listdir(workspace)) == 1


def test_prepare_workspace_archive(
    test_processor: AACProcessor, temp_zip_file: str
) -> None:
    """Test workspace preparation with archive file"""
    test_processor.is_archive = True
    workspace = test_processor._prepare_workspace(temp_zip_file)
    assert os.path.exists(workspace)
    assert "test.txt" in os.listdir(workspace)


def test_get_output_path(test_processor: AACProcessor, temp_test_file: str) -> None:
    """Test output path generation"""
    test_processor.set_source_file(temp_test_file)
    output_path = test_processor.get_output_path("es")
    assert output_path.endswith("_es")
    assert os.path.dirname(output_path) == test_processor.get_session_workspace()


def test_get_output_path_no_source(test_processor: AACProcessor) -> None:
    """Test output path generation without source file"""
    with pytest.raises(ValueError):
        test_processor.get_output_path()


def test_process_texts_extract(
    test_processor: AACProcessor, temp_test_file: str
) -> None:
    """Test text extraction mode"""
    texts = test_processor.process_texts(temp_test_file)
    assert texts == ["test1", "test2"]


def test_process_texts_translate(
    test_processor: AACProcessor, temp_test_file: str
) -> None:
    """Test translation mode"""
    translations = {"test1": "prueba1", "test2": "prueba2"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".test") as output:
        result = test_processor.process_texts(temp_test_file, translations, output.name)
        assert result == output.name
        with open(output.name) as f:
            saved_translations = json.load(f)
        assert saved_translations == translations


def test_cleanup(test_processor: AACProcessor) -> None:
    """Test cleanup of temporary files"""
    workspace = test_processor.get_session_workspace()
    assert os.path.exists(workspace)
    test_processor.cleanup_temp_files()
    assert not os.path.exists(workspace)
    assert test_processor._temp_dir is None


def test_debug_print(test_processor: AACProcessor) -> None:
    """Test debug print functionality"""
    messages = []
    test_processor._debug_output = messages.append
    test_processor._debug_print("test message")
    assert len(messages) == 1
    assert messages[0].endswith("test message")
