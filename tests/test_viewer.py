from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from aac_processors.tree_structure import AACButton, AACPage, AACTree, ButtonType
from aac_processors.viewer import (
    get_processor_for_file,
    main,
    print_button,
    print_page,
    print_tree,
)


def pytest_configure(config):
    """Register custom marks"""
    config.addinivalue_line("markers", "integration: mark test as an integration test")


@pytest.fixture
def sample_button():
    """Create a sample button for testing"""
    return AACButton(
        id="btn1",
        label="Test Button",
        type=ButtonType.SPEAK,
        position=(0, 1),
        vocalization="Hello World",
    )


@pytest.fixture
def sample_page():
    """Create a sample page with buttons"""
    # Create buttons
    button1 = AACButton(
        id="btn1",
        label="Button 1",
        type=ButtonType.SPEAK,
        position=(0, 0),
        vocalization="Hello",
    )

    button2 = AACButton(
        id="btn2",
        label="Button 2",
        type=ButtonType.NAVIGATE,
        position=(0, 1),
        target_page_id="page2",
    )

    return AACPage(
        id="page1", name="Test Page", grid_size=(2, 2), buttons=[button1, button2]
    )


@pytest.fixture
def sample_tree(sample_page):
    """Create a sample tree with pages"""
    tree = AACTree()

    # Add main page
    tree.pages[sample_page.id] = sample_page

    # Add target page for navigation
    target_page = AACPage(id="page2", name="Target Page", grid_size=(1, 1), buttons=[])
    tree.pages[target_page.id] = target_page

    tree.root_id = sample_page.id
    return tree


def test_get_processor_for_file():
    """Test processor detection for different file types"""
    assert get_processor_for_file("test.gridset") is not None
    assert get_processor_for_file("test.obf") is not None
    assert get_processor_for_file("test.ce") is not None  # TouchChat uses .ce extension
    assert get_processor_for_file("test.spb") is not None
    assert get_processor_for_file("test.unknown") is None


def test_print_button(sample_button):
    """Test button printing with various button types"""
    with patch("sys.stdout", new=StringIO()) as fake_out:
        print_button(sample_button)
        output = fake_out.getvalue()

        # Check output contains essential elements
        assert "Test Button" in output
        assert "(0, 1)" in output
        assert "Says: Hello World" in output  # Check for vocalization with prefix
        assert "🗣️" in output  # Speech emoji


def test_print_button_navigation(sample_button):
    """Test printing navigation button with circular reference detection"""
    sample_button.type = ButtonType.NAVIGATE
    sample_button.target_page_id = "target_page"

    with patch("sys.stdout", new=StringIO()) as fake_out:
        # Test without circular reference
        print_button(sample_button)
        output1 = fake_out.getvalue()
        assert "circular" not in output1
        assert "target_page" in output1

        # Test with circular reference
        fake_out.seek(0)
        fake_out.truncate()
        print_button(sample_button, visited_pages={"target_page"})
        output2 = fake_out.getvalue()
        assert "circular" in output2


def test_print_page(sample_page, sample_tree):
    """Test page printing with grid layout"""
    with patch("sys.stdout", new=StringIO()) as fake_out:
        print_page(sample_page, sample_tree)
        output = fake_out.getvalue()

        # Check output contains essential elements
        assert "Test Page" in output
        assert "2x2 grid" in output
        assert "Button 1" in output
        assert "Button 2" in output
        assert "Row 0" in output
        assert "[Empty]" in output  # For empty grid positions


def test_print_tree(sample_tree):
    """Test complete tree printing with navigation analysis"""
    with patch("sys.stdout", new=StringIO()) as fake_out:
        print_tree(sample_tree)
        output = fake_out.getvalue()

        # Check structure section
        assert "AAC Board Structure" in output
        assert "Root Page" in output
        assert "Test Page" in output
        assert "Target Page" in output

        # Check navigation analysis
        assert "Navigation Analysis" in output
        assert "Total Pages: 2" in output


def test_main_file_not_found():
    """Test main function with non-existent file"""
    with patch("sys.argv", ["viewer.py", "nonexistent.gridset"]):
        with pytest.raises(SystemExit):
            main()


def test_main_unsupported_file():
    """Test main function with unsupported file type"""
    with patch("sys.argv", ["viewer.py", "test.unknown"]):
        with pytest.raises(SystemExit):
            main()


def test_main_missing_argument():
    """Test main function with missing file argument"""
    with patch("sys.argv", ["viewer.py"]):
        with pytest.raises(SystemExit):
            main()


@pytest.mark.integration
def test_viewer_integration(tmp_path, sample_page, sample_tree):
    """Integration test using a real file"""
    # Create a mock gridset file
    test_file = tmp_path / "test.gridset"
    test_file.write_text("dummy content")

    # Mock the processor and tree
    mock_processor = MagicMock()
    mock_processor.can_process.return_value = True
    mock_processor.load_into_tree.return_value = sample_tree

    with patch(
        "aac_processors.viewer.get_processor_for_file", return_value=mock_processor
    ):
        with patch("sys.argv", ["viewer.py", str(test_file)]):
            with patch("sys.stdout", new=StringIO()) as fake_out:
                main()
                output = fake_out.getvalue()

                # Verify complete output
                assert "AAC Board Structure" in output
                assert "Navigation Analysis" in output
                assert "Test Page" in output
                assert "Target Page" in output
