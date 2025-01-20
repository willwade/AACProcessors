"""Processor for Apple Panels format (.ascconfig)."""

import os
import plistlib
from pathlib import Path
from typing import Any, Optional

from .file_processor import FileProcessor
from .tree_structure import AACButton, AACPage, AACTree, ButtonStyle, ButtonType


class ApplePanelsProcessor(FileProcessor):
    """Process Apple Panels format (.ascconfig folders)."""

    def __init__(self) -> None:
        """Initialize the processor."""
        super().__init__()
        self.collected_texts = []
        self.file_path: Optional[str] = None
        self.original_filename: Optional[str] = None
        self.original_file_path: Optional[str] = None

    def can_process(self, file_path: str) -> bool:
        """Check if file is an Apple Panels config.

        Args:
            file_path: Path to check

        Returns:
            True if path ends with .ascconfig
        """
        return file_path.lower().endswith(".ascconfig")

    def _load_plist(self, file_path: str) -> dict[str, Any]:
        """Load and parse a plist file.

        Args:
            file_path: Path to plist file

        Returns:
            Parsed plist data as dictionary
        """
        with open(file_path, "rb") as f:
            return plistlib.load(f)

    def _extract_button_info(
        self, button_dict: dict[str, Any]
    ) -> tuple[str, str, str, tuple[int, int]]:
        """Extract button information from button dictionary.

        Args:
            button_dict: Dictionary containing button data

        Returns:
            Tuple of (id, text, color, position)
        """
        # Extract button ID
        button_id = button_dict.get("ID", "")

        # Get display text
        text = button_dict.get("DisplayText", "")

        # Get color (default to white if not specified)
        color = button_dict.get("DisplayColor", "1.000 1.000 1.000 1.000")

        # Parse rect string like "{{x, y}, {w, h}}"
        rect_str = button_dict.get("Rect", "{{0, 0}, {0, 0}}")
        try:
            # Remove braces and split
            rect_parts = rect_str.replace("{", "").replace("}", "").split(",")
            x = int(float(rect_parts[0]))
            y = int(float(rect_parts[1]))
            # Calculate grid position based on coordinates
            # Assuming standard button size of 100x25
            row = y // 100
            col = x // 100
        except (ValueError, IndexError):
            row, col = 0, 0

        return button_id, text, color, (row, col)

    def _convert_color(self, color_str: str) -> str:
        """Convert color string from Apple format to hex.

        Args:
            color_str: Color string in format "r g b a" with values 0-1

        Returns:
            Hex color string like "#RRGGBB"
        """
        try:
            # Split color components and convert to 0-255 range
            r, g, b, _ = [float(x) for x in color_str.split()]
            return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        except (ValueError, IndexError):
            return "#ffffff"  # Default to white

    def load_into_tree(self, file_path: str) -> AACTree:
        """Load Apple Panels config into tree structure.

        Args:
            file_path: Path to .ascconfig folder

        Returns:
            Tree structure containing pages and buttons
        """
        tree = AACTree()

        # Check paths
        contents_dir = Path(file_path) / "Contents"
        if not contents_dir.exists():
            msg = f"Invalid Apple Panels config - no Contents directory in {file_path}"
            raise ValueError(msg)

        # Load Info.plist
        info_path = contents_dir / "Info.plist"
        if not info_path.exists():
            raise ValueError(f"Missing Info.plist in {file_path}")

        self._load_plist(str(info_path))

        # Load panel definitions
        panels_path = contents_dir / "Resources" / "PanelDefinitions.plist"
        if not panels_path.exists():
            raise ValueError(f"Missing PanelDefinitions.plist in {file_path}")

        panels = self._load_plist(str(panels_path))

        # Process each panel
        for panel_id, panel_data in panels.get("Panels", {}).items():
            # Create page for panel
            page = AACPage(
                id=panel_id,
                name=panel_data.get("Name", "Untitled Panel"),
                grid_size=(0, 0),  # Will be calculated from buttons
            )

            # Process buttons
            max_row = 0
            max_col = 0
            for button_data in panel_data.get("PanelObjects", []):
                if button_data.get("PanelObjectType") == "Button":
                    # Extract button info
                    btn_id, text, color, pos = self._extract_button_info(button_data)
                    row, col = pos

                    # Track grid size
                    max_row = max(max_row, row)
                    max_col = max(max_col, col)

                    # Create button
                    btn = AACButton(
                        id=btn_id,
                        label=text,
                        type=ButtonType.SPEAK,  # Default to speak
                        position=pos,
                        style=ButtonStyle(body_color=self._convert_color(color)),
                    )

                    # Check for navigation action
                    actions = button_data.get("Actions", [])
                    for action in actions:
                        if action.get("ActionType") == "ActionOpenPanel":
                            btn.type = ButtonType.NAVIGATE
                            target = action.get("ActionParam", {})
                            btn.target_page_id = target.get("PanelID")
                        elif action.get("ActionType") == "ActionPressKeyCharSequence":
                            params = action.get("ActionParam", {})
                            btn.vocalization = params.get("CharString", text)

                    page.buttons.append(btn)

            # Update grid size
            page.grid_size = (max_row + 1, max_col + 1)

            # Add page to tree
            tree.add_page(page)

        return tree

    def save_from_tree(self, tree: AACTree, output_path: str) -> None:
        """Save tree structure as Apple Panels config.

        Args:
            tree: Tree structure to save
            output_path: Path to save to (must end with .ascconfig)
        """
        if not output_path.endswith(".ascconfig"):
            output_path += ".ascconfig"

        # Create directory structure
        config_dir = Path(output_path)
        contents_dir = config_dir / "Contents"
        resources_dir = contents_dir / "Resources"
        os.makedirs(resources_dir, exist_ok=True)

        # Create Info.plist
        stem = Path(output_path).stem
        info = {
            "ASCConfigurationDisplayName": "Converted Configuration",
            "ASCConfigurationIdentifier": str(stem),
            "ASCConfigurationProductSupportType": "VirtualKeyboard",
            "ASCConfigurationVersion": "7.1",
            "CFBundleDevelopmentRegion": "en",
            "CFBundleIdentifier": f"com.apple.AssistiveControl.panel.{stem}",
            "CFBundleName": "Assistive Control Panels",
            "CFBundleShortVersionString": "2.0",
            "CFBundleVersion": "1",
            "NSHumanReadableCopyright": "Generated by AAC Processors",
        }

        with open(contents_dir / "Info.plist", "wb") as f:
            plistlib.dump(info, f)

        # Create AssetIndex.plist for images
        assets = {}

        # Convert pages to panels
        panels = {
            "Panels": {},
            "ToolbarOrdering": {
                "ToolbarIdentifiersAfterBasePanel": [],
                "ToolbarIdentifiersPriorToBasePanel": [],
            },
        }

        # Convert pages to panels
        for page in tree.pages.values():
            panel = {
                "DisplayOrder": 1,
                "GlidingLensSize": 5,
                "HasTransientPosition": False,
                "HideHome": False,
                "HideMinimize": False,
                "HidePanelAdjustments": False,
                "HideSwitchDock": False,
                "HideSwitchDockContextualButtons": False,
                "HideTitlebar": False,
                "ID": page.id,
                "Name": page.name,
                "PanelObjects": [],
                "ProductSupportType": "All",
                "Rect": "{{15, 75}, {425, 55}}",
                "ScanStyle": 0,
                "ShowPanelLocationString": "CustomPanelList",
                "UsesPinnedResizing": False,
            }

            # Get page dimensions
            rows, cols = page.grid_size
            page_width = 1100  # Default width
            page_height = page_width * (
                rows / cols
            )  # Make height proportional to maintain square buttons
            button_size = min(page_width / cols, page_height / rows)  # Square buttons

            # Convert buttons
            for btn in page.buttons:
                # Use absolute position if available, otherwise calculate from grid
                if btn.left is not None and btn.top is not None:
                    x = int(btn.left * page_width)
                    y = int(btn.top * page_height)
                else:
                    row, col = btn.position
                    x = int(col * button_size)
                    y = int(row * button_size)

                # Use square button dimensions
                width = int(button_size)
                height = int(button_size)

                button = {
                    "ButtonType": 0,
                    "DisplayColor": self._convert_hex_to_apple_color(
                        btn.style.body_color or "#ffffff"
                    ),
                    "DisplayImageResourceIsTemplate": False,
                    "DisplayImageWeight": "FontWeightRegular",
                    "DisplayText": btn.label,
                    "FontSize": 12,
                    "ID": btn.id,
                    "PanelObjectType": "Button",
                    "Rect": f"{{{{{x}, {y}}}, {{{width}, {height}}}}}",
                }

                # Handle image if present
                if btn.image and btn.image.get("url"):
                    import uuid

                    # Generate unique image ID in Apple format
                    image_id = f"Image.{str(uuid.uuid4()).upper()}"

                    # Add to assets index with proper format
                    assets[image_id] = {
                        "Type": "Image",
                        "Name": btn.label
                        or "Button Image",  # Use button label as image name
                    }

                    # Add image reference to button
                    button["DisplayImageResource"] = image_id

                    # Download and save image directly in Resources
                    try:
                        import requests

                        response = requests.get(btn.image["url"])
                        if response.status_code == 200:
                            # Save image with the same ID as referenced
                            with open(resources_dir / image_id, "wb") as f:
                                f.write(response.content)
                    except Exception as e:
                        self.debug(f"Failed to download image {btn.image['url']}: {e}")

                # Add actions
                if btn.type == ButtonType.NAVIGATE and btn.target_page_id:
                    button["Actions"] = [
                        {
                            "ActionParam": {"PanelID": btn.target_page_id},
                            "ActionRecordedOffset": 0.0,
                            "ActionType": "ActionOpenPanel",
                            "ID": f"Action.{btn.id}",
                        }
                    ]
                elif btn.vocalization:
                    button["Actions"] = [
                        {
                            "ActionParam": {
                                "CharString": btn.vocalization,
                                "isStickyKey": False,
                            },
                            "ActionRecordedOffset": 0.0,
                            "ActionType": "ActionPressKeyCharSequence",
                            "ID": f"Action.{btn.id}",
                        }
                    ]

                panel["PanelObjects"].append(button)

            panels["Panels"][page.id] = panel

        # Save AssetIndex.plist
        with open(resources_dir / "AssetIndex.plist", "wb") as f:
            plistlib.dump(assets, f)

        # Save panel definitions
        with open(resources_dir / "PanelDefinitions.plist", "wb") as f:
            plistlib.dump(panels, f)

    def _convert_hex_to_apple_color(self, hex_color: str) -> str:
        """Convert hex color to Apple color string format.

        Args:
            hex_color: Color in hex format (#RRGGBB)

        Returns:
            Color string in format "r g b a" with values 0-1
        """
        try:
            # Remove # and convert to RGB
            rgb = tuple(int(hex_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
            # Convert to 0-1 range and add alpha
            return f"{rgb[0]/255:.3f} {rgb[1]/255:.3f} {rgb[2]/255:.3f} 1.000"
        except (ValueError, IndexError):
            return "1.000 1.000 1.000 1.000"  # Default white

    def extract_texts(self, file_path: str) -> list[str]:
        """Extract all text content from Apple Panels config.

        Args:
            file_path: Path to .ascconfig folder

        Returns:
            List of extracted texts
        """
        tree = self.load_into_tree(file_path)
        texts = []

        for page in tree.pages.values():
            if page.name:
                texts.append(page.name)
            for btn in page.buttons:
                if btn.label:
                    texts.append(btn.label)
                if btn.vocalization and btn.vocalization != btn.label:
                    texts.append(btn.vocalization)

        return texts

    def process_files(
        self, directory: str, translations: Optional[dict[str, str]] = None
    ) -> Optional[str]:
        """Process files in directory.

        Args:
            directory: Directory containing files to process
            translations: Optional translations to apply

        Returns:
            Path to translated file if translations applied, None otherwise
        """
        try:
            # Load tree structure
            tree = self.load_into_tree(directory)

            if translations is None:
                # Just collect texts
                self.collected_texts = self.extract_texts(directory)
                return None

            # Apply translations
            for page in tree.pages.values():
                if page.name in translations:
                    page.name = translations[page.name]

                for btn in page.buttons:
                    if btn.label in translations:
                        btn.label = translations[btn.label]
                    if btn.vocalization in translations:
                        btn.vocalization = translations[btn.vocalization]

            # Save translated version
            target_lang = translations.get("target_lang", "unknown")
            base = os.path.splitext(directory)[0]
            output_path = f"{base}_{target_lang}.ascconfig"
            self.save_from_tree(tree, output_path)

            return output_path

        except Exception as e:
            self.debug(f"Error processing files: {str(e)}")
            return None

    def create_translated_file(
        self, file_path: str, translations: dict[str, str]
    ) -> Optional[str]:
        """Create a translated version of the file.

        Args:
            file_path: Path to source file
            translations: Dictionary of text translations

        Returns:
            Path to translated file if successful, None otherwise
        """
        try:
            # Load tree structure
            tree = self.load_into_tree(file_path)

            # Apply translations
            for page in tree.pages.values():
                if page.name in translations:
                    page.name = translations[page.name]

                for btn in page.buttons:
                    if btn.label in translations:
                        btn.label = translations[btn.label]
                    if btn.vocalization in translations:
                        btn.vocalization = translations[btn.vocalization]

            # Save translated version
            target_lang = translations.get("target_lang", "unknown")
            base = os.path.splitext(file_path)[0]
            output_path = f"{base}_{target_lang}.ascconfig"
            self.save_from_tree(tree, output_path)

            return output_path

        except Exception as e:
            self.debug(f"Error creating translated file: {str(e)}")
            return None
