#!/usr/bin/env python3

import os
import sys
import argparse
import readline
import glob
import tempfile
import shutil
import traceback
from typing import Optional, Dict, Type

from aac_processors.gridset_processor import GridsetProcessor
from aac_processors.touchchat_processor import TouchChatProcessor
from aac_processors.snap_processor import SnapProcessor
from aac_processors.coughdrop_processor import CoughDropProcessor
from aac_processors.tree_structure import AACTree, ButtonType
from aac_processors.base_processor import AACProcessor


def print_tree(tree: AACTree, indent: int = 0):
    """Print tree structure recursively"""
    for page_id, page in tree.pages.items():
        print("  " * indent + f"Page: {page.name} ({page.id})")
        print("  " * (indent + 1) + f"Grid: {page.grid_size[0]}x{page.grid_size[1]}")
        for button in page.buttons:
            button_type = "NAVIGATE" if button.type == ButtonType.NAVIGATE else "SPEAK"
            print("  " * (indent + 1) + f"Button: {button.label} ({button_type})")
            if button.target_page_id:
                print("  " * (indent + 2) + f"-> {button.target_page_id}")


def get_processor_for_format(format_name: str) -> Optional[AACProcessor]:
    """Get processor instance for target format"""
    format_map = {
        "grid": GridsetProcessor,
        "touchchat": TouchChatProcessor,
        "snap": SnapProcessor,
        "coughdrop": CoughDropProcessor,
    }

    processor_class = format_map.get(format_name.lower())
    if processor_class:
        return processor_class()
    return None


def get_processor_for_file(file_path: str) -> Optional[AACProcessor]:
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


def get_available_formats():
    """Get list of available format processors"""
    return {
        "grid": GridsetProcessor,
        "touchchat": TouchChatProcessor,
        "snap": SnapProcessor,
        "coughdrop": CoughDropProcessor,
    }


def convert_format(
    input_file: str, output_format: str, output_path: Optional[str] = None
) -> Optional[str]:
    """Convert between AAC formats"""
    try:
        # Get source processor
        source_processor = get_processor_for_file(input_file)
        if not source_processor:
            print(f"Error: Unsupported input format: {input_file}")
            return None

        print(f"Loading {input_file} using {source_processor.__class__.__name__}")
        # Load into tree structure
        tree = source_processor.load_into_tree(input_file)
        if not tree or not isinstance(tree, AACTree):
            print("Error: Failed to load input file into tree structure")
            return None

        print(f"Loaded tree with {len(tree.pages)} pages")

        # Get target processor
        target_processor = get_processor_for_format(output_format)
        if not target_processor:
            print(f"Error: Unsupported output format: {output_format}")
            return None

        # Set file path on target processor
        target_processor.file_path = input_file

        # Generate output path if not provided
        if not output_path:
            output_path = target_processor.get_output_path()

        print(f"Converting to {output_format} format at {output_path}")
        # Save using target processor
        target_processor.save_from_tree(tree, output_path)

        return output_path

    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        traceback.print_exc()
        return None
    finally:
        # Cleanup any temporary files
        if "source_processor" in locals():
            source_processor.cleanup_temp_files()
        if "target_processor" in locals():
            target_processor.cleanup_temp_files()


def complete_path(text, state):
    """Tab completion function for file paths"""
    if "~" in text:
        text = os.path.expanduser(text)

    if os.path.isdir(text):
        text = os.path.join(text, "")

    dir_name = os.path.dirname(text)
    if dir_name and not os.path.exists(dir_name):
        return None

    if dir_name:
        pattern = os.path.join(dir_name, os.path.basename(text) + "*")
    else:
        pattern = text + "*"

    matches = glob.glob(pattern)
    matches = [f"{m}{'/' if os.path.isdir(m) else ''}" for m in matches]
    return matches[state] if state < len(matches) else None


def interactive_mode(file_path: str = None):
    """Interactive CLI mode"""
    print("\nAAC Processor Tool")
    print("=================\n")

    # Get input file if not provided
    if not file_path:
        # Set up tab completion
        readline.set_completer_delims(" \t\n;")
        readline.parse_and_bind("tab: complete")
        readline.set_completer(complete_path)

        while True:
            file_path = input("Enter path to AAC file: ").strip()
            # Expand ~ to home directory
            file_path = os.path.expanduser(file_path)
            if os.path.exists(file_path):
                break
            print("Error: File not found. Please try again.")

        # Reset completer
        readline.set_completer(None)

    processor = get_processor_for_file(file_path)
    if not processor:
        print(f"Error: Unsupported file type: {file_path}")
        sys.exit(1)

    # Show options
    print("\nAvailable actions:")
    print("1. View AAC structure")
    print("2. Convert to different format")
    print("3. Exit")

    while True:
        choice = input("\nSelect action (1-3): ").strip()

        if choice == "1":
            tree = processor.load_into_tree(file_path)
            print_tree(tree)
            break

        elif choice == "2":
            print("\nAvailable formats:")
            formats = list(get_available_formats().keys())
            for i, fmt in enumerate(formats, 1):
                print(f"{i}. {fmt}")

            while True:
                fmt_choice = input(
                    f"\nSelect target format (1-{len(formats)}): "
                ).strip()
                try:
                    target_format = formats[int(fmt_choice) - 1]
                    break
                except (ValueError, IndexError):
                    print("Invalid choice. Please try again.")

            output = input("Enter output path (or press Enter for default): ").strip()
            if convert_format(file_path, target_format, output):
                print("Conversion successful")
            break

        elif choice == "3":
            print("Goodbye!")
            sys.exit(0)

        else:
            print("Invalid choice. Please try again.")


def main():
    parser = argparse.ArgumentParser(description="AAC Format Processor and Converter")
    parser.add_argument("file_path", nargs="?", help="Path to AAC file")

    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument("--view", action="store_true", help="View AAC structure")
    action_group.add_argument(
        "--convert",
        choices=get_available_formats().keys(),
        help="Convert to specified format",
    )

    parser.add_argument("--output", help="Output file path")

    args = parser.parse_args()

    # If no arguments provided, run interactive mode
    if len(sys.argv) == 1:
        interactive_mode()
        return

    if not os.path.exists(args.file_path):
        print(f"Error: File not found: {args.file_path}")
        sys.exit(1)

    processor = get_processor_for_file(args.file_path)
    if not processor:
        print(f"Error: Unsupported file type: {args.file_path}")
        sys.exit(1)

    try:
        if args.convert:
            output_path = args.output
            if convert_format(args.file_path, args.convert, output_path):
                print("Conversion successful")
            else:
                print("Conversion failed")
                sys.exit(1)

        else:  # view (default)
            tree = processor.load_into_tree(args.file_path)
            print_tree(tree)

    except Exception as e:
        print(f"Error processing file: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
