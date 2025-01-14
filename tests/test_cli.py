import tempfile
from unittest.mock import MagicMock, patch

import pytest

from aac_processors.cli import (
    complete_path,
    convert_format,
    get_available_formats,
    interactive_mode,
    main,
)
from aac_processors.tree_structure import AACButton, AACPage, AACTree, ButtonType


def test_get_available_formats():
    """Test that available formats are returned correctly"""
    formats = get_available_formats()
    assert isinstance(formats, list)
    assert len(formats) == 4
    assert "grid" in formats
    assert "touchchat" in formats
    assert "snap" in formats
    assert "coughdrop" in formats


def test_complete_path(tmp_path):
    """Test path completion functionality"""
    # Create test directory structure
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").touch()
    (test_dir / "file2.txt").touch()
    sub_dir = test_dir / "subdir"
    sub_dir.mkdir()

    # Test directory completion
    result = complete_path(str(test_dir), 0)
    assert result == str(test_dir) + "/"

    # Test file completion with pattern
    result = complete_path(str(test_dir / "file1"), 0)
    assert result == str(test_dir / "file1.txt")
    result = complete_path(str(test_dir / "file2"), 0)
    assert result == str(test_dir / "file2.txt")
    result = complete_path(str(test_dir / "nonexistent"), 0)
    assert result is None


@pytest.fixture
def sample_tree():
    """Create a sample AACTree for testing"""
    tree = AACTree()
    page = AACPage(id="test_page", name="Test Page", grid_size=(2, 2))
    button = AACButton(
        id="btn1",
        label="Test Button",
        type=ButtonType.SPEAK,
        position=(0, 0),
        vocalization="Test Message",
    )
    page.buttons.append(button)
    tree.pages[page.id] = page
    tree.root_id = page.id
    return tree


@pytest.fixture
def mock_processor(sample_tree):
    """Create a mock processor for testing"""
    processor = MagicMock()
    processor.load_into_tree.return_value = sample_tree
    processor.default_extension = ".test"
    processor.export_tree = MagicMock()
    processor.can_process.return_value = True
    return processor


def test_convert_format(tmp_path, sample_tree, mock_processor):
    """Test format conversion functionality"""
    input_file = tmp_path / "input.test"
    input_file.touch()

    with (
        patch("aac_processors.cli.get_processor_for_file") as mock_get_processor,
        patch("aac_processors.cli.GridsetProcessor") as mock_grid_processor,
    ):
        # Configure source processor
        mock_get_processor.return_value = mock_processor

        # Configure target processor
        mock_grid_instance = MagicMock()
        mock_grid_instance.default_extension = ".test"
        mock_grid_processor.return_value = mock_grid_instance

        # Test successful conversion
        result = convert_format(str(input_file), "grid")
        assert result is not None
        assert result.endswith("_converted.test")
        mock_grid_instance.export_tree.assert_called_once()

        # Reset mocks for next test
        mock_grid_instance.export_tree.reset_mock()

        # Test unsupported input format
        mock_get_processor.return_value = None
        result = convert_format(str(input_file), "grid")
        assert result is None

        # Test custom output path
        mock_get_processor.return_value = mock_processor
        output_path = str(tmp_path / "output.test")
        result = convert_format(str(input_file), "grid", output_path)
        assert result == output_path
        mock_grid_instance.export_tree.assert_called_once()


@pytest.mark.integration
def test_main_view_command(tmp_path, mock_processor):
    """Test main function with view command"""
    input_file = tmp_path / "input.test"
    input_file.touch()

    test_args = ["aac-processors", "view", str(input_file)]
    with (
        patch("sys.argv", test_args),
        patch("aac_processors.cli.get_processor_for_file") as mock_get_proc,
        patch("aac_processors.cli.print_tree") as mock_print_tree,
    ):
        mock_get_proc.return_value = mock_processor
        main()
        mock_print_tree.assert_called_once()


@pytest.mark.integration
def test_main_convert_command(tmp_path, mock_processor):
    """Test main function with convert command"""
    input_file = tmp_path / "input.test"
    input_file.touch()

    test_args = ["aac-processors", "convert", str(input_file), "--to", "grid"]
    with (
        patch("sys.argv", test_args),
        patch("aac_processors.cli.get_processor_for_file") as mock_get_proc,
        pytest.raises(SystemExit) as exit_info,
    ):
        mock_get_proc.return_value = mock_processor
        main()
        mock_processor.export_tree.assert_called_once()
        assert exit_info.value.code == 0  # Should exit successfully


@pytest.mark.integration
def test_interactive_mode(mock_processor):
    """Test interactive mode"""
    with (
        tempfile.NamedTemporaryFile(suffix=".test") as temp_file,
        patch("builtins.input") as mock_input,
        patch("aac_processors.cli.get_processor_for_file") as mock_get_proc,
        patch("aac_processors.cli.print_tree") as mock_print_tree,
    ):
        mock_get_proc.return_value = mock_processor
        mock_input.side_effect = [
            temp_file.name,  # File path
            "1",  # View option
        ]

        interactive_mode()
        mock_print_tree.assert_called_once()
