import json
import os
import shutil
import tempfile
import zipfile
from typing import Any, Optional, Union

from .file_processor import FileProcessor
from .tree_structure import AACButton, AACPage, AACSymbol, AACTree, ButtonType


class CoughDropProcessor(FileProcessor):
    """Processor for CoughDrop OBZ/OBF files."""

    def __init__(self) -> None:
        """Initialize CoughDrop processor."""
        super().__init__()
        self.collected_texts: list[str] = []
        self.file_path: Optional[str] = None
        self.original_filename: Optional[str] = None
        self.original_file_path: Optional[str] = None

    def can_process(self, file_path: str) -> bool:
        """Check if file can be processed.

        Args:
            file_path (str): Path to the file to check.

        Returns:
            bool: True if file can be processed, False otherwise.
        """
        return file_path.endswith(".obz") or file_path.endswith(".obf")

    def export_tree(self, tree: AACTree, output_path: str) -> None:
        """Export tree to OBF/OBZ format.

        Args:
            tree (AACTree): Tree to export.
            output_path (str): Path where to save the file.
        """
        self.save_from_tree(tree, output_path)

    def _load_board_into_tree(self, file_path: str, tree: AACTree) -> None:
        """Load board data into tree structure.

        Args:
            file_path: Path to the OBF file to load
            tree: Tree to add the board to
        """
        try:
            # Load and parse the JSON file first
            with open(file_path, encoding="utf-8") as f:
                board_data = json.load(f)

            # Get grid dimensions
            grid = board_data.get("grid", {})
            rows = grid.get("rows", 1)
            cols = grid.get("columns", 1)

            # Create page
            # Map OBF image id to loaded image dict for faster lookup
            images_map = {img.get("id"): img for img in board_data.get("images", []) if img.get("id")}

            page = AACPage(
                id=board_data.get("id", ""),
                name=board_data.get("name", ""),
                grid_size=(rows, cols),
                parent_id=None,  # Will be set when processing navigation buttons
            )

            # Process buttons
            buttons = board_data.get("buttons", [])
            for button in buttons:
                # Get button type and target
                button_type = ButtonType.SPEAK
                target_page_id = None
                action = None

                if "load_board" in button:
                    button_type = ButtonType.NAVIGATE
                    target_page_id = button["load_board"].get("id", "")
                    # Set parent_id for the target page if it exists
                    if target_page_id and target_page_id in tree.pages:
                        tree.pages[target_page_id].parent_id = page.id
                elif "action" in button:
                    button_type = ButtonType.ACTION
                    action = button["action"]

                # Get position from grid order
                pos_x = 0
                pos_y = 0
                if "grid" in board_data:
                    order = grid.get("order", [])
                    for i, row in enumerate(order):
                        if button["id"] in row:
                            pos_y = i
                            pos_x = row.index(button["id"])
                            break  # Found position, exit inner loop

                # Get image data if present
                symbol: Optional[AACSymbol] = None
                if "image_id" in button:
                    image_id = button["image_id"]
                    if image_id in images_map:
                        img_data = images_map[image_id]
                        internal_id = img_data.get("id")
                        data_url = img_data.get("data")
                        url = img_data.get("url")
                        library = img_data.get("symbol_set")
                        identifier = img_data.get("symbol_key")
                        content_type = img_data.get("content_type")  # Usually present with data url

                        if data_url:
                            symbol = AACSymbol.from_data_url(data_url, internal_id=internal_id)
                        elif url:
                            symbol = AACSymbol(url=url, content_type=content_type, internal_id=internal_id)
                        elif library and identifier:
                            symbol = AACSymbol(library=library, identifier=identifier, internal_id=internal_id)
                        # Add path handling here if supporting direct OBZ extraction later
                        else:
                            # Store raw image dict if no other info? Or create empty symbol?
                            # Let's create an empty symbol for now, maybe log warning
                            symbol = AACSymbol(internal_id=internal_id)
                            self.debug(f"Image {internal_id} has no parsable data, url, or symbol info.")

                # Get dimensions - these are percentages in OBF format
                # Provide default grid-based sizes if width/height missing
                default_width = 1.0 / cols if cols > 0 else 1.0
                default_height = 1.0 / rows if rows > 0 else 1.0
                width = button.get("width", default_width)
                height = button.get("height", default_height)
                left = button.get("left")  # Optional absolute position
                top = button.get("top")

                # Create button
                btn = AACButton(
                    id=button.get("id", ""),
                    label=button.get("label", ""),
                    type=button_type,
                    position=(pos_y, pos_x),
                    target_page_id=target_page_id,
                    vocalization=button.get("vocalization", ""),
                    action=action,
                    symbol=symbol,
                    width=width,
                    height=height,
                    left=left,
                    top=top,
                )

                # Set button style
                if "background_color" in button:
                    btn.style.body_color = button["background_color"]
                if "border_color" in button:
                    btn.style.border_color = button["border_color"]

                page.buttons.append(btn)

            tree.add_page(page)
        except Exception as e:
            self.debug(f"Error loading board file {file_path}: {str(e)}")
            raise

    def _convert_page_to_board(self, page: AACPage, tree: AACTree) -> dict[str, Any]:
        """Convert a page to a board format.

        Args:
            page (AACPage): Page to convert.
            tree (AACTree): Full tree containing all pages.

        Returns:
            Dict[str, Any]: Board data.
        """
        rows, cols = page.grid_size
        grid_order: list[list[Optional[str]]] = [[None] * cols for _ in range(rows)]
        buttons_data: list[dict[str, Any]] = []
        images_data: list[dict[str, Any]] = []
        # Keep track of added symbols to avoid duplicates in images_data
        # Map symbol content representation (url, datahash, lib+id) to its OBF image_id
        added_symbol_map: dict[str, str] = {}
        next_image_id_counter = 0

        # First pass: Create all buttons and track their positions
        for button in page.buttons:
            # Create button data
            button_data: dict[str, Any] = {"id": button.id, "label": button.label}

            # Add background color if present
            if button.style and button.style.body_color:
                button_data["background_color"] = button.style.body_color

            if button.vocalization and button.vocalization != button.label:
                button_data["vocalization"] = button.vocalization

            # Add image if present
            if button.symbol:
                symbol = button.symbol
                image_id = None
                symbol_key = None  # Key to check if this exact symbol data is already added

                # Create base image entry with dimensions
                base_image = {
                    "width": symbol.width if symbol.width else 1024,  # Default width if not specified
                    "height": symbol.height if symbol.height else 768,  # Default height if not specified
                    "content_type": symbol.content_type or "image/png"
                }

                if symbol.url:
                    symbol_key = symbol.url
                    base_image["url"] = symbol.url
                elif symbol.data:
                    # Use hash of data as key to avoid duplicates
                    symbol_key = str(hash(symbol.data))
                    # Add data URI scheme prefix if not present
                    data = symbol.data
                    if isinstance(data, bytes):
                        # Convert bytes to base64 string if needed
                        import base64
                        data = base64.b64encode(data).decode('utf-8')
                    if not isinstance(data, str):
                        data = str(data)
                    if not data.startswith('data:'):
                        data = f"data:{base_image['content_type']};base64,{data}"
                    base_image["data"] = data
                elif symbol.library and symbol.identifier:
                    symbol_key = f"{symbol.library}:{symbol.identifier}"
                    base_image["symbol_set"] = symbol.library
                    base_image["symbol_key"] = symbol.identifier

                if symbol_key in added_symbol_map:
                    # Reuse existing image_id if we've seen this symbol before
                    image_id = added_symbol_map[symbol_key]
                else:
                    # Create new image entry
                    image_id = str(next_image_id_counter)
                    next_image_id_counter += 1
                    base_image["id"] = image_id
                    added_symbol_map[symbol_key] = image_id
                    images_data.append(base_image)

                button_data["image_id"] = image_id

            # Only add navigation if target page exists in the tree
            if button.type == ButtonType.NAVIGATE and button.target_page_id:
                if button.target_page_id in tree.pages:
                    button_data["load_board"] = {
                        "id": button.target_page_id,
                        "path": f"boards/{button.target_page_id}.obf",
                    }
                else:
                    self.debug(
                        f"Warning: Navigation target {button.target_page_id} not found, converting to speak button"
                    )

            # Add to grid order if position is valid
            y, x = button.position
            if 0 <= y < rows and 0 <= x < cols:
                grid_order[y][x] = button.id
            else:
                # If button position is outside grid, append to first available spot
                placed = False
                for i in range(rows):
                    if placed:
                        break
                    for j in range(cols):
                        if grid_order[i][j] is None:
                            grid_order[i][j] = button.id
                            placed = True
                            break

            buttons_data.append(button_data)

        # If there are no buttons, return a minimal valid board
        if not buttons_data:
            return {
                "format": "open-board-0.1",
                "id": page.id,
                "name": page.name,
                "locale": "en_US",
                "grid": {
                    "rows": 1,
                    "columns": 1,
                    "order": [[None]]
                },
                "buttons": [],
                "images": [],
                "sounds": []
            }

        # For pages with buttons, ensure grid only references existing button IDs
        # Calculate minimum grid size needed to fit all buttons
        if not any(any(cell is not None for cell in row) for row in grid_order):
            # No buttons were placed in their original positions
            # Calculate a reasonable grid size based on number of buttons
            button_count = len(buttons_data)
            grid_size = max(1, int((button_count ** 0.5) + 0.5))  # Square root rounded up
            rows = cols = grid_size
            grid_order = [[None] * cols for _ in range(rows)]

            # Place buttons in a grid pattern
            button_idx = 0
            for i in range(rows):
                for j in range(cols):
                    if button_idx < len(buttons_data):
                        grid_order[i][j] = buttons_data[button_idx]["id"]
                        button_idx += 1

        # Ensure all cells contain either a valid button ID or None
        final_grid_order = []
        for row in grid_order:
            final_row = []
            for cell in row:
                if cell and any(b["id"] == cell for b in buttons_data):
                    final_row.append(cell)
                else:
                    final_row.append(None)
            final_grid_order.append(final_row)

        return {
            "format": "open-board-0.1",
            "id": page.id,
            "name": page.name,
            "locale": "en_US",
            "grid": {
                "rows": rows,
                "columns": cols,
                "order": final_grid_order
            },
            "buttons": buttons_data,
            "images": images_data,
            "sounds": []
        }

    def process_texts(
        self,
        file_path: str,
        translations: Optional[dict[str, str]] = None,
        output_path: Optional[str] = None,
    ) -> Union[list[str], str, None]:
        """Process texts in CoughDrop file.

        Args:
            file_path: Path to the file to process.
            translations: Dictionary of translations.
            output_path: Optional path where to save the translated file.

        Returns:
            Union[List[str], str, None]: List of texts if extracting,
            path to translated file if translating, None if error.
        """
        try:
            # Reset state for new translation
            self.collected_texts = []
            self.file_path = file_path
            self.original_file_path = file_path
            self.original_filename = os.path.splitext(os.path.basename(file_path))[0]

            # Create temp directory for processing
            temp_dir = tempfile.mkdtemp()

            # Copy file to temp directory
            temp_file = os.path.join(temp_dir, os.path.basename(file_path))
            shutil.copy2(file_path, temp_file)

            if file_path.endswith(".obz"):
                # Extract OBZ file
                extract_dir = os.path.join(temp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)

                with zipfile.ZipFile(temp_file, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)

                # Process all board files
                manifest_path = os.path.join(extract_dir, "manifest.json")
                if os.path.exists(manifest_path):
                    with open(manifest_path, encoding="utf-8") as f:
                        manifest = json.load(f)
                        paths = manifest.get("paths", {})
                        boards = paths.get("boards", {})

                        # Process each board file
                        for board_path in boards.values():
                            board_file = os.path.join(extract_dir, board_path)
                            if os.path.exists(board_file):
                                tree = self.load_into_tree(board_file)
                                if translations is None:
                                    # Extract texts
                                    for page in tree.pages.values():
                                        if page.name:
                                            self.collected_texts.append(page.name)
                                        for button in page.buttons:
                                            if button.label:
                                                self.collected_texts.append(button.label)
                                            if (
                                                button.vocalization
                                                and button.vocalization != button.label
                                            ):
                                                self.collected_texts.append(
                                                    button.vocalization
                                                )
                                else:
                                    # Apply translations
                                    for page in tree.pages.values():
                                        if page.name in translations:
                                            page.name = translations[page.name]
                                        for button in page.buttons:
                                            if button.label in translations:
                                                button.label = translations[button.label]
                                            if button.vocalization in translations:
                                                button.vocalization = translations[
                                                    button.vocalization
                                                ]
                                    self.save_from_tree(tree, board_file)
            else:
                # Process single OBF file
                tree = self.load_into_tree(temp_file)
                if translations is None:
                    # Extract texts
                    for page in tree.pages.values():
                        if page.name:
                            self.collected_texts.append(page.name)
                        for button in page.buttons:
                            if button.label:
                                self.collected_texts.append(button.label)
                            if (
                                button.vocalization
                                and button.vocalization != button.label
                            ):
                                self.collected_texts.append(button.vocalization)
                else:
                    # Apply translations
                    for page in tree.pages.values():
                        if page.name in translations:
                            page.name = translations[page.name]
                        for button in page.buttons:
                            if button.label in translations:
                                button.label = translations[button.label]
                            if button.vocalization in translations:
                                button.vocalization = translations[button.vocalization]
                    self.save_from_tree(tree, temp_file)

            if translations is None:
                return self.collected_texts

            # Create output file
            if file_path.endswith(".obz"):
                target_lang = translations.get("target_lang", "translated")
                output_name = f"{self.original_filename}_{target_lang}.obz"
                temp_output = os.path.join(temp_dir, output_name)
                with zipfile.ZipFile(temp_output, "w", zipfile.ZIP_DEFLATED) as zip_ref:
                    for root, _dirs, files in os.walk(extract_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arc_name = os.path.relpath(file_path, extract_dir)
                            zip_ref.write(file_path, arc_name)
                # Move to permanent location
                final_output = output_path or os.path.join(
                    os.path.dirname(self.original_file_path), output_name
                )
                shutil.copy2(temp_output, final_output)
                return final_output
            else:
                # For single OBF file
                original_ext = os.path.splitext(self.original_file_path)[1]
                target_lang = translations.get("target_lang", "translated")
                output_name = f"{self.original_filename}_{target_lang}{original_ext}"
                temp_output = os.path.join(temp_dir, output_name)
                shutil.copy2(temp_file, temp_output)
                # Move to permanent location
                final_output = output_path or os.path.join(
                    os.path.dirname(self.original_file_path), output_name
                )
                shutil.copy2(temp_output, final_output)
                return final_output

        except Exception as e:
            self.debug(f"Error processing texts: {e}")
            return None
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def process_files(
        self, directory: str, translations: Optional[dict[str, str]] = None
    ) -> Optional[str]:
        """Process files in the directory - extract or update texts.

        Args:
            directory (str): Directory containing the files to process.
            translations (Optional[Dict[str, str]]): Dictionary of translations.

        Returns:
            Optional[str]: Path to translated file if successful, None otherwise.
        """
        try:
            # For single .obf file, process it directly
            if self.file_path and self.file_path.endswith(".obf"):
                self.debug(f"Processing single OBF file: {self.file_path}")
                tree = self.load_into_tree(self.file_path)
                if translations:
                    # Apply translations
                    for page in tree.pages.values():
                        if page.name in translations:
                            page.name = translations[page.name]
                        for button in page.buttons:
                            if button.label in translations:
                                button.label = translations[button.label]
                            if button.vocalization in translations:
                                button.vocalization = translations[button.vocalization]
                    # Save translated tree
                    output_path = os.path.join(
                        directory, os.path.basename(self.file_path)
                    )
                    self.save_from_tree(tree, output_path)
                    return output_path
                else:
                    # Extract texts
                    for page in tree.pages.values():
                        if page.name:
                            self.collected_texts.append(page.name)
                        for button in page.buttons:
                            if button.label:
                                self.collected_texts.append(button.label)
                            if (
                                button.vocalization
                                and button.vocalization != button.label
                            ):
                                self.collected_texts.append(button.vocalization)
                    return None

            # Look for manifest.json first (for .obz files)
            manifest_path = os.path.join(directory, "manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)
                    paths = manifest.get("paths", {})
                    boards = paths.get("boards", {})

                    # Process each board file
                    for board_path in boards.values():
                        board_file = os.path.join(directory, board_path)
                        if os.path.exists(board_file):
                            tree = self.load_into_tree(board_file)
                            if translations:
                                # Apply translations
                                for page in tree.pages.values():
                                    if page.name in translations:
                                        page.name = translations[page.name]

                                    for button in page.buttons:
                                        if button.label in translations:
                                            button.label = translations[button.label]
                                        if button.vocalization in translations:
                                            button.vocalization = translations[
                                                button.vocalization
                                            ]

                                # Save translated tree
                                self.save_from_tree(tree, board_file)
                            else:
                                # Extract texts
                                for page in tree.pages.values():
                                    if page.name:
                                        self.collected_texts.append(page.name)

                                    for button in page.buttons:
                                        if button.label:
                                            self.collected_texts.append(button.label)
                                        if (
                                            button.vocalization
                                            and button.vocalization != button.label
                                        ):
                                            self.collected_texts.append(
                                                button.vocalization
                                            )
            else:
                # Look for individual .obf files
                for file in os.listdir(directory):
                    if file.endswith(".obf"):
                        file_path = os.path.join(directory, file)
                        tree = self.load_into_tree(file_path)
                        if translations:
                            # Apply translations
                            for page in tree.pages.values():
                                if page.name in translations:
                                    page.name = translations[page.name]

                                for button in page.buttons:
                                    if button.label in translations:
                                        button.label = translations[button.label]
                                    if button.vocalization in translations:
                                        button.vocalization = translations[
                                            button.vocalization
                                        ]

                            # Save translated tree
                            self.save_from_tree(tree, file_path)
                        else:
                            # Extract texts
                            for page in tree.pages.values():
                                if page.name:
                                    self.collected_texts.append(page.name)

                                for button in page.buttons:
                                    if button.label:
                                        self.collected_texts.append(button.label)
                                    if (
                                        button.vocalization
                                        and button.vocalization != button.label
                                    ):
                                        self.collected_texts.append(button.vocalization)

            # If translations were applied, create new file
            if translations:
                output_path = self.get_output_path(translations.get("target_lang"))
                if self.file_path and self.file_path.endswith(".obz"):
                    with zipfile.ZipFile(
                        output_path, "w", zipfile.ZIP_DEFLATED
                    ) as zip_ref:
                        for root, _, files in os.walk(directory):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arc_name = os.path.relpath(file_path, directory)
                                zip_ref.write(file_path, arc_name)
                else:
                    # For single OBF file, just copy the translated file
                    for file in os.listdir(directory):
                        if file.endswith(".obf"):
                            src = os.path.join(directory, file)
                            shutil.copy2(src, output_path)
                            break
                return output_path

            return None

        except Exception as e:
            self.debug(f"Error processing files: {str(e)}")
            return None

    def load_into_tree(self, file_path: str) -> AACTree:
        """Load OBF/OBZ file into common tree structure.

        Args:
            file_path (str): Path to the file to load.

        Returns:
            AACTree: Tree structure representing the file contents.
        """
        tree = AACTree()
        temp_dir = self.create_temp_dir()

        try:
            if file_path.endswith(".obz"):
                # Extract OBZ file
                with zipfile.ZipFile(file_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Read manifest
                manifest_path = os.path.join(temp_dir, "manifest.json")
                if not os.path.exists(manifest_path):
                    raise ValueError("Invalid OBZ file: missing manifest.json")

                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)
                    paths = manifest.get("paths", {})
                    boards = paths.get("boards", {})

                    # Process each board file
                    for _board_id, board_path in boards.items():
                        full_path = os.path.join(temp_dir, board_path)
                        if os.path.exists(full_path):
                            self._load_board_into_tree(full_path, tree)
            else:
                # Single OBF file
                self._load_board_into_tree(file_path, tree)

            return tree

        except Exception as e:
            self.debug(f"Error loading tree: {str(e)}")
            raise

    def save_from_tree(self, tree: AACTree, output_path: str) -> None:
        """Save tree to OBF/OBZ format.

        Args:
            tree (AACTree): Tree to save.
            output_path (str): Path where to save the file.
        """
        temp_dir = self.create_temp_dir()

        try:
            if output_path.endswith(".obz"):
                # Create boards directory
                boards_dir = os.path.join(temp_dir, "boards")
                os.makedirs(boards_dir, exist_ok=True)

                # Save each page as a board file
                board_paths = {}
                for page_id, page in tree.pages.items():
                    board_file = f"{page_id}.obf"
                    board_path = os.path.join("boards", board_file)
                    full_path = os.path.join(temp_dir, board_path)

                    board_data = self._convert_page_to_board(page, tree)
                    with open(full_path, "w", encoding="utf-8") as f:
                        json.dump(board_data, f, indent=2)

                    board_paths[page_id] = board_path

                if not board_paths:
                    raise ValueError("No pages to save")

                # Create manifest
                root_id = next(iter(tree.pages))
                manifest = {
                    "format": "open-board-0.1",
                    "root": board_paths[root_id],
                    "paths": {"boards": board_paths, "images": {}, "sounds": {}},
                }

                # Save manifest
                manifest_path = os.path.join(temp_dir, "manifest.json")
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2)

                # Create OBZ file
                with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
                    for root, _dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arc_name = os.path.relpath(file_path, temp_dir)
                            zip_ref.write(file_path, arc_name)
            else:
                # Save single OBF file
                if len(tree.pages) > 1:
                    self.debug("Warning: Multiple pages found, only saving first page")

                page = next(iter(tree.pages.values()))
                board_data = self._convert_page_to_board(page, tree)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(board_data, f, indent=2)

        except Exception as e:
            self.debug(f"Error saving tree: {str(e)}")
            raise

    def extract_texts(self, file_path: str) -> list[str]:
        """Extract translatable texts from OBF/OBZ file.

        Args:
            file_path (str): Path to the file to process.

        Returns:
            List[str]: List of extracted texts.
        """
        result = self.process_texts(file_path, None)
        if isinstance(result, list):
            return result
        return []

    def create_translated_file(
        self, file_path: str, translations: dict[str, str]
    ) -> Optional[str]:
        """Create a translated version of the file.

        Args:
            file_path (str): Path to the file to translate.
            translations (Dict[str, str]): Dictionary of translations.

        Returns:
            Optional[str]: Path to translated file or None if error occurred.
        """
        try:
            temp_dir = self.create_temp_dir()

            # Copy original file to temp dir
            temp_file = os.path.join(temp_dir, os.path.basename(file_path))
            shutil.copy2(file_path, temp_file)

            # Process translations
            if file_path.endswith(".obz"):
                # Extract OBZ file
                extract_dir = os.path.join(temp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)

                with zipfile.ZipFile(temp_file, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)

                # Process all board files
                manifest_path = os.path.join(extract_dir, "manifest.json")
                if os.path.exists(manifest_path):
                    with open(manifest_path, encoding="utf-8") as f:
                        manifest = json.load(f)
                        paths = manifest.get("paths", {})
                        boards = paths.get("boards", {})

                        # Process each board file
                        for board_path in boards.values():
                            board_file = os.path.join(extract_dir, board_path)
                            if os.path.exists(board_file):
                                tree = self.load_into_tree(board_file)
                                for page in tree.pages.values():
                                    if page.name in translations:
                                        page.name = translations[page.name]

                                    for button in page.buttons:
                                        if button.label in translations:
                                            button.label = translations[button.label]
                                        if button.vocalization in translations:
                                            button.vocalization = translations[
                                                button.vocalization
                                            ]

                                self.save_from_tree(tree, board_file)

                # Create new OBZ file with target language code
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                target_lang = translations.get("target_lang")
                if not target_lang:
                    self.debug("No target language found in translations")
                    return None

                # Remove any existing language suffix if present
                if "_" in base_name:
                    base_parts = base_name.split("_")
                    if (
                        len(base_parts[-1]) <= 5
                    ):  # Assuming language codes are <= 5 chars
                        base_name = "_".join(base_parts[:-1])

                output_name = f"{base_name}_{target_lang}.obz"
                output_path = os.path.join(temp_dir, output_name)

                with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
                    for root, _, files in os.walk(extract_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arc_name = os.path.relpath(file_path, extract_dir)
                            zip_ref.write(file_path, arc_name)

                return output_path
            else:
                # Process single OBF file
                tree = self.load_into_tree(temp_file)
                for page in tree.pages.values():
                    if page.name in translations:
                        page.name = translations[page.name]

                    for button in page.buttons:
                        if button.label in translations:
                            button.label = translations[button.label]
                        if button.vocalization in translations:
                            button.vocalization = translations[button.vocalization]

                self.save_from_tree(tree, temp_file)

                # Create output path with target language code
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                target_lang = translations.get("target_lang")
                if not target_lang:
                    self.debug("No target language found in translations")
                    return None

                # Remove any existing language suffix if present
                if "_" in base_name:
                    base_parts = base_name.split("_")
                    if (
                        len(base_parts[-1]) <= 5
                    ):  # Assuming language codes are <= 5 chars
                        base_name = "_".join(base_parts[:-1])

                output_name = f"{base_name}_{target_lang}.obf"
                output_path = os.path.join(temp_dir, output_name)
                shutil.move(temp_file, output_path)
                return output_path

        except Exception as e:
            self.debug(f"Error creating translated file: {str(e)}")
            return None
