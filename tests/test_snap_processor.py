import logging
import os
import shutil
import sqlite3

from aac_processors.snap_processor import SnapProcessor
from aac_processors.tree_structure import ButtonType


def test_can_process(temp_dir):
    processor = SnapProcessor()
    assert processor.can_process("test.sps")
    assert processor.can_process("test.spb")
    assert not processor.can_process("test.txt")


def test_load_tree(test_snap_db):
    processor = SnapProcessor()
    tree = processor.load_into_tree(test_snap_db)

    assert len(tree.pages) == 2
    assert "Test Page" in [p.name for p in tree.pages.values()]
    assert "Second Page" in [p.name for p in tree.pages.values()]

    # Find main page
    main_page = next(p for p in tree.pages.values() if p.name == "Test Page")
    assert len(main_page.buttons) == 2

    # Check speak button
    speak_button = next(b for b in main_page.buttons if b.type == ButtonType.SPEAK)
    assert speak_button.label == "Speak Button"
    assert speak_button.vocalization == "Hello"

    # Check navigate button
    nav_button = next(b for b in main_page.buttons if b.type == ButtonType.NAVIGATE)
    assert nav_button.label == "Navigate"
    assert nav_button.target_page_id == "2"


def test_save_tree(test_snap_db, temp_dir):
    processor = SnapProcessor()
    tree = processor.load_into_tree(test_snap_db)

    # Save tree to new file
    output_path = os.path.join(temp_dir, "output.sps")
    processor.save_from_tree(tree, output_path)

    # Verify the saved file
    assert os.path.exists(output_path)

    # Check database contents
    with sqlite3.connect(output_path) as conn:
        cursor = conn.cursor()

        # Check pages
        cursor.execute("SELECT Title FROM Page")
        pages = cursor.fetchall()
        assert len(pages) == 2
        page_titles = [p[0] for p in pages]
        assert "Test Page" in page_titles
        assert "Second Page" in page_titles

        # Check buttons
        cursor.execute(
            """
            SELECT Label, Message
            FROM Button
            WHERE Label = 'Speak Button'
        """
        )
        button = cursor.fetchone()
        assert button is not None
        assert button[0] == "Speak Button"
        assert button[1] == "Hello"

        # Check navigation
        cursor.execute(
            """
            SELECT b.Label, ba.action_type, ba.target_page_id
            FROM Button b
            JOIN ButtonAction ba ON b.id = ba.button_id
            WHERE b.Label = 'Go to Page 2'
        """
        )
        nav = cursor.fetchone()
        assert nav is not None
        assert nav[1] == "navigate"


def test_translation(test_snap_db):
    processor = SnapProcessor()

    # Extract texts
    texts = processor.extract_texts(test_snap_db)
    assert "Speak Button" in texts
    assert "Navigate" in texts
    assert "Test Page" in texts


def test_process_workflow(test_snap_db, temp_dir):
    """Test the complete workflow as it happens in app.py"""
    processor = SnapProcessor()

    # Set up debug logging like app.py does
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    processor._debug_output = logger.debug

    try:
        # Create a separate working directory
        work_dir = os.path.join(temp_dir, "work")
        os.makedirs(work_dir)

        # Copy test file to work dir (like app.py does with uploaded file)
        test_file = os.path.join(work_dir, "test.spb")
        shutil.copy2(test_snap_db, test_file)

        # First phase: Extract texts
        texts = processor.process_texts(test_file)
        assert texts is not None and len(texts) > 0, "No texts found to translate"
        logger.debug(f"Extracted texts: {texts}")

        # Verify file paths after extraction
        assert (
            processor.file_path == test_file
        ), "File path not set correctly after extraction"

        # Second phase: Translate texts
        translations = {
            "Speak Button": "Botón de Hablar",
            "Hello": "Hola",
            "Go to Page 2": "Ir a Página 2",
            "target_lang": "es",
        }
        logger.debug(f"Created translations: {translations}")

        # Construct output path like app.py does
        output_path = os.path.join(
            work_dir, f"{os.path.splitext(os.path.basename(test_file))[0]}_es.spb"
        )
        result = processor.process_texts(test_file, translations, output_path)

        # Verify translation succeeded
        assert result is not None, "Translation failed"
        assert os.path.exists(output_path), f"Output file not created at {output_path}"
        assert processor.file_path == test_file, "File path changed during translation"

        # Verify the output file is a valid SQLite database
        with sqlite3.connect(output_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT Label FROM Button WHERE Label = 'Botón de Hablar'")
            assert cursor.fetchone() is not None, "Translation not found in database"

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
