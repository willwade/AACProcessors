import os
import json
import zipfile
from aac_processors.coughdrop_processor import CoughDropProcessor
from aac_processors.tree_structure import ButtonType


def test_can_process():
    processor = CoughDropProcessor()
    assert processor.can_process("test.obf")
    assert processor.can_process("test.obz")
    assert not processor.can_process("test.txt")


def test_load_tree_obf(test_coughdrop_obf):
    processor = CoughDropProcessor()
    tree = processor.load_into_tree(test_coughdrop_obf)

    assert len(tree.pages) == 1
    page = next(iter(tree.pages.values()))
    assert page.name == "Test Board"
    assert page.grid_size == (2, 2)

    assert len(page.buttons) == 2
    speak_button = next(b for b in page.buttons if b.type == ButtonType.SPEAK)
    assert speak_button.label == "Test Button"
    assert speak_button.vocalization == "Hello"

    nav_button = next(b for b in page.buttons if b.type == ButtonType.NAVIGATE)
    assert nav_button.label == "Navigate"
    assert nav_button.target_page_id == "page2"


def test_load_tree_obz(test_coughdrop_obz):
    processor = CoughDropProcessor()
    tree = processor.load_into_tree(test_coughdrop_obz)

    assert len(tree.pages) == 1
    page = next(iter(tree.pages.values()))
    assert page.name == "Test Board"
    assert page.grid_size == (2, 2)

    assert len(page.buttons) == 2
    speak_button = next(b for b in page.buttons if b.type == ButtonType.SPEAK)
    assert speak_button.label == "Test Button"
    assert speak_button.vocalization == "Hello"

    nav_button = next(b for b in page.buttons if b.type == ButtonType.NAVIGATE)
    assert nav_button.label == "Navigate"
    assert nav_button.target_page_id == "page2"


def test_save_tree_obf(test_coughdrop_obf, temp_dir):
    processor = CoughDropProcessor()
    tree = processor.load_into_tree(test_coughdrop_obf)

    # Save tree to new file
    output_path = os.path.join(temp_dir, "output.obf")
    processor.save_from_tree(tree, output_path)

    # Verify the saved file
    assert os.path.exists(output_path)

    # Check contents
    with open(output_path, "r") as f:
        board_data = json.load(f)
        assert board_data["name"] == "Test Board"
        assert board_data["grid"]["rows"] == 2
        assert board_data["grid"]["columns"] == 2
        assert len(board_data["buttons"]) == 2
        assert board_data["buttons"][0]["label"] == "Test Button"


def test_save_tree_obz(test_coughdrop_obz, temp_dir):
    processor = CoughDropProcessor()
    tree = processor.load_into_tree(test_coughdrop_obz)

    # Save tree to new file
    output_path = os.path.join(temp_dir, "output.obz")
    processor.save_from_tree(tree, output_path)

    # Verify the saved file
    assert os.path.exists(output_path)

    # Extract and check contents
    with zipfile.ZipFile(output_path, "r") as zip_ref:
        # Check manifest
        zip_ref.extract("manifest.json", temp_dir)
        manifest_path = os.path.join(temp_dir, "manifest.json")

        with open(manifest_path, "r") as f:
            manifest = json.load(f)
            assert "boards/home.obf" in manifest["paths"]["boards"].values()

        # Check board
        board_path = manifest["paths"]["boards"]["home"]
        zip_ref.extract(board_path, temp_dir)
        board_file = os.path.join(temp_dir, board_path)

        with open(board_file, "r") as f:
            board_data = json.load(f)
            assert board_data["name"] == "Test Board"
            assert len(board_data["buttons"]) == 2
            assert any(b["label"] == "Test Button" for b in board_data["buttons"])
            assert any(b["label"] == "Navigate" for b in board_data["buttons"])


def test_translation_obf(test_coughdrop_obf, temp_dir):
    processor = CoughDropProcessor()

    # Extract texts
    texts = processor.extract_texts(test_coughdrop_obf)
    assert "Test Button" in texts
    assert "Hello" in texts

    # Create translations
    translations = {
        "Test Button": "Botón de Prueba", 
        "Hello": "Hola",
        "target_lang": "es"
    }

    # Create translated file
    output_path = os.path.join(temp_dir, f"{os.path.splitext(os.path.basename(test_coughdrop_obf))[0]}_es.obf")
    result = processor.process_texts(test_coughdrop_obf, translations, output_path)
    assert result is not None, "Translation failed"
    assert os.path.exists(output_path), f"Output file not created at {output_path}"

    # Verify translations
    tree = processor.load_into_tree(output_path)
    page = next(iter(tree.pages.values()))
    button = page.buttons[0]
    assert button.label == "Botón de Prueba"
    assert button.vocalization == "Hola"


def test_translation_obz(test_coughdrop_obz, temp_dir):
    processor = CoughDropProcessor()

    # Extract texts
    texts = processor.extract_texts(test_coughdrop_obz)
    assert "Test Button" in texts
    assert "Navigate" in texts
    assert "Test Board" in texts

    # Create translations
    translations = {
        "Test Button": "Botón de Prueba",
        "Navigate": "Navegar",
        "Test Board": "Tablero de Prueba",
        "Hello": "Hola",
        "target_lang": "es"
    }

    # Create translated file
    output_path = os.path.join(temp_dir, f"{os.path.splitext(os.path.basename(test_coughdrop_obz))[0]}_es.obz")
    result = processor.process_texts(test_coughdrop_obz, translations, output_path)
    assert result is not None, "Translation failed"
    assert os.path.exists(output_path), f"Output file not created at {output_path}"

    # Verify translations
    tree = processor.load_into_tree(output_path)
    page = next(iter(tree.pages.values()))
    assert page.name == "Tablero de Prueba"

    speak_button = next(b for b in page.buttons if b.type == ButtonType.SPEAK)
    assert speak_button.label == "Botón de Prueba"
    assert speak_button.vocalization == "Hola"

    nav_button = next(b for b in page.buttons if b.type == ButtonType.NAVIGATE)
    assert nav_button.label == "Navegar"


def test_translation(test_coughdrop_obf):
    processor = CoughDropProcessor()

    # Extract texts
    texts = processor.extract_texts(test_coughdrop_obf)
    assert "Test Button" in texts
    assert "Navigate" in texts
    assert "Test Board" in texts
