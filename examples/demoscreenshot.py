"""Demo script for screenshot processing."""

from pathlib import Path

from aac_processors import viewer
from aac_processors.optional.screenshot_processor import ScreenshotProcessor

# Initialize processor
processor = ScreenshotProcessor(save_debug_images=True)  # Enable debug images

# Process example files
example_files = [
    ("TouchChat24.png", 6, 4),  # 6 rows, 4 columns
    (
        "TouchChat+HD+-+AAC+with+WordPower+60+Basic.jpg",
        6,  # rows
        10,  # columns
    ),
    ("proloquo2go.png", 7, 11),
]

for filename, rows, cols in example_files:
    print(f"\nProcessing {filename}:")
    print("-" * 50)

    # Full path to example file
    file_path = Path("examples") / "demofiles" / filename

    # Create tree from screenshot
    tree = processor.load_into_tree(str(file_path))

    # Print detected structure
    print("\nDetected board structure:\n")
    viewer.print_tree(tree)

    # Print navigation analysis
    print("\n=== Navigation Analysis ===\n")
    print(f"Total Pages: {len(tree.pages)}\n")

    # Extract and print texts
    texts = processor.extract_texts(str(file_path))
    print("Extracting texts:")
    print(f"Found {len(texts)} text items:")
    for text in texts:
        print(f"- {text}")

    # Print detailed page info
    print("\nDetailed page information:")
    page = list(tree.pages.values())[0]  # First page
    print(f"Grid size: {page.grid_size}")
    print(f"Expected buttons: {rows * cols}, Found: {len(page.buttons)}\n")

    print("Buttons with text:")
    for btn in page.buttons:
        print(
            f"- Position {btn.position}: '{btn.label}' "
            f"(color: {btn.style.body_color})"
        )
