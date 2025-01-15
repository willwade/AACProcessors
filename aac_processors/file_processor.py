import os
import shutil
import tempfile
import zipfile
from abc import abstractmethod
from collections.abc import Iterator
from typing import Any, Optional, Union

from .base_processor import AACProcessor
from .tree_structure import AACTree


class FileProcessor(AACProcessor):
    """Base class for AAC file processors that work with files."""

    def __init__(self) -> None:
        """Initialize the file processor."""
        super().__init__()
        self.file_path: Optional[str] = None
        self.original_filename: Optional[str] = None
        self.original_file_path: Optional[str] = None
        self._temp_dirs: list[str] = []
        self.collected_texts: list[str] = []
        self._debug_output = print  # Default debug output

    def set_source_file(self, file_path: str) -> None:
        """Set source file path.

        Args:
            file_path: Path to source file.
        """
        self.file_path = file_path
        self.original_file_path = file_path
        self.original_filename = os.path.splitext(os.path.basename(file_path))[0]

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

    def _sanitize_name(self, name: Optional[str]) -> str:
        """Sanitize a filename.

        Args:
            name: Name to sanitize.

        Returns:
            Sanitized name.
        """
        if not name:
            return ""
        # Remove punctuation and convert spaces/hyphens to underscores
        import re

        sanitized = re.sub(r"[^\w\s-]", "", name)
        sanitized = re.sub(r"[-\s]+", "_", sanitized)
        return sanitized.lower().strip("_")

    def get_output_path(self, target_lang: Optional[str] = None) -> str:
        """Get output path for translated file.

        Args:
            target_lang: Target language code.

        Returns:
            Path for translated file.

        Raises:
            ValueError: If no source file has been set.
        """
        if not self.file_path:
            raise ValueError("No source file has been set")

        if not target_lang:
            target_lang = "translated"

        # Get base name without any existing language suffix
        if self.original_filename:
            base_name = self.original_filename
        else:
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]

        if "_" in base_name:
            base_parts = base_name.split("_")
            if len(base_parts[-1]) <= 5:  # Assuming language codes are <= 5 chars
                base_name = "_".join(base_parts[:-1])

        # Get original extension
        ext = os.path.splitext(self.file_path)[1]

        # Create output name with target language
        output_name = f"{base_name}_{target_lang}{ext}"
        return os.path.join(os.path.dirname(self.file_path), output_name)

    def process_texts(
        self,
        file_path: str,
        translations: Optional[dict[str, str]] = None,
        output_path: Optional[str] = None,
    ) -> Union[list[str], str, None]:
        """Process texts in file.

        Args:
            file_path: Path to file to process.
            translations: Dictionary of translations.
            output_path: Optional path where to save translated file.

        Returns:
            Union[List[str], str, None]: List of texts if extracting,
            path to translated file if translating, None if error.
        """
        try:
            # Reset state for new translation
            self.collected_texts = []
            self.set_source_file(file_path)

            # Create temp directory for processing
            temp_dir = self.create_temp_dir()

            # Extract archive if necessary, or copy file
            if self.check_is_archive(file_path):
                self.extract_archive(file_path, temp_dir)
            else:
                # Copy file to temp directory
                temp_file = os.path.join(temp_dir, os.path.basename(file_path))
                shutil.copy2(file_path, temp_file)

            # Process the files
            result = self.process_files(temp_dir, translations)

            if translations is None:
                # In extract mode, return extracted texts
                return self.extract_texts(file_path)

            if result:
                if output_path:
                    # Copy result to output path
                    shutil.copy2(result, output_path)
                    return output_path
                return result

            return None

        except Exception as e:
            self.debug(f"Error processing texts: {str(e)}")
            return None
        finally:
            self.cleanup_temp_files()

    def check_is_archive(self, file_path: Optional[str]) -> bool:
        """Check if file is an archive.

        Args:
            file_path: Path to file to check.

        Returns:
            bool: True if file is an archive.
        """
        if not file_path:
            return False
        try:
            with zipfile.ZipFile(file_path, "r") as _:
                return True
        except zipfile.BadZipFile:
            return False

    def extract_archive(self, archive_path: str, target_dir: str) -> None:
        """Extract archive to target directory.

        Args:
            archive_path: Path to archive file.
            target_dir: Directory to extract to.
        """
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(target_dir)

    def create_archive(self, source_dir: str, output_path: str) -> None:
        """Create archive from directory.

        Args:
            source_dir: Directory to archive.
            output_path: Path where to save archive.
        """
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zf.write(file_path, arcname)
