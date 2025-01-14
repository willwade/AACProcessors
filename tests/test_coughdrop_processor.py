import json
import os
import tempfile
import zipfile

import pytest

from aac_processors.coughdrop_processor import CoughDropProcessor
from aac_processors.tree_structure import ButtonType


@pytest.fixture
def processor():
    return CoughDropProcessor()


@pytest.fixture
def sample_obf_data():
    return {
        "format": "open-board-0.1",
        "id": "test_board",
        "locale": "en",
        "name": "Test Board",
        "grid": {
            "rows": 2,
            "columns": 2,
            "order": [["btn1", "btn2"], ["btn3", "btn4"]],
        },
        "buttons": [
            {
                "id": "btn1",
                "label": "Hello",
                "vocalization": "Hello there!",
                "image_id": "img1",
            },
            {
                "id": "btn2",
                "label": "More",
                "load_board": {"id": "board2", "path": "boards/board2.obf"},
            },
            {"id": "btn3", "label": "Clear", "action": ":clear"},
            {"id": "btn4", "label": "A", "action": "+a"},
        ],
        "images": [
            {
                "id": "img1",
                "url": "http://example.com/hello.png",
                "width": 300,
                "height": 300,
                "content_type": "image/png",
            }
        ],
    }


@pytest.fixture
def sample_obf_file(sample_obf_data):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".obf", delete=False) as f:
        json.dump(sample_obf_data, f)
    yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_obz_file(sample_obf_data):
    with tempfile.NamedTemporaryFile(suffix=".obz", delete=False) as f:
        with zipfile.ZipFile(f.name, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add manifest
            manifest = {
                "format": "open-board-0.1",
                "root": "boards/test_board.obf",
                "paths": {
                    "boards": {
                        "test_board": "boards/test_board.obf",
                        "board2": "boards/board2.obf",
                    }
                },
            }
            zf.writestr("manifest.json", json.dumps(manifest))

            # Add main board
            zf.writestr("boards/test_board.obf", json.dumps(sample_obf_data))

            # Add secondary board
            board2_data = {
                "format": "open-board-0.1",
                "id": "board2",
                "name": "Second Board",
                "grid": {"rows": 1, "columns": 1},
                "buttons": [
                    {
                        "id": "btn1",
                        "label": "Back",
                        "load_board": {
                            "id": "test_board",
                            "path": "boards/test_board.obf",
                        },
                    }
                ],
            }
            zf.writestr("boards/board2.obf", json.dumps(board2_data))
    yield f.name
    os.unlink(f.name)


def test_can_process(processor):
    """Test file type detection"""
    assert processor.can_process("test.obf") is True
    assert processor.can_process("test.obz") is True
    assert processor.can_process("test.txt") is False


def test_load_single_board(processor, sample_obf_file):
    """Test loading a single OBF file"""
    tree = processor.load_into_tree(sample_obf_file)

    assert len(tree.pages) == 1
    page = tree.pages["test_board"]
    assert page.name == "Test Board"
    assert page.grid_size == (2, 2)
    assert len(page.buttons) == 4

    # Check button types and properties
    speak_btn = next(b for b in page.buttons if b.id == "btn1")
    assert speak_btn.type == ButtonType.SPEAK
    assert speak_btn.label == "Hello"
    assert speak_btn.vocalization == "Hello there!"

    nav_btn = next(b for b in page.buttons if b.id == "btn2")
    assert nav_btn.type == ButtonType.NAVIGATE
    assert nav_btn.label == "More"
    assert nav_btn.target_page_id == "board2"

    action_btn = next(b for b in page.buttons if b.id == "btn3")
    assert action_btn.type == ButtonType.ACTION
    assert action_btn.label == "Clear"
    assert action_btn.action == ":clear"

    spell_btn = next(b for b in page.buttons if b.id == "btn4")
    assert spell_btn.type == ButtonType.ACTION
    assert spell_btn.label == "A"
    assert spell_btn.action == "+a"


def test_load_board_set(processor, sample_obz_file):
    """Test loading an OBZ file with multiple boards"""
    tree = processor.load_into_tree(sample_obz_file)

    assert len(tree.pages) == 2
    assert "test_board" in tree.pages
    assert "board2" in tree.pages

    # Check main board
    main_page = tree.pages["test_board"]
    assert main_page.name == "Test Board"
    assert len(main_page.buttons) == 4

    # Check secondary board
    second_page = tree.pages["board2"]
    assert second_page.name == "Second Board"
    assert len(second_page.buttons) == 1
    back_btn = second_page.buttons[0]
    assert back_btn.type == ButtonType.NAVIGATE
    assert back_btn.target_page_id == "test_board"


def test_extract_texts(processor, sample_obf_file):
    """Test text extraction from OBF file"""
    texts = processor.extract_texts(sample_obf_file)
    expected = ["Test Board", "Hello", "Hello there!", "More", "Clear", "A"]
    assert sorted(texts) == sorted(expected)


def test_create_translated_file(processor, sample_obf_file):
    """Test translation of OBF file"""
    translations = {
        "Test Board": "Tablero de Prueba",
        "Hello": "Hola",
        "Hello there!": "¡Hola!",
        "More": "Más",
        "Clear": "Borrar",
        "A": "A",
        "target_lang": "es",
    }

    result = processor.create_translated_file(sample_obf_file, translations)
    assert result is not None

    # Load and verify translated file
    tree = processor.load_into_tree(result)
    page = tree.pages["test_board"]
    assert page.name == "Tablero de Prueba"

    hello_btn = next(b for b in page.buttons if b.id == "btn1")
    assert hello_btn.label == "Hola"
    assert hello_btn.vocalization == "¡Hola!"


def test_process_texts_obz(processor, sample_obz_file):
    """Test processing texts in OBZ file"""
    # Test extraction
    texts = processor.process_texts(sample_obz_file)
    assert isinstance(texts, list)
    assert "Test Board" in texts
    assert "Second Board" in texts
    assert "Back" in texts

    # Test translation
    translations = {
        "Test Board": "Tablero de Prueba",
        "Second Board": "Segundo Tablero",
        "Back": "Volver",
        "target_lang": "es",
    }

    with tempfile.NamedTemporaryFile(suffix=".obz") as output:
        result = processor.process_texts(sample_obz_file, translations, output.name)
        assert result == output.name

        # Verify translated file
        with zipfile.ZipFile(output.name, "r") as zf:
            assert "manifest.json" in zf.namelist()
            assert "boards/test_board.obf" in zf.namelist()
            assert "boards/board2.obf" in zf.namelist()

            # Check main board translation
            main_board = json.loads(zf.read("boards/test_board.obf"))
            assert main_board["name"] == "Tablero de Prueba"

            # Check second board translation
            board2 = json.loads(zf.read("boards/board2.obf"))
            assert board2["name"] == "Segundo Tablero"
            assert board2["buttons"][0]["label"] == "Volver"
