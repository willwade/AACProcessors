import os
import shutil
import sqlite3
import tempfile
from abc import abstractmethod
from pathlib import Path
from sqlite3 import Connection, Cursor
from threading import Lock
from typing import Any, Optional, Union

from .base_processor import AACProcessor
from .tree_structure import AACButton, AACPage, ButtonType


class SQLiteProcessor(AACProcessor):
    """Base class for processors that handle SQLite database files."""

    def __init__(self) -> None:
        """Initialize the SQLite processor."""
        super().__init__()
        self.collected_texts = []
        self._db_lock = Lock()
        self._query_cache: dict[str, list[tuple[Any, ...]]] = {}
        self._temp_dirs: list[str] = []  # Track temporary directories for cleanup
        self.file_path: Optional[str] = None  # Store the current file path
        self._conn: Optional[Connection] = None

    def create_temp_dir(self) -> str:
        """Create a temporary directory and track it for cleanup.

        The directory will be automatically cleaned up when cleanup() is called.

        Returns:
            str: Path to created temporary directory.
        """
        temp_dir = tempfile.mkdtemp()
        self._temp_dirs.append(temp_dir)
        return temp_dir

    def cleanup(self) -> None:
        """Clean up temporary directories."""
        for temp_dir in self._temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        self._temp_dirs = []

    def process_texts(
        self,
        file_path: str,
        translations: Optional[dict[str, str]] = None,
        output_path: Optional[str] = None,
    ) -> Union[list[str], str, None]:
        """Process texts in SQLite database.

        Args:
            file_path (str): Path to the SQLite database file.
            translations (Optional[Dict[str, str]]): Dictionary of translations.
            output_path (Optional[str]): Path where to save the translated file.

        Returns:
            Union[List[str], str, None]: List of texts if extracting,
            path to translated file if translating, None if error.
        """
        try:
            # Reset state for new translation
            self.collected_texts = []
            self.set_source_file(file_path)

            # Prepare workspace and get working directory
            workspace = self._prepare_workspace(file_path)

            # Process the files
            result = self.process_files(workspace, translations)

            if translations is None:
                return self.collected_texts

            if result and output_path:
                self._create_output(workspace, output_path)
                return output_path

            return None

        finally:
            self.cleanup_temp_files()

    def _connect(self, db_path: Union[str, Path]) -> Connection:
        """Connect to SQLite database"""
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found: {db_path}")
        return sqlite3.connect(db_path)

    def _execute_query(
        self, query: str, params: Optional[tuple] = None
    ) -> list[tuple[Any, ...]]:
        """Execute a query and return results"""
        if not self._conn:
            raise RuntimeError("No database connection")

        cursor: Cursor = self._conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()

    def _execute_many(self, query: str, params: list[tuple]) -> None:
        """Execute multiple queries with different parameters"""
        if not self._conn:
            raise RuntimeError("No database connection")

        cursor: Cursor = self._conn.cursor()
        cursor.executemany(query, params)
        self._conn.commit()

    @abstractmethod
    def process_files(
        self, directory: str, translations: Optional[dict[str, str]] = None
    ) -> Optional[str]:
        """Process files in the directory - implement in child class.

        Args:
            directory (str): Directory containing the files to process.
            translations (Optional[Dict[str, str]]): Dictionary of translations.

        Returns:
            Optional[str]: Path to translated file if successful, None otherwise.
        """
        pass

    def get_output_path(self, target_lang: Optional[str] = None) -> str:
        """Get output path for translated file.

        Args:
            target_lang (Optional[str]): Target language code.

        Returns:
            str: Path where translated file should be saved.

        Raises:
            ValueError: If no file path is set.
        """
        if not self.file_path:
            raise ValueError("No file path set")
        dir_name = os.path.dirname(self.file_path)
        basename = os.path.basename(self.file_path)
        base_name = os.path.splitext(basename)[0]
        ext = os.path.splitext(self.file_path)[1]
        return os.path.join(dir_name, f"{base_name}_{target_lang}{ext}")

    def _convert_page_to_obf(self, page: AACPage) -> dict:
        """Convert page to OBF format - common implementation for SQLite processors.

        Args:
            page (AACPage): Page to convert.

        Returns:
            dict: OBF format data.
        """
        return {
            "id": page.id,
            "name": page.name,
            "grid": {"rows": page.grid_size[0], "columns": page.grid_size[1]},
            "buttons": [
                {
                    "id": button.id,
                    "label": button.label,
                    "vocalization": button.vocalization,
                    "load_board": (
                        {"id": button.target_page_id}
                        if button.type == ButtonType.NAVIGATE
                        else None
                    ),
                }
                for button in page.buttons
            ],
        }

    def _convert_obf_to_page(self, obf_data: dict) -> AACPage:
        """Convert OBF data to AACPage.

        Args:
            obf_data (dict): OBF format data.

        Returns:
            AACPage: Converted page.
        """
        page = AACPage(
            id=obf_data.get("id", ""),
            name=obf_data.get("name", ""),
            grid_size=(
                obf_data.get("grid", {}).get("rows", 1),
                obf_data.get("grid", {}).get("columns", 1),
            ),
        )

        # Process buttons
        for button_data in obf_data.get("buttons", []):
            if not button_data:  # Skip if button_data is None
                continue

            # Get button type and target
            button_type = ButtonType.SPEAK
            target_page_id = None

            # Handle navigation buttons
            load_board = button_data.get("load_board", {})
            if load_board:
                button_type = ButtonType.NAVIGATE
                target_page_id = load_board.get("id")

            # Handle action buttons
            actions = button_data.get("actions", [])
            if actions:
                button_type = ButtonType.ACTION

            # Create button
            button = AACButton(
                id=button_data.get("id", ""),
                label=button_data.get("label", ""),
                type=button_type,
                position=(0, 0),  # Default position
                vocalization=button_data.get("vocalization"),
                target_page_id=target_page_id,
            )

            # Add actions if present
            if actions:
                button.action = actions[0]  # Take first action

            page.buttons.append(button)

        return page

    def debug(self, message: str) -> None:
        """Output debug message.

        Args:
            message (str): Message to output.
        """
        if self._debug_output:
            self._debug_output(f"{self.__class__.__name__}: {message}")

    def _debug_print(self, message: str) -> None:
        """Print debug message.

        Args:
            message (str): Message to print.
        """
        if self._debug_output:
            self._debug_output(message)

    def set_source_file(self, file_path: str) -> None:
        """Set source file path.

        Args:
            file_path: Path to source file.
        """
        super().set_source_file(file_path)  # Call parent implementation
        self.file_path = file_path  # Set file_path for SQLite operations
