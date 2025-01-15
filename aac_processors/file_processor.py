import os
import shutil
import tempfile
from abc import abstractmethod
from collections.abc import Iterator
from typing import Any, Optional

from .base_processor import AACProcessor
from .tree_structure import AACTree


class FileProcessor(AACProcessor):
    """Base class for AAC file processors that work with files."""

    def __init__(self) -> None:
        """Initialize the file processor."""
        super().__init__()
        self.file_path: Optional[str] = None
        self._temp_dirs: list[str] = []

    def set_source_file(self, file_path: str) -> None:
        """Set source file path.

        Args:
            file_path: Path to source file.
        """
        self.file_path = file_path

    def create_temp_dir(self) -> str:
        """Create a temporary directory.

        Returns:
            Path to created temporary directory.
        """
        temp_dir = tempfile.mkdtemp()
        self._temp_dirs.append(temp_dir)
        return temp_dir

    def cleanup_temp_files(self) -> None:
        """Clean up temporary files."""
        for temp_dir in self._temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        self._temp_dirs = []

    def _prepare_workspace(self, file_path: str) -> str:
        """Prepare workspace for processing.

        Args:
            file_path: Path to file to process.

        Returns:
            Path to workspace directory.
        """
        workspace = self.create_temp_dir()
        self.set_source_file(file_path)
        return workspace

    @abstractmethod
    def process_files(
        self, directory: str, translations: Optional[dict[str, str]] = None
    ) -> Optional[str]:
        """Process files in directory.

        Args:
            directory: Directory containing files to process.
            translations: Dictionary of translations.

        Returns:
            Path to translated file if successful, None otherwise.
        """
        pass

    def analyze_vocabulary(self, tree: AACTree) -> dict[str, Any]:
        """Analyze vocabulary in tree structure.

        Args:
            tree: Tree structure to analyze.

        Returns:
            Dictionary containing vocabulary analysis.
        """
        analysis: dict[str, Any] = {
            "total_buttons": 0,
            "unique_words": set[str](),
            "word_frequency": dict[str, int](),
            "button_types": {
                "speak": 0,
                "navigate": 0,
                "action": 0,
                "wordlist": 0,
                "command": 0,
            },
        }

        for page in tree.pages.values():
            for button in page.buttons:
                analysis["total_buttons"] += 1
                analysis["button_types"][button.type.value] += 1

                if button.vocalization:
                    words = button.vocalization.lower().split()
                    for word in words:
                        analysis["unique_words"].add(word)
                        analysis["word_frequency"][word] = (
                            analysis["word_frequency"].get(word, 0) + 1
                        )

        # Convert set to list for JSON serialization
        analysis["unique_words"] = list(analysis["unique_words"])
        return analysis

    def _walk_files(self, directory: str) -> Iterator[tuple[str, str]]:
        """Walk through files in directory.

        Args:
            directory: Directory to walk through.

        Yields:
            Tuple of (relative path, absolute path) for each file.
        """
        for root, _, files in os.walk(directory):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, directory)
                yield rel_path, abs_path

    def _copy_file(self, src: str, dst: str) -> None:
        """Copy file with proper error handling.

        Args:
            src: Source file path.
            dst: Destination file path.
        """
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        except Exception as e:
            self.debug(f"Error copying file {src} to {dst}: {str(e)}")
            raise
