"""Example script showing how to convert a screenshot to OBF format."""

from pathlib import Path

from aac_processors import viewer
from aac_processors.coughdrop_processor import CoughDropProcessor  # For OBF format
from aac_processors.optional.screenshot_processor import ScreenshotProcessor
from aac_processors.tree_structure import AACTree  # Import AACTree

# First install the package with dependencies:
# uv pip install -e ".[dev,screenshot]"

# Initialize processors
screenshot_processor = ScreenshotProcessor(
    save_debug_images=True
)  # Set to True to save debug images
coughdrop_processor = CoughDropProcessor()

# Input screenshot
input_file = Path("examples/demofiles/IMG_2427.JPG")
output_file = input_file.with_suffix(".obf")  # OBF extension

# Create tree from screenshot
page = screenshot_processor.create_page_from_screenshot(
    str(input_file),
    grid_rows=6,  # Specify number of rows
    grid_cols=4,  # Specify number of columns
)

# Create tree with the page
tree = AACTree()
tree.add_page(page)

# Show what we detected
print("\nDetected board structure:")
viewer.print_tree(tree)

# Print detailed page info
page = list(tree.pages.values())[0]  # First page
print("\nDetailed page information:")
print(f"Grid size: {page.grid_size}")
print(f"Expected buttons: {2 *3}, Found: {len(page.buttons)}\n")

print("Buttons with text:")
for btn in page.buttons:
    print(f"- Position {btn.position}: '{btn.label}' (color: {btn.style.body_color})")

# Then save tree as OBF format
coughdrop_processor.save_from_tree(tree, str(output_file))

print(f"\nConverted {input_file} to {output_file}")
