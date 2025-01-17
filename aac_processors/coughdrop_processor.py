import json
import os
import shutil
import tempfile
import zipfile
from typing import Any, Optional, Union

from .file_processor import FileProcessor
from .tree_structure import AACButton, AACPage, AACTree, ButtonType


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
        """Load a board file into the tree.

        Args:
            file_path (str): Path to the board file.
            tree (AACTree): Tree to load into.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                board_data = json.load(f)

            # Get grid size
            grid = board_data.get("grid", {})
            rows = grid.get("rows", 1)
            cols = grid.get("columns", 1)

            # Create page
            page = AACPage(
                id=board_data.get("id", ""),
                name=board_data.get("name", ""),
                grid_size=(rows, cols),
            )

            # Process buttons
            buttons = board_data.get("buttons", [])
            for button in buttons:
                if not isinstance(button, dict):
                    continue

                # Determine button type and target
                button_type = ButtonType.SPEAK
                target_page_id = None
                action = None
                load_board = button.get("load_board", {})
                if load_board:
                    button_type = ButtonType.NAVIGATE
                    target_page_id = load_board.get("id")
                elif "action" in button:
                    button_type = ButtonType.ACTION
                    action = button["action"]

                # Get position from grid order or absolute positioning
                pos_x = pos_y = 0
                if "left" in button and "top" in button:
                    # Convert absolute positioning to grid coordinates
                    pos_x = int(float(button["left"]) * cols)
                    pos_y = int(float(button["top"]) * rows)
                elif grid.get("order"):
                    # Find position in grid order
                    button_id = button.get("id")
                    for row_idx, row in enumerate(grid["order"]):
                        if button_id in row:
                            pos_y = row_idx
                            pos_x = row.index(button_id)
                            break

                # Create button
                btn = AACButton(
                    id=button.get("id", ""),
                    label=button.get("label", ""),
                    type=button_type,
                    position=(pos_y, pos_x),
                    target_page_id=target_page_id,
                    vocalization=button.get("vocalization", ""),
                    action=action,
                )
                page.buttons.append(btn)

            tree.pages[page.id] = page

        except Exception as e:
            self.debug(f"Error loading board file {file_path}: {str(e)}")

    def _convert_page_to_board(self, page: AACPage) -> dict[str, Any]:
        """Convert a page to a board format.

        Args:
            page (AACPage): Page to convert.

        Returns:
            Dict[str, Any]: Board data.
        """
        rows, cols = page.grid_size
        grid_order: list[list[Optional[str]]] = [[None] * cols for _ in range(rows)]
        buttons_data: list[dict[str, Any]] = []

        for button in page.buttons:
            # Create button data
            button_data: dict[str, Any] = {"id": button.id, "label": button.label}

            if button.vocalization and button.vocalization != button.label:
                button_data["vocalization"] = button.vocalization

            if button.type == ButtonType.NAVIGATE and button.target_page_id:
                button_data["load_board"] = {
                    "id": button.target_page_id,
                    "path": f"boards/{button.target_page_id}.obf",
                }

            # Add to grid order
            y, x = button.position
            if 0 <= y < rows and 0 <= x < cols:
                grid_order[y][x] = button.id

            buttons_data.append(button_data)

        return {
            "format": "open-board-0.1",
            "id": page.id,
            "name": page.name,
            "locale": "en_US",
            "grid": {"rows": rows, "columns": cols, "order": grid_order},
            "buttons": buttons_data,
            "images": [],
            "sounds": [],
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
                                                self.collected_texts.append(
                                                    button.label
                                                )
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
                                                button.label = translations[
                                                    button.label
                                                ]
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
                    for root, _, files in os.walk(extract_dir):
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

                    board_data = self._convert_page_to_board(page)
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
                board_data = self._convert_page_to_board(page)
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
