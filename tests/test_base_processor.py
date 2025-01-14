import os
import tempfile
import pytest
from aac_processors.base_processor import AACProcessor
from aac_processors.tree_structure import AACTree, AACPage, AACButton, ButtonType
import zipfile
import json


class TestProcessor(AACProcessor):
    """Test implementation of AACProcessor"""

    def __init__(self):
        super().__init__()
        self.collected_texts = []

    def can_process(self, file_path):
        return file_path.endswith(".test")

    def extract_texts(self, file_path):
        return ["test1", "test2"]

    def create_translated_file(self, file_path, translations, output_path):
        with open(output_path, 'w') as f:
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


@pytest.fixture
def processor():
    return TestProcessor()


@pytest.fixture
def temp_test_file():
    with tempfile.NamedTemporaryFile(suffix=".test", delete=False) as f:
        f.write(b"test content")
    yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_zip_file():
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        with zipfile.ZipFile(f.name, 'w') as zf:
            zf.writestr("test.txt", "test content")
    yield f.name
    os.unlink(f.name)


def test_session_workspace(processor):
    """Test workspace creation and management"""
    workspace = processor.get_session_workspace()
    assert os.path.exists(workspace)
    assert workspace == processor.get_session_workspace()  # Should return same path
    processor.cleanup_temp_files()
    assert not os.path.exists(workspace)


def test_set_source_file(processor, temp_test_file):
    """Test source file setting"""
    processor.set_source_file("/path/to/example.test")
    assert processor._original_filename == "example"


def test_prepare_workspace_normal_file(processor, temp_test_file):
    """Test workspace preparation with normal file"""
    processor.is_archive = False
    workspace = processor._prepare_workspace(temp_test_file)
    assert os.path.exists(workspace)
    assert len(os.listdir(workspace)) == 1


def test_prepare_workspace_archive(processor, temp_zip_file):
    """Test workspace preparation with archive file"""
    processor.is_archive = True
    workspace = processor._prepare_workspace(temp_zip_file)
    assert os.path.exists(workspace)
    assert "test.txt" in os.listdir(workspace)


def test_get_output_path(processor, temp_test_file):
    """Test output path generation"""
    processor.set_source_file(temp_test_file)
    output_path = processor.get_output_path("es")
    assert output_path.endswith("_es")
    assert os.path.dirname(output_path) == processor.get_session_workspace()


def test_get_output_path_no_source(processor):
    """Test output path generation without source file"""
    with pytest.raises(ValueError):
        processor.get_output_path()


def test_process_texts_extract(processor, temp_test_file):
    """Test text extraction mode"""
    texts = processor.process_texts(temp_test_file)
    assert texts == ["test1", "test2"]


def test_process_texts_translate(processor, temp_test_file):
    """Test translation mode"""
    translations = {"test1": "prueba1", "test2": "prueba2"}
    with tempfile.NamedTemporaryFile(suffix=".test") as output:
        result = processor.process_texts(temp_test_file, translations, output.name)
        assert result == output.name
        with open(output.name) as f:
            saved_translations = json.load(f)
        assert saved_translations == translations


def test_cleanup(processor):
    """Test cleanup of temporary files"""
    workspace = processor.get_session_workspace()
    assert os.path.exists(workspace)
    processor.cleanup_temp_files()
    assert not os.path.exists(workspace)
    assert processor._temp_dir is None


def test_debug_print(processor):
    """Test debug print functionality"""
    messages = []
    processor._debug_output = messages.append
    processor._debug_print("test message")
    assert len(messages) == 1
    assert messages[0].endswith("test message")
