import os
import shutil

import pytest

from aac_processors.dot_processor import DotProcessor
from aac_processors.tree_structure import AACButton, AACPage, ButtonType


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

    # Find home page by node label
    home_page = next((p for p in tree.pages.values() if p.name == "Home Page"), None)
    assert home_page is not None
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
    import os

    processor = DotProcessor()
    tree = processor.load_into_tree(test_dot_file)

    # Save tree to new file
    output_path = os.path.join(temp_dir, "output.dot")
    processor.save_from_tree(tree, output_path)

    # Verify the saved file
    assert os.path.exists(output_path)

    # Check content
    with open(output_path) as f:
        content = f.read()

    # The node IDs might be different now, but the labels should be present
    assert 'label="Home Page"' in content
    assert 'label="About"' in content
    assert 'label="Contact"' in content
    assert 'label="Products"' in content

    # Verify edges - check for the labels which should be in the file
    assert 'label="Go to About"' in content
    assert 'label="Go to Contact"' in content
    assert 'label="View Products"' in content
    assert 'label="Back to Home"' in content


@pytest.mark.slow
def test_translation(test_dot_file: str, temp_dir: str) -> None:
    """Test translation of DOT file"""
    processor = DotProcessor()

    # Extract texts
    texts = processor.extract_texts(test_dot_file)

    # Check extracted texts
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
    }

    # Process translations
    output_path = os.path.join(temp_dir, "translated.dot")
    result = processor.process_texts(test_dot_file, translations, output_path)

    # Check result
    assert result
    assert os.path.exists(output_path)

    # Verify translated content
    with open(output_path) as f:
        content = f.read()

    assert "Página Principal" in content
    assert "Acerca de" in content
    assert "Contacto" in content
    assert "Productos" in content
    assert "Ir a Acerca de" in content
    assert "Ir a Contacto" in content
    assert "Ver Productos" in content
    assert "Volver a Inicio" in content


@pytest.mark.integration
def test_dot_workflow(test_dot_file: str, temp_dir: str) -> None:
    """Test full workflow with DOT files"""
    import os

    # Setup
    processor = DotProcessor()
    test_file = os.path.join(temp_dir, "test_workflow.dot")
    output_file = os.path.join(temp_dir, "output_workflow.dot")

    # Copy test file
    shutil.copy2(test_dot_file, test_file)

    # Load into tree
    tree = processor.load_into_tree(test_file)
    assert tree is not None

    # Modify tree
    new_page_id = "new_page"
    new_page = AACPage(id=new_page_id, name="New Page", grid_size=(3, 3))
    tree.add_page(new_page)

    # Get home page by node label
    home_page = next((p for p in tree.pages.values() if p.name == "Home Page"), None)
    assert home_page is not None

    # Add button to home page
    new_button = AACButton(
        id="new_button",
        label="Go to New Page",
        type=ButtonType.NAVIGATE,
        target_page_id=new_page_id,
    )
    home_page.buttons.append(new_button)

    # Save modified tree
    processor.save_from_tree(tree, output_file)

    # Verify output
    assert os.path.exists(output_file)

    # Load modified tree
    modified_tree = processor.load_into_tree(output_file)
    assert modified_tree is not None

    # Verify new page exists
    assert "New Page" in [p.name for p in modified_tree.pages.values()]

    # Verify new button exists
    new_home_page = next(
        (p for p in modified_tree.pages.values() if p.name == "Home Page"), None
    )
    assert new_home_page is not None
    assert "Go to New Page" in [b.label for b in new_home_page.buttons]
