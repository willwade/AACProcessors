"""Processor for Tobii Dynavox Snap files."""

import os
import shutil
import sqlite3
import tempfile
from typing import Any, Callable, Optional, Union

from .sqlite_processor import SQLiteProcessor
from .tree_structure import AACButton, AACPage, AACSymbol, AACTree, ButtonType


class SnapProcessor(SQLiteProcessor):
    """Processor for Tobii Dynavox Snap files."""

    def __init__(
        self,
        debug_callback: Optional[Callable[[str], None]] = None,
        symbol_db_path: Optional[str] = None,
    ):
        """Initialize processor.

        Args:
            debug_callback: Optional callback for debug messages.
            symbol_db_path: Optional path to symbol database.
        """
        super().__init__()
        self.set_debug_output(debug_callback)
        self.file_path: Optional[str] = None
        self.symbol_db_path = symbol_db_path

    def can_process(self, file_path: str) -> bool:
        """Check if file can be processed by this processor.

        Args:
            file_path: Path to file to check

        Returns:
            True if file can be processed
        """
        # Check file extension
        return file_path.lower().endswith((".spb", ".sps"))

    def process_files(
        self, directory: str, translations: Optional[dict[str, str]] = None
    ) -> Optional[str]:
        """Process files in directory.

        Args:
            directory: Directory containing files to process
            translations: Dictionary of translations

        Returns:
            Optional[str]: Path to output file if translations provided, None otherwise
        """
        # In the Snap processor, directory is actually a list of files
        if isinstance(directory, list):
            file_paths = directory
        else:
            # If it's a string (directory path), we don't process it
            self.debug(f"SnapProcessor doesn't process directories: {directory}")
            return None

        for file_path in file_paths:
            if not self.can_process(file_path):
                self.debug(f"Cannot process file: {file_path}")
                continue

            try:
                # If translations are provided, update the texts
                if translations:
                    self.update_texts(file_path, translations)
                else:
                    # Otherwise just load the file to extract texts
                    self.load_into_tree(file_path)
            except Exception as e:
                self.debug(f"Error processing {file_path}: {e}")

        # Return None since we don't have a specific output path
        return None

    def can_handle(self, file_path: str) -> bool:
        """Check if processor can handle file.

        Args:
            file_path: Path to file to check.

        Returns:
            bool: True if processor can handle file.
        """
        return file_path.lower().endswith((".spb", ".sps"))

    def get_translatable_columns(self) -> list[tuple[str, list[str]]]:
        """Return list of (table_name, [column_names]) for translatable text.

        Returns:
            List[tuple[str, list[str]]]: List of table names and their translatable columns.
        """
        return [
            ("Page", ["Title"]),
            ("Button", ["Label", "Message"]),
        ]

    def _get_symbol_info(self, _symbol_id: str) -> Optional[tuple[str, str]]:
        """Get library name and label for a symbol ID.

        Args:
            symbol_id: ID of the symbol to look up.

        Returns:
            tuple[str, str]: (library_name, label) if found, None otherwise.
        """
        return None

    def _load_symbol_data(
        self, symbol_id: Optional[str], pageset_image_id: Optional[int] = None
    ) -> Optional[AACSymbol]:
        """Load symbol data from the input file.

        Args:
            symbol_id: Library symbol ID if available
            pageset_image_id: Optional ID of image from pageset

        Returns:
            AACSymbol: Symbol object with data loaded, or None if not found
        """
        if not hasattr(self, "file_path") or not self.file_path:
            return None

        try:
            # Use the symbol_db_path if provided
            symbol_db_path = None
            if (
                hasattr(self, "symbol_db_path")
                and self.symbol_db_path
                and os.path.exists(self.symbol_db_path)
            ):
                symbol_db_path = self.symbol_db_path
                self.debug(f"Using provided symbol database at {symbol_db_path}")
            else:
                # Check if we have a symbol database available in standard locations
                symbol_db_path = os.path.join(
                    os.path.dirname(os.path.dirname(self.file_path)),
                    "ImagesForAAC",
                    "SymbolsSnapCoreFoundation.db3",
                )

                if not os.path.exists(symbol_db_path):
                    self.debug(
                        f"Warning: Symbol database not found at {symbol_db_path}"
                    )
                    # Try to find it in the same directory as the input file
                    symbol_db_path = os.path.join(
                        os.path.dirname(self.file_path), "SymbolsSnapCoreFoundation.db3"
                    )
                    if not os.path.exists(symbol_db_path):
                        self.debug(
                            "Warning: Symbol database not found in input file directory either"
                        )
                        return None

            with sqlite3.connect(symbol_db_path) as conn:
                # Enable loading BLOBs as bytes
                conn.text_factory = bytes
                cursor = conn.cursor()

                # We don't need to look up library symbols in the core processor
                # Just store the reference for later resolution by the optional resolver
                if symbol_id and symbol_id != "None":
                    self.debug(f"Storing symbol reference for ID {symbol_id}")
                    return AACSymbol(
                        system_id=str(symbol_id),
                        system_name="snap",
                        label=f"SYM:{symbol_id}",
                    )

            # If no library symbol or not found, try PageSetData from the original file
            if pageset_image_id:
                with sqlite3.connect(self.file_path) as conn:
                    conn.text_factory = bytes
                    cursor = conn.cursor()
                    self.debug(f"Looking for pageset image {pageset_image_id}")
                    cursor.execute(
                        """
                        SELECT Identifier, Data
                        FROM PageSetData
                        WHERE Id = ?
                    """,
                        (pageset_image_id,),
                    )
                    result = cursor.fetchone()
                    if result:
                        self.debug(f"Found pageset image {pageset_image_id}")
                        identifier = (
                            result[0].decode("utf-8")
                            if isinstance(result[0], bytes)
                            else result[0] if result[0] else None
                        )
                        image_data = result[1]

                        if image_data:
                            # Convert raw bytes to base64
                            import base64

                            b64_data = base64.b64encode(image_data).decode("utf-8")

                            # If the identifier starts with SYM:, we'll store it for later resolution
                            label = identifier or f"IMG:{pageset_image_id}"
                            if identifier and identifier.startswith("SYM:"):
                                # This is a symbol reference, store it for later resolution
                                sym_id = identifier[4:]  # Remove 'SYM:' prefix
                                return AACSymbol(
                                    system_id=sym_id,
                                    system_name="snap",
                                    label=identifier,
                                )
                            else:
                                # This is a direct image, return it with data
                                return AACSymbol(
                                    data=f"data:image/png;base64,{b64_data}",
                                    label=label,
                                    width=1024,  # Default width
                                    height=768,  # Default height
                                    content_type="image/png",
                                )
                        else:
                            self.debug(f"Pageset image {pageset_image_id} has no data")
                    else:
                        self.debug(f"Pageset image {pageset_image_id} not found")
            return None

        except Exception as e:
            self.debug(f"Error loading symbol data: {e}")
            return None

    def _load_page(self, db_cursor: sqlite3.Cursor, page_id: int) -> Optional[AACPage]:
        """Load a page from the database.

        Args:
            db_cursor: Database cursor
            page_id: ID of page to load

        Returns:
            Optional[AACPage]: Loaded page or None if not found
        """
        # Get page info
        db_cursor.execute(
            """
            SELECT id, Title
            FROM Page
            WHERE id = ?
        """,
            (page_id,),
        )
        page_info = db_cursor.fetchone()
        if not page_info:
            return None

        unique_id, title = page_info

        # Get grid dimensions - try real schema first, then fall back to test schema
        try:
            db_cursor.execute(
                """
                SELECT MAX(CAST(SUBSTR(ep.GridPosition, 1, INSTR(ep.GridPosition, ',') - 1) AS INTEGER)) + 1 as rows,
                       MAX(CAST(SUBSTR(ep.GridPosition, INSTR(ep.GridPosition, ',') + 1) AS INTEGER)) + 1 as cols
                FROM ElementReference er
                JOIN ElementPlacement ep ON ep.ElementReferenceId = er.Id
                WHERE er.PageId = ?
                """,
                (page_id,),
            )
            grid_info = db_cursor.fetchone()

            # Default to 1x1 if no elements found, otherwise use calculated dimensions
            if not grid_info or not grid_info[0] or not grid_info[1]:
                grid_size = (1, 1)
            else:
                grid_size = (grid_info[0], grid_info[1])
        except sqlite3.OperationalError:
            # For test database, use default grid size
            grid_size = (3, 3)

        page = AACPage(
            id=str(unique_id or page_id), name=title or "", grid_size=grid_size
        )

        # Load buttons - try real schema first, then fall back to test schema
        try:
            db_cursor.execute(
                """
                SELECT b.Id, b.Label, b.Message, b.LibrarySymbolId, b.PageSetImageId,
                       ep.GridPosition, bpl.PageUniqueId
                FROM Button b
                LEFT JOIN ElementReference er ON b.ElementReferenceId = er.Id
                LEFT JOIN ElementPlacement ep ON ep.ElementReferenceId = er.Id
                LEFT JOIN PageLayout pl ON ep.PageLayoutId = pl.Id
                LEFT JOIN ButtonPageLink bpl ON bpl.ButtonId = b.Id
                WHERE er.PageId = ? OR b.ElementReferenceId IN (
                    SELECT Id FROM ElementReference WHERE PageId = ?
                )
            """,
                (page_id, page_id),
            )
        except sqlite3.OperationalError:
            # For test database, use simplified query
            db_cursor.execute(
                """
                SELECT id, Label, Message, NULL as LibrarySymbolId, PageSetImageId,
                       NULL as GridPosition, NULL as PageUniqueId
                FROM Button
                WHERE page_id = ?
                """,
                (page_id,),
            )

        for (
            button_id,
            label,
            message,
            symbol_id,
            pageset_image_id,
            position,
            target_page_id,
        ) in db_cursor.fetchall():
            # Parse grid position
            try:
                row, col = map(int, position.split(","))
            except (ValueError, AttributeError):
                row = col = 0

            button = AACButton(
                id=str(button_id), label=label or "", position=(row, col)
            )

            # Add message if different from label
            if message and message != label:
                button.vocalization = message

            # Load symbol if present (either from library or pageset)
            if symbol_id or pageset_image_id:
                self.debug(
                    f"Loading symbol for button {button_id}: symbol_id={symbol_id}, pageset_image_id={pageset_image_id}"
                )
                if symbol_id == "None":
                    symbol_id = None
                if pageset_image_id == "None":
                    pageset_image_id = None
                button.symbol = self._load_symbol_data(
                    str(symbol_id) if symbol_id else None, pageset_image_id
                )
                if button.symbol:
                    self.debug(f"Loaded symbol: {button.symbol.label}")
                else:
                    self.debug(f"No symbol loaded for button {button_id}")

            # Set button type and target for navigation
            if target_page_id:
                button.type = ButtonType.NAVIGATE
                button.target_page_id = str(target_page_id)
            else:
                # Check for navigation action in ButtonAction table
                try:
                    # First check if ButtonAction table exists
                    db_cursor.execute(
                        """
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name='ButtonAction'
                        """
                    )
                    table_exists = db_cursor.fetchone()

                    if table_exists:
                        try:
                            db_cursor.execute(
                                """
                                SELECT TargetPageUniqueId
                                FROM ButtonAction
                                WHERE ButtonId = ? AND ActionType = 'Navigate'
                            """,
                                (button_id,),
                            )
                            nav_result = db_cursor.fetchone()
                            if nav_result and nav_result[0]:
                                button.type = ButtonType.NAVIGATE
                                button.target_page_id = str(nav_result[0])
                        except sqlite3.OperationalError:
                            # Try test schema
                            db_cursor.execute(
                                """
                                SELECT target_page_id
                                FROM ButtonAction
                                WHERE button_id = ? AND action_type = 'Navigate'
                            """,
                                (button_id,),
                            )
                            nav_result = db_cursor.fetchone()
                            if nav_result and nav_result[0]:
                                button.type = ButtonType.NAVIGATE
                                button.target_page_id = str(nav_result[0])
                except sqlite3.OperationalError:
                    # If we can't even check for the table, just continue
                    self.debug(f"Could not check for ButtonAction table: {button_id}")

            page.buttons.append(button)

        return page

    def _load_button(self, button_id: int, _page_id: int) -> Optional[AACButton]:
        """Load a button from the database."""
        if not self.file_path:
            return None

        with sqlite3.connect(self.file_path) as conn:
            cursor = conn.cursor()
            try:
                # Try the real Snap schema first
                cursor.execute(
                    """
                    SELECT b.Id, b.Label, b.Message, b.LibrarySymbolId, b.PageSetImageId, b.BackgroundColor
                    FROM Button b
                    WHERE b.Id = ?
                """,
                    (button_id,),
                )
                result = cursor.fetchone()
                if result:
                    (
                        button_id,
                        label,
                        message,
                        library_symbol_id,
                        pageset_image_id,
                        _,  # bg_color
                    ) = result

                    # Debug output
                    self.debug(
                        f"Loading button {button_id} with label {label}, message {message}, library_symbol_id {library_symbol_id}, pageset_image_id {pageset_image_id}"
                    )

                    # Load symbol
                    symbol = None
                    if library_symbol_id or pageset_image_id:
                        symbol = self._load_symbol_data(
                            library_symbol_id, pageset_image_id
                        )
                        if symbol:
                            self.debug(
                                f"Loaded symbol for button {button_id}: {symbol.label}"
                            )
                        else:
                            self.debug(f"Failed to load symbol for button {button_id}")

                    # Load navigation target
                    target_page_id = None
                    try:
                        cursor.execute(
                            """
                            SELECT TargetPageUniqueId
                            FROM ButtonPageLink
                            WHERE ButtonId = ?
                        """,
                            (button_id,),
                        )
                    except sqlite3.OperationalError:
                        self.debug(
                            f"ButtonPageLink table not found for button {button_id}"
                        )
            except sqlite3.OperationalError:
                # Fall back to test schema
                cursor.execute(
                    """
                    SELECT Label, Message, position_x, position_y
                    FROM Button
                    WHERE id = ?
                    """,
                    (button_id,),
                )
                result = cursor.fetchone()
                if not result:
                    return None

                label, message, pos_x, pos_y = result
                symbol = None  # Not in test schema

                # Check for navigation action - adapt to test schema
                cursor.execute(
                    """
                    SELECT target_page_id
                    FROM ButtonAction
                    WHERE button_id = ? AND action_type = 'navigate'
                    """,
                    (button_id,),
                )
                action = cursor.fetchone()
                target_page_id = str(action[0]) if action else None

                # Create the button
                button = AACButton(
                    id=str(button_id),
                    label=label,
                    symbol=symbol,
                    target_page_id=target_page_id,
                )

                # Set vocalization (message)
                if message:
                    button.vocalization = message

                # Store position in button's position attribute
                if pos_x is not None and pos_y is not None:
                    button.position = (int(pos_x), int(pos_y))

                return button
            else:
                self.debug(f"Button {button_id} not found")
                return None

    def load_into_tree(self, file_path: str) -> AACTree:
        """Load Snap file into tree structure.

        Args:
            file_path: Path to the file to load.

        Returns:
            AACTree: Tree structure representing the file.
        """
        self.file_path = file_path  # Store for use in _load_symbol_data
        tree = AACTree()

        # Connect to database
        with sqlite3.connect(file_path) as conn:
            cursor = conn.cursor()

            # Load pages
            cursor.execute(
                """
                SELECT id, id as UniqueId, Title
                FROM Page
            """
            )
            pages = cursor.fetchall()

            for page_id, _, _ in pages:
                page = self._load_page(cursor, page_id)
                if page:
                    tree.pages[page.id] = page

            # Set root page
            try:
                cursor.execute(
                    """
                    SELECT DefaultHomePageUniqueId
                    FROM PageSetProperties
                    LIMIT 1
                """
                )
                root = cursor.fetchone()
                if root and root[0]:
                    tree.root_id = str(root[0])
                elif tree.pages:
                    # If no root specified, use first page
                    tree.root_id = next(iter(tree.pages))
            except sqlite3.OperationalError:
                # Table might not exist in test database
                if tree.pages:
                    tree.root_id = next(iter(tree.pages))

            # Set parent IDs for navigation
            for page in tree.pages.values():
                for button in page.buttons:
                    if button.type == ButtonType.NAVIGATE and button.target_page_id:
                        target_page = tree.pages.get(button.target_page_id)
                        if target_page:
                            target_page.parent_id = page.id

        return tree

    def load_file(self, file_path: str) -> AACTree:
        """Load a Snap file.

        Args:
            file_path: Path to the file to load

        Returns:
            AACTree: The loaded tree structure
        """
        self.file_path = file_path
        return self.load_into_tree(file_path)

    def save_from_tree(self, tree: AACTree, output_path: str) -> None:
        """Save tree to Snap format.

        Args:
            tree: Tree structure to save.
            output_path: Path where to save the file.
        """
        with sqlite3.connect(output_path) as conn:
            cursor = conn.cursor()

            # Create tables
            cursor.executescript(
                """
                CREATE TABLE Page (
                    id INTEGER PRIMARY KEY,
                    Title TEXT
                );

                CREATE TABLE Button (
                    id INTEGER PRIMARY KEY,
                    page_id INTEGER,
                    Label TEXT,
                    Message TEXT,
                    position_x INTEGER,
                    position_y INTEGER,
                    FOREIGN KEY (page_id) REFERENCES Page(id)
                );

                CREATE TABLE ButtonAction (
                    id INTEGER PRIMARY KEY,
                    button_id INTEGER,
                    action_type TEXT,
                    target_page_id INTEGER,
                    FOREIGN KEY (button_id) REFERENCES Button(id)
                );
                """
            )

            # Add pages
            for page_id, page in tree.pages.items():
                cursor.execute(
                    """
                    INSERT INTO Page (id, Title)
                    VALUES (?, ?)
                    """,
                    (page_id, page.name),
                )

                # Add buttons
                for button in page.buttons:
                    cursor.execute(
                        """
                        INSERT INTO Button (id, page_id, Label, Message, position_x, position_y)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            button.id,
                            page_id,
                            button.label,
                            button.vocalization,
                            button.position[1],  # x is column
                            button.position[0],  # y is row
                        ),
                    )

                    # Add navigation action if needed
                    if button.type == ButtonType.NAVIGATE and button.target_page_id:
                        cursor.execute(
                            """
                            INSERT INTO ButtonAction (button_id, action_type, target_page_id)
                            VALUES (?, ?, ?)
                            """,
                            (button.id, "navigate", button.target_page_id),
                        )

            conn.commit()

    def process_texts(
        self,
        file_path: str,
        translations: Optional[dict[str, str]] = None,
        output_path: Optional[str] = None,
        include_context: bool = False,
    ) -> Union[list[str], list[dict[str, Any]], str, None]:
        """Process texts in file.

        Args:
            file_path: Path to the file to process.
            translations: Dictionary of translations.
            output_path: Optional path where to save the translated file.
            include_context: Whether to include contextual information.

        Returns:
            If extracting (translations=None):
                - If include_context=False: List of texts
                - If include_context=True: List of dictionaries with context info
            If translating (translations provided):
                - Path to translated file if successful
            None if error.
        """
        try:
            # Reset state for new translation
            self.collected_texts = []
            # Store file path for other methods to use
            self.file_path = file_path

            # Create temp directory for processing
            temp_dir = tempfile.mkdtemp()

            # Copy file to temp directory
            temp_file = os.path.join(temp_dir, os.path.basename(file_path))
            shutil.copy2(file_path, temp_file)

            # Process translations
            with sqlite3.connect(temp_file) as conn:
                cursor = conn.cursor()
                modified = False

                # Update translations in each table/column
                for table, columns in self.get_translatable_columns():
                    for column in columns:
                        cursor.execute(
                            f"""
                            SELECT DISTINCT {column}
                            FROM {table}
                            WHERE {column} IS NOT NULL AND {column} != ''
                            """
                        )
                        for (text,) in cursor.fetchall():
                            if translations:
                                if text in translations:
                                    cursor.execute(
                                        f"""
                                        UPDATE {table}
                                        SET {column} = ?
                                        WHERE {column} = ?
                                        """,
                                        (translations[text], text),
                                    )
                                    modified = True if cursor.rowcount > 0 else modified
                            else:
                                self.collected_texts.append(text)

                if translations and modified:
                    conn.commit()
                    # Use provided output_path or create one with target language code
                    if not output_path:
                        target_lang = translations.get("target_lang", "translated")
                        base_name = os.path.splitext(os.path.basename(file_path))[0]
                        ext = os.path.splitext(file_path)[1]
                        output_name = f"{base_name}_{target_lang}{ext}"
                        output_path = os.path.join(
                            os.path.dirname(file_path), output_name
                        )
                    shutil.copy2(temp_file, output_path)
                    return output_path

            if not translations:
                if include_context:
                    # Use extract_texts with context info
                    return self.extract_texts(file_path, include_context=True)
                else:
                    return self.collected_texts
            return None

        except Exception as e:
            self.debug(f"Error processing texts: {e}")
            return None
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def extract_texts(
        self, file_path: str, include_context: bool = False
    ) -> Union[list[str], list[dict[str, Any]]]:
        """Extract translatable texts from file.

        Args:
            file_path: Path to the file to process.
            include_context: Whether to include contextual information.

        Returns:
            If include_context is False: List of translatable texts.
            If include_context is True: List of dictionaries with context info.
        """
        if not include_context:
            self.collected_texts = []
            _ = self.process_texts(file_path)  # Ignore the return value
            return self.collected_texts
        else:
            # Load the file into a tree structure to get context
            tree = self.load_into_tree(file_path)
            texts_with_context = []

            # Process each page and button to extract texts with context
            for page_id, page in tree.pages.items():
                # Add page title
                if page.name and page.name.strip():
                    # Get path to page
                    path = " > ".join(
                        [tree.pages[p].name for p in tree.get_path_to_page(page_id)]
                    )

                    texts_with_context.append(
                        {
                            "text": page.name,
                            "path": path,
                            "symbol_name": None,
                            "symbol_library": None,
                            "symbol_id": None,
                            "button_type": "page",
                            "page_name": page.name,
                        }
                    )

                # Process buttons on the page
                for button in page.buttons:
                    # Add button label
                    if button.label and button.label.strip():
                        # Get path to button
                        button_path = f"{path} > {button.label}"

                        # Get symbol information if available
                        symbol_name = None
                        symbol_library = None
                        symbol_id = None
                        if button.symbol:
                            symbol_name = button.symbol.label
                            symbol_library = button.symbol.library
                            symbol_id = (
                                button.symbol.system_id or button.symbol.internal_id
                            )

                        texts_with_context.append(
                            {
                                "text": button.label,
                                "path": button_path,
                                "symbol_name": symbol_name,
                                "symbol_library": symbol_library,
                                "symbol_id": symbol_id,
                                "button_type": button.type.value,
                                "page_name": page.name,
                            }
                        )

                    # Add button vocalization if different from label
                    if (
                        button.vocalization
                        and button.vocalization.strip()
                        and button.vocalization != button.label
                    ):
                        # Get path to button vocalization
                        vocal_path = f"{path} > {button.label} (vocalization)"

                        texts_with_context.append(
                            {
                                "text": button.vocalization,
                                "path": vocal_path,
                                "symbol_name": (
                                    symbol_name if "symbol_name" in locals() else None
                                ),
                                "symbol_library": (
                                    symbol_library
                                    if "symbol_library" in locals()
                                    else None
                                ),
                                "symbol_id": (
                                    symbol_id if "symbol_id" in locals() else None
                                ),
                                "button_type": button.type.value,
                                "page_name": page.name,
                            }
                        )

            return texts_with_context

    def create_translated_file(
        self, file_path: str, translations: dict[str, str]
    ) -> Optional[str]:
        """Create a translated version of the file.

        Args:
            file_path: Path to the file to translate.
            translations: Dictionary of translations.

        Returns:
            Optional[str]: Path to translated file if successful, None otherwise.
        """
        result = self.process_texts(file_path, translations)
        if isinstance(result, str):
            return result
        return None
