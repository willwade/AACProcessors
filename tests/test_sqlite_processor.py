import os
import sqlite3
import tempfile

import pytest

from aac_processors.sqlite_processor import SQLiteProcessor
from aac_processors.tree_structure import AACButton, AACPage, ButtonType


class TestSQLiteProcessor(SQLiteProcessor):
    """Test implementation of SQLiteProcessor"""

    def can_process(self, file_path: str) -> bool:
        return file_path.endswith(".db")

    def process_files(self, directory: str, translations=None) -> str:
        if translations:
            return os.path.join(directory, "translated.db")
        return None


@pytest.fixture
def processor():
    return TestSQLiteProcessor()


@pytest.fixture
def test_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        conn = sqlite3.connect(f.name)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                text TEXT
            )
        """
        )
        cursor.execute("INSERT INTO test_table (text) VALUES (?)", ("test text",))
        conn.commit()
        conn.close()
    yield f.name
    os.unlink(f.name)


def test_init(processor):
    """Test initialization"""
    assert processor._db_lock is not None
    assert processor._query_cache == {}
    assert processor._temp_dirs == []
    assert processor.file_path is None


def test_create_temp_dir(processor):
    """Test temporary directory creation"""
    temp_dir = processor.create_temp_dir()
    assert os.path.exists(temp_dir)
    assert temp_dir in processor._temp_dirs
    processor.cleanup()
    assert not os.path.exists(temp_dir)


def test_cleanup(processor):
    """Test cleanup functionality"""
    temp_dir1 = processor.create_temp_dir()
    temp_dir2 = processor.create_temp_dir()
    assert len(processor._temp_dirs) == 2
    processor.cleanup()
    assert len(processor._temp_dirs) == 0
    assert not os.path.exists(temp_dir1)
    assert not os.path.exists(temp_dir2)


def test_execute_query(processor, test_db):
    """Test SQL query execution"""
    processor.file_path = test_db
    results = processor._execute_query("SELECT * FROM test_table")
    assert len(results) == 1
    assert results[0][1] == "test text"


def test_execute_many(processor, test_db):
    """Test batch SQL execution"""
    processor.file_path = test_db
    data = [("text1",), ("text2",)]
    processor._execute_many("INSERT INTO test_table (text) VALUES (?)", data)
    results = processor._execute_query("SELECT text FROM test_table")
    assert len(results) == 3  # Original + 2 new rows
    assert set(r[0] for r in results) == {"test text", "text1", "text2"}


def test_get_output_path(processor, test_db):
    """Test output path generation"""
    processor.file_path = test_db
    output_path = processor.get_output_path("es")
    assert output_path.endswith("_es.db")


def test_get_output_path_no_file(processor):
    """Test output path generation without file path"""
    with pytest.raises(ValueError):
        processor.get_output_path()


def test_convert_page_to_obf(processor):
    """Test page conversion to OBF format"""
    page = AACPage("test_id", "Test Page", (2, 3))
    button = AACButton(
        "btn1", "Test Button", ButtonType.NAVIGATE, (0, 0), target_page_id="target_page"
    )
    page.buttons.append(button)

    obf = processor._convert_page_to_obf(page)
    assert obf["id"] == "test_id"
    assert obf["name"] == "Test Page"
    assert obf["grid"] == {"rows": 2, "columns": 3}
    assert len(obf["buttons"]) == 1
    assert obf["buttons"][0]["id"] == "btn1"
    assert obf["buttons"][0]["load_board"] == {"id": "target_page"}


def test_convert_obf_to_page(processor):
    """Test OBF format conversion to page"""
    obf_data = {
        "id": "test_id",
        "name": "Test Page",
        "grid": {"rows": 2, "columns": 3},
        "buttons": [
            {"id": "btn1", "label": "Test Button", "load_board": {"id": "target_page"}}
        ],
    }

    page = processor._convert_obf_to_page(obf_data)
    assert page.id == "test_id"
    assert page.name == "Test Page"
    assert page.grid_size == (2, 3)
    assert len(page.buttons) == 1
    assert page.buttons[0].id == "btn1"
    assert page.buttons[0].type == ButtonType.NAVIGATE
    assert page.buttons[0].target_page_id == "target_page"


def test_debug_output(processor):
    """Test debug output functionality"""
    messages = []
    processor._debug_output = messages.append

    processor.debug("test message")
    assert len(messages) == 1
    assert "test message" in messages[0]

    processor._debug_print("debug message")
    assert len(messages) == 2
    assert "debug message" in messages[1]
