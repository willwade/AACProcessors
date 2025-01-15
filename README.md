# AACProcessors

[![PyPI version](https://badge.fury.io/py/aac-processors.svg)](https://badge.fury.io/py/aac-processors)
[![Python Versions](https://img.shields.io/pypi/pyversions/aac-processors.svg)](https://pypi.org/project/aac-processors/)
[![Tests](https://github.com/willwade/AACProcessors/actions/workflows/test.yml/badge.svg)](https://github.com/willwade/AACProcessors/actions/workflows/test.yml)
[![Coverage](https://codecov.io/gh/willwade/AACProcessors/branch/main/graph/badge.svg)](https://codecov.io/gh/willwade/AACProcessors)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

A Python library to read, import, export and modify pagesets from different AAC (Augmentative and Alternative Communication) providers. Currently supports:

- Grid 3 (`.gridset`)
- CoughDrop (OpenBoard) (`.obf`, `.obz`)
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

## Try it now!

Want to try AACProcessors without installing? Click below to run our interactive demo:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/willwade/AACProcessors/blob/main/examples/demo_aacprocessors.ipynb)

This interactive notebook will:
- Install AACProcessors
- Download example AAC files
- Demonstrate key features:
  - Viewing file structures
  - Extracting texts
  - Analyzing vocabulary
  - Converting between formats

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

The library includes two ways to view AAC board structures:

1. Using the command-line viewer:

```bash
# Using the standalone viewer script
python demo_viewer.py path/to/your/board.gridset

# Or using the package module directly
python -m aac_processors.viewer path/to/your/board.gridset

# Programmatically:
from aac_processors import viewer, GridsetProcessor

# Load and print a board structure
processor = GridsetProcessor()
tree = processor.load_into_tree("path/to/your.gridset")
viewer.print_tree(tree)

# Or use the auto-detection feature
viewer.main()  # Will prompt for file path
```

2. Programmatically:
```python
from aac_processors import viewer, GridsetProcessor
from aac_processors.tree_structure import ButtonType

# Load and print a board structure
processor = GridsetProcessor()
tree = processor.load_into_tree("path/to/your.gridset")
viewer.print_tree(tree)

# Or use the auto-detection feature
viewer.main()  # Will prompt for file path
```

The viewer will show:
- Complete board structure with pages and buttons
- Button types (🗣️ Speech, 🔀 Navigation, ⚡ Action)
- Grid layout and button positions
- Navigation analysis (dead ends, orphaned pages)
- Circular references in navigation

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

## Demo

See `demo.py` for a complete example of how to use the library.

```bash
python demo.py
```

Output:

```bash
=== Viewing File Structure ===

Viewing structure of SimpleTest.gridset:

=== AAC Board Structure ===

Root Page:
  📄 Start (4x4 grid)
    Row 0:
      [Empty] (0, 0)
      🔀 quick chat (0, 1)
        └─ Says: quick chat
        └─ Goes to: quick chat
      🔀 don't like (0, 2)
        └─ Says: don't like
        └─ Goes to: Don't like
      🔀 something different (0, 3)
        └─ Says: something different
        └─ Goes to: something different
    Row 1:
      [Empty] (1, 0)
      🔀 something's wrong (1, 1)
        └─ Says: something's wrong
        └─ Goes to: something's wrong
      🔀 I want (1, 2)
        └─ Says: I want
        └─ Goes to: I want
      🔀 Comment (1, 3)
        └─ Says: Comment
        └─ Goes to: Comment
    Row 2:
      [Empty] (2, 0)
      🔀 About me (2, 1)
        └─ Says: About me
        └─ Goes to: About me
      └─ Target Page:
          📄 About me (5x4 grid)
            Row 0:
              🗣️ [No Label] (0, 0)
              🗣️ Back (0, 1)
                └─ Says: Back
              🔀 Family (0, 2)
                └─ Says: Family
                └─ Goes to: Family
              └─ Target Page:
                  📄 Family (5x7 grid)
                    Row 0:
                      [Empty] (0, 0)
                      🗣️ Back (0, 1)
                        └─ Says: Back
                      [Empty] (0, 2)
                      🗣️ Younger Sister (0, 3)
                        └─ Says: Younger Sister
                      [Empty] (0, 4)
                      [Empty] (0, 5)
                      [Empty] (0, 6)
                    Row 1:
                      [Empty] (1, 0)
                      🗣️ Dad (1, 1)
                        └─ Says: Dad
                      [Empty] (1, 2)
                      [Empty] (1, 3)
                      [Empty] (1, 4)
                      [Empty] (1, 5)
                      [Empty] (1, 6)
                    Row 2:
                      [Empty] (2, 0)
                      [Empty] (2, 1)
                      [Empty] (2, 2)
                      🔀 Cousins (2, 3)
                        └─ Says: Cousins
                        └─ Goes to: Cousins
                      [Empty] (2, 4)
                      [Empty] (2, 5)
                      [Empty] (2, 6)
                    Row 3:
                      [Empty] (3, 0)
                      🗣️ Mum (3, 1)
                        └─ Says: Mum
                      [Empty] (3, 2)
                      [Empty] (3, 3)
                      [Empty] (3, 4)
                      [Empty] (3, 5)
                      [Empty] (3, 6)
                    Row 4:
                      [Empty] (4, 0)
                      [Empty] (4, 1)
                      [Empty] (4, 2)
                      🔀 Aunts and Uncles (4, 3)
                        └─ Says: Aunts and Uncles
                        └─ Goes to: Aunts and Uncles
                      [Empty] (4, 4)
                      [Empty] (4, 5)
                      [Empty] (4, 6)
              🗣️ Vegetarian (0, 3)
                └─ Says: Vegetarian
            Row 1:
              [Empty] (1, 0)
              🗣️ Name (1, 1)
                └─ Says: Name
              🔀 Pets (1, 2)
                └─ Says: Pets
                └─ Goes to: Pets
              [Empty] (1, 3)
            Row 2:
              [Empty] (2, 0)
              🗣️ Age (2, 1)
                └─ Says: Age
              🔀 Places I have been (2, 2)
                └─ Says: Places I have been
                └─ Goes to: Places I have been
              [Empty] (2, 3)
            Row 3:
              [Empty] (3, 0)
              🗣️ My birthday (3, 1)
                └─ Says: My birthday
              🗣️ like to look (3, 2)
                └─ Says: like to look
              [Empty] (3, 3)
            Row 4:
              [Empty] (4, 0)
              [Empty] (4, 1)
              [Empty] (4, 2)
              [Empty] (4, 3)
      🔀 I'm asking a question (2, 2)
        └─ Says: I'm asking a question
        └─ Goes to: questions
      🔀 I feel (2, 3)
        └─ Says: I feel
        └─ Goes to: Feelings
      └─ Target Page:
          📄 Feelings (6x4 grid)
            Row 0:
              🗣️ [No Label] (0, 0)
              🗣️ Back (0, 1)
                └─ Says: Back
              🗣️ angry. (0, 2)
                └─ Says: angry.
              [Empty] (0, 3)
            Row 1:
              [Empty] (1, 0)
              🗣️ happy. (1, 1)
                └─ Says: happy.
              🗣️ excited. (1, 2)
                └─ Says: excited.
              [Empty] (1, 3)
            Row 2:
              [Empty] (2, 0)
              🗣️ sad. (2, 1)
                └─ Says: sad.
              🗣️ fantastic. (2, 2)
                └─ Says: fantastic.
              [Empty] (2, 3)
            Row 3:
              [Empty] (3, 0)
              🗣️ tired. (3, 1)
                └─ Says: tired.
              [Empty] (3, 2)
              [Empty] (3, 3)
            Row 4:
              [Empty] (4, 0)
              [Empty] (4, 1)
              [Empty] (4, 2)
              [Empty] (4, 3)
            Row 5:
              [Empty] (5, 0)
              [Empty] (5, 1)
              [Empty] (5, 2)
              [Empty] (5, 3)
    Row 3:
      [Empty] (3, 0)
      🔀 like (3, 1)
        └─ Says: like
        └─ Goes to: Like
      🔀 Places to go (3, 2)
        └─ Says: Places to go
        └─ Goes to: let's go
      🔀 Alphabet (3, 3)
        └─ Says: Alphabet
        └─ Goes to: Alphabet

=== Navigation Analysis ===

Total Pages: 6

Dead End Pages (no way back):
  - Family
  - Feelings

Orphaned Pages (no way to reach):
  - Drinks
  - About me 2

=== Extracting Texts ===

Extracted 43 texts from SimpleTest.gridset
Sample texts: ["something's wrong", 'Age', 'Back to home page', 'I feel', 'Pets']

=== Loading Tree Structure ===

Loaded 6 pages from SimpleTest.gridset

Page Drinks: Drinks
Grid size: (5, 4)
Buttons: 7

Page Family: Family
Grid size: (5, 7)
Buttons: 8
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



## Command Line Interface

The package provides a command-line interface (CLI) for viewing and converting AAC files. After installation, you can use it in two ways:

### Interactive Mode

Simply run without arguments to enter interactive mode:

```bash
aac-processors
```

This will guide you through:
1. Selecting an AAC file (with tab completion)
2. Choosing to view its structure or convert it
3. If converting, selecting the target format and output path

### Command Line Mode

For direct command-line usage:

1. View an AAC file structure:
```bash
aac-processors view input.gridset
```

2. Convert between formats:
```bash
# Basic conversion (auto-generates output filename)
aac-processors convert input.gridset --to coughdrop

# Specify custom output path
aac-processors convert input.obf --to grid --output custom_name.gridset
```

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
        
    def process_texts(
        self,
        file_path: str,
        translations: Optional[Dict[str, str]] = None,
        output_path: Optional[str] = None
    ) -> Union[List[str], str, None]:
        """Process and translate texts in the file.
        
        Returns:
            - List[str] if extracting texts (translations=None)
            - str if translating (path to translated file)
            - None if error occurs
        """
        
    def set_source_file(self, file_path: str) -> None:
        """Set the source file path for processing"""
        
    def cleanup_temp_files(self) -> None:
        """Clean up any temporary files created during processing"""
```

### Common Data Structures

#### AACTree
Represents the common structure for all AAC formats.

```python
class AACTree:
    pages: Dict[str, AACPage]  # Dictionary of pages by ID
    root_id: Optional[str]  # ID of the root page
    
    def add_page(self, page: AACPage) -> None:
        """Add a page to the tree"""
        
    def get_page(self, page_id: str) -> Optional[AACPage]:
        """Get a page by ID"""
```

#### AACPage
Represents a single page in an AAC system.

```python
class AACPage:
    id: str  # Unique identifier for the page
    name: str  # Display name of the page
    grid_size: Tuple[int, int]  # (rows, columns)
    buttons: List[AACButton]  # List of buttons on the page
```

#### AACButton
Represents a button in an AAC system.

```python
class AACButton:
    id: str  # Unique identifier for the button
    label: str  # Display text
    type: ButtonType  # SPEAK, NAVIGATE, ACTION, etc.
    position: Tuple[int, int]  # Grid position (row, col)
    vocalization: Optional[str]  # Text to speak
    target_page_id: Optional[str]  # For navigation buttons
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

## Contributors

- [Will Wade](https://github.com/willwade)
- [OpenAAC](https://github.com/OpenAAC)
