#!/usr/bin/env python3

import argparse
import glob
import os
import readline
import sys
from typing import Optional, Union

from .coughdrop_processor import CoughDropProcessor
from .gridset_processor import GridsetProcessor
from .snap_processor import SnapProcessor
from .touchchat_processor import TouchChatProcessor
from .tree_structure import AACTree
from .viewer import get_processor_for_file, print_tree

# Type alias for processors
ProcessorType = Union[
    GridsetProcessor, TouchChatProcessor, SnapProcessor, CoughDropProcessor
]


def complete_path(text: str, state: int) -> Optional[str]:
    """Tab completion function for file paths"""
    if "~" in text:
        text = os.path.expanduser(text)

    # If text is a directory, return it with a trailing slash
    if os.path.isdir(text):
        return text + "/" if not text.endswith("/") else text

    dir_name = os.path.dirname(text)
    if dir_name and not os.path.exists(dir_name):
        return None

    # Get pattern for matching
    if dir_name:
        pattern = os.path.join(dir_name, os.path.basename(text) + "*")
    else:
        pattern = text + "*"

    # Get matches and sort them (directories first)
    matches = glob.glob(pattern)
    matches = sorted(
        [f"{m}{'/' if os.path.isdir(m) else ''}" for m in matches],
        key=lambda x: (not x.endswith("/"), x),  # Sort directories first
    )

    return matches[state] if state < len(matches) else None


def get_available_formats() -> list[str]:
    """Get list of available format names"""
    return ["grid", "touchchat", "snap", "coughdrop"]


def convert_format(
    input_file: str, output_format: str, output_path: Optional[str] = None
) -> Optional[str]:
    """Convert between AAC formats

    Args:
        input_file: Path to input AAC file
        output_format: Target format name
        output_path: Optional output path (default: auto-generated)

    Returns:
        Path to output file if successful, None otherwise
    """
    try:
        # Get source processor
        source_processor = get_processor_for_file(input_file)
        if not source_processor:
            print(f"Error: Unsupported input format: {input_file}")
            return None

        print(f"Loading {input_file}")
        # Load into tree structure
        tree = source_processor.load_into_tree(input_file)
        if not tree or not isinstance(tree, AACTree):
            print("Error: Failed to load input file into tree structure")
            return None

        print(f"Loaded tree with {len(tree.pages)} pages")

        # Get target processor based on format
        target_processor: Optional[ProcessorType] = None
        if output_format == "grid":
            target_processor = GridsetProcessor()
        elif output_format == "touchchat":
            target_processor = TouchChatProcessor()
        elif output_format == "snap":
            target_processor = SnapProcessor()
        elif output_format == "coughdrop":
            target_processor = CoughDropProcessor()

        if not target_processor:
            print(f"Error: Unsupported output format: {output_format}")
            return None

        # Generate output path if not provided
        if not output_path:
            base = os.path.splitext(input_file)[0]
            # Each processor should define its default extension
            ext = getattr(target_processor, "default_extension", ".unknown")
            output_path = f"{base}_converted{ext}"

        print(f"Converting to {output_format} format at {output_path}")
        # Export tree using target processor
        target_processor.export_tree(tree, output_path)
        return output_path

    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        return None


def interactive_mode() -> None:
    """Interactive CLI mode"""
    print("\nAAC Processor Tool")
    print("=================\n")

    # Set up tab completion
    readline.set_completer_delims(" \t\n;")
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete_path)

    # Get input file
    while True:
        file_path = input("Enter path to AAC file: ").strip()
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
            formats = get_available_formats()
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

            prompt = "Enter output path (or press Enter for default): "
            output_path: Optional[str] = input(prompt).strip()
            output_path = output_path if output_path else None
            if convert_format(file_path, target_format, output_path):
                print("Conversion successful")
            break

        elif choice == "3":
            print("Goodbye!")
            sys.exit(0)

        else:
            print("Invalid choice. Please try again.")


def main() -> None:
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(description="AAC Format Processor and Converter")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # View command
    view_parser = subparsers.add_parser("view", help="View AAC structure")
    view_parser.add_argument("file", help="Path to AAC file")

    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert AAC format")
    convert_parser.add_argument("input", help="Input AAC file")
    convert_parser.add_argument(
        "--to", choices=get_available_formats(), required=True, help="Target format"
    )
    convert_parser.add_argument("--output", help="Output file path (optional)")

    args = parser.parse_args()

    # If no command specified, run interactive mode
    if not args.command:
        interactive_mode()
        return

    # Handle view command
    if args.command == "view":
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}")
            sys.exit(1)

        processor = get_processor_for_file(args.file)
        if not processor:
            print(f"Error: Unsupported file type: {args.file}")
            sys.exit(1)

        try:
            tree = processor.load_into_tree(args.file)
            print_tree(tree)
        except Exception as e:
            print(f"Error viewing file: {str(e)}")
            sys.exit(1)

    # Handle convert command
    elif args.command == "convert":
        if not os.path.exists(args.input):
            print(f"Error: File not found: {args.input}")
            sys.exit(1)

        if convert_format(args.input, args.to, args.output):
            print("Conversion successful")
        else:
            print("Conversion failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
