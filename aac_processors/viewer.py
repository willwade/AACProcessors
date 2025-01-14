#!/usr/bin/env python3

import os
import sys
from typing import Optional, Union

from .coughdrop_processor import CoughDropProcessor
from .gridset_processor import GridsetProcessor
from .snap_processor import SnapProcessor
from .touchchat_processor import TouchChatProcessor
from .tree_structure import AACButton, AACPage, AACTree, ButtonType

ProcessorType = Union[
    GridsetProcessor, TouchChatProcessor, SnapProcessor, CoughDropProcessor
]


def get_processor_for_file(file_path: str) -> Optional[ProcessorType]:
    """Get appropriate processor for file type.

    Args:
        file_path: Path to the file to process.

    Returns:
        A processor instance that can handle the file type, or None if no suitable
        processor is found.
    """
    processors: list[ProcessorType] = [
        GridsetProcessor(),
        TouchChatProcessor(),
        SnapProcessor(),
        CoughDropProcessor(),
    ]

    for processor in processors:
        if processor.can_process(file_path):
            return processor

    return None


def print_button(
    button: AACButton, indent: int = 0, visited_pages: Optional[set[str]] = None
) -> None:
    """Print button details with indentation.

    Args:
        button: The button to print.
        indent: Number of spaces to indent the output.
        visited_pages: Set of visited page IDs (for circular reference detection).
    """
    if visited_pages is None:
        visited_pages = set()

    indent_str = "  " * indent
    type_str = {
        ButtonType.SPEAK: "🗣️ ",
        ButtonType.NAVIGATE: "🔀 ",
        ButtonType.ACTION: "⚡ ",
    }.get(button.type, "  ")

    # Split long line for better readability
    button_info = f"{indent_str}{type_str}{button.label or '[No Label]'}"
    position_info = f"({button.position[0]}, {button.position[1]})"
    print(f"{button_info} {position_info}")

    if hasattr(button, "vocalization") and button.vocalization:
        print(f"{indent_str}  └─ Says: {button.vocalization}")
    if button.target_page_id:
        if visited_pages and button.target_page_id in visited_pages:
            print(f"{indent_str}  └─ Goes to: {button.target_page_id} (circular)")
        else:
            print(f"{indent_str}  └─ Goes to: {button.target_page_id}")


def print_page(
    page: AACPage,
    tree: AACTree,
    indent: int = 0,
    visited_pages: Optional[set[str]] = None,
) -> None:
    """Print page details with indentation.

    Args:
        page: The page to print.
        tree: The complete AAC tree (needed for navigation).
        indent: Number of spaces to indent the output.
        visited_pages: Set of visited page IDs (for circular reference detection).
    """
    if visited_pages is None:
        visited_pages = set()

    indent_str = "  " * indent

    if page.id in visited_pages:
        print(f"{indent_str}📄 {page.name} (circular reference)")
        return

    visited_pages.add(page.id)
    print(f"{indent_str}📄 {page.name} ({page.grid_size[0]}x{page.grid_size[1]} grid)")

    # Group buttons by row and column
    buttons_by_position: dict[tuple[int, int], AACButton] = {}
    for button in page.buttons:
        row, col = button.position
        if 0 <= row < page.grid_size[0] and 0 <= col < page.grid_size[1]:
            buttons_by_position[(row, col)] = button

    # Print grid with buttons
    for row in range(page.grid_size[0]):
        print(f"{indent_str}  Row {row}:")
        for col in range(page.grid_size[1]):
            maybe_button = buttons_by_position.get((row, col))
            if maybe_button is not None:
                print_button(maybe_button, indent + 2, visited_pages)
                # If it's a navigation button, follow it
                if (
                    maybe_button.type == ButtonType.NAVIGATE
                    and maybe_button.target_page_id in tree.pages
                ):
                    target_page = tree.pages[maybe_button.target_page_id]
                    print(f"{indent_str}    └─ Target Page:")
                    print_page(target_page, tree, indent + 4, visited_pages.copy())
            else:
                print(f"{indent_str}    [Empty] ({row}, {col})")


def print_tree(tree: AACTree) -> None:
    """Print entire tree structure with navigation analysis.

    Args:
        tree: The AAC tree to print.
    """
    print("\n=== AAC Board Structure ===\n")

    # Print root page first
    if tree.root_id and tree.root_id in tree.pages:
        root_page = tree.pages[tree.root_id]
        print("Root Page:")
        print_page(root_page, tree, 1, set())
    else:
        # No root page, print all pages at top level
        for page in tree.pages.values():
            print_page(page, tree, 0, set())

    print("\n=== Navigation Analysis ===\n")
    analysis = tree.analyze_navigation()
    print(f"Total Pages: {analysis['total_pages']}")

    if analysis["dead_ends"]:
        print("\nDead End Pages (no way back):")
        for page_id in analysis["dead_ends"]:
            if page_id in tree.pages:
                print(f"  - {tree.pages[page_id].name}")

    if analysis["orphaned_pages"]:
        print("\nOrphaned Pages (no way to reach):")
        for page_id in analysis["orphaned_pages"]:
            if page_id in tree.pages:
                print(f"  - {tree.pages[page_id].name}")


def main() -> None:
    """Main entry point for the viewer."""
    if len(sys.argv) != 2:
        print("Usage: python -m aac_processors.viewer <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    processor = get_processor_for_file(file_path)
    if not processor:
        print(f"Error: Unsupported file type: {file_path}")
        sys.exit(1)

    try:
        tree = processor.load_into_tree(file_path)
        print_tree(tree)
    except Exception as e:
        print(f"Error loading file: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
