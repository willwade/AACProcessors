import os
import re
from typing import Optional

from aac_processors.dot_processor import DotProcessor
from aac_processors.tree_structure import ButtonType


def test_can_process() -> None:
    processor = DotProcessor()
    assert processor.can_process("test.dot")
    assert processor.can_process("test.gv")
    assert not processor.can_process("test.txt")


def test_load_tree(test_dot_file: str) -> None:
    processor = DotProcessor()
    tree = processor.load_into_tree(test_dot_file)

    # Verify pages
    assert len(tree.pages) == 4  # Four nodes

    # Find home page
    home_page = next(p for p in tree.pages.values() if p.name == "Home Page")
    assert len(home_page.buttons) == 3  # Three outgoing edges

    # Verify buttons
    button_labels = [b.label for b in home_page.buttons]
    assert "Go to About" in button_labels
    assert "Go to Contact" in button_labels
    assert "View Products" in button_labels

    # Check button types
    for button in home_page.buttons:
        assert button.type == ButtonType.NAVIGATE


def test_save_tree(test_dot_file: str, temp_dir: str) -> None:
    processor = DotProcessor()
    tree = processor.load_into_tree(test_dot_file)

    # Save tree to new file
    output_path = os.path.join(temp_dir, "output.dot")
    processor.save_from_tree(tree, output_path)

    # Verify the saved file
    assert os.path.exists(output_path)

    # Check content
    with open(output_path, "r") as f:
        content = f.read()
    
    # Verify nodes
    assert re.search(r'node\d+\s*\[\s*label\s*=\s*"Home Page"\s*\]', content)
    assert re.search(r'node\d+\s*\[\s*label\s*=\s*"About"\s*\]', content)
    assert re.search(r'node\d+\s*\[\s*label\s*=\s*"Contact"\s*\]', content)
    assert re.search(r'node\d+\s*\[\s*label\s*=\s*"Products"\s*\]', content)
    
    # Verify edges
    assert re.search(r'node\d+\s*->\s*node\d+\s*\[\s*label\s*=\s*"Go to About"\s*\]', content)
    assert re.search(r'node\d+\s*->\s*node\d+\s*\[\s*label\s*=\s*"Go to Contact"\s*\]', content)
    assert re.search(r'node\d+\s*->\s*node\d+\s*\[\s*label\s*=\s*"View Products"\s*\]', content)


def test_translation(test_dot_file: str, temp_dir: str) -> None:
    processor = DotProcessor()

    # Extract texts
    texts = processor.extract_texts(test_dot_file)
    assert "Home Page" in texts
    assert "About" in texts
    assert "Contact" in texts
    assert "Products" in texts
    assert "Go to About" in texts
    assert "Go to Contact" in texts
    assert "View Products" in texts
    assert "Back to Home" in texts

    # Create translations
    translations = {
        "Home Page": "Página Principal",
        "About": "Acerca de",
        "Contact": "Contacto",
        "Products": "Productos",
        "Go to About": "Ir a Acerca de",
        "Go to Contact": "Ir a Contacto",
        "View Products": "Ver Productos",
        "Back to Home": "Volver a Inicio",
        "target_lang": "es",
    }

    # Create translated file
    output_path = os.path.join(temp_dir, "translated.dot")
    result = processor.process_texts(test_dot_file, translations, output_path)
    assert result is not None

    # Verify translations
    with open(result, "r") as f:
        content = f.read()
    
    # Check translated content
    assert "Página Principal" in content
    assert "Acerca de" in content
    assert "Contacto" in content
    assert "Productos" in content
    assert "Ir a Acerca de" in content
    assert "Ir a Contacto" in content
    assert "Ver Productos" in content
    assert "Volver a Inicio" in content


def test_dot_workflow(test_dot_file: str, temp_dir: str) -> None:
    """Test the complete workflow as it happens in app.py"""
    processor = DotProcessor()

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
        test_file = os.path.join(work_dir, "test.dot")
        import shutil
        shutil.copy2(test_dot_file, test_file)

        # First phase: Extract texts
        texts = processor.process_texts(test_file)
        assert texts is not None and len(texts) > 0, "No texts found to translate"
        logger.debug(f"Extracted texts: {texts}")

        # Verify file paths after extraction
        assert processor.file_path == test_file, "File path not set correctly after extraction"
        assert processor.original_file_path == test_file, "Original file path not set correctly"

        # Second phase: Translate texts
        # Create translations for each text
        translations = {}
        for i, text in enumerate(texts):
            translations[text] = f"Translated_{i}"
        translations["target_lang"] = "es"
        logger.debug(f"Created translations: {translations}")

        # Construct output path
        output_path = os.path.join(
            work_dir, f"{os.path.splitext(os.path.basename(test_file))[0]}_es.dot"
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


def test_prag_dot_file() -> None:
    """Test parsing the prag.dot example file which has node names with spaces."""
    # Path to the example file
    example_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "examples", "demofiles", "prag.dot"
    )
    
    # Verify the file exists
    assert os.path.exists(example_file), f"Example file not found: {example_file}"
    
    # Parse the file
    processor = DotProcessor()
    tree = processor.load_into_tree(example_file)
    
    # Verify the number of pages (nodes)
    assert len(tree.pages) > 0, "No pages found in the tree"
    
    # Print all node names for debugging
    node_names = list(tree.pages.keys())
    print(f"All node names: {node_names}")
    
    # Find nodes with 'like' in the name
    like_nodes = [name for name in node_names if 'like' in name.lower()]
    print(f"Nodes with 'like': {like_nodes}")
    
    # Find nodes with apostrophes
    apostrophe_nodes = [name for name in node_names if "'" in name]
    print(f"Nodes with apostrophes: {apostrophe_nodes}")
    
    # Find nodes with "don't" in the name (regardless of apostrophe type)
    dont_nodes = [name for name in node_names if "don" in name.lower() and "t" in name.lower()]
    print(f"Nodes with 'don't': {dont_nodes}")
    
    # Verify that nodes with spaces are correctly parsed
    assert "I have something to say" in tree.pages, "Node with spaces not found"
    assert "Quick Messages" in tree.pages, "Node with spaces not found"
    
    # Check for the node with "don't like" using a fuzzy match
    dont_like_node_exists = any("don" in name.lower() and "like" in name.lower() for name in node_names)
    assert dont_like_node_exists, "Node with 'don't like' not found"
    
    # Verify that edges between nodes with spaces are correctly parsed
    quick_messages_page = tree.pages["Quick Messages"]
    assert any(b.target_page_id == "more" for b in quick_messages_page.buttons), \
        "Edge to 'more' not found"
    assert any(b.target_page_id == "finish" for b in quick_messages_page.buttons), \
        "Edge to 'finish' not found"
    
    # Verify that a node with a complex name is correctly parsed
    complex_node = "I want to do what the others are doing"
    assert complex_node in tree.pages, "Complex node name not found"
    
    # Test saving the tree to a new file
    temp_dir = os.path.dirname(example_file)
    output_path = os.path.join(temp_dir, "prag_output.dot")
    processor.save_from_tree(tree, output_path)
    
    # Verify the saved file exists
    assert os.path.exists(output_path), f"Output file not created: {output_path}"
    
    # Load the saved file and verify it has the same structure
    new_tree = processor.load_into_tree(output_path)
    assert len(new_tree.pages) == len(tree.pages), \
        "Number of pages doesn't match after save/load"
    
    # Clean up
    if os.path.exists(output_path):
        os.remove(output_path)
