"""Optional tools for working with AAC symbols from various systems."""

import base64
import os
import sqlite3
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from typing import Optional
from zipfile import ZipFile

from ..tree_structure import AACSymbol


class SymbolExtractor(ABC):
    """Base class for extracting symbols from AAC systems."""

    @abstractmethod
    def get_symbol_references(self, file_path: str) -> list[str]:
        """Get list of symbol references from an AAC file.

        Args:
            file_path: Path to the AAC file

        Returns:
            List of symbol IDs/references found in the file
        """
        pass


class SymbolResolver(ABC):
    """Base class for resolving symbol references to actual files."""

    def __init__(self, symbol_path: Optional[str] = None, db_path: Optional[str] = None):
        """Initialize resolver.

        Args:
            symbol_path: Base path where symbol files are stored
            db_path: Path to symbol database if applicable
        """
        self.symbol_path = symbol_path
        self.db_path = db_path

    @abstractmethod
    def resolve_symbol(self, symbol_ref: str) -> Optional[AACSymbol]:
        """Resolve a symbol reference to an actual symbol file.

        Args:
            symbol_ref: Symbol reference (e.g. ID) to resolve

        Returns:
            AACSymbol if found, None otherwise
        """
        pass


class SnapSymbolExtractor(SymbolExtractor):
    """Extract symbol references from Snap files."""

    def get_symbol_references(self, file_path: str) -> list[str]:
        """Get list of symbol IDs from a Snap file.

        Args:
            file_path: Path to the Snap file

        Returns:
            List of symbol IDs found in the file
        """
        symbols = []
        try:
            with sqlite3.connect(file_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT LibrarySymbolId
                    FROM Button
                    WHERE LibrarySymbolId IS NOT NULL
                """)
                symbols = [str(row[0]) for row in cursor.fetchall()]
        except Exception:
            pass
        return symbols


class Grid3SymbolExtractor(SymbolExtractor):
    """Extract symbol references from Grid3 files."""

    def get_symbol_references(self, file_path: str) -> list[str]:
        """Get list of symbol references from a Grid3 gridset.

        Args:
            file_path: Path to the .gridset file

        Returns:
            List of symbol references found in the file
        """
        symbols = []
        try:
            # Grid3 files are zip archives
            with ZipFile(file_path) as gridset:
                # Look through all grid XML files
                for info in gridset.filelist:
                    if info.filename.startswith('Grids/') and info.filename.endswith('/grid.xml'):
                        with gridset.open(info.filename) as f:
                            tree = ET.parse(f)
                            root = tree.getroot()
                            # Find all cells with symbols
                            for cell in root.findall('.//Cell'):
                                symbol = cell.find('Symbol')
                                if symbol is not None and 'ID' in symbol.attrib:
                                    symbols.append(symbol.attrib['ID'])
        except Exception:
            pass
        return symbols


class TouchChatSymbolExtractor(SymbolExtractor):
    """Extract symbol references from TouchChat files."""

    def get_symbol_references(self, file_path: str) -> list[str]:
        """Get list of symbol references from a TouchChat file.

        Args:
            file_path: Path to the .ce file

        Returns:
            List of symbol references found in the file
        """
        symbols = []
        try:
            # TouchChat files are zip archives
            with ZipFile(file_path) as vocab:
                # Look in Images.c4s
                with vocab.open('Images.c4s') as f:
                    # Copy to temp file since sqlite3 needs file path
                    import tempfile
                    with tempfile.NamedTemporaryFile() as temp:
                        temp.write(f.read())
                        temp.flush()
                        with sqlite3.connect(temp.name) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT DISTINCT image_id
                                FROM buttons
                                WHERE image_id IS NOT NULL
                            """)
                            symbols = [str(row[0]) for row in cursor.fetchall()]
        except Exception:
            pass
        return symbols


