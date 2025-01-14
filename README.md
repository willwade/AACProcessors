# AACProcessors

[![PyPI version](https://badge.fury.io/py/aac-processors.svg)](https://badge.fury.io/py/aac-processors)
[![Python Versions](https://img.shields.io/pypi/pyversions/aac-processors.svg)](https://pypi.org/project/aac-processors/)
[![Tests](https://github.com/willwade/AACProcessors/actions/workflows/tests.yml/badge.svg)](https://github.com/willwade/AACProcessors/actions/workflows/tests.yml)
[![Coverage](https://codecov.io/gh/willwade/AACProcessors/branch/main/graph/badge.svg)](https://codecov.io/gh/willwade/AACProcessors)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

A Python library to read, import, export and modify pagesets from different AAC (Augmentative and Alternative Communication) providers. Currently supports:

- Grid 3 (`.gridset`)
- CoughDrop (`.obf`, `.obz`)
- TouchChat (`.touchChat`)
- Snap Core First (`.spb`)

## Features

- Extract text content from AAC pagesets
- Load AAC pagesets into a common tree structure
- Support for multiple AAC software formats
- Translation support for extracted text
- Consistent API across different AAC formats
- Convert between different AAC formats
- Analyze vocabulary usage and structure

## Installation

```bash
pip install aac-processors
```

## Quick Start

```python
from aac_processors import GridsetProcessor, CoughDropProcessor, TouchChatProcessor, SnapProcessor

# Example with Grid 3
processor = GridsetProcessor()
texts = processor.extract_texts("path/to/your.gridset")
print(f"Found {len(texts)} text items")

# Load into tree structure
tree = processor.load_into_tree("path/to/your.gridset")
print(f"Found {len(tree.pages)} pages")

# Translate texts
translations = {
    "Hello": "Hola",
    "Goodbye": "Adiós"
}
translated_file = processor.process_texts("path/to/your.gridset", translations, "path/to/output.gridset")
```

## Usage Examples

### Converting Between Formats (OBZ Import/Export)

```python
from aac_processors import GridsetProcessor, CoughDropProcessor

# Convert Grid3 to CoughDrop OBZ
grid_processor = GridsetProcessor()
cough_processor = CoughDropProcessor()

# Load Grid3 file into common tree structure
tree = grid_processor.load_into_tree("path/to/your.gridset")

# Export tree to CoughDrop OBZ format
cough_processor.export_tree(tree, "output.obz")

# Import from OBZ
imported_tree = cough_processor.load_into_tree("path/to/board.obz")
```

### Viewing File Structure

The library includes a viewer utility to inspect AAC board structures. You can either use the command-line tool:

```bash
python -m aac_processors.viewer path/to/your/board.gridset
```

Or programmatically:

```python
from aac_processors import GridsetProcessor
from aac_processors.tree_structure import ButtonType

processor = GridsetProcessor()
tree = processor.load_into_tree("path/to/your.gridset")

# Print basic structure
for page_id, page in tree.pages.items():
    print(f"Page: {page.name} ({page.grid_size[0]}x{page.grid_size[1]} grid)")
    for button in page.buttons:
        if button.type == ButtonType.SPEAK:
            print(f"  - Speech Button: {button.label} says '{button.message}'")
        elif button.type == ButtonType.NAVIGATE:
            print(f"  - Navigation Button: {button.label} -> {button.target_page_id}")

# Analyze navigation
analysis = tree.analyze_navigation()
print(f"\nTotal Pages: {analysis['total_pages']}")
print(f"Dead End Pages: {len(analysis['dead_ends'])}")
print(f"Orphaned Pages: {len(analysis['orphaned_pages'])}")
```

### Vocabulary Analysis

```python
from aac_processors import GridsetProcessor
from collections import Counter
import re

def analyze_vocabulary(file_path):
    processor = GridsetProcessor()
    tree = processor.load_into_tree(file_path)
    
    # Collect all text from buttons
    words = []
    for page in tree.pages.values():
        for button in page.buttons:
            if button.label:
                # Split into words and clean
                button_words = re.findall(r'\w+', button.label.lower())
                words.extend(button_words)
            if button.message:
                message_words = re.findall(r'\w+', button.message.lower())
                words.extend(message_words)
    
    # Count word frequencies
    word_counts = Counter(words)
    
    # Print statistics
    print(f"Total unique words: {len(word_counts)}")
    print("\nMost common words:")
    for word, count in word_counts.most_common(10):
        print(f"  {word}: {count}")
    
    return word_counts

# Example usage
vocabulary = analyze_vocabulary("path/to/your.gridset")
```

## Supported Formats

### Grid 3 (`.gridset`)
- Full support for reading grid layouts
- Text extraction from buttons and pages
- Translation support

### CoughDrop (`.obf`, `.obz`)
- Support for both single board (`.obf`) and board set (`.obz`) formats
- Extraction of button labels and messages
- Translation capabilities

### TouchChat (`.touchChat`)
- Support for TouchChat page sets
- Button text extraction
- Page structure loading

### Snap Core First (`.spb`)
- Support for Snap Core First board sets
- Text extraction from buttons and pages
- Basic translation support

## API Documentation

### Base Classes

#### FileProcessor
The base class that all format-specific processors inherit from.

```python
class FileProcessor:
    def extract_texts(self, file_path: str) -> List[str]:
        """Extract all text content from the file"""
        
    def load_into_tree(self, file_path: str) -> AACTree:
        """Load the file into a common tree structure"""
        
    def process_texts(self, file_path: str, translations: Dict[str, str], output_path: str) -> str:
        """Process and translate texts in the file"""
```

### Common Data Structures

#### AACTree
Represents the common structure for all AAC formats.

```python
class AACTree:
    pages: Dict[str, AACPage]  # Dictionary of pages by ID
    root_page: str  # ID of the root page
```

#### AACPage
Represents a single page in an AAC system.

```python
class AACPage:
    id: str
    title: str
    grid_size: Tuple[int, int]
    buttons: Dict[str, AACButton]
```

#### AACButton
Represents a button in an AAC system.

```python
class AACButton:
    id: str
    label: str
    message: str
    position: Tuple[int, int]
    type: ButtonType
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Testing

To run the tests:

```bash
python -m pytest
```

Current test coverage: 52%

## License

This project is licensed under the AGPLv3 License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAAC 
- The AAC community for their feedback and support
