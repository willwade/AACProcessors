import os
import tempfile
import pytest
import json
import zipfile
from aac_processors.file_processor import FileProcessor
from aac_processors.tree_structure import AACTree, AACPage, AACButton, ButtonType


class TestFileProcessor(FileProcessor):
    """Test implementation of FileProcessor"""
    def can_process(self, file_path: str) -> bool:
        return file_path.endswith(".test")

    def process_files(self, directory: str, translations=None) -> str | None:
        modified = False
        if translations:
            # Find and process all test files
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(".test"):
                        input_path = os.path.join(root, file)
                        try:
                            with open(input_path, "r") as f:
                                content = json.load(f)
                            
                            # Apply translations
                            if "text" in content and content["text"] in translations:
                                content["text"] = translations[content["text"]]
                                modified = True
                            
                            # Write translated content
                            with open(input_path, "w") as f:
                                json.dump(content, f)
                        except json.JSONDecodeError:
                            # Handle non-JSON content
                            with open(input_path, "r") as f:
                                content = f.read()
                            if content in translations:
                                with open(input_path, "w") as f:
                                    f.write(translations[content])
                                modified = True
        
        if modified:
            # Return the directory path for archive processing
            return directory
        return None

    def load_into_tree(self, file_path: str) -> AACTree:
        tree = AACTree()
        page = AACPage("test", "Test Page", (2, 2))
        page.buttons.append(
            AACButton("btn1", "Test", ButtonType.SPEAK, (0, 0))
        )
        tree.add_page(page)
        return tree

    def save_from_tree(self, tree: AACTree, output_path: str) -> None:
        with open(output_path, "w") as f:
            json.dump({"pages": len(tree.pages)}, f)


@pytest.fixture
def processor():
    return TestFileProcessor()


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
            zf.writestr("test.test", "test content")
    yield f.name
    os.unlink(f.name)


def test_init(processor):
    """Test initialization"""
    assert processor._temp_dirs == []
    assert processor._debug_output is not None
    assert processor.collected_texts == []
    assert processor.file_path is None
    assert processor.original_filename is None


def test_debug_output(processor):
    """Test debug output functionality"""
    messages = []
    processor._debug_output = messages.append
    processor.debug("test message")
    assert len(messages) == 1
    assert "test message" in messages[0]


def test_create_and_cleanup_temp_dir(processor):
    """Test temporary directory creation and cleanup"""
    temp_dir = processor.create_temp_dir()
    assert os.path.exists(temp_dir)
    assert temp_dir in processor._temp_dirs
    processor.cleanup()
    assert not os.path.exists(temp_dir)
    assert len(processor._temp_dirs) == 0


def test_get_output_path(processor, temp_test_file):
    """Test output path generation"""
    processor.file_path = temp_test_file
    processor.original_filename = "test"
    output_path = processor.get_output_path("es")
    assert output_path.endswith("_es.test")


def test_get_output_path_with_existing_lang(processor):
    """Test output path generation with existing language code"""
    processor.file_path = "/path/to/file_en.test"
    processor.original_filename = "file_en"
    output_path = processor.get_output_path("es")
    assert output_path.endswith("file_es.test")
    assert "_en_es" not in output_path


def test_check_is_archive(processor, temp_zip_file, temp_test_file):
    """Test archive detection"""
    assert processor.check_is_archive(temp_zip_file) is True
    assert processor.check_is_archive(temp_test_file) is False
    assert processor.check_is_archive(None) is False


def test_extract_archive(processor, temp_zip_file):
    """Test archive extraction"""
    temp_dir = processor.create_temp_dir()
    processor.extract_archive(temp_zip_file, temp_dir)
    assert "test.txt" in os.listdir(temp_dir)
    assert "test.test" in os.listdir(temp_dir)


def test_create_archive(processor):
    """Test archive creation"""
    temp_dir = processor.create_temp_dir()
    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test content")

    output_zip = os.path.join(temp_dir, "output.zip")
    processor.create_archive(temp_dir, output_zip)

    assert os.path.exists(output_zip)
    with zipfile.ZipFile(output_zip, "r") as zf:
        assert "test.txt" in zf.namelist()


def test_process_texts_extract(processor, temp_test_file):
    """Test text extraction mode"""
    result = processor.process_texts(temp_test_file)
    assert result == []  # Our test implementation doesn't collect texts


def test_process_texts_translate(processor, temp_test_file):
    """Test translation mode"""
    translations = {"test": "prueba"}
    # Write JSON content to the test file
    with open(temp_test_file, "w") as f:
        json.dump({"text": "test"}, f)
    
    output_path = os.path.join(os.path.dirname(temp_test_file), "output.test")
    result = processor.process_texts(temp_test_file, translations, output_path)
    assert result == output_path
    with open(result) as f:
        saved = json.load(f)
    assert saved["text"] == "prueba"


def test_process_texts_archive(processor, temp_zip_file):
    """Test processing archive file"""
    translations = {"test content": "prueba"}
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as output:
        result = processor.process_texts(temp_zip_file, translations, output.name)
        assert result == output.name
        
        # Verify the translated content
        with zipfile.ZipFile(result, "r") as zf:
            # Check test.test file
            with zf.open("test.test") as f:
                content = f.read().decode("utf-8")
                assert content == "prueba"
            # Check that test.txt is unchanged
            with zf.open("test.txt") as f:
                content = f.read().decode("utf-8")
                assert content == "test content"


def test_sanitize_name(processor):
    """Test name sanitization"""
    assert processor._sanitize_name("Hello World!") == "hello_world"
    assert processor._sanitize_name("Test-123") == "test_123"
    assert processor._sanitize_name("___test___") == "test"
    assert processor._sanitize_name("") == ""
    assert processor._sanitize_name(None) == ""
