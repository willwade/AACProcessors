"""Example script showing how to convert an OBF file to Apple Panels format."""

from pathlib import Path

from aac_processors import viewer
from aac_processors.apple_panels_processor import ApplePanelsProcessor
from aac_processors.coughdrop_processor import CoughDropProcessor

# First install the package with dependencies:
# uv pip install -e ".[dev]"

# Initialize processors
coughdrop_processor = CoughDropProcessor()
panels_processor = ApplePanelsProcessor()

# Input OBF file
input_file = Path("examples/demofiles/project-core_es.obf")
output_file = input_file.with_suffix(".ascconfig")  # Apple Panels extension

# Load OBF into tree structure
tree = coughdrop_processor.load_into_tree(str(input_file))

# Show what we detected
print("\nDetected board structure:")
viewer.print_tree(tree)

# Print detailed page info
page = list(tree.pages.values())[0]  # First page
print("\nDetailed page information:")
print(f"Grid size: {page.grid_size}")
print(f"Found: {len(page.buttons)} buttons\n")

print("Buttons with text and images:")
for btn in page.buttons:
    has_image = bool(btn.image and btn.image.get("url"))
    image_info = f"(image: {btn.image['url']})" if has_image else "(no image)"
    print(f"- Position {btn.position}: '{btn.label}' {image_info}")

# Convert tree to Apple Panels format
panels_processor.save_from_tree(tree, str(output_file))

print(f"\nConverted {input_file} to {output_file}")
print("Images will be downloaded to Contents/Resources/Images/")
