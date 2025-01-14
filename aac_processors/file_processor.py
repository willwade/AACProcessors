import os
from os import walk
import tempfile
import shutil
import zipfile
from abc import abstractmethod
from typing import Optional, Dict, List, Union, Any, Callable
from .base_processor import AACProcessor
from .tree_structure import AACTree, AACPage
import re


class FileProcessor(AACProcessor):
    """Base class for AAC file processors that work with files."""

    def __init__(self, debug_output: Optional[Callable[[str], None]] = None):
        """Initialize processor.

        Args:
            debug_output: Function to use for debug output.
        """
        super().__init__()  # Call AACProcessor's __init__
        self._temp_dirs: List[str] = []
        self._debug_output = debug_output or print
        self.collected_texts: List[str] = []
        self.file_path: Optional[str] = None
        self.original_filename: Optional[str] = None
        self.original_file_path: Optional[str] = None

    def debug(self, message: str) -> None:
        """Output debug message.

        Args:
            message (str): Message to output.
        """
        if self._debug_output:
            self._debug_output(message)

    def create_temp_dir(self) -> str:
        """Create a temporary directory and track it for cleanup.

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

    def get_output_path(self, target_lang: Optional[str] = None) -> str:
        """Get output path for translated file.

        Args:
            target_lang: Target language code.

        Returns:
            str: Path where translated file should be saved.

        Raises:
            ValueError: If no file path is set.
        """
        if not self.file_path:
            raise ValueError("No file path is set")
        
        dir_name = os.path.dirname(self.file_path)
        base_name = (
            self.original_filename
            or os.path.splitext(os.path.basename(self.file_path))[0]
        )
        # Remove any existing language suffix if present
        if '_' in base_name:
            base_parts = base_name.split('_')
            if len(base_parts[-1]) <= 5:  # Assuming language codes are <= 5 chars
                base_name = '_'.join(base_parts[:-1])
        
        ext = os.path.splitext(self.file_path)[1]
        suffix = f"_{target_lang}" if target_lang else "_translated"
        return os.path.join(dir_name, f"{base_name}{suffix}{ext}")

    def analyze_vocabulary(self) -> Dict[str, Any]:
        """File-specific vocabulary analysis.

        Returns:
            Dict[str, Any]: Analysis results including file-specific metrics.
        """
        analysis = super().analyze_vocabulary()
        # Add file-specific analysis
        analysis.update(
            {
                "file_type": self.__class__.__name__,
                "file_size": os.path.getsize(self.file_path) if self.file_path else 0,
            }
        )
        return analysis

    def process_texts(
        self,
        file_path: str,
        translations: Optional[Dict[str, str]] = None,
        output_path: Optional[str] = None
    ) -> Union[List[str], str, None]:
        """Process texts in a single file - extract or translate.

        Args:
            file_path (str): Path to the file to process.
            translations (Optional[Dict[str, str]]): Dictionary of translations.
            output_path (Optional[str]): Path where to save the translated file.

        Returns:
            Union[List[str], str, None]: List of texts if extracting,
            path to translated file if translating, None if no changes.
        """
        try:
            # Reset state for new translation
            self.collected_texts = []
            
            if file_path:
                # Always update file_path to the current file
                self.file_path = file_path
                
                # If this is a new original file, update original paths
                if not self.original_file_path or (translations is None and file_path != self.original_file_path):
                    self.original_file_path = file_path
                    basename = os.path.basename(file_path)
                    self.original_filename = os.path.splitext(basename)[0]
                    self.debug(f"Set original paths: file={self.original_file_path}, name={self.original_filename}")

            # Create working directory
            temp_dir = self.create_temp_dir()
            self.debug(f"Created temp dir: {temp_dir}")

            # Extract if it's an archive
            if not self.file_path:
                self.debug("No file path set")
                return None
                           
            # Check if file is an archive and set the flag
            try:
                self.is_archive = self.check_is_archive(self.file_path)
                self.debug(f"Archive check: is_archive={self.is_archive}")
            except Exception as e:
                self.debug(f"Error checking if file is archive: {str(e)}")
                raise
            
            if self.is_archive:
                self.debug(f"Extracting archive: {self.file_path} to {temp_dir}")
                self.extract_archive(self.file_path, temp_dir)
            else:
                self.debug(f"Copying file: {self.file_path} to {temp_dir}")
                shutil.copy2(self.file_path, temp_dir)

            # Process the files
            modified = self.process_files(temp_dir, translations)
            self.debug(f"Process files result: modified={modified}")

            if translations is None:
                return self.collected_texts  # Return extracted texts

            if modified:
                if output_path:
                    self.debug(f"Creating output at: {output_path}")
                    if self.is_archive:
                        self.create_archive(temp_dir, output_path)
                    else:
                        basename = os.path.basename(self.file_path)
                        src = os.path.join(temp_dir, basename)
                        shutil.copy2(src, output_path)
                    return output_path  # Return path to translated file
                else:
                    # Create default output path if none provided
                    target_lang = translations.get('target_lang', 'unknown')
                    base_name = os.path.splitext(self.file_path)[0]
                    ext = os.path.splitext(self.file_path)[1]
                    default_output = f"{base_name}_{target_lang}{ext}"
                    self.debug(f"Using default output path: {default_output}")
                    if self.is_archive:
                        self.create_archive(temp_dir, default_output)
                    else:
                        basename = os.path.basename(self.file_path)
                        src = os.path.join(temp_dir, basename)
                        shutil.copy2(src, default_output)
                    return default_output

            return None

        finally:
            self.cleanup()

    @abstractmethod
    def process_files(
        self, directory: str, translations: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """Process all files in directory - implement in child class.

        Args:
            directory (str): Path to directory containing files.
            translations (Optional[Dict[str, str]]): Dictionary of translations to apply.

        Returns:
            str: Path to translated file if any files were modified, None otherwise.
        """
        self.collected_texts = []
        self.file_path = None
        
        pass

    def check_is_archive(self, file_path: Optional[str]) -> bool:
        """Check if file is an archive.

        Args:
            file_path (Optional[str]): Path to file to check.

        Returns:
            bool: True if file is a valid archive.
        """
        if not file_path:
            return False
        
        # First check extension
        if not file_path.lower().endswith((".zip", ".gridset", ".obz")):
            return False
            
        # Then verify it's a valid ZIP file
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # Try reading the file list - this will fail if not a valid ZIP
                zf.namelist()
            return True
        except zipfile.BadZipFile:
            return False
        except Exception as e:
            self.debug(f"Error checking if file is archive: {str(e)}")
            return False

    def extract_archive(self, file_path: str, directory: str) -> None:
        """Extract archive to directory.

        Args:
            file_path (str): Path to archive file.
            directory (str): Directory to extract to.
        """
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(directory)

    def create_archive(self, directory: str, output_path: str) -> None:
        """Create archive from directory.

        Args:
            directory (str): Directory to archive.
            output_path (str): Path where to save archive.
        """
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
            for root, dirs, files in os.walk(directory):  # type: Iterator[Tuple[str, List[str], List[str]]]
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, directory)
                    zip_ref.write(file_path, arc_name)

    def load_into_tree(self, file_path: str) -> AACTree:
        """Load file into common tree structure.

        Args:
            file_path (str): Path to the file to load.

        Returns:
            AACTree: Tree structure representing the file contents.

        Raises:
            NotImplementedError: Must be implemented by child class.
        """
        raise NotImplementedError("load_into_tree must be implemented by child class")

    def save_from_tree(self, tree: AACTree, output_path: str):
        """Save tree structure back to file.

        Args:
            tree (AACTree): Tree structure to save.
            output_path (str): Path where to save the file.

        Raises:
            NotImplementedError: Must be implemented by child class.
        """
        raise NotImplementedError("save_from_tree must be implemented by child class")

    def _convert_page_to_obf(self, page: AACPage) -> dict:
        """Convert page to OBF format.

        Args:
            page (AACPage): Page to convert.

        Returns:
            dict: OBF format data.

        Raises:
            NotImplementedError: Must be implemented by child class.
        """
        raise NotImplementedError(
            "_convert_page_to_obf must be implemented by child class"
        )

    def _convert_obf_to_page(self, obf_data: dict) -> AACPage:
        """Convert OBF data to page.

        Args:
            obf_data (dict): OBF format data.

        Returns:
            AACPage: Converted page.

        Raises:
            NotImplementedError: Must be implemented by child class.
        """
        raise NotImplementedError(
            "_convert_obf_to_page must be implemented by child class"
        )

    def _read_file_content(self) -> str:
        """Thread-safe file reading.

        Returns:
            str: Contents of the file.
        """
        temp_copy = self._create_temp_file(prefix="file_copy")
        try:
            # Create a temporary copy for processing
            import shutil

            shutil.copy2(self.file_path, temp_copy)

            with open(temp_copy, "r", encoding="utf-8") as f:
                return f.read()
        finally:
            if os.path.exists(temp_copy):
                os.remove(temp_copy)

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name to be used as an ID.

        Args:
            name (str): Name to sanitize.

        Returns:
            str: Sanitized name with special characters and spaces removed.
        """
        if not name:
            return ""
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r"[^a-zA-Z0-9]", "_", name)
        # Remove consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        return sanitized.lower()
