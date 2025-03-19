import re
from typing import Any, Optional

from aac_processors.base_processor import AACProcessor
from aac_processors.tree_structure import AACButton, AACPage, AACTree, ButtonType


class DotProcessor(AACProcessor):
    """Processor for DOT (Graph Description Language) files."""

    def __init__(self) -> None:
        """Initialize the processor."""
        super().__init__()
        self.debug = False
        self.file_path = ""
        self.original_file_path = ""

    def can_process(self, file_path: str) -> bool:
        """Check if file is a DOT file.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if file is a DOT file.
        """
        return file_path.lower().endswith((".dot", ".gv"))

    def set_source_file(self, file_path: str) -> None:
        """Set the source file path.

        Args:
            file_path: Path to the source file.
        """
        self.file_path = file_path
        if not self.original_file_path:
            self.original_file_path = file_path

    def load_into_tree(self, file_path: str) -> AACTree:
        """Load a DOT file into an AAC tree structure.

        Args:
            file_path: Path to the DOT file.

        Returns:
            AACTree structure.
        """
        self.set_source_file(file_path)

        # Read DOT file
        with open(file_path) as f:
            dot_content = f.read()

        print(f"DOT content: {dot_content}")

        # Parse DOT content
        nodes, edges = self._parse_dot(dot_content)

        print(f"Parsed nodes: {nodes}")
        print(f"Parsed edges: {edges}")

        # Create tree structure
        tree = AACTree()

        # Add pages
        for node_id, label in nodes.items():
            # Create a page for each node
            page = AACPage(
                id=node_id,
                name=label,  # Use the label as the page name
                buttons=[],
                grid_size=(3, 3),  # Default grid size
            )
            tree.add_page(page)

        # Add buttons (edges)
        for source, target, edge_label in edges:
            if source in tree.pages and target in tree.pages:
                # Create a button for each edge
                button_label = (
                    edge_label or f"Go to {nodes[target]}"
                )  # Use the actual node label
                button = AACButton(
                    id=f"button_{source}_{target}",
                    label=button_label,
                    type=ButtonType.NAVIGATE,
                    target_page_id=target,
                )
                tree.pages[source].buttons.append(button)

        print(f"Tree pages: {[p.name for p in tree.pages.values()]}")

        return tree

    def save_from_tree(self, tree: AACTree, file_path: str) -> None:
        """Save an AAC tree to a DOT file.

        Args:
            tree: AACTree structure.
            file_path: Path to save the DOT file.
        """
        # Create DOT content
        dot_lines = ["digraph G {"]

        # Add nodes
        node_counter = 1
        node_id_map = {}  # Map page_id to node_id

        for page_id, page in tree.pages.items():
            # Use consistent node IDs
            node_id = f"node{node_counter}"
            node_id_map[page_id] = node_id
            node_counter += 1

            # Create a node for each page
            dot_lines.append(f'    {node_id} [label="{page.name}"];')

        # Add edges
        for page_id, page in tree.pages.items():
            source_id = node_id_map[page_id]

            for button in page.buttons:
                if button.type == ButtonType.NAVIGATE and button.target_page_id:
                    if button.target_page_id in node_id_map:
                        target_id = node_id_map[button.target_page_id]
                        # Create an edge for each navigation button
                        dot_lines.append(
                            f'    {source_id} -> {target_id} [label="{button.label}"];'
                        )
                elif button.type == ButtonType.SPEAK:
                    # For speak buttons, create a node for the button itself
                    speak_node_id = f"node{node_counter}"
                    node_counter += 1
                    dot_lines.append(f'    {speak_node_id} [label="{button.label}"];')
                    dot_lines.append(
                        f'    {source_id} -> {speak_node_id} [label="{button.label}"];'
                    )

        dot_lines.append("}")

        # Write to file
        with open(file_path, "w") as f:
            f.write("\n".join(dot_lines))

    def export_tree(self, tree: AACTree, output_path: str) -> None:
        """Export tree to DOT format.

        Args:
            tree (AACTree): Tree to export.
            output_path (str): Path where to save the file.
        """
        self.save_from_tree(tree, output_path)

    def extract_texts(self, file_path: str) -> list[str]:
        """Extract translatable texts from DOT file.

        Args:
            file_path: Path to the DOT file.

        Returns:
            List of translatable texts.
        """
        texts = []

        try:
            # Read DOT file
            with open(file_path) as f:
                dot_content = f.read()

            # Extract node labels
            node_pattern = r'(\w+)\s*\[.*?label\s*=\s*["\']([^"\']*)["\'].*?\]'
            for match in re.finditer(node_pattern, dot_content):
                label = match.group(2)
                if label and label.strip():
                    texts.append(label.strip())

            # Extract edge labels
            edge_pattern = (
                r'(\w+)\s*(-[->])\s*(\w+)\s*\[.*?label\s*=\s*["\']([^"\']*)["\'].*?\]'
            )
            for match in re.finditer(edge_pattern, dot_content):
                label = match.group(4)
                if label and label.strip():
                    texts.append(label.strip())

        except Exception as e:
            self._debug_print(f"Error extracting texts from DOT file: {str(e)}")

        return list(set(texts))  # Remove duplicates

    def process_texts(
        self,
        file_path: str,
        translations: Optional[dict[str, Any]] = None,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """Process texts in a DOT file.

        Args:
            file_path: Path to the DOT file.
            translations: Optional translations to apply.
            output_path: Optional path to save the translated file.

        Returns:
            Optional path to the translated file.
        """
        try:
            # Check if we can process this file
            if not self.can_process(file_path):
                return None

            # If no translations, just return None
            if not translations:
                return None

            # Extract texts from the DOT file
            texts = self.extract_texts(file_path)

            # Apply translations
            translated_texts = {}
            for text in texts:
                if text in translations:
                    translated_texts[text] = translations[text]
                else:
                    translated_texts[text] = text  # Default to original text

            # Create translated file if output path is provided
            if output_path and translated_texts:
                self.create_translated_file(file_path, translated_texts, output_path)
                return output_path

            return None
        except Exception as e:
            self._debug_print(f"Error translating DOT file: {str(e)}")
            return None

    def process_files(
        self, directory: str, translations: Optional[dict[str, Any]] = None
    ) -> Optional[str]:
        """Process files in directory.

        Args:
            directory: Directory containing files to process.
            translations: Dictionary of translations.

        Returns:
            Path to translated file if successful, None otherwise.
        """
        import os

        for root, _, files in os.walk(directory):
            for file in files:
                abs_path = os.path.join(root, file)
                if self.can_process(abs_path):
                    output_path = None
                    if translations:
                        # Generate output path in the same directory
                        target_lang = translations.get("target_lang")
                        filename = os.path.basename(abs_path)
                        if target_lang:
                            base, ext = os.path.splitext(filename)
                            translated_filename = f"{base}_{target_lang}{ext}"
                        else:
                            translated_filename = f"translated_{filename}"
                        output_path = os.path.join(directory, translated_filename)

                    result = self.process_texts(abs_path, translations, output_path)
                    if result and translations:
                        return result

        return None

    def get_dot_text(self, file_path: str) -> str:
        """Get the DOT text from a file.

        Args:
            file_path: Path to the DOT file.

        Returns:
            DOT text.
        """
        with open(file_path) as f:
            return f.read()

    def _debug_print(self, message: str) -> None:
        """Print debug message if debug is enabled.

        Args:
            message: Debug message to print.
        """
        if self.debug:
            print(f"[DotProcessor] {message}")

    def create_translated_file(
        self, input_file: str, translations: dict, output_path: str
    ) -> Optional[str]:
        """Create a translated version of the DOT file.

        Args:
            input_file: Path to the input file.
            translations: Dictionary of translations.
            output_path: Path to save the translated file.

        Returns:
            Path to the translated file if successful, otherwise None.
        """
        try:
            # Load the DOT file
            with open(input_file) as f:
                content = f.read()

            # Apply translations to all text in the file
            translated_content = content
            for original, translated in translations.items():
                if original != "target_lang" and original != "output_path":
                    # Replace the text in labels, being careful with quotes
                    pattern = f'label="({re.escape(original)})"'
                    replacement = f'label="{translated}"'
                    translated_content = re.sub(
                        pattern, replacement, translated_content
                    )

            # Write the translated content to the output file
            with open(output_path, "w") as f:
                f.write(translated_content)

            return output_path
        except Exception as e:
            if self._debug_output:
                self._debug_output(f"Error creating translated file: {e}")
            return None

    def _parse_dot(
        self, dot_content: str
    ) -> tuple[dict[str, str], list[tuple[str, str, str]]]:
        """Parse DOT content to extract nodes and edges.

        Args:
            dot_content: Content of the DOT file.

        Returns:
            Tuple containing:
                - Dictionary mapping node IDs to labels
                - List of edge tuples (source, target, edge_label)
        """
        # First, clean up the DOT content by removing comments
        lines = []
        for line in dot_content.split("\n"):
            line = line.strip()
            if line and not line.startswith("//") and not line.startswith("#"):
                lines.append(line)

        # Process line by line
        nodes = {}
        edges = []

        for line in lines:
            # Check if it's a node definition with explicit label
            # Pattern: node1 [label="Home Page"];
            node_match = re.match(
                r'\s*(\w+|\".+?\")\s*\[\s*label\s*=\s*["\']([^"\']*)["\'].*?\];?', line
            )
            if node_match:
                node_id = node_match.group(1).strip('"')
                label = node_match.group(2)
                nodes[node_id] = label
                continue

            # Check if it's an edge definition
            # Pattern: "more quick chat" -> "That tickles";
            # Or: node1 -> node2 [label="Go to About"];
            edge_match = re.match(
                r"\s*(\w+|\".+?\")\s*->\s*(\w+|\".+?\")"
                r'(?:\s*\[\s*label\s*=\s*["\']([^"\']*)["\'].*?\])?;?',
                line,
            )
            if edge_match:
                source = edge_match.group(1).strip('"')
                target = edge_match.group(2).strip('"')
                edge_label = edge_match.group(3) if edge_match.group(3) else ""

                # Add nodes if they don't exist yet (implicit node definition)
                if source not in nodes:
                    nodes[source] = source
                if target not in nodes:
                    nodes[target] = target

                edges.append((source, target, edge_label))

        # Debug output
        print(f"Parsed nodes: {nodes}")
        print(f"Parsed edges: {edges}")

        return nodes, edges
