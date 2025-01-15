import os
import sqlite3
import zipfile

from aac_processors.touchchat_processor import TouchChatProcessor
from aac_processors.tree_structure import ButtonType


def test_can_process():
    processor = TouchChatProcessor()
    assert processor.can_process("test.ce")
    assert not processor.can_process("test.txt")


def test_load_tree(test_touchchat_ce):
    processor = TouchChatProcessor()
    tree = processor.load_into_tree(test_touchchat_ce)

    assert len(tree.pages) == 1
    page = next(iter(tree.pages.values()))
    assert page.name == "Test Page"

    assert len(page.buttons) == 1
    button = page.buttons[0]
    assert button.label == "Test Button"
    assert button.vocalization == "Hello"
    assert button.type == ButtonType.SPEAK


def test_save_tree(test_touchchat_ce, temp_dir):
    processor = TouchChatProcessor()
    tree = processor.load_into_tree(test_touchchat_ce)

    # Save tree to new file
    output_path = os.path.join(temp_dir, "output.ce")
    processor.save_from_tree(tree, output_path)

    # Verify the saved file
    assert os.path.exists(output_path)

    # Extract and check database
    with zipfile.ZipFile(output_path, "r") as zip_ref:
        c4v_path = None
        for name in zip_ref.namelist():
            if name.endswith(".c4v"):
                c4v_path = name
                zip_ref.extract(name, temp_dir)
                break

        assert c4v_path is not None
        db_path = os.path.join(temp_dir, c4v_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT b.label, b.message
                FROM buttons b
                JOIN resources r ON b.resource_id = r.id
                WHERE b.label = 'Test Button'
            """
            )
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "Test Button"
            assert row[1] == "Hello"


def test_translation(test_touchchat_ce, temp_dir):
    processor = TouchChatProcessor()

    print(f"Initial file: {test_touchchat_ce}")
    texts = processor.extract_texts(test_touchchat_ce)
    print(f"Extracted texts: {texts}")

    translations = {"Test Button": "Botón de prueba", "Hello": "Hola"}
    translated_file = processor.process_texts(test_touchchat_ce, translations)
    print(f"Translated file: {translated_file}")

    tree = processor.load_into_tree(translated_file)
    page = next(iter(tree.pages.values()))
    button = page.buttons[0]
    print(f"Button label after translation: {button.label}")


def test_check_is_archive(test_touchchat_ce):
    """Test check_is_archive method."""
    processor = TouchChatProcessor()
    assert processor.check_is_archive(test_touchchat_ce)
    assert not processor.check_is_archive("not_an_archive.txt")
    assert not processor.check_is_archive(None)


def test_extract_archive(test_touchchat_ce, temp_dir):
    """Test extract_archive method."""
    processor = TouchChatProcessor()
    output_dir = os.path.join(temp_dir, "extracted")
    os.makedirs(output_dir)
    processor.extract_archive(test_touchchat_ce, output_dir)
    assert os.path.exists(os.path.join(output_dir, "test.c4v"))


def test_process_workflow(test_touchchat_ce, temp_dir):
    """Test the complete workflow as it happens in app.py"""
    # Create a temp dir like app.py does
    import tempfile

    work_dir = tempfile.mkdtemp()

    # Initialize processor with the work dir
    processor = TouchChatProcessor()
    processor._temp_dirs = [work_dir]  # Use the same temp dir

    # Set up debug logging like app.py does
    import logging

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    # Add a stream handler if none exists
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    processor._debug_output = logger.debug

    try:
        # Copy test file to work dir (like app.py does with uploaded file)
        import shutil

        test_file = os.path.join(work_dir, "test.ce")
        shutil.copy2(test_touchchat_ce, test_file)
        processor.debug(f"Copied test file from {test_touchchat_ce} to {test_file}")

        # Process texts (extraction phase)
        texts = processor.process_texts(test_file)
        assert texts is not None and len(texts) > 0, "No texts found to translate"

        # Verify expected texts are present
        assert "Test Button" in texts
        assert "Hello" in texts

        # Create translations
        translations = {
            "Test Button": "Botón de Prueba",
            "Hello": "Hola",
            "target_lang": "es",
        }

        # Process translations
        output_path = os.path.join(
            work_dir, f"{os.path.splitext(os.path.basename(test_file))[0]}_es.ce"
        )
        result = processor.process_texts(test_file, translations, output_path)
        assert result is not None, "Translation failed"

        # Verify the translated file exists and is not empty
        assert os.path.exists(result), "Translated file does not exist"
        assert os.path.getsize(result) > 0, "Translated file is empty"

    finally:
        # Clean up
        try:
            shutil.rmtree(work_dir)
        except FileNotFoundError:
            pass  # Directory might already be cleaned up
