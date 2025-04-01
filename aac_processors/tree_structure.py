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
class AACSymbol:
    """Represents a symbol or image used in an AAC button.

    This class provides a unified way to reference symbols across different AAC systems:

    1. Library References:
       - Grid 3: [library]filename.wmf
       - TouchChat: RID in symbol_links table
       - Snap: LibrarySymbolId
       - OBF: symbol_set + symbol_key

    2. Direct References:
       - Local file path
       - Web URL
       - Base64 data (OBF)

    The class doesn't store actual image data, only references. Image resolution
    is handled by the specific processor implementations.
    """
    # Library Reference (primary method)
    library: Optional[str] = None      # Symbol library name (e.g., "widgit", "pcs", "grid3x")
    library_key: Optional[str] = None  # Key within library (e.g., "apple", "123")

    # System-specific IDs
    system_id: Optional[str] = None    # ID used by source system (e.g., LibrarySymbolId in Snap)
    system_name: Optional[str] = None  # Name of source system (e.g., "snap", "grid3")
    internal_id: Optional[str] = None  # Internal ID for cross-referencing

    # Direct References
    local_path: Optional[str] = None   # Path to local file
    url: Optional[str] = None          # URL to remote file
    data: Optional[str] = None         # Base64 encoded data
    content_type: Optional[str] = None # MIME type of the image (e.g., "image/png")

    # Metadata
    format: Optional[str] = None       # File format (e.g., "png", "wmf")
    label: Optional[str] = None        # Display name/label
    width: Optional[int] = None        # Image width in pixels
    height: Optional[int] = None       # Image height in pixels

    def __post_init__(self):
        """Set internal_id if not provided and infer content_type if possible."""
        if not self.internal_id:
            # Use system_id if available, otherwise generate one
            self.internal_id = self.system_id or f"{self.system_name}_{self.library_key}"

        # Infer content_type from format if not set
        if not self.content_type and self.format:
            format_to_mime = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'wmf': 'image/wmf',
                'svg': 'image/svg+xml'
            }
            self.content_type = format_to_mime.get(self.format.lower(), 'image/png')

    @property
    def data_url(self) -> Optional[str]:
        """Get data URL if data is present."""
        if self.data:
            content_type = self.content_type or 'image/png'
            return f"data:{content_type};base64,{self.data}"
        return None

    @classmethod
    def from_data_url(cls, data_url: str, internal_id: Optional[str] = None) -> 'AACSymbol':
        """Create symbol from data URL.

        Args:
            data_url: Data URL string
            internal_id: Optional internal ID

        Returns:
            New AACSymbol instance
        """
        try:
            # Parse data URL format: data:[<media type>][;base64],<data>
            header, data = data_url.split(',', 1)
            content_type = None
            if header.startswith('data:'):
                content_type = header[5:].split(';')[0] or None

            return cls(
                data=data,
                content_type=content_type,
                internal_id=internal_id
            )
        except Exception:
            # Return empty symbol if parsing fails
            return cls(internal_id=internal_id)


@dataclass
class AACButton:
    """Button in an AAC system."""

    id: str
    label: str
    type: ButtonType = ButtonType.SPEAK
    symbol: Optional[AACSymbol] = None
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
