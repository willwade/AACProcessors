from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Union
from .tree_structure import AACTree, AACPage
import zipfile
import json
import tempfile
import os
import uuid
from threading import Lock
import shutil


class AACProcessor(ABC):
    """Base class for AAC file processors."""

    _temp_lock = Lock()  # Class-level lock for temp operations

    def __init__(self):
        """Initialize the processor."""
        self.tree = AACTree()
        self._session_id = str(uuid.uuid4())
        self._temp_dir = None
        self._original_filename = None
        self._debug_output = print
        self.is_archive = False  # Default to non-archive

    def get_session_workspace(self) -> str:
        """Get a unique workspace directory for this processing session.

        Returns:
            str: Path to the session workspace directory.
        """
        if not self._temp_dir:
            with self._temp_lock:
                self._temp_dir = tempfile.mkdtemp(prefix=f"aac_{self._session_id}_")
                self._debug_print(f"Created session workspace: {self._temp_dir}")
        return self._temp_dir

    def set_source_file(self, file_path: str) -> None:
        """Record the original filename.

        Args:
            file_path (str): Path to the source file.
        """
        self._original_filename = os.path.splitext(os.path.basename(file_path))[0]
        self._debug_print(f"Set source file: {self._original_filename}")

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
            target_lang (Optional[str]): Target language code.

        Returns:
            str: Path where output file should be saved.

        Raises:
            ValueError: If no source file has been set.
        """
        if not self._original_filename:
            raise ValueError("No source file has been set")
        
        # Use original filename but in session workspace
        output_name = f"{self._original_filename}_{target_lang or 'translated'}"
        return os.path.join(self.get_session_workspace(), output_name)

    def cleanup_temp_files(self):
        """Clean up temporary files and directories."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
                self._temp_dir = None
                self._debug_print(f"Cleaned up workspace directory")
            except Exception as e:
                self._debug_print(f"Error cleaning workspace: {str(e)}")

    def _debug_print(self, message: str):
        """Print debug message using configured output function.

        Args:
            message (str): Debug message to print.
        """
        if self._debug_output:
            self._debug_output(f"DEBUG:{self.__class__.__name__}: {message}")

    @abstractmethod
    def can_process(self, file_path: str) -> bool:
        """Check if this processor can handle the given file.

        Args:
            file_path (str): Path to the file to check.

        Returns:
            bool: True if this processor can handle the file.
        """
        pass

    def process_texts(
        self, 
        file_path: str, 
        translations: Optional[Dict[str, str]] = None,
        output_path: Optional[str] = None
    ) -> Union[List[str], str, None]:
        """Process texts in a file.

        Args:
            file_path: Path to the file to process.
            translations: Optional dictionary of translations.
            output_path: Optional path where to save the translated file.

        Returns:
            List[str]: List of texts if no translations provided.
            str: Path to translated file if translations provided.
            None: If an error occurs.
        """
        try:
            # Reset state for new translation
            self.collected_texts = []
            self.set_source_file(file_path)

            # Extract texts if no translations provided
            if translations is None:
                return self.extract_texts(file_path)

            # Process translations and save to output path
            if output_path:
                self.create_translated_file(file_path, translations, output_path)
                return output_path

            return None

        except Exception as e:
            self.debug(f"Error processing texts: {str(e)}")
            return None
