#!/usr/bin/env python3

import os
import sys
from typing import Dict, List, Set
from aac_processors.gridset_processor import GridsetProcessor
from aac_processors.touchchat_processor import TouchChatProcessor
from aac_processors.snap_processor import SnapProcessor
from aac_processors.coughdrop_processor import CoughDropProcessor
from aac_processors.tree_structure import AACTree, AACPage, AACButton, ButtonType


def get_processor_for_file(file_path: str):
    """Get appropriate processor for file type"""
    processors = [
        GridsetProcessor(),
        TouchChatProcessor(),
        SnapProcessor(),
        CoughDropProcessor(),
    ]

    for processor in processors:
        if processor.can_process(file_path):
            return processor

    return None


def print_button(button: AACButton, indent: int = 0, visited_pages: Set[str] = None):
    """Print button details with indentation"""
    indent_str = "  " * indent
    type_str = {
        ButtonType.SPEAK: "🗣️ ",
        ButtonType.NAVIGATE: "🔀 ",
        ButtonType.COMMAND: "⚡ ",
        ButtonType.WORDLIST: "📝 ",
    }.get(button.type, "  ")

    print(
        f"{indent_str}{type_str}{button.label or '[No Label]'} ({button.position[0]}, {button.position[1]})"
    )
    if button.vocalization:
        print(f"{indent_str}  └─ Says: {button.vocalization}")
    if button.target_page_id:
        if visited_pages and button.target_page_id in visited_pages:
            print(
                f"{indent_str}  └─ Goes to: {button.target_page_id} (circular reference)"
            )
        else:
            print(f"{indent_str}  └─ Goes to: {button.target_page_id}")


def print_page(
    page: AACPage, tree: AACTree, indent: int = 0, visited_pages: Set[str] = None
):
    """Print page details with indentation"""
    if visited_pages is None:
        visited_pages = set()

    if page.id in visited_pages:
        print(f"{indent_str}📄 {page.name} (circular reference)")
        return

    visited_pages.add(page.id)
    indent_str = "  " * indent
    print(f"{indent_str}📄 {page.name} ({page.grid_size[0]}x{page.grid_size[1]} grid)")

    # Group buttons by row and column
    grid = [[None for _ in range(page.grid_size[1])] for _ in range(page.grid_size[0])]
    for button in page.buttons:
        row, col = button.position
        if 0 <= row < page.grid_size[0] and 0 <= col < page.grid_size[1]:
            grid[row][col] = button

    # Print grid with buttons
    for row_idx, row in enumerate(grid):
        print(f"{indent_str}  Row {row_idx}:")
        for col_idx, button in enumerate(row):
            if button:
                print_button(button, indent + 2, visited_pages)
                # If it's a navigation button, follow it
                if (
                    button.type == ButtonType.NAVIGATE
                    and button.target_page_id in tree.pages
                ):
                    target_page = tree.pages[button.target_page_id]
                    print(f"{indent_str}    └─ Target Page:")
                    print_page(target_page, tree, indent + 4, visited_pages.copy())
            else:
                print(f"{indent_str}    [Empty] ({row_idx}, {col_idx})")


def print_tree(tree: AACTree):
    """Print entire tree structure"""
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


def main():
    if len(sys.argv) != 2:
        print("Usage: python demo_viewer.py <file_path>")
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
