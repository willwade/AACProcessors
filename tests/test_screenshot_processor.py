import os
from typing import Optional

import pytest

from aac_processors.optional.screenshot_processor import ScreenshotProcessor
from aac_processors.tree_structure import AACPage

# Mark for tests requiring screenshot dependencies
screenshot = pytest.mark.screenshot


@pytest.fixture
def demo_dir() -> str:
    """Get the demo files directory."""
    return "examples/demofiles"


@pytest.fixture
def screenshot_processor() -> ScreenshotProcessor:
    """Create a ScreenshotProcessor instance."""

    class TestProcessor(ScreenshotProcessor):
        def create_translated_file(
            self, file_path: str, translations: dict[str, str]
        ) -> Optional[str]:
            """Mock implementation of create_translated_file."""
            return "test_output.png"

    return TestProcessor()


@pytest.fixture
def demo_screenshots(demo_dir: str) -> list[str]:
    """Get paths to demo screenshot files."""
    files = [
        "TouchChat+HD+-+AAC+with+WordPower+60+Basic.jpg",
        "TouchChat24.png",
    ]
    return [os.path.join(demo_dir, f) for f in files]


@screenshot
def test_can_process(
    screenshot_processor: ScreenshotProcessor, demo_screenshots: list[str]
) -> None:
    """Test that processor can handle screenshot files."""
    for file_path in demo_screenshots:
        assert screenshot_processor.can_process(file_path)

    # Test invalid extensions
    assert not screenshot_processor.can_process("test.txt")
    assert not screenshot_processor.can_process("test.pdf")


@screenshot
def test_detect_grid(
    screenshot_processor: ScreenshotProcessor, demo_screenshots: list[str]
) -> None:
    """Test grid detection from screenshots."""
    for file_path in demo_screenshots:
        grid_width, grid_height, boxes = screenshot_processor.detect_grid(file_path)

        # Check grid dimensions are reasonable
        assert grid_width > 0
        assert grid_height > 0
        assert grid_width <= 20  # Reasonable max for AAC grids
        assert grid_height <= 20

        # Check we found some cells
        assert len(boxes) > 0

        # Check box coordinates are valid
        for x, y, w, h in boxes:
            assert x >= 0
            assert y >= 0
            assert w > 0
            assert h > 0


@screenshot
def test_detect_cell_content(
    screenshot_processor: ScreenshotProcessor, demo_screenshots: list[str]
) -> None:
    """Test content detection from grid cells."""
    for file_path in demo_screenshots:
        # Get grid info
        grid_width, grid_height, boxes = screenshot_processor.detect_grid(file_path)

        # Load image
        import cv2

        img = cv2.imread(file_path)
        assert img is not None

        # Test each cell
        for box in boxes:
            content = screenshot_processor.detect_cell_content(img, box)

            # Check content structure
            assert "text" in content
            assert "color" in content
            assert all(c in content["color"] for c in ["r", "g", "b"])

            # Check color values are valid
            for c in content["color"].values():
                assert 0 <= c <= 255


@screenshot
def test_create_page(
    screenshot_processor: ScreenshotProcessor, demo_screenshots: list[str]
) -> None:
    """Test creating AACPage from screenshots."""
    for file_path in demo_screenshots:
        page = screenshot_processor.create_page_from_screenshot(file_path)

        # Check page properties
        assert isinstance(page, AACPage)
        assert isinstance(page.id, str)
        assert page.id.startswith("screenshot_")
        assert isinstance(page.name, str)
        assert page.name.startswith("Detected Page")
        assert len(page.grid_size) == 2
        assert all(dim > 0 for dim in page.grid_size)

        # Check buttons
        assert len(page.buttons) > 0
        for btn in page.buttons:
            assert isinstance(btn.id, str)
            assert btn.id.startswith("btn_")
            assert len(btn.position) == 2
            assert all(pos >= 0 for pos in btn.position)
            assert btn.style is not None
            assert isinstance(btn.style.body_color, str)
            assert btn.style.body_color.startswith("#")


@screenshot
def test_extract_texts(
    screenshot_processor: ScreenshotProcessor, demo_screenshots: list[str]
) -> None:
    """Test extracting texts from screenshots."""
    for file_path in demo_screenshots:
        texts = screenshot_processor.extract_texts(file_path)

        # We should find some text
        assert len(texts) > 0

        # Check text properties
        for text in texts:
            assert isinstance(text, str)
            assert len(text.strip()) > 0  # Non-empty after stripping whitespace


@screenshot
def test_load_into_tree(
    screenshot_processor: ScreenshotProcessor, demo_screenshots: list[str]
) -> None:
    """Test loading screenshots into tree structure."""
    for file_path in demo_screenshots:
        tree = screenshot_processor.load_into_tree(file_path)

        # Check tree structure
        assert len(tree.pages) > 0
        page = next(iter(tree.pages.values()))

        # Check page properties
        assert isinstance(page, AACPage)
        assert isinstance(page.id, str)
        assert page.id.startswith("screenshot_")
        assert len(page.buttons) > 0


@screenshot
def test_save_from_tree(
    screenshot_processor: ScreenshotProcessor, demo_screenshots: list[str]
) -> None:
    """Test that save_from_tree raises NotImplementedError."""
    tree = screenshot_processor.load_into_tree(demo_screenshots[0])
    with pytest.raises(NotImplementedError):
        screenshot_processor.save_from_tree(tree, "output.png")
