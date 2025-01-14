import json
import os
import tempfile
import zipfile

import pytest

from aac_processors.base_processor import AACProcessor
from aac_processors.tree_structure import AACButton, AACPage, AACTree, ButtonType


@pytest.fixture
def test_processor():
    """Create a test implementation of AACProcessor"""

    class TestProcessor(AACProcessor):
        def can_process(self, file_path):
            return file_path.endswith(".test")

        def extract_texts(self, file_path):
            return ["test1", "test2"]

        def create_translated_file(self, file_path, translations, output_path):
            with open(output_path, "w") as f:
                json.dump(translations, f)

        def load_into_tree(self, file_path: str) -> AACTree:
            tree = AACTree()
            home = AACPage("home", "Home", (2, 2))
            page1 = AACPage("page1", "Page 1", (2, 2))
            home.buttons.append(
                AACButton(
                    "btn1", "Test", ButtonType.NAVIGATE, (0, 0), target_page_id="page1"
                )
            )
            tree.add_page(home)
            tree.add_page(page1)
            return tree

    processor = TestProcessor()
    processor.collected_texts = []
    return processor


@pytest.fixture
def temp_test_file():
    with tempfile.NamedTemporaryFile(suffix=".test", delete=False) as f:
        f.write(b"test content")
    yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_zip_file():
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        with zipfile.ZipFile(f.name, "w") as zf:
            zf.writestr("test.txt", "test content")
    yield f.name
    os.unlink(f.name)


def test_session_workspace(test_processor):
    """Test workspace creation and management"""
    workspace = test_processor.get_session_workspace()
    assert os.path.exists(workspace)
    assert (
        workspace == test_processor.get_session_workspace()
    )  # Should return same path
    test_processor.cleanup_temp_files()
    assert not os.path.exists(workspace)


def test_set_source_file(test_processor, temp_test_file):
    """Test source file setting"""
    test_processor.set_source_file("/path/to/example.test")
    assert test_processor._original_filename == "example"


def test_prepare_workspace_normal_file(test_processor, temp_test_file):
    """Test workspace preparation with normal file"""
    test_processor.is_archive = False
    workspace = test_processor._prepare_workspace(temp_test_file)
    assert os.path.exists(workspace)
    assert len(os.listdir(workspace)) == 1


def test_prepare_workspace_archive(test_processor, temp_zip_file):
    """Test workspace preparation with archive file"""
    test_processor.is_archive = True
    workspace = test_processor._prepare_workspace(temp_zip_file)
    assert os.path.exists(workspace)
    assert "test.txt" in os.listdir(workspace)


def test_get_output_path(test_processor, temp_test_file):
    """Test output path generation"""
    test_processor.set_source_file(temp_test_file)
    output_path = test_processor.get_output_path("es")
    assert output_path.endswith("_es")
    assert os.path.dirname(output_path) == test_processor.get_session_workspace()


def test_get_output_path_no_source(test_processor):
    """Test output path generation without source file"""
    with pytest.raises(ValueError):
        test_processor.get_output_path()


def test_process_texts_extract(test_processor, temp_test_file):
    """Test text extraction mode"""
    texts = test_processor.process_texts(temp_test_file)
    assert texts == ["test1", "test2"]


def test_process_texts_translate(test_processor, temp_test_file):
    """Test translation mode"""
    translations = {"test1": "prueba1", "test2": "prueba2"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".test") as output:
        result = test_processor.process_texts(temp_test_file, translations, output.name)
        assert result == output.name
        with open(output.name) as f:
            saved_translations = json.load(f)
        assert saved_translations == translations


def test_cleanup(test_processor):
    """Test cleanup of temporary files"""
    workspace = test_processor.get_session_workspace()
    assert os.path.exists(workspace)
    test_processor.cleanup_temp_files()
    assert not os.path.exists(workspace)
    assert test_processor._temp_dir is None


def test_debug_print(test_processor):
    """Test debug print functionality"""
    messages = []
    test_processor._debug_output = messages.append
    test_processor._debug_print("test message")
    assert len(messages) == 1
    assert messages[0].endswith("test message")
