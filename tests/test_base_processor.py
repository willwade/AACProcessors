import os
import tempfile
from aac_processors.base_processor import AACProcessor
from aac_processors.tree_structure import AACTree, AACPage, AACButton, ButtonType
import zipfile
import json


class TestProcessor(AACProcessor):
    """Test implementation of AACProcessor"""

    def __init__(self):
        self.temp_dirs = []
        self.collected_texts = []
        self.file_path = None
        self.original_filename = None

    def can_process(self, file_path):
        return file_path.endswith(".test")

    def process_texts(self, file_path, translations=None, target_lang=None):
        return []

    def load_into_tree(self, file_path: str) -> AACTree:
        tree = AACTree()
        # Create a simple test tree
        home = AACPage("home", "Home", (2, 2))
        page1 = AACPage("page1", "Page 1", (2, 2))
        home.buttons.append(
            AACButton(
                "btn1", "Test", ButtonType.NAVIGATE, (0, 0), target_page_id="page1"
            )
        )
        tree.add_page(home)
        tree.add_page(page1)
        return tree

    def export_to_obz(self, output_path):
        """Export to OBZ format"""
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
            # Add manifest
            manifest = {"format": "open-board-0.1", "root": "boards/home.obf"}
            zip_ref.writestr("manifest.json", json.dumps(manifest))
            # Add a dummy board file
            zip_ref.writestr("boards/home.obf", "{}")
        return output_path

    def import_from_obz(self, obz_path):
        """Import from OBZ format"""
        tree = AACTree()
        # Create a simple test tree
        home = AACPage("home", "Home", (2, 2))
        page1 = AACPage("page1", "Page 1", (2, 2))
        home.buttons.append(
            AACButton(
                "btn1", "Test", ButtonType.NAVIGATE, (0, 0), target_page_id="page1"
            )
        )
        tree.add_page(home)
        tree.add_page(page1)
        return tree


def test_obz_export():
    """Test exporting to OBZ format"""
    processor = TestProcessor()

    with tempfile.NamedTemporaryFile(suffix=".test") as temp_input:
        processor.file_path = temp_input.name

        with tempfile.NamedTemporaryFile(suffix=".obz") as temp_output:
            output_path = processor.export_to_obz(temp_output.name)

            assert os.path.exists(output_path)
            assert output_path.endswith(".obz")

            # Verify OBZ structure
            with zipfile.ZipFile(output_path, "r") as zip_ref:
                files = zip_ref.namelist()
                assert "manifest.json" in files
                assert any(f.startswith("boards/") for f in files)


def test_obz_import():
    """Test importing from OBZ format"""
    processor = TestProcessor()

    # First create a test OBZ file
    with tempfile.NamedTemporaryFile(suffix=".obz", delete=False) as temp_obz:
        processor.export_to_obz(temp_obz.name)

        # Now import it
        tree = processor.import_from_obz(temp_obz.name)

        assert isinstance(tree, AACTree)
        assert len(tree.pages) > 0
        assert tree.root_id is not None

        # Clean up
        os.unlink(temp_obz.name)
