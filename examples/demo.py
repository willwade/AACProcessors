"""Demo script showing usage of AAC processors."""

import os
import sys
from typing import NoReturn

# Add parent directory to path so we can import aac_processors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aac_processors import GridsetProcessor, viewer
from aac_processors.cli import convert_format


def main() -> NoReturn:
    """Run demo examples."""
    # Demo files paths - use absolute paths based on script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    demo_dir = os.path.join(script_dir, "demofiles")
    gridset_file = os.path.join(demo_dir, "SimpleTest.gridset")
    communikate_file = os.path.join(demo_dir, "communikate-20.obz")
    dot_file = os.path.join(demo_dir, "prag.dot")
    opml_file = os.path.join(demo_dir, "prag.opml")

    print("\n=== DEMO 1: Basic GridSet Processing ===")
    # Initialize processor
    processor = GridsetProcessor()

    # 1. View file structure
    print("\n=== Viewing File Structure ===")
    if os.path.exists(gridset_file):
        print(f"\nViewing structure of {os.path.basename(gridset_file)}:")
        viewer.print_tree(processor.load_into_tree(gridset_file))
    else:
        print(f"GridSet file not found: {gridset_file}")

    # 2. Extract texts
    print("\n=== Extracting Texts ===")
    if os.path.exists(gridset_file):
        texts = processor.extract_texts(gridset_file)
        print(f"\nExtracted {len(texts)} texts from {os.path.basename(gridset_file)}")
        print("Sample texts:", texts[:5])

    # 3. Load into tree structure
    print("\n=== Loading Tree Structure ===")
    if os.path.exists(gridset_file):
        tree = processor.load_into_tree(gridset_file)
        print(f"\nLoaded {len(tree.pages)} pages from {os.path.basename(gridset_file)}")
        for page_id, page in list(tree.pages.items())[:2]:  # Show first 2 pages
            print(f"\nPage {page_id}: {page.name}")
            print(f"Grid size: {page.grid_size}")
            print(f"Buttons: {len(page.buttons)}")

    # 4. Convert format
    print("\n=== Converting GridSet to CoughDrop ===")
    if os.path.exists(gridset_file):
        output_obz = convert_format(
            input_file=gridset_file,
            output_format="coughdrop",
            output_path=os.path.join(script_dir, "translated_grid.obz"),
        )

        if output_obz:
            print(f"Successfully converted to OBZ: {output_obz}")
        else:
            print("Conversion failed")
    else:
        print(f"GridSet file not found: {gridset_file}")

    # DEMO 2: Convert CommuniKate to DOT and OPML
    print("\n=== DEMO 2: Convert CommuniKate to DOT and OPML ===")
    if os.path.exists(communikate_file):
        # Convert to DOT
        print("\n=== Converting CommuniKate to DOT ===")
        output_dot = convert_format(
            input_file=communikate_file,
            output_format="dot",
            output_path=os.path.join(script_dir, "communikate.dot"),
        )
        if output_dot:
            print(f"Successfully converted to DOT: {output_dot}")
        else:
            print("Conversion to DOT failed")

        # Convert to OPML
        print("\n=== Converting CommuniKate to OPML ===")
        output_opml = convert_format(
            input_file=communikate_file,
            output_format="opml",
            output_path=os.path.join(script_dir, "communikate.opml"),
        )
        if output_opml:
            print(f"Successfully converted to OPML: {output_opml}")
        else:
            print("Conversion to OPML failed")
    else:
        print(f"CommuniKate file not found: {communikate_file}")

    # DEMO 3: Convert DOT and OPML to GridSet
    print("\n=== DEMO 3: Convert DOT and OPML to GridSet ===")

    # Convert DOT to GridSet
    if os.path.exists(dot_file):
        print("\n=== Converting DOT to GridSet ===")
        output_gridset = convert_format(
            input_file=dot_file,
            output_format="grid",
            output_path=os.path.join(script_dir, "prag_from_dot.gridset"),
        )
        if output_gridset:
            print(f"Successfully converted to GridSet: {output_gridset}")
        else:
            print("Conversion from DOT to GridSet failed")
    else:
        print(f"DOT file not found: {dot_file}")

    # Convert OPML to GridSet
    if os.path.exists(opml_file):
        print("\n=== Converting OPML to GridSet ===")
        output_gridset = convert_format(
            input_file=opml_file,
            output_format="grid",
            output_path=os.path.join(script_dir, "prag_from_opml.gridset"),
        )
        if output_gridset:
            print(f"Successfully converted to GridSet: {output_gridset}")
        else:
            print("Conversion from OPML to GridSet failed")
    else:
        print(f"OPML file not found: {opml_file}")

    # DEMO 4: Convert between DOT and OPML formats
    print("\n=== DEMO 4: Convert between DOT and OPML formats ===")

    # Convert DOT to OPML
    if os.path.exists(dot_file):
        print("\n=== Converting DOT to OPML ===")
        output_opml_from_dot = convert_format(
            input_file=dot_file,
            output_format="opml",
            output_path=os.path.join(script_dir, "prag_from_dot.opml"),
        )
        if output_opml_from_dot:
            print(f"Successfully converted DOT to OPML: {output_opml_from_dot}")
        else:
            print("Conversion from DOT to OPML failed")
    else:
        print(f"DOT file not found: {dot_file}")

    # Convert OPML to DOT
    if os.path.exists(opml_file):
        print("\n=== Converting OPML to DOT ===")
        output_dot_from_opml = convert_format(
            input_file=opml_file,
            output_format="dot",
            output_path=os.path.join(script_dir, "prag_from_opml.dot"),
        )
        if output_dot_from_opml:
            print(f"Successfully converted OPML to DOT: {output_dot_from_opml}")
        else:
            print("Conversion from OPML to DOT failed")
    else:
        print(f"OPML file not found: {opml_file}")

    raise SystemExit(0)  # Exit cleanly


if __name__ == "__main__":
    main()