class TobiiSymbolResolver(SymbolResolver):
    """Resolve Tobii Dynavox symbol references to files."""

    def resolve_symbol(self, symbol_id: str) -> Optional[AACSymbol]:
        """Resolve a symbol by its ID."""
        if not symbol_id:
            return None

        # Remove SYM: prefix if present
        if symbol_id.startswith('SYM:'):
            symbol_id = symbol_id[4:]

        try:
            symbol_id = int(symbol_id)
        except ValueError:
            return None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SymbolId, Label, Image
                FROM Symbol
                WHERE SymbolId = ?
            """, (symbol_id,))
            result = cursor.fetchone()

            if result:
                symbol_id, label, image_data = result
                if image_data:
                    # Convert raw bytes to base64
                    import base64
                    b64_data = base64.b64encode(image_data).decode('utf-8')

                    return AACSymbol(
                        data=f"data:image/png;base64,{b64_data}",
                        label=label,
                        width=1024,  # Default width
                        height=768,  # Default height
                        content_type='image/png'
                    )

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use in filenames."""
        import re
        # Replace Library:PCS\Core with Library_PCS_Core
        name = name.replace(':', '_').replace('\\', '_')
        # Replace any other invalid characters
        name = re.sub(r'[<>"/|?*]', '_', name).strip()
        return name

    def _create_symbol(self, symbol_id: str, label: str, file_path: str) -> Optional[AACSymbol]:
        """Create an AACSymbol from a file.

        Args:
            symbol_id: Symbol ID
            label: Symbol label
            file_path: Path to symbol file

        Returns:
            AACSymbol if successful, None otherwise
        """
        try:
            # Get file format from extension
            format = os.path.splitext(file_path)[1][1:]  # Remove leading dot

            # Read file as base64
            with open(file_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode('utf-8')

            # Create symbol
            return AACSymbol(
                system_id=symbol_id,
                system_name='tobii',
                label=label,
                format=format,
                data=data
            )
        except Exception as e:
            print(f"Error creating symbol from {file_path}: {e}")
            return None


class Grid3SymbolResolver(SymbolResolver):
    """Resolve Grid3 symbol references to files."""

    def resolve_symbol(self, symbol_ref: str) -> Optional[AACSymbol]:
        """Resolve a Grid3 symbol reference to a file.

        Args:
            symbol_ref: Symbol reference to resolve

        Returns:
            AACSymbol if found, None otherwise
        """
        if not self.symbol_path:
            return None

        try:
            # Grid3 symbols are typically stored in a symbols directory
            # Try common image formats
            for ext in ['.png', '.bmp', '.jpg']:
                path = os.path.join(self.symbol_path, f"{symbol_ref}{ext}")
                if os.path.exists(path):
                    return self._create_symbol(symbol_ref, os.path.basename(symbol_ref), path)

        except Exception:
            pass

        return None

    def _create_symbol(self, symbol_id: str, label: str, file_path: str) -> Optional[AACSymbol]:
        """Create an AACSymbol from a file.

        Args:
            symbol_id: Symbol ID
            label: Symbol label
            file_path: Path to symbol file

        Returns:
            AACSymbol if successful, None otherwise
        """
        try:
            # Get file format from extension
            format = os.path.splitext(file_path)[1][1:]  # Remove leading dot

            # Read file as base64
            with open(file_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode('utf-8')

            # Create symbol
            return AACSymbol(
                system_id=symbol_id,
                system_name='grid3',
                label=label,
                format=format,
                data=data
            )
        except Exception as e:
            print(f"Error creating symbol from {file_path}: {e}")
            return None


class TouchChatSymbolResolver(SymbolResolver):
    """Resolve TouchChat symbol references to files."""

    def resolve_symbol(self, symbol_ref: str) -> Optional[AACSymbol]:
        """Resolve a TouchChat symbol reference to a file.

        Args:
            symbol_ref: Symbol reference to resolve

        Returns:
            AACSymbol if found, None otherwise
        """
        if not self.db_path:
            return None

        try:
            # TouchChat stores images in the Images.c4s database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name, image_data
                    FROM images
                    WHERE id = ?
                """, (symbol_ref,))
                result = cursor.fetchone()
                if result:
                    name, image_data = result
                    # TouchChat stores images as binary blobs
                    # Create a temporary file to save it
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp:
                        temp.write(image_data)
                        temp.flush()
                        symbol = self._create_symbol(symbol_ref, name, temp.path)
                        os.unlink(temp.path)  # Clean up temp file
                        return symbol

        except Exception:
            pass

        return None

    def _create_symbol(self, symbol_id: str, label: str, file_path: str) -> Optional[AACSymbol]:
        """Create an AACSymbol from a file.

        Args:
            symbol_id: Symbol ID
            label: Symbol label
            file_path: Path to symbol file

        Returns:
            AACSymbol if successful, None otherwise
        """
        try:
            # Get file format from extension
            format = os.path.splitext(file_path)[1][1:]  # Remove leading dot

            # Read file as base64
            with open(file_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode('utf-8')

            # Create symbol
            return AACSymbol(
                system_id=symbol_id,
                system_name='touchchat',
                label=label,
                format=format,
                data=data
            )
        except Exception as e:
            print(f"Error creating symbol from {file_path}: {e}")
            return None
