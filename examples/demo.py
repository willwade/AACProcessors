"""Demo script showing usage of AAC processors."""

import os
from typing import NoReturn

from aac_processors import GridsetProcessor, viewer


def main() -> NoReturn:
    """Run demo examples."""
    # Demo files paths
    demo_dir = "demofiles"
    gridset_file = os.path.join(demo_dir, "SimpleTest.gridset")

    # Initialize processor
    processor = GridsetProcessor()

    # 1. View file structure
    print("\n=== Viewing File Structure ===")
    if os.path.exists(gridset_file):
        print(f"\nViewing structure of {os.path.basename(gridset_file)}:")
        viewer.print_tree(processor.load_into_tree(gridset_file))

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

    from aac_processors.cli import convert_format

    output_obz = convert_format(
        input_file=gridset_file,
        output_format="coughdrop",
        output_path="translated_grid.obz",
    )

    if output_obz:
        print(f"Successfully converted to OBZ: {output_obz}")
    else:
        print("Conversion failed")

    raise SystemExit(0)  # Exit cleanly


if __name__ == "__main__":
    main()
