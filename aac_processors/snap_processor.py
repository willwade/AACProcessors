import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Callable, Optional, Union

from .sqlite_processor import SQLiteProcessor
from .tree_structure import AACButton, AACPage, AACTree, ButtonType


class SnapProcessor(SQLiteProcessor):
    """Processor for Snap files (.sps, .spb)."""

    def __init__(self, debug_output: Optional[Callable[[str], None]] = None) -> None:
        """Initialize Snap processor.

        Args:
            debug_output: Function to use for debug output.
        """
        super().__init__()  # Call SQLiteProcessor's __init__
        self._debug_output = debug_output or print
        self.collected_texts: list[str] = []
        self.file_path: Optional[str] = None  # Match SQLiteProcessor's type
        self.original_filename: str = ""  # Initialize as empty string
        self.original_file_path: str = ""  # Initialize as empty string

    def can_process(self, file_path: str) -> bool:
        """Check if file is a Snap export.

        Args:
            file_path: Path to the file to check.

        Returns:
            bool: True if file is a Snap export.
        """
        return file_path.lower().endswith((".sps", ".spb"))

    def process_files(
        self, directory: str, translations: Optional[dict[str, str]] = None
    ) -> Optional[str]:
        """Process files in the extracted directory.

        Args:
            directory: Directory containing the files to process.
            translations: Dictionary of translations.

        Returns:
            Optional[str]: Path to translated file if successful, None otherwise.
        """
        try:
            # Find database files (.sps, .spb, or copied with original extension)
            db_files = [
                f
                for f in os.listdir(directory)
                if f.endswith((".sps", ".spb", ".sqlite"))
            ]
            self._debug_print(f"Found database files: {db_files}")

            if not db_files:
                self._debug_print("No database files found")
                return None

            db_path = os.path.join(directory, db_files[0])
            self._debug_print(f"Using database: {db_path}")

            if translations is None:
                # Extract mode
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    for table, columns in self.get_translatable_columns():
                        for column in columns:
                            self._debug_print(f"Querying {table}.{column}")
                            query = f"""
                                SELECT DISTINCT {column}
                                FROM {table}
                                WHERE {column} IS NOT NULL AND {column} != ''
                                """
                            cursor.execute(query)
                            texts = [row[0] for row in cursor.fetchall()]
                            self._debug_print(
                                f"Found {len(texts)} texts in {table}.{column}"
                            )
                            self.collected_texts.extend(texts)
                # Return None in extract mode, texts are in self.collected_texts
                return None

            else:
                # Translation mode
                modified = False
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    for table, columns in self.get_translatable_columns():
                        for column in columns:
                            query = f"""
                                SELECT DISTINCT {column}
                                FROM {table}
                                WHERE {column} IS NOT NULL AND {column} != ''
                                """
                            cursor.execute(query)
                            for (text,) in cursor.fetchall():
                                if text in translations:
                                    self._debug_print(
                                        f"Translating {text} to {translations[text]} "
                                        f"in {table}.{column}"
                                    )
                                    cursor.execute(
                                        f"""
                                        UPDATE {table}
                                        SET {column} = ?
                                        WHERE {column} = ?
                                        """,
                                        (translations[text], text),
                                    )
                                    modified = True if cursor.rowcount > 0 else modified
                                    self._debug_print(f"Updated {cursor.rowcount} rows")

                    if modified:
                        conn.commit()
                        # Create new file with translations
                        target_lang = translations.get("target_lang", "translated")
                        if not self.original_file_path:
                            return None
                        base_path = Path(self.original_file_path)
                        output_name = (
                            f"{base_path.stem}_{target_lang}{base_path.suffix}"
                        )
                        output_path = os.path.join(directory, output_name)
                        shutil.copy2(db_path, output_path)
                        return output_path

                return None

        except Exception as e:
            self._debug_print(f"Error processing files: {e}")
            return None

    def get_translatable_columns(self) -> list[tuple[str, list[str]]]:
        """Return list of (table_name, [column_names]) for translatable text.

        Returns:
            List[Tuple[str, List[str]]]: List of tuples containing table name
            and list of column names that contain translatable text.
        """
        return [("Button", ["Label", "Message"]), ("Page", ["Title"])]

    def load_into_tree(self, file_path: str) -> AACTree:
        """Load Snap file into tree structure.

        Args:
            file_path (str): Path to the file to load.

        Returns:
            AACTree: Tree structure representing the file contents.

        Raises:
            Exception: If there is an error loading the file.
        """
        try:
            with sqlite3.connect(file_path) as conn:
                cursor = conn.cursor()

                # Create new tree
                tree = AACTree()

                # Get pages
                cursor.execute(
                    """
                    SELECT p.id, p.Title
                    FROM Page p
                    WHERE p.Title IS NOT NULL
                    """
                )

                for page_id, title in cursor.fetchall():
                    page = AACPage(
                        id=str(page_id),
                        name=title,
                        grid_size=(2, 2),  # Default grid size
                    )

                    # Get buttons for this page
                    cursor.execute(
                        """
                        SELECT b.id, b.Label, b.Message,
                               b.position_x, b.position_y,
                               ba.action_type, ba.target_page_id
                        FROM Button b
                        LEFT JOIN ButtonAction ba ON ba.button_id = b.id
                        WHERE b.page_id = ?
                        """,
                        (page_id,),
                    )

                    for row in cursor.fetchall():
                        (
                            button_id,
                            label,
                            message,
                            pos_x,
                            pos_y,
                            action_type,
                            target_page_id,
                        ) = row

                        # Determine button type
                        button_type = ButtonType.SPEAK
                        if action_type == "navigate":
                            button_type = ButtonType.NAVIGATE

                        button = AACButton(
                            id=str(button_id),
                            label=label or "",
                            type=button_type,
                            position=(pos_y or 0, pos_x or 0),
                            target_page_id=(
                                str(target_page_id) if target_page_id else None
                            ),
                            vocalization=message,
                        )
                        page.buttons.append(button)

                    tree.add_page(page)

                return tree

        except Exception as e:
            self.debug(f"Error loading Snap file: {e}")
            raise

    def save_from_tree(self, tree: AACTree, output_path: str) -> None:
        """Save tree to Snap format.

        Args:
            tree (AACTree): Tree structure to save.
            output_path (str): Path where to save the file.
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
                    (int(page_id), page.name),
                )

                # Add buttons
                for button in page.buttons:
                    # For navigation buttons, use "Go to Page X" as label
                    label = button.label
                    if button.type == ButtonType.NAVIGATE and button.target_page_id:
                        label = f"Go to Page {button.target_page_id}"

                    cursor.execute(
                        """
                        INSERT INTO Button (
                            id, page_id, Label, Message,
                            position_x, position_y
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            int(button.id),
                            int(page_id),
                            label,
                            button.vocalization,
                            button.position[1],  # x = col
                            button.position[0],  # y = row
                        ),
                    )

                    # Add navigation action if needed
                    if button.type == ButtonType.NAVIGATE and button.target_page_id:
                        target_id = int(button.target_page_id)
                        cursor.execute(
                            """
                            INSERT INTO ButtonAction (
                                button_id, action_type, target_page_id
                            )
                            VALUES (?, ?, ?)
                            """,
                            (int(button.id), "navigate", target_id),
                        )

            conn.commit()
            return None

    def process_texts(
        self,
        file_path: str,
        translations: Optional[dict[str, str]] = None,
        output_path: Optional[str] = None,
    ) -> Union[list[str], str, None]:
        """Process texts in Snap file.

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
            # Set file paths
            self.file_path = file_path  # Set the file_path for SQLiteProcessor
            self.original_file_path = file_path
            self.original_filename = Path(file_path).stem

            # Create temp directory for processing
            temp_dir = tempfile.mkdtemp()

            # Copy file to temp directory
            temp_file = Path(temp_dir) / Path(file_path).name
            shutil.copy2(file_path, temp_file)

            # Process the files
            result = self.process_files(temp_dir, translations)

            if translations is None:
                return self.collected_texts  # Return collected texts in extract mode

            if result:
                target_lang = translations.get("target_lang", "translated")
                base_path = Path(file_path)
                output_name = f"{base_path.stem}_{target_lang}{base_path.suffix}"
                final_output = output_path or str(base_path.parent / output_name)
                shutil.copy2(result, final_output)
                return final_output

            return None

        except Exception as e:
            self.debug(f"Error processing texts: {e}")
            return None
        finally:
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir)

    def extract_texts(self, file_path: str) -> list[str]:
        """Extract translatable texts from Snap file.

        Args:
            file_path: Path to the file to process.

        Returns:
            List[str]: List of extracted texts.
        """
        self.collected_texts = []
        _ = self.process_texts(file_path)  # Ignore the return value
        return self.collected_texts

    def create_translated_file(
        self, file_path: str, translations: dict[str, str]
    ) -> Optional[str]:
        """Create a translated version of the Snap file.

        Args:
            file_path: Path to the Snap file.
            translations: Dictionary of translations.

        Returns:
            Optional[str]: Path to translated file if successful, None otherwise.
        """
        try:
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

                if modified:
                    conn.commit()
                    # Create output path with target language code
                    target_lang = translations.get("target_lang", "translated")
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    ext = os.path.splitext(file_path)[1]
                    output_name = f"{base_name}_{target_lang}{ext}"
                    output_path = os.path.join(os.path.dirname(file_path), output_name)
                    shutil.copy2(temp_file, output_path)
                    return output_path

            return None

        except Exception as e:
            self.debug(f"Error creating translated file: {str(e)}")
            return None
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
