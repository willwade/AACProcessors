#!/usr/bin/env python3

"""
Demo script showing how to convert an OBF file to PowerPoint format.
This script takes an OBF file as input and creates a PowerPoint presentation
where each board becomes a slide and each button becomes a text box.
"""

import os
import sys
from typing import Optional

from aac_processors.coughdrop_processor import CoughDropProcessor
from aac_processors.pptx_processor import PowerPointProcessor


def convert_obf_to_pptx(
    input_file: str, output_file: Optional[str] = None
) -> Optional[str]:
    """Convert OBF file to PowerPoint format.

    Args:
        input_file: Path to input OBF file
        output_file: Optional path for output PPTX file. If not provided,
                    will use input filename with .pptx extension

    Returns:
        Path to created PowerPoint file if successful, None otherwise
    """
    # Create processors
    obf_processor = CoughDropProcessor()
    pptx_processor = PowerPointProcessor()

    # Verify input file
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        return None

    if not obf_processor.can_process(input_file):
        print(f"Error: Input file is not a valid OBF file: {input_file}")
        return None

    try:
        # Load OBF into tree structure
        print(f"Loading OBF file: {input_file}")
        tree = obf_processor.load_into_tree(input_file)

        # Create output path if not provided
        if output_file is None:
            base_name = os.path.splitext(input_file)[0]
            output_file = f"{base_name}.pptx"

        # Save tree as PowerPoint
        print(f"Creating PowerPoint file: {output_file}")
        pptx_processor.save_from_tree(tree, output_file)

        print("Conversion completed successfully!")
        return output_file

    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        return None


def main() -> None:
    """Main entry point."""
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python obf_to_pptx.py <input_file.obf> [output_file.pptx]")
        sys.exit(1)

    # Get input and optional output paths
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    # Perform conversion
    result = convert_obf_to_pptx(input_file, output_file)
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
