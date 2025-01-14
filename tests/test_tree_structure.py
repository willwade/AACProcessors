import pytest

from aac_processors.tree_structure import (
    AACButton,
    AACPage,
    AACTree,
    ButtonStyle,
    ButtonType,
)


@pytest.fixture
def sample_button():
    """Create a sample button for testing"""
    return AACButton(
        id="btn1",
        label="Test Button",
        type=ButtonType.SPEAK,
        position=(0, 0),
        vocalization="Hello",
        style=ButtonStyle(
            font_color="#000000",
            body_color="#FFFFFF",
            border_color="#000000",
            border_width=1,
        ),
    )


@pytest.fixture
def sample_page(sample_button):
    """Create a sample page with buttons"""
    page = AACPage(id="page1", name="Test Page", grid_size=(3, 3))
    page.buttons.extend(
        [
            sample_button,
            AACButton(
                "btn2", "Navigate", ButtonType.NAVIGATE, (0, 1), target_page_id="page2"
            ),
        ]
    )
    return page


def test_button_creation(sample_button):
    """Test basic button creation and properties"""
    assert sample_button.id == "btn1"
    assert sample_button.label == "Test Button"
    assert sample_button.type == ButtonType.SPEAK
    assert sample_button.position == (0, 0)
    assert sample_button.vocalization == "Hello"
    assert sample_button.style.font_color == "#000000"


def test_page_creation():
    """Test page creation and button management"""
    page = AACPage(id="page1", name="Test Page", grid_size=(3, 3))

    button1 = AACButton("btn1", "Button 1", ButtonType.SPEAK, (0, 0))
    button2 = AACButton("btn2", "Button 2", ButtonType.NAVIGATE, (0, 1))

    page.buttons.extend([button1, button2])

    assert page.id == "page1"
    assert page.name == "Test Page"
    assert page.grid_size == (3, 3)
    assert len(page.buttons) == 2
    assert not page.is_wordlist


def test_tree_navigation():
    """Test tree navigation and relationships"""
    tree = AACTree()

    # Create pages
    home = AACPage("home", "Home", (2, 2))
    page1 = AACPage("page1", "Page 1", (2, 2))
    page2 = AACPage("page2", "Page 2", (2, 2))

    # Set relationships
    page1.parent_id = "home"
    page2.parent_id = "home"

    # Add navigation buttons
    home.buttons.append(
        AACButton(
            "nav1", "To Page 1", ButtonType.NAVIGATE, (0, 0), target_page_id="page1"
        )
    )

    # Add pages to tree
    tree.add_page(home)
    tree.add_page(page1)
    tree.add_page(page2)

    # Test navigation
    assert tree.root_id == "home"
    assert len(tree.get_children("home")) == 2
    assert tree.get_path_to_page("page1") == ["home", "page1"]


def test_navigation_analysis():
    """Test navigation analysis functionality"""
    tree = AACTree()

    # Create a simple navigation structure
    home = AACPage("home", "Home", (2, 2))
    page1 = AACPage("page1", "Page 1", (2, 2))
    orphan = AACPage("orphan", "Orphan", (2, 2))

    # Add navigation button
    home.buttons.append(
        AACButton(
            "nav1", "To Page 1", ButtonType.NAVIGATE, (0, 0), target_page_id="page1"
        )
    )

    # Add pages to tree
    tree.add_page(home)
    tree.add_page(page1)
    tree.add_page(orphan)

    analysis = tree.analyze_navigation()

    assert analysis["total_pages"] == 3
    assert len(analysis["dead_ends"]) == 1  # Only page1 is a dead end
    assert len(analysis["orphaned_pages"]) == 1
    assert analysis["orphaned_pages"][0] == "orphan"
