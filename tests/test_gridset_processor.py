import os
import shutil
import zipfile

from lxml import etree as et

from aac_processors.gridset_processor import GridsetProcessor


def test_can_process() -> None:
    processor = GridsetProcessor()
    assert processor.can_process("test.gridset")
    assert not processor.can_process("test.txt")


def test_load_tree(test_gridset: str) -> None:
    processor = GridsetProcessor()
    tree = processor.load_into_tree(test_gridset)

    # Verify regular grid
    assert len(tree.pages) == 2  # Two grids

    # Find regular grid
    grid_page = next(p for p in tree.pages.values() if p.name == "Test Grid")
    assert grid_page.grid_size == (2, 2)

    # Verify button
    assert len(grid_page.buttons) == 1
    button = grid_page.buttons[0]
    assert button.label == "Test Button"
    assert button.position == (0, 0)

    # Find wordlist grid
    wordlist_page = next(p for p in tree.pages.values() if p.name == "Test List")
    assert len(wordlist_page.buttons) == 1
    assert wordlist_page.buttons[0].label == "Test Word"


def test_save_tree(test_gridset: str, temp_dir: str) -> None:
    processor = GridsetProcessor()
    tree = processor.load_into_tree(test_gridset)

    # Save tree to new file
    output_path = os.path.join(temp_dir, "output.gridset")
    processor.save_from_tree(tree, output_path)

    # Verify the saved file
    assert os.path.exists(output_path)

    # Extract and check contents
    with zipfile.ZipFile(output_path, "r") as zip_ref:
        # Check first grid
        zip_ref.extract("Grids/Test Grid/grid.xml", temp_dir)
        grid_path = os.path.join(temp_dir, "Grids/Test Grid/grid.xml")

        grid_tree = et.parse(grid_path)
        grid_root = grid_tree.getroot()

        # Check grid name
        assert grid_root.get("Name") == "Test Grid"

        # Check button
        cell = grid_root.find(".//Cell")
        assert cell is not None
        caption = cell.find(".//CaptionAndImage/Caption")
        assert caption is not None
        assert caption.text == "Test Button"

        # Check wordlist grid
        zip_ref.extract("Grids/Test List/grid.xml", temp_dir)
        wordlist_path = os.path.join(temp_dir, "Grids/Test List/grid.xml")

        wordlist_tree = et.parse(wordlist_path)
        wordlist_root = wordlist_tree.getroot()

        # Check wordlist name
        assert wordlist_root.get("Name") == "Test List"

        # Check word
        text = wordlist_root.find(".//WordList/Items/WordListItem/Text")
        assert text is not None
        assert text.text == "Test Word"


def test_translation(test_gridset, temp_dir):
    processor = GridsetProcessor()

    # Extract texts
    texts = processor.extract_texts(test_gridset)
    assert "Test Button" in texts
    assert "Test Word" in texts

    # Create translations
    translations = {
        "Test Button": "Botón de Prueba",
        "Test Word": "Palabra de Prueba",
        "target_lang": "es",
    }

    # Create translated file
    result = processor.create_translated_file(test_gridset, translations)
    assert result is not None

    # Verify translations
    tree = processor.load_into_tree(result)

    # Check regular grid translation
    grid_page = next(p for p in tree.pages.values() if p.name == "Test Grid")
    assert grid_page.buttons[0].label == "Botón de Prueba"

    # Check wordlist translation
    wordlist_page = next(p for p in tree.pages.values() if p.name == "Test List")
    assert wordlist_page.buttons[0].label == "Palabra de Prueba"


def test_gridset_workflow(test_gridset, temp_dir):
    """Test the complete workflow as it happens in app.py"""
    processor = GridsetProcessor()

    # Set up debug logging like app.py does
    import logging

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    processor._debug_output = logger.debug

    try:
        # Create a separate working directory
        work_dir = os.path.join(temp_dir, "work")
        os.makedirs(work_dir)

        # Copy test file to work dir (like app.py does with uploaded file)
        test_file = os.path.join(work_dir, "test.gridset")
        shutil.copy2(test_gridset, test_file)

        # First phase: Extract texts
        texts = processor.process_texts(test_file)
        assert texts is not None and len(texts) > 0, "No texts found to translate"
        logger.debug(f"Extracted texts: {texts}")

        # Verify file paths after extraction
        assert (
            processor.file_path == test_file
        ), "File path not set correctly after extraction"
        assert (
            processor.original_file_path == test_file
        ), "Original file path not set correctly"

        # Second phase: Translate texts
        # Create translations for each text
        translations = {}
        for i, text in enumerate(texts):
            translations[text] = f"Translated_{i}"
        translations["target_lang"] = "es"
        logger.debug(f"Created translations: {translations}")

        # Construct output path like app.py does
        output_path = os.path.join(
            work_dir, f"{os.path.splitext(os.path.basename(test_file))[0]}_es.gridset"
        )
        result = processor.process_texts(test_file, translations, output_path)

        # Verify translation succeeded
        assert result is not None, "Translation failed"
        assert os.path.exists(output_path), f"Output file not created at {output_path}"
        assert processor.file_path == test_file, "File path changed during translation"
        assert processor.original_file_path == test_file, "Original file path changed"

        # Verify the output file is a valid gridset
        assert output_path.endswith(".gridset"), "Output file has wrong extension"
        assert processor.check_is_archive(
            output_path
        ), "Output file is not a valid archive"

        # Clean up
        if os.path.exists(output_path):
            os.remove(output_path)

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
