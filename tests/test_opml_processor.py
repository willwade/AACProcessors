import os
import xml.etree.ElementTree as ET

from aac_processors.opml_processor import OPMLProcessor
from aac_processors.tree_structure import ButtonType


def test_can_process() -> None:
    processor = OPMLProcessor()
    assert processor.can_process("test.opml")
    assert not processor.can_process("test.txt")


def test_load_tree(test_opml_file: str) -> None:
    processor = OPMLProcessor()
    tree = processor.load_into_tree(test_opml_file)

    # Verify pages
    assert len(tree.pages) == 5  # Main page + 2 categories + 4 items

    # Find main page
    main_page = next(p for p in tree.pages.values() if p.name == "Main Page")
    assert len(main_page.buttons) == 2  # Two category buttons

    # Verify category pages
    category1_page = next(p for p in tree.pages.values() if p.name == "Category 1")
    category2_page = next(p for p in tree.pages.values() if p.name == "Category 2")

    assert len(category1_page.buttons) == 2  # Two item buttons
    assert len(category2_page.buttons) == 2  # Two item buttons

    # Check button types
    for button in main_page.buttons:
        assert button.type == ButtonType.NAVIGATE


def test_save_tree(test_opml_file: str, temp_dir: str) -> None:
    processor = OPMLProcessor()
    tree = processor.load_into_tree(test_opml_file)

    # Save tree to new file
    output_path = os.path.join(temp_dir, "output.opml")
    processor.save_from_tree(tree, output_path)

    # Verify the saved file
    assert os.path.exists(output_path)

    # Parse the saved file
    tree_xml = ET.parse(output_path)
    root = tree_xml.getroot()

    # Verify structure
    body = root.find("body")
    assert body is not None

    # Find main outline
    main_outline = body.find("outline")
    assert main_outline is not None
    assert main_outline.get("text") == "Main Page"

    # Find category outlines
    categories = main_outline.findall("outline")
    assert len(categories) == 2

    # Verify category names
    category_names = [cat.get("text") for cat in categories]
    assert "Category 1" in category_names
    assert "Category 2" in category_names

    # Verify items
    for category in categories:
        items = category.findall("outline")
        assert len(items) == 2

        if category.get("text") == "Category 1":
            item_names = [item.get("text") for item in items]
            assert "Item 1" in item_names
            assert "Item 2" in item_names
        elif category.get("text") == "Category 2":
            item_names = [item.get("text") for item in items]
            assert "Item 3" in item_names
            assert "Item 4" in item_names


def test_translation(test_opml_file: str, temp_dir: str) -> None:
    processor = OPMLProcessor()

    # Extract texts
    texts = processor.extract_texts(test_opml_file)
    assert "Main Page" in texts
    assert "Category 1" in texts
    assert "Category 2" in texts
    assert "Item 1" in texts
    assert "Item 2" in texts
    assert "Item 3" in texts
    assert "Item 4" in texts

    # Create translations
    translations = {
        "Main Page": "Página Principal",
        "Category 1": "Categoría 1",
        "Category 2": "Categoría 2",
        "Item 1": "Elemento 1",
        "Item 2": "Elemento 2",
        "Item 3": "Elemento 3",
        "Item 4": "Elemento 4",
        "target_lang": "es",
    }

    # Create translated file
    output_path = os.path.join(temp_dir, "translated.opml")
    result = processor.process_texts(test_opml_file, translations, output_path)
    assert result is not None

    # Verify translations
    tree_xml = ET.parse(result)
    root = tree_xml.getroot()

    # Check main outline
    body = root.find("body")
    main_outline = body.find("outline")
    assert main_outline.get("text") == "Página Principal"

    # Check categories
    categories = main_outline.findall("outline")
    for category in categories:
        if category.get("text") == "Categoría 1":
            items = category.findall("outline")
            assert items[0].get("text") == "Elemento 1"
            assert items[1].get("text") == "Elemento 2"
        elif category.get("text") == "Categoría 2":
            items = category.findall("outline")
            assert items[0].get("text") == "Elemento 3"
            assert items[1].get("text") == "Elemento 4"


def test_opml_workflow(test_opml_file: str, temp_dir: str) -> None:
    """Test the complete workflow as it happens in app.py"""
    processor = OPMLProcessor()

    # Set up debug logging
    import logging

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    processor._debug_output = logger.debug

    try:
        # Create a working directory
        work_dir = os.path.join(temp_dir, "work")
        os.makedirs(work_dir)

        # Copy test file to work dir
        test_file = os.path.join(work_dir, "test.opml")
        import shutil

        shutil.copy2(test_opml_file, test_file)

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

        # Construct output path
        output_path = os.path.join(
            work_dir, f"{os.path.splitext(os.path.basename(test_file))[0]}_es.opml"
        )
        result = processor.process_texts(test_file, translations, output_path)

        # Verify translation succeeded
        assert result is not None, "Translation failed"
        assert os.path.exists(output_path), f"Output file not created at {output_path}"
        assert processor.file_path == test_file, "File path changed during translation"
        assert processor.original_file_path == test_file, "Original file path changed"

        # Clean up
        if os.path.exists(output_path):
            os.remove(output_path)

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
