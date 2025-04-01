"""Test translation functionality across all processors."""

import os
import tempfile

import pytest

from aac_processors.base_processor import AACProcessor
from aac_processors.coughdrop_processor import CoughDropProcessor
from aac_processors.dot_processor import DotProcessor
from aac_processors.gridset_processor import GridsetProcessor
from aac_processors.opml_processor import OPMLProcessor
from aac_processors.snap_processor import SnapProcessor
from aac_processors.touchchat_processor import TouchChatProcessor

# Get the absolute path to the demofiles directory
DEMOFILES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples", "demofiles"
)

# Define processor classes and their corresponding demo files
PROCESSOR_TEST_FILES = [
    (GridsetProcessor, os.path.join(DEMOFILES_DIR, "SimpleTest.gridset")),
    (TouchChatProcessor, os.path.join(DEMOFILES_DIR, "WordPower42 Basic SS_UK.ce")),
    (SnapProcessor, os.path.join(DEMOFILES_DIR, "Medical Advocacy.spb")),
    (CoughDropProcessor, os.path.join(DEMOFILES_DIR, "communikate-20.obz")),
    (OPMLProcessor, os.path.join(DEMOFILES_DIR, "test.opml")),
    (DotProcessor, os.path.join(DEMOFILES_DIR, "test.dot")),
]

# Skip processors that don't have demo files available
PROCESSOR_TEST_FILES = [
    (processor_cls, file_path)
    for processor_cls, file_path in PROCESSOR_TEST_FILES
    if os.path.exists(file_path)
]


@pytest.mark.parametrize("processor_cls,demo_file", PROCESSOR_TEST_FILES)
def test_processor_translation(
    processor_cls: type[AACProcessor], demo_file: str
) -> None:
    """Test translation functionality for a specific processor.

    This test:
    1. Extracts texts from the demo file
    2. Creates simple test translations
    3. Applies translations to create a new file
    4. Verifies the translations were applied correctly
    """
    # Skip if demo file doesn't exist
    if not os.path.exists(demo_file):
        pytest.skip(f"Demo file not found: {demo_file}")

    processor = processor_cls()
    processor_name = processor.__class__.__name__

    # Extract texts
    texts = processor.extract_texts(demo_file)
    assert texts, f"No texts extracted from {demo_file} using {processor_name}"

    # Create test translations (prefix with TEST_)
    # Only translate a subset of texts to keep the test fast
    translations = {}
    for i, text in enumerate(texts):
        if (
            i % 5 == 0 and text and len(text.strip()) > 0
        ):  # Translate every 5th non-empty text
            translations[text] = f"TEST_{text}"
            if len(translations) >= 5:  # Limit to 5 translations for speed
                break

    # Add target language
    translations["target_lang"] = "test"

    # Skip if no translations could be created
    if len(translations) <= 1:  # Only has target_lang
        pytest.skip(f"No suitable texts found for translation in {demo_file}")

    # Get file extension for temp file
    _, ext = os.path.splitext(demo_file)

    # Create translated file
    with tempfile.NamedTemporaryFile(suffix=ext) as output:
        # Process texts and create translated file
        result = processor.process_texts(demo_file, translations, output.name)

        # Verify result is a valid path
        assert result is not None, f"Translation failed for {processor_name}"
        assert isinstance(result, str), f"Expected string path, got {type(result)}"
        assert os.path.exists(result), f"Translated file not created at {result}"

        # Extract texts from translated file
        translated_texts = processor.extract_texts(result)
        assert (
            translated_texts
        ), f"No texts extracted from translated file using {processor_name}"

        # Verify translations were applied
        translation_found = False
        for original, translated in translations.items():
            if original != "target_lang":
                if translated in translated_texts:
                    translation_found = True
                    break

        assert (
            translation_found
        ), f"No translations found in output file for {processor_name}"


def test_translate_gridset_script_functionality() -> None:
    """Test the core functionality of the translate_gridset.py script.

    This test verifies that the main workflow of the script works:
    1. Identifying the appropriate processor
    2. Extracting texts
    3. Applying translations
    4. Creating a translated file
    """
    # Import the necessary function from translate_gridset.py
    from translate_gridset import get_processor

    # Test processor identification - only test processors that are in the
    # PROCESSORS list in translate_gridset.py (GridsetProcessor, TouchChatProcessor,
    # SnapProcessor, CoughDropProcessor)
    supported_processors = [
        (processor_cls, file_path)
        for processor_cls, file_path in PROCESSOR_TEST_FILES
        if processor_cls
        in [GridsetProcessor, TouchChatProcessor, SnapProcessor, CoughDropProcessor]
    ]

    for processor_cls, file_path in supported_processors:
        if os.path.exists(file_path):
            processor = get_processor(file_path)
            assert isinstance(
                processor, processor_cls
            ), f"Expected {processor_cls.__name__}, got {processor.__class__.__name__}"

    # Test simplified process_file functionality (without actual translation APIs)
    # We'll create a mock version that uses our simple TEST_ prefix translation
    def mock_process_file(file_path: str) -> str:
        """Simplified version of process_file that doesn't use translation APIs."""
        # Get processor
        processor = get_processor(file_path)

        # Extract texts
        texts = processor.extract_texts(file_path)

        # Create simple translations
        translations = {}
        for i, text in enumerate(texts):
            if i % 5 == 0 and text and len(text.strip()) > 0:
                translations[text] = f"TEST_{text}"
                if len(translations) >= 5:
                    break

        # Add target language
        translations["target_lang"] = "test"

        # Create output path
        file_name, file_ext = os.path.splitext(file_path)
        output_path = f"{file_name}_test{file_ext}"

        # Process translations
        result = processor.process_texts(file_path, translations, output_path)

        # Ensure we return a string
        if isinstance(result, str):
            return result
        else:
            raise ValueError(f"Expected string result, got {type(result)}")

    # Test with one file from each processor type
    for _, file_path in PROCESSOR_TEST_FILES[
        :1
    ]:  # Just test the first one to save time
        if os.path.exists(file_path):
            try:
                result = mock_process_file(file_path)
                assert result is not None
                assert os.path.exists(result)

                # Clean up
                if os.path.exists(result) and result != file_path:
                    os.remove(result)
            except Exception as e:
                pytest.fail(f"Failed to process {file_path}: {str(e)}")
