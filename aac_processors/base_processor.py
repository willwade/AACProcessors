import os
import shutil
import tempfile
import uuid
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Optional, Union

from .tree_structure import AACTree, ButtonStyle, ButtonType


class AACProcessor(ABC):
    """Base class for AAC file processors."""

    _temp_lock = Lock()  # Class-level lock for temp operations

    def __init__(self) -> None:
        """Initialize the processor."""
        self.tree = AACTree()
        self._session_id = str(uuid.uuid4())
        self.source_file: Optional[Path] = None
        self.temp_dir: Optional[Path] = None
        self._original_filename: Optional[str] = None
        self._debug_output: Optional[Callable[[str], None]] = None
        self.is_archive = False  # Default to non-archive
        self.collected_texts: list[str] = []

    def get_session_workspace(self) -> str:
        """Get a unique workspace directory for this processing session.

        Returns:
            str: Path to the session workspace directory.

        Raises:
            RuntimeError: If workspace creation fails.
        """
        if not self.temp_dir:
            with self._temp_lock:
                temp_dir = tempfile.mkdtemp(prefix=f"aac_{self._session_id}_")
                if not temp_dir:
                    raise RuntimeError("Failed to create temporary directory")
                self.temp_dir = Path(temp_dir)
                self._debug_print(f"Created session workspace: {temp_dir}")

        if not self.temp_dir:  # For type checker
            raise RuntimeError("Temporary directory not available")
        return str(self.temp_dir)

    def set_source_file(self, file_path: str) -> None:
        """Record the original filename.

        Args:
            file_path: Path to the source file.
        """
        filename = os.path.splitext(os.path.basename(file_path))[0]
        self._original_filename = filename
        self.source_file = Path(file_path)
        self._debug_print(f"Set source file: {filename}")

    def _prepare_workspace(self, file_path: str) -> str:
        """Prepare workspace based on file type.

        Args:
            file_path (str): Path to the source file

        Returns:
            str: Path to the working directory
        """
        workspace = self.get_session_workspace()

        if self.is_archive and zipfile.is_zipfile(file_path):
            self._debug_print(f"Extracting archive to workspace: {workspace}")
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(workspace)
        else:
            self._debug_print(f"Copying file to workspace: {workspace}")
            shutil.copy2(file_path, workspace)

        return workspace

    def _create_output(self, workspace: str, output_path: str) -> None:
        """Create final output file from workspace.

        Args:
            workspace (str): Path to the working directory
            output_path (str): Desired output path
        """
        if self.is_archive:
            self._debug_print(f"Creating archive at: {output_path}")
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
                for root, _, files in os.walk(workspace):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, workspace)
                        zip_ref.write(file_path, arc_name)
        else:
            self._debug_print(f"Copying output file to: {output_path}")
            # For non-archives, find and copy the processed file
            processed_files = os.listdir(workspace)
            if processed_files:
                source = os.path.join(workspace, processed_files[0])
                shutil.copy2(source, output_path)

    def get_output_path(self, target_lang: Optional[str] = None) -> str:
        """Generate output path using original filename.

        Args:
            target_lang: Target language code.

        Returns:
            str: Path where output file should be saved.

        Raises:
            ValueError: If no source file has been set.
        """
        if not self._original_filename:
            raise ValueError("No source file has been set")

        # Use original filename but in session workspace
        output_name = f"{self._original_filename}_{target_lang or 'translated'}"
        workspace = (
            self.get_session_workspace()
        )  # This ensures we have a valid workspace
        return os.path.join(workspace, output_name)

    def cleanup_temp_files(self) -> None:
        """Clean up temporary files and directories."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
                self._debug_print("Cleaned up workspace directory")
            except Exception as e:
                self._debug_print(f"Error cleaning workspace: {str(e)}")

    def _debug_print(self, message: str) -> None:
        """Print debug message using configured output function.

        Args:
            message (str): Debug message to print.
        """
        if self._debug_output:
            self._debug_output(f"DEBUG:{self.__class__.__name__}: {message}")

    def set_debug_output(self, debug_output: Optional[Callable[[str], None]]) -> None:
        """Set debug output callback.

        Args:
            debug_output: Callback function for debug output.
        """
        self._debug_output = debug_output

    def debug(self, message: str) -> None:
        """Output debug message.

        Args:
            message: Message to output.
        """
        if self._debug_output:
            self._debug_output(f"{self.__class__.__name__}: {message}")

    @abstractmethod
    def can_process(self, file_path: str) -> bool:
        """Check if processor can handle this file type.

        Args:
            file_path: Path to file to check.

        Returns:
            True if processor can handle this file type.
        """
        pass

    @abstractmethod
    def load_into_tree(self, file_path: str) -> AACTree:
        """Load file into tree structure.

        Args:
            file_path: Path to file to load.

        Returns:
            Tree structure representing the AAC system.
        """
        pass

    @abstractmethod
    def save_from_tree(self, tree: AACTree, output_path: str) -> None:
        """Save tree structure to file.

        Args:
            tree: Tree structure to save.
            output_path: Path where to save the file.
        """
        pass

    @abstractmethod
    def extract_texts(self, file_path: str) -> list[str]:
        """Extract translatable texts from file.

        Args:
            file_path: Path to file to extract texts from.

        Returns:
            List of translatable texts.
        """
        pass

    @abstractmethod
    def create_translated_file(
        self, file_path: str, translations: dict[str, str]
    ) -> Optional[str]:
        """Create translated version of file.

        Args:
            file_path: Path to original file.
            translations: Dictionary of translations.

        Returns:
            Path to translated file if successful, None otherwise.
        """
        pass

    def process_texts(
        self,
        file_path: str,
        translations: Optional[dict[str, str]] = None,
        output_path: Optional[str] = None,
    ) -> Optional[Union[list[str], str]]:
        """Process texts in file.

        Args:
            file_path: Path to file to process.
            translations: Dictionary of translations.
            output_path: Path where to save translated file.

        Returns:
            List of texts if extracting, path to translated file if translating,
            None if error.
        """
        try:
            # Reset state for new translation
            self.collected_texts = []

            if translations is None:
                # Extract texts
                texts = self.extract_texts(file_path)
                return texts

            # Create translated file
            result = self.create_translated_file(file_path, translations)
            if result:
                if output_path:
                    # Copy result to output path if specified
                    shutil.copy2(result, output_path)
                    return output_path
                return result

            return None

        except Exception as e:
            self.debug(f"Error processing texts: {str(e)}")
            return None


class AACButton:
    """Button in an AAC system."""

    def __init__(
        self,
        id: str,
        label: str,
        type: ButtonType = ButtonType.SPEAK,
        position: tuple[int, int] = (0, 0),
        target_page_id: Optional[str] = None,
        vocalization: Optional[str] = None,
        action: Optional[str] = None,
        image: Optional[dict[str, Any]] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
    ) -> None:
        """Initialize button.

        Args:
            id: Unique identifier
            label: Button text
            type: Button type (speak, navigate, action)
            position: Grid position (row, col)
            target_page_id: ID of target page for navigation
            vocalization: Text to speak (if different from label)
            action: Action to perform
            image: Image data dictionary
            width: Button width as percentage of page width (0.0-1.0)
            height: Button height as percentage of page height (0.0-1.0)
        """
        self.id = id
        self.label = label
        self.type = type
        self.position = position
        self.target_page_id = target_page_id
        self.vocalization = vocalization or label
        self.action = action
        self.image = image or {}
        self.style = ButtonStyle()
        self.width = width
        self.height = height
