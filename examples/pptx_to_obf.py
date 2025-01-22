#!/usr/bin/env python3
"""Demo script to convert PowerPoint files to OBF format."""

import sys
from pathlib import Path

from aac_processors.coughdrop_processor import CoughDropProcessor
from aac_processors.pptx_processor import PowerPointProcessor


def main() -> None:
    """Convert PowerPoint file to OBF format."""
    if len(sys.argv) < 3:
        print("Usage: pptx_to_obf.py input.pptx output.obf")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not Path(input_file).exists():
        print(f"Input file not found: {input_file}")
        sys.exit(1)

    print(f"Loading PowerPoint file: {input_file}")
    pptx_processor = PowerPointProcessor()
    tree = pptx_processor.load_into_tree(input_file)

    print(f"Creating OBF file: {output_file}")
    obf_processor = CoughDropProcessor()
    obf_processor.save_from_tree(tree, output_file)

    print("Conversion completed successfully!")


if __name__ == "__main__":
    main()
