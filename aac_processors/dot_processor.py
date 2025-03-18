import os
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
        with open(file_path, "r") as f:
            dot_content = f.read()
        
        # Parse DOT content
        nodes, edges = self._parse_dot(dot_content)
        
        # Create tree structure
        tree = AACTree()
        
        # Add pages
        for node_id, label in nodes.items():
            # Create a page for each node
            page = AACPage(
                id=node_id,
                name=label,
                buttons=[],
                grid_size=(1, 1)  # Default grid size
            )
            tree.add_page(page)
        
        # Add buttons (edges)
        for source, target, edge_label in edges:
            if source in tree.pages and target in tree.pages:
                # Create a button for each edge
                button_label = edge_label or f"Go to {tree.pages[target].name}"
                button = AACButton(
                    id=f"button_{source}_{target}",
                    label=button_label,
                    type=ButtonType.NAVIGATE,
                    target_page_id=target,
                )
                tree.pages[source].buttons.append(button)
        
        return tree

    def _parse_dot(self, dot_content: str) -> tuple[dict[str, str], list[tuple[str, str, Optional[str]]]]:
        """Parse DOT content to extract nodes and edges.
        
        Args:
            dot_content: Content of the DOT file.
            
        Returns:
            Tuple containing:
                - Dictionary mapping node IDs to labels
                - List of edge tuples (source, target, edge_label)
        """
        nodes = {}
        edges = []
        
        # Remove comments
        dot_content = re.sub(r'//.*$', '', dot_content, flags=re.MULTILINE)
        dot_content = re.sub(r'/\*.*?\*/', '', dot_content, flags=re.DOTALL)
        
        # Extract graph name
        graph_match = re.search(r'(digraph|graph)\s+(\w+)\s*{', dot_content)
        graph_type = "digraph" if graph_match and graph_match.group(1) == "digraph" else "graph"
        
        # Extract node definitions with explicit labels (format: node1 [label="Home Page"])
        node_pattern = r'(["\']?(\w+)["\']?)\s*\[\s*label\s*=\s*["\']([^"\']*)["\'].*?\]'
        for match in re.finditer(node_pattern, dot_content):
            node_id = match.group(2)  # Use the ID without quotes
            label = match.group(3)    # This is the actual node label
            nodes[node_id] = label    # Store the original node label
        
        # Extract nodes without explicit labels
        simple_node_pattern = r'(["\']?(\w+)["\']?)\s*;'
        for match in re.finditer(simple_node_pattern, dot_content):
            node_id = match.group(2)  # Use the ID without quotes
            if node_id not in nodes:
                nodes[node_id] = node_id
        
        # Extract edges
        if graph_type == "digraph":
            edge_symbol = "->"
        else:
            edge_symbol = "--"
            
        # Pattern 1: Format with node IDs (node1 -> node2 [label="Go to About"])
        edge_pattern1 = rf'(["\']?(\w+)["\']?)\s*{re.escape(edge_symbol)}\s*(["\']?(\w+)["\']?)(?:\s*\[\s*label\s*=\s*["\']([^"\']*)["\'].*?\])?'
        for match in re.finditer(edge_pattern1, dot_content):
            source = match.group(2)  # Source node ID without quotes
            target = match.group(4)  # Target node ID without quotes
            edge_label = match.group(5) if match.lastindex >= 5 else None
            
            # Add nodes if they don't exist yet
            if source not in nodes:
                nodes[source] = source
            if target not in nodes:
                nodes[target] = target
                
            edges.append((source, target, edge_label))
            
            # For undirected graphs, add the reverse edge as well
            if graph_type == "graph":
                edges.append((target, source, edge_label))
        
        # Pattern 2: Format with quoted node names ("I have something to say" -> "Quick Messages")
        # This pattern handles node names with spaces
        edge_pattern2 = rf'"([^"]+)"\s*{re.escape(edge_symbol)}\s*"([^"]+)"(?:\s*\[\s*label\s*=\s*["\']([^"\']*)["\'].*?\])?'
        for match in re.finditer(edge_pattern2, dot_content):
            source_label = match.group(1)  # Full source node name/label
            target_label = match.group(2)  # Full target node name/label
            edge_label = match.group(3) if match.lastindex >= 3 else None
            
            # For this format, use the full label as both ID and label
            if source_label not in nodes:
                nodes[source_label] = source_label
            if target_label not in nodes:
                nodes[target_label] = target_label
                
            # Use the full label as the node ID in edges
            edges.append((source_label, target_label, edge_label))
            
            # For undirected graphs, add the reverse edge as well
            if graph_type == "graph":
                edges.append((target_label, source_label, edge_label))
        
        self._debug_print(f"Parsed nodes: {nodes}")
        self._debug_print(f"Parsed edges: {edges}")
        
        return nodes, edges

    def save_from_tree(self, tree: AACTree, file_path: str) -> None:
        """Save an AAC tree structure to a DOT file.
        
        Args:
            tree: The AAC tree structure to save.
            file_path: Path to save the DOT file.
        """
        # Set the file path
        self.set_source_file(file_path)
        
        # Create DOT content
        dot_content = ["digraph G {"]
    
        # Add nodes
        for page_id, page in tree.pages.items():
            # Sanitize node ID to ensure it's valid in DOT format
            node_id = page_id if re.match(r'^[a-zA-Z]\w*$', page_id) else f'node{hash(page_id) % 10000}'
            dot_content.append(f'    {node_id} [label="{page.name}"];')
    
        # Add edges (buttons)
        for page_id, page in tree.pages.items():
            # Sanitize source node ID
            source_id = page_id if re.match(r'^[a-zA-Z]\w*$', page_id) else f'node{hash(page_id) % 10000}'
            
            for button in page.buttons:
                if button.type == ButtonType.NAVIGATE and button.target_page_id:
                    # Sanitize target node ID
                    target_id = button.target_page_id if re.match(r'^[a-zA-Z]\w*$', button.target_page_id) else f'node{hash(button.target_page_id) % 10000}'
                    
                    dot_content.append(f'    {source_id} -> {target_id} [label="{button.label}"];')
                elif button.type == ButtonType.SPEAK:
                    # For speak buttons, create a node for the button itself
                    button_id = f'button_{hash(button.id) % 10000}'
                    dot_content.append(f'    {button_id} [label="{button.label}"];')
                    dot_content.append(f'    {source_id} -> {button_id} [label="{button.label}"];')
        
        dot_content.append("}")
        
        # Write to file
        with open(file_path, "w") as f:
            f.write("\n".join(dot_content))

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
            edge_pattern = r'(\w+)\s*(-[->])\s*(\w+)\s*\[.*?label\s*=\s*["\']([^"\']*)["\'].*?\]'
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
        translations: Optional[dict[str, str]] = None,
        output_path: Optional[str] = None,
    ) -> Any:
        """Process texts in DOT file.

        Args:
            file_path: Path to the DOT file.
            translations: Dictionary of translations.
            output_path: Path where to save the translated file.

        Returns:
            List of texts if extracting, path to translated file if translating, None if error.
        """
        # Set the file path
        self.set_source_file(file_path)
        
        if translations is None:
            # Extract mode
            return self.extract_texts(file_path)
        
        if output_path is None:
            # Generate output path
            target_lang = translations.get("target_lang")
            filename = os.path.basename(file_path)
            if target_lang:
                base, ext = os.path.splitext(filename)
                translated_filename = f"{base}_{target_lang}{ext}"
            else:
                translated_filename = f"translated_{filename}"
            output_path = os.path.join(os.path.dirname(file_path), translated_filename)
        
        try:
            # Read DOT file
            with open(file_path) as f:
                dot_content = f.read()
            
            modified = False
            
            # Translate node labels
            def replace_node_label(match: re.Match) -> str:
                nonlocal modified
                node_id = match.group(1)
                attrs = match.group(2)
                label_match = re.search(r'label\s*=\s*["\']([^"\']*)["\']', attrs)
                if label_match:
                    label = label_match.group(1)
                    if label in translations:
                        modified = True
                        translated_label = translations[label]
                        return (
                            f'{node_id} [' + 
                            attrs.replace(
                                f'label="{label}"', f'label="{translated_label}"'
                            ) + 
                            ']'
                        )
                return match.group(0)
            
            node_pattern = r'(\w+)\s*\[(.*?)\]'
            dot_content = re.sub(node_pattern, replace_node_label, dot_content)
            
            # Translate edge labels
            def replace_edge_label(match: re.Match) -> str:
                nonlocal modified
                src = match.group(1)
                edge_type = match.group(2)
                tgt = match.group(3)
                attrs = match.group(4)
                label_match = re.search(r'label\s*=\s*["\']([^"\']*)["\']', attrs)
                if label_match:
                    label = label_match.group(1)
                    if label in translations:
                        modified = True
                        translated_label = translations[label]
                        return (
                            f'{src} {edge_type} {tgt} [' + 
                            attrs.replace(
                                f'label="{label}"', f'label="{translated_label}"'
                            ) + 
                            ']'
                        )
                return match.group(0)
            
            edge_pattern = r'(\w+)\s*(-[->])\s*(\w+)\s*\[(.*?)\]'
            dot_content = re.sub(edge_pattern, replace_edge_label, dot_content)
            
            if modified:
                # Write to file
                with open(output_path, "w") as f:
                    f.write(dot_content)
                self._debug_print(f"Saved translated DOT file to {output_path}")
                return output_path
            else:
                self._debug_print("No texts were translated")
                return None
            
        except Exception as e:
            self._debug_print(f"Error translating DOT file: {str(e)}")
            return None

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
        import os
        
        for rel_path, abs_path in self._walk_files(directory):
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
                    translated_content = re.sub(pattern, replacement, translated_content)
            
            # Write the translated content to the output file
            with open(output_path, "w") as f:
                f.write(translated_content)
            
            return output_path
        except Exception as e:
            if self._debug_output:
                self._debug_output(f"Error creating translated file: {e}")
            return None

    def _debug_print(self, message: str) -> None:
        """Print debug messages if debug is enabled.
        
        Args:
            message: Message to print.
        """
        if self.debug:
            print(f"[DotProcessor] {message}")
