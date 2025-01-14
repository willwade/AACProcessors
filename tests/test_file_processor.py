import os
import tempfile
import shutil
import pytest
from aac_processors.file_processor import FileProcessor

class TestFileProcessor(FileProcessor):
    """Test implementation of FileProcessor."""
    
    def __init__(self):
        super().__init__()
        self.is_archive = False
    
    def can_process(self, file_path: str) -> bool:
        return file_path.endswith('.test')
        
    def process_files(self, directory: str, translations=None):
        if translations is None:
            # Extraction phase
            self.collected_texts = ['test1', 'test2']
            return True
        else:
            # Translation phase - create a new file
            output_file = os.path.join(directory, os.path.basename(self.file_path))
            with open(output_file, 'w') as f:
                f.write('translated content')
            return True

def test_file_path_handling():
    """Test that file paths are handled correctly between extraction and translation."""
    processor = TestFileProcessor()
    
    # Create a test file
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test.test")
        with open(test_file, 'w') as f:
            f.write('test content')
            
        # First phase: Extract texts
        texts = processor.process_texts(test_file)
        assert texts == ['test1', 'test2'], "Extraction failed"
        assert processor.file_path == test_file, "File path not set correctly after extraction"
        assert processor.original_file_path == test_file, "Original file path not set correctly"
        
        # Second phase: Translate texts
        translations = {'test1': 'prueba1', 'test2': 'prueba2', 'target_lang': 'es'}
        output_path = os.path.join(temp_dir, f"{os.path.splitext(os.path.basename(test_file))[0]}_es.test")
        result = processor.process_texts(test_file, translations, output_path)
        assert result is not None, "Translation failed"
        assert os.path.exists(output_path), f"Output file not created at {output_path}"
        assert processor.file_path == test_file, "File path changed during translation"
        assert processor.original_file_path == test_file, "Original file path changed"

def test_archive_handling():
    """Test that archives are handled correctly between extraction and translation."""
    processor = TestFileProcessor()
    processor.is_archive = True  # Force archive mode
    
    # Create a test archive
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test.test")
        with open(test_file, 'w') as f:
            f.write('test content')
            
        # First phase: Extract texts
        texts = processor.process_texts(test_file)
        assert texts == ['test1', 'test2'], "Extraction from archive failed"
        assert processor.file_path == test_file, "Archive path not set correctly after extraction"
        assert processor.original_file_path == test_file, "Original archive path not set correctly"
        
        # Second phase: Translate texts
        translations = {'test1': 'prueba1', 'test2': 'prueba2', 'target_lang': 'es'}
        output_path = os.path.join(temp_dir, f"{os.path.splitext(os.path.basename(test_file))[0]}_es.test")
        result = processor.process_texts(test_file, translations, output_path)
        assert result is not None, "Translation in archive failed"
        assert os.path.exists(output_path), f"Output archive not created at {output_path}"
        assert processor.file_path == test_file, "Archive path changed during translation"
        assert processor.original_file_path == test_file, "Original archive path changed"

def test_temp_directory_cleanup():
    """Test that temporary directories are cleaned up properly."""
    processor = TestFileProcessor()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test.test")
        with open(test_file, 'w') as f:
            f.write('test content')
            
        # Run extraction
        processor.process_texts(test_file)
        
        # Check temp dirs are cleaned up
        assert len(processor._temp_dirs) == 0, "Temp dirs not cleaned up after extraction"
        
        # Run translation
        translations = {'test1': 'prueba1', 'test2': 'prueba2', 'target_lang': 'es'}
        output_path = os.path.join(temp_dir, f"{os.path.splitext(os.path.basename(test_file))[0]}_es.test")
        processor.process_texts(test_file, translations, output_path)
        
        # Check temp dirs are cleaned up
        assert len(processor._temp_dirs) == 0, "Temp dirs not cleaned up after translation" 