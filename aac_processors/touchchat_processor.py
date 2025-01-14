import logging
import os
import os.path
import shutil
import sqlite3
import zipfile
from typing import Optional, Union

from .sqlite_processor import SQLiteProcessor
from .tree_structure import AACButton, AACPage, AACTree, ButtonType


class TouchChatProcessor(SQLiteProcessor):
    """Processor for TouchChat files (.ce)."""

    def __init__(self) -> None:
        """Initialize TouchChat processor."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.is_archive = True  # CE files are archives containing SQLite DB
        self.file_path: Optional[str] = None
        self.original_filename: Optional[str] = None
        self.original_file_path: Optional[str] = None

    def can_process(self, file_path: str) -> bool:
        """Check if file is a TouchChat export.

        Args:
            file_path (str): Path to the file to check.

        Returns:
            bool: True if file is a TouchChat export.
        """
        return file_path.lower().endswith(".ce")

    def process_texts(
        self,
        file_path: str,
        translations: Optional[dict[str, str]] = None,
        output_path: Optional[str] = None,
    ) -> Union[list[str], str, None]:
        """Process texts from a TouchChat file.

        Process and optionally translate texts from a TouchChat file.

        Args:
            file_path: Path to the TouchChat file.
            translations: Optional dictionary of translations.
            output_path: Optional path where to save the translated file.

        Returns:
            List[str]: List of extracted texts if no translations provided.
            str: Path to translated file if translations provided.
            None: If an error occurs during processing.
        """
        try:
            # Reset state for new translation
            self.collected_texts = []
            self.file_path = file_path
            self.original_file_path = file_path
            self.original_filename = os.path.splitext(os.path.basename(file_path))[0]
            self.debug(f"Processing file: {file_path}")
            self.debug(f"Original filename: {self.original_filename}")

            # Use existing temp dir if available, otherwise create new one
            if not self._temp_dirs:
                self._temp_dirs.append(self.create_temp_dir())
            temp_dir = self._temp_dirs[0]
            self.debug(f"Using temp dir: {temp_dir}")

            # Clean temp dir before use
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if os.path.isfile(item_path) and not item_path == file_path:
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)

            # Extract the archive
            self.debug("Extracting archive...")
            self.extract_archive(file_path, temp_dir)
            self.debug(f"Temp dir contents after extraction: {os.listdir(temp_dir)}")

            # Process the files
            self.debug("Processing files...")
            result = self.process_files(temp_dir, translations)
            self.debug(f"Process files result: {result}")

            if translations is None:
                # self.debug(f"Returning collected texts: {self.collected_texts}")
                return self.collected_texts

            if result:
                # Create output path if not provided
                target_lang = translations.get("target_lang", "translated")
                final_output = output_path or os.path.join(
                    os.path.dirname(file_path),
                    f"{self.original_filename}_{target_lang}.ce",
                )
                self.debug(f"Creating output file: {final_output}")

                # Create CE file
                with zipfile.ZipFile(
                    final_output, "w", zipfile.ZIP_DEFLATED
                ) as zip_ref:
                    # First, copy all files from original archive except .c4v
                    with zipfile.ZipFile(file_path, "r") as orig_zip:
                        for item in orig_zip.namelist():
                            if not item.endswith(".c4v"):
                                self.debug(f"Copying original file: {item}")
                                zip_ref.writestr(item, orig_zip.read(item))

                    # Find and add the translated c4v file
                    c4v_found = False
                    for root, _, files in os.walk(result):
                        for file in files:
                            if file.endswith(".c4v"):
                                file_path = os.path.join(root, file)
                                self.debug(f"Adding translated c4v file: {file_path}")
                                # Get original c4v filename from the archive
                                with zipfile.ZipFile(
                                    self.original_file_path, "r"
                                ) as orig_zip:
                                    orig_c4v = next(
                                        (
                                            name
                                            for name in orig_zip.namelist()
                                            if name.endswith(".c4v")
                                        ),
                                        None,
                                    )
                                    if orig_c4v:
                                        zip_ref.write(
                                            file_path, orig_c4v
                                        )  # Use original path
                                    else:
                                        zip_ref.write(
                                            file_path, os.path.basename(file_path)
                                        )
                                c4v_found = True
                                break
                        if c4v_found:
                            break

                    if not c4v_found:
                        self.debug("No .c4v file found to add to archive")
                        return None

                self.debug(f"Successfully created output file: {final_output}")
                return final_output

            self.debug("No result from process_files")
            return None

        except Exception as e:
            self.debug(f"Error processing texts: {e}")
            return None

    def check_is_archive(self, file_path: Optional[str]) -> bool:
        """Check if file is a TouchChat archive.

        Args:
            file_path (Optional[str]): Path to file to check.

        Returns:
            bool: True if file is a valid TouchChat archive.
        """
        if not file_path:
            return False

        # Check if it's a .ce file
        if not file_path.lower().endswith(".ce"):
            return False

        # Verify it's a valid ZIP file
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                # Try reading the file list
                zf.namelist()
                return True
        except (zipfile.BadZipFile, OSError):
            self.debug(f"File {file_path} is not a valid ZIP archive")
            return False

    def extract_archive(self, file_path: str, target_dir: str) -> None:
        """Extract TouchChat .ce archive.

        Args:
            file_path (str): Path to .ce file
            target_dir (str): Directory to extract to
        """
        self.debug(
            f"Extract archive called with file: {file_path}, target: {target_dir}"
        )
        self.debug(f"File exists check: {os.path.exists(file_path)}")
        self.debug(f"File size: {os.path.getsize(file_path)} bytes")
        self.debug(f"Target dir exists check: {os.path.exists(target_dir)}")

        try:
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                # List all files in archive
                files = zip_ref.namelist()
                self.debug(f"Files in archive: {files}")

                # Look for any .c4v file
                c4v_file = None
                for f in files:
                    if f.endswith(".c4v"):
                        c4v_file = f
                        self.debug(f"Found .c4v file in archive: {c4v_file}")
                        break

                if not c4v_file:
                    self.debug("No .c4v file found in archive")
                    return

                # Extract the .c4v file
                self.debug(f"Extracting {c4v_file} to {target_dir}")
                zip_ref.extract(c4v_file, target_dir)
                self.debug(
                    "Extraction complete. "
                    f"Target dir contents: {os.listdir(target_dir)}"
                )

        except zipfile.BadZipFile as e:
            self.debug(
                f"Failed to extract .ce file - not a valid ZIP archive: {str(e)}"
            )
            # If extraction fails, copy the file as-is
            shutil.copy2(file_path, target_dir)
        except Exception as e:
            self.debug(f"Unexpected error during extraction: {str(e)}")
            raise

    def process_files(
        self, directory: str, translations: Optional[dict[str, str]] = None
    ) -> Optional[str]:
        """Process files in directory.

        Args:
            directory (str): Path to directory containing files.
            translations (Optional[Dict[str, str]]): Dictionary of translations.

        Returns:
            Optional[str]: Path to processed file if successful, None if error.
        """
        try:
            # Find any .c4v file
            c4v_file = None
            self.debug(f"Process files called with directory: {directory}")
            self.debug(f"Directory exists check: {os.path.exists(directory)}")
            self.debug(f"Directory contents: {os.listdir(directory)}")

            for file in os.listdir(directory):
                if file.endswith(".c4v"):
                    c4v_file = os.path.join(directory, file)
                    self.debug(f"Found .c4v file: {c4v_file}")
                    self.debug(f"C4v file exists check: {os.path.exists(c4v_file)}")
                    self.debug(f"C4v file size: {os.path.getsize(c4v_file)} bytes")
                    break

            if not c4v_file:
                self.debug("No .c4v file found in directory")
                return None

            # Create new database with translations
            new_db_path = os.path.join(directory, "translated.c4v")
            shutil.copy2(c4v_file, new_db_path)
            self.debug(f"Created new database at: {new_db_path}")

            # Connect to database
            conn = sqlite3.connect(new_db_path)
            cursor = conn.cursor()

            if translations:
                self.debug(f"Processing translations: {translations}")
                modified = False

                # Update button labels and messages
                for original, translated in translations.items():
                    if original == "target_lang":
                        continue
                    self.debug(f"Translating '{original}' to '{translated}'")

                    # Update button labels
                    cursor.execute(
                        """
                        UPDATE buttons
                        SET label = ?
                        WHERE label = ?
                        """,
                        (translated, original),
                    )
                    if cursor.rowcount > 0:
                        modified = True
                        self.debug(f"Updated {cursor.rowcount} button labels")

                    # Update button messages
                    cursor.execute(
                        """
                        UPDATE buttons
                        SET message = ?
                        WHERE message = ?
                        """,
                        (translated, original),
                    )
                    if cursor.rowcount > 0:
                        modified = True
                        self.debug(f"Updated {cursor.rowcount} button messages")

                    # Update page names
                    cursor.execute(
                        """
                        UPDATE resources
                        SET name = ?
                        WHERE name = ?
                        """,
                        (translated, original),
                    )
                    if cursor.rowcount > 0:
                        modified = True
                        self.debug(f"Updated {cursor.rowcount} resource names")

                # Commit changes and close connection
                conn.commit()
                conn.close()

                if modified:
                    self.debug("Changes were made, replacing original database")
                    # Remove the original database
                    os.remove(c4v_file)
                    # Move the new database to the original location
                    shutil.move(new_db_path, c4v_file)
                    self.debug(f"Moved translated database to: {c4v_file}")
                    return directory
                else:
                    self.debug("No changes were made to the database")
                    # Clean up unused translated database
                    os.remove(new_db_path)
                    return None

            else:
                # Collect texts
                cursor.execute(
                    """
                    SELECT DISTINCT label, message
                    FROM buttons
                    WHERE label IS NOT NULL OR message IS NOT NULL
                    """
                )
                for label, message in cursor.fetchall():
                    if label and label.strip():
                        self.collected_texts.append(label.strip())
                    if message and message.strip():
                        self.collected_texts.append(message.strip())

                conn.close()
                return directory

            return None

        except Exception as e:
            self.debug(f"Error processing files: {e}")
            if "conn" in locals():
                conn.close()
            return None

    def extract_texts(self, file_path: str) -> list[str]:
        """Extract texts from TouchChat file.

        Args:
            file_path (str): Path to the file to extract texts from.

        Returns:
            List[str]: List of extracted texts.
        """
        try:
            # Reset state for new extraction
            self.collected_texts = []
            self.set_source_file(file_path)

            # Prepare workspace
            workspace = self._prepare_workspace(file_path)

            # Process the files
            self.process_files(workspace, None)
            return self.collected_texts

        except Exception as e:
            msg = f"Error extracting texts: {e}"
            self.debug(msg)
            return []

    def _check_database_schema(self, cursor: sqlite3.Cursor) -> None:
        """Check and create database schema if needed.

        Args:
            cursor (sqlite3.Cursor): Database cursor.
        """
        # Check if tables exist
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN (
                'special_pages', 'pages', 'resources', 'buttons',
                'button_boxes', 'button_box_instances', 'button_box_cells',
                'actions', 'action_data'
            )
            """
        )
        existing_tables = {row[0] for row in cursor.fetchall()}

        # Create missing tables
        if "special_pages" not in existing_tables:
            cursor.execute(
                """
                CREATE TABLE special_pages (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    page_id INTEGER
                )
                """
            )

        if "pages" not in existing_tables:
            cursor.execute(
                """
                CREATE TABLE pages (
                    id INTEGER PRIMARY KEY,
                    resource_id INTEGER
                )
                """
            )

        if "resources" not in existing_tables:
            cursor.execute(
                """
                CREATE TABLE resources (
                    id INTEGER PRIMARY KEY,
                    rid TEXT,
                    name TEXT,
                    type INTEGER
                )
                """
            )

        if "buttons" not in existing_tables:
            cursor.execute(
                """
                CREATE TABLE buttons (
                    id INTEGER PRIMARY KEY,
                    resource_id INTEGER,
                    label TEXT,
                    message TEXT,
                    page_id INTEGER
                )
                """
            )

        if "button_boxes" not in existing_tables:
            cursor.execute(
                """
                CREATE TABLE button_boxes (
                    id INTEGER PRIMARY KEY,
                    init_size_x INTEGER,
                    init_size_y INTEGER
                )
                """
            )

        if "button_box_instances" not in existing_tables:
            cursor.execute(
                """
                CREATE TABLE button_box_instances (
                    id INTEGER PRIMARY KEY,
                    button_box_id INTEGER,
                    page_id INTEGER
                )
                """
            )

        if "button_box_cells" not in existing_tables:
            cursor.execute(
                """
                CREATE TABLE button_box_cells (
                    id INTEGER PRIMARY KEY,
                    button_box_id INTEGER,
                    resource_id INTEGER,
                    location INTEGER,
                    span_x INTEGER DEFAULT 1,
                    span_y INTEGER DEFAULT 1
                )
                """
            )

        if "actions" not in existing_tables:
            cursor.execute(
                """
                CREATE TABLE actions (
                    id INTEGER PRIMARY KEY,
                    resource_id INTEGER,
                    code INTEGER
                )
                """
            )

        if "action_data" not in existing_tables:
            cursor.execute(
                """
                CREATE TABLE action_data (
                    id INTEGER PRIMARY KEY,
                    action_id INTEGER,
                    key INTEGER,
                    value TEXT
                )
                """
            )

    def create_translated_file(
        self, file_path: str, translations: dict[str, str]
    ) -> str:
        """Create a translated version of the TouchChat file.

        Args:
            file_path: Path to the TouchChat file.
            translations: Dictionary of translations.

        Returns:
            Path to the translated file.
        """
        # Load the tree structure
        tree = self.load_into_tree(file_path)

        # Apply translations
        for page in tree.pages.values():
            for button in page.buttons:
                if button.label in translations:
                    button.label = translations[button.label]
                if button.vocalization in translations:
                    button.vocalization = translations[button.vocalization]

        # Save the translated tree
        target_lang = translations.get("target_lang", "translated")
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_name = f"{base_name}_{target_lang}.ce"
        output_path = os.path.join(os.path.dirname(file_path), output_name)
        self.save_from_tree(tree, output_path)
        return output_path

    def save_from_tree(self, tree: AACTree, output_path: str) -> None:
        """Save tree to TouchChat format.

        Args:
            tree (AACTree): Tree structure to save.
            output_path (str): Path where to save the file.
        """
        # Create a temporary directory for the database
        workspace = self.get_session_workspace()
        db_path = os.path.join(workspace, "output.c4v")

        # Create database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # Create tables
            self._check_database_schema(cursor)

            # Process each page
            for page_id, page in tree.pages.items():
                # Insert page resource
                cursor.execute(
                    """
                    INSERT INTO resources (rid, name, type)
                    VALUES (?, ?, ?)
                    """,
                    (f"page_{page_id}", page.name, 1),  # type 1 = page
                )
                page_resource_id = cursor.lastrowid

                # Insert page
                cursor.execute(
                    """
                    INSERT INTO pages (resource_id)
                    VALUES (?)
                    """,
                    (page_resource_id,),
                )
                db_page_id = cursor.lastrowid

                # Create button box for the page's grid
                cursor.execute(
                    """
                    INSERT INTO button_boxes (init_size_x, init_size_y)
                    VALUES (?, ?)
                    """,
                    (page.grid_size[1], page.grid_size[0]),  # x = cols, y = rows
                )
                button_box_id = cursor.lastrowid

                # Link button box to page
                cursor.execute(
                    """
                    INSERT INTO button_box_instances (button_box_id, page_id)
                    VALUES (?, ?)
                    """,
                    (button_box_id, db_page_id),
                )

                # Process each button
                for button in page.buttons:
                    # Calculate button location in grid
                    row, col = button.position
                    location = row * page.grid_size[1] + col

                    # Insert button resource
                    rid = f"btn_{button.id}"
                    cursor.execute(
                        """
                        INSERT INTO resources
                        (rid, name, type)
                        VALUES (?, ?, ?)
                        """,
                        (rid, button.label, 2),  # type 2 = button
                    )
                    button_resource_id = cursor.lastrowid

                    # Insert button
                    cursor.execute(
                        """
                        INSERT INTO buttons
                        (resource_id, label, message, page_id)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            button_resource_id,
                            button.label,
                            button.vocalization,
                            db_page_id,
                        ),
                    )

                    # Insert button cell
                    cursor.execute(
                        """
                        INSERT INTO button_box_cells
                        (button_box_id, resource_id, location)
                        VALUES (?, ?, ?)
                        """,
                        (button_box_id, button_resource_id, location),
                    )

                    # If it's a navigation button, add action
                    if button.type == ButtonType.NAVIGATE and button.target_page_id:
                        cursor.execute(
                            """
                            INSERT INTO actions
                            (resource_id, code)
                            VALUES (?, ?)
                            """,
                            (button_resource_id, 1),  # code 1 = navigate
                        )
                        action_id = cursor.lastrowid

                        cursor.execute(
                            """
                            INSERT INTO action_data
                            (action_id, key, value)
                            VALUES (?, ?, ?)
                            """,
                            (
                                action_id,
                                1,
                                button.target_page_id,
                            ),  # key 1 = target page
                        )

                # Set home page if this is the root page
                if page_id == tree.root_id:
                    cursor.execute(
                        """
                        INSERT INTO special_pages (name, page_id)
                        VALUES (?, ?)
                        """,
                        ("Home", db_page_id),
                    )

            conn.commit()

            # Create CE file
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
                zip_ref.write(db_path, "output.c4v")

        except Exception as e:
            msg = f"Error saving tree: {e}"
            self.debug(msg)
            raise
        finally:
            conn.close()

    def load_into_tree(self, file_path: str) -> AACTree:
        """Load TouchChat file into tree structure.

        Args:
            file_path (str): Path to the file to load.

        Returns:
            AACTree: Tree structure representing the file contents.

        Raises:
            ValueError: If the file is not a valid TouchChat archive.
            Exception: If there is an error loading the file.
        """
        try:
            tree = AACTree()
            workspace = self._prepare_workspace(file_path)

            # Find the .c4v file
            c4v_file = None
            for file in os.listdir(workspace):
                if file.endswith(".c4v"):
                    c4v_file = os.path.join(workspace, file)
                    break

            if not c4v_file:
                raise ValueError("No .c4v file found in archive")

            # Connect to database
            conn = sqlite3.connect(c4v_file)
            cursor = conn.cursor()

            # Ensure database schema exists
            self._check_database_schema(cursor)

            # First find home page from special_pages
            cursor.execute(
                """
                SELECT page_id
                FROM special_pages
                WHERE name = 'Home'
                """
            )
            result = cursor.fetchone()
            if result:
                tree.root_id = str(result[0])

            # Get all pages
            cursor.execute(
                """
                SELECT p.id, r.name, bb.init_size_x, bb.init_size_y
                FROM pages p
                JOIN resources r ON p.resource_id = r.id
                JOIN button_box_instances bbi ON bbi.page_id = p.id
                JOIN button_boxes bb ON bbi.button_box_id = bb.id
                """
            )

            for page_id, page_name, grid_x, grid_y in cursor.fetchall():
                page = AACPage(
                    id=str(page_id),
                    name=page_name,
                    grid_size=(
                        grid_y or 1,
                        grid_x or 1,
                    ),  # TouchChat uses x,y but we use rows,cols
                )

                # Get buttons for this page
                cursor.execute(
                    """
                    SELECT b.id, b.label, b.message,
                        bbc.location, bbc.span_x, bbc.span_y,
                        a.code
                    FROM button_box_instances bbi
                    JOIN button_boxes bb ON bbi.button_box_id = bb.id
                    JOIN button_box_cells bbc ON bbc.button_box_id = bb.id
                    JOIN buttons b ON b.resource_id = bbc.resource_id
                    LEFT JOIN actions a ON a.resource_id = b.resource_id
                    WHERE bbi.page_id = ?
                    """,
                    (page_id,),
                )

                for row in cursor.fetchall():
                    (
                        button_id,
                        label,
                        message,
                        location,
                        span_x,
                        span_y,
                        action_code,
                    ) = row

                    # Calculate position from location
                    y = location // grid_x if grid_x else 0
                    x = location % grid_x if grid_x else 0

                    # Determine button type based on action code
                    button_type = ButtonType.SPEAK
                    target_page_id = None

                    if action_code == 1:  # Navigate action
                        button_type = ButtonType.NAVIGATE
                        # Get target page from action data
                        cursor.execute(
                            """
                            SELECT value
                            FROM action_data
                            WHERE action_id = ? AND key = 1
                            """,
                            (button_id,),
                        )
                        target_result = cursor.fetchone()
                        if target_result:
                            target_page_id = str(target_result[0])

                    button = AACButton(
                        id=str(button_id),
                        label=label or "",
                        type=button_type,
                        position=(y, x),
                        target_page_id=target_page_id,
                        vocalization=message,
                    )
                    page.buttons.append(button)

                tree.add_page(page)

            conn.close()
            return tree

        except Exception as e:
            msg = f"Error loading TouchChat file: {e}"
            self.debug(msg)
            raise

    def process_translations(
        self, input_path: str, translations: dict[str, str], output_path: str
    ) -> None:
        """Process translations and create translated file.

        Copy the input file and update its contents with translations.

        Args:
            input_path: Path to input file.
            translations: Dictionary of translations.
            output_path: Path to output file.
        """
        # Copy original file to output path
        shutil.copy2(input_path, output_path)

        # Update translations in the copied file
        self.create_translated_file(output_path, translations)
