from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ButtonType(Enum):
    SPEAK = "speak"
    NAVIGATE = "navigate"
    ACTION = "action"
    WORDLIST = "wordlist"
    COMMAND = "command"


@dataclass
class ButtonStyle:
    """Visual properties for buttons"""

    font_color: Optional[str] = None
    body_color: Optional[str] = None
    border_color: Optional[str] = None
    border_width: Optional[int] = None
    font_name: Optional[str] = None
    font_size: Optional[int] = None
    font_bold: bool = False
    font_italic: bool = False
    font_underline: bool = False


@dataclass
class AACButton:
    """Button in an AAC system."""

    id: str
    label: str
    type: ButtonType = ButtonType.SPEAK
    position: tuple[int, int] = (0, 0)
    target_page_id: Optional[str] = None
    vocalization: Optional[str] = None
    action: Optional[str] = None
    image: Optional[dict[str, Any]] = None
    style: ButtonStyle = field(default_factory=ButtonStyle)
    # Dimensions as percentage of page (0.0-1.0)
    width: float = 0.1  # Default 10% of page width
    height: float = 0.1  # Default 10% of page height
    left: Optional[float] = None  # Absolute position from left
    top: Optional[float] = None  # Absolute position from top


@dataclass
class AACPage:
    """Represents a page in an AAC system"""

    id: str
    name: str
    grid_size: tuple[int, int]  # (rows, cols)
    buttons: list[AACButton] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None  # ID of parent page for navigation

    def __post_init__(self) -> None:
        """Initialize any additional attributes after dataclass initialization"""
        # Ensure buttons exists
        if not hasattr(self, "buttons"):
            self.buttons = []
        # Ensure metadata exists
        if not hasattr(self, "metadata"):
            self.metadata = {}


class AACTree:
    """Tree structure for AAC pages."""

    def __init__(self) -> None:
        """Initialize empty tree."""
        self.pages: dict[str, AACPage] = {}
        self.root_id: Optional[str] = None
        self.metadata: dict[str, Any] = {}

    def add_page(self, page: AACPage) -> None:
        """Add a page to the tree"""
        self.pages[page.id] = page
        if not self.root_id:
            self.root_id = page.id

    def get_children(self, page_id: str) -> list[AACPage]:
        """Get child pages of the given page"""
        return [p for p in self.pages.values() if p.parent_id == page_id]

    def get_path_to_page(self, target_id: str) -> list[str]:
        """Find navigation path to a specific page"""
        if target_id not in self.pages:
            return []

        path: list[str] = []
        current: Optional[str] = target_id
        while current:
            path.append(current)
            current = self.pages[current].parent_id
            if current in path:  # Detect cycles
                break
        return list(reversed(path))

    def analyze_navigation(self) -> dict[str, Any]:
        """Analyze navigation structure"""
        analysis: dict[str, Any] = {
            "total_pages": len(self.pages),
            "max_depth": 0,
            "dead_ends": [],
            "circular_refs": [],
            "orphaned_pages": [],
            "navigation_stats": {
                "speak_buttons": 0,
                "nav_buttons": 0,
                "wordlist_buttons": 0,
                "command_buttons": 0,
            },
        }

        # First find all reachable pages from root
        reachable_pages = set()

        def find_reachable_pages(page_id: str) -> None:
            if page_id in reachable_pages:
                return
            reachable_pages.add(page_id)
            page = self.pages[page_id]
            for button in page.buttons:
                if (
                    button.type == ButtonType.NAVIGATE
                    and button.target_page_id in self.pages
                ):
                    find_reachable_pages(button.target_page_id)

        if self.root_id:
            find_reachable_pages(self.root_id)

        # Analyze each page
        for page_id, page in self.pages.items():
            # Check for orphaned pages - pages not reachable from root
            if page_id != self.root_id and page_id not in reachable_pages:
                analysis["orphaned_pages"].append(page_id)
                continue  # Skip dead end analysis for orphaned pages

            # Count navigation buttons and check for dead ends
            has_valid_navigation = False
            for button in page.buttons:
                if button.type == ButtonType.SPEAK:
                    analysis["navigation_stats"]["speak_buttons"] += 1
                elif button.type == ButtonType.NAVIGATE:
                    analysis["navigation_stats"]["nav_buttons"] += 1
                    if button.target_page_id in self.pages:
                        has_valid_navigation = True
                    else:
                        analysis["dead_ends"].append((page_id, button.id))
                elif button.type == ButtonType.WORDLIST:
                    analysis["navigation_stats"]["wordlist_buttons"] += 1
                elif button.type == ButtonType.COMMAND:
                    analysis["navigation_stats"]["command_buttons"] += 1

            # If page is reachable but has no
            #  valid navigation buttons and isn't the root,
            #  it's a dead end
            if (
                not has_valid_navigation
                and page_id != self.root_id
                and page_id in reachable_pages
            ):
                analysis["dead_ends"].append(page_id)

        # Calculate max depth
        def get_depth(page_id: str, visited: set) -> int:
            if page_id in visited:
                analysis["circular_refs"].append(page_id)
                return 0
            visited.add(page_id)
            children = self.get_children(page_id)
            if not children:
                return 1
            return 1 + max(get_depth(child.id, visited.copy()) for child in children)

        if self.root_id:
            analysis["max_depth"] = get_depth(self.root_id, set())

        return analysis
