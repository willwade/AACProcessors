from pathlib import Path
from typing import Any, Optional

import numpy  # type: ignore

from ..base_processor import AACProcessor
from ..tree_structure import AACButton, AACPage, AACTree, ButtonStyle, ButtonType


class ScreenshotProcessor(AACProcessor):
    """Process screenshots to detect AAC grid layouts and content."""

    def __init__(self, save_debug_images: bool = False) -> None:
        """Initialize the processor.

        Args:
            save_debug_images: Whether to save debug visualization images. Defaults to False.
        """
        super().__init__()
        self._check_dependencies()
        self.save_debug_images = save_debug_images

    @staticmethod
    def _check_dependencies() -> None:
        """Check if required dependencies are installed."""
        try:
            import cv2  # noqa: F401
            import easyocr  # noqa: F401
            import numpy  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError as e:
            msg = (
                "Screenshot processing requires additional dependencies. "
                "Install with: pip install aac-processors[screenshot]"
            )
            raise ImportError(msg) from e
        return None

    def _save_debug_image(
        self, img: Any, boxes: list[tuple[int, int, int, int]], output_path: str
    ) -> None:
        """Save debug image showing detected grid cells.

        Args:
            img: Original image
            boxes: List of detected cell boxes
            output_path: Where to save debug image
        """
        import cv2

        # Make a copy for drawing
        debug_img = img.copy()

        # Draw each detected cell
        for x, y, w, h in boxes:
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Save debug image
        cv2.imwrite(output_path, debug_img)

    def _try_detection(
        self,
        img: Any,
        area_min_pct: float,
        area_max_pct: float,
        aspect_min: float,
        aspect_max: float,
    ) -> list[tuple[int, int, int, int]]:
        """Try detection with given parameters."""
        import cv2
        import numpy as np

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150)

        # Dilate edges to connect gaps
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=2)  # Increased iterations

        # Find contours
        contours, _ = cv2.findContours(
            edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE  # Always use LIST mode
        )

        # Filter contours
        min_area = img.shape[0] * img.shape[1] * area_min_pct
        max_area = img.shape[0] * img.shape[1] * area_max_pct
        cell_contours = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_area < area < max_area:
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
                if len(approx) == 4:  # Looking for rectangles
                    x, y, w, h = cv2.boundingRect(cnt)
                    aspect_ratio = float(w) / h
                    if aspect_min < aspect_ratio < aspect_max:
                        # Check if this contour is unique (not overlapping with existing)
                        is_unique = True
                        for existing in cell_contours:
                            ex, ey, ew, eh = cv2.boundingRect(existing)
                            # Calculate overlap
                            overlap_x = max(0, min(x + w, ex + ew) - max(x, ex))
                            overlap_y = max(0, min(y + h, ey + eh) - max(y, ey))
                            if (overlap_x * overlap_y) / (w * h) > 0.5:
                                is_unique = False
                                break
                        if is_unique:
                            cell_contours.append(cnt)

        return [cv2.boundingRect(cnt) for cnt in cell_contours]

    def detect_grid(
        self,
        image_path: str,
        grid_rows: Optional[int] = None,
        grid_cols: Optional[int] = None,
    ) -> tuple[int, int, list[tuple[int, int, int, int]]]:
        """Detect grid dimensions and cell positions from image."""
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")

        # If dimensions provided, use more permissive detection
        if grid_rows is not None and grid_cols is not None:
            expected_cells = grid_rows * grid_cols
            area_ranges = [
                (0.0005, 0.2),  # Extremely permissive
                (0.001, 0.1),  # Very permissive
                (0.003, 0.07),  # More permissive
                (0.005, 0.05),  # Default
            ]
        else:
            area_ranges = [
                (0.005, 0.05),  # Default
                (0.003, 0.07),  # More permissive
                (0.001, 0.1),  # Very permissive
            ]

        aspect_ranges = [
            (0.2, 5.0),  # Extremely permissive
            (0.5, 2.0),  # Very permissive
            (0.7, 1.5),  # More permissive
            (0.8, 1.2),  # Nearly square
        ]

        best_boxes = []

        # Try different parameter combinations
        for area_range in area_ranges:
            for aspect_range in aspect_ranges:
                boxes = self._try_detection(img, *area_range, *aspect_range)
                if boxes:
                    if grid_rows and grid_cols:
                        # With known dimensions, accept if we found enough cells
                        if (
                            len(boxes) >= expected_cells * 0.5
                        ):  # More permissive - allow 50% missing
                            best_boxes = boxes
                            break
                    else:
                        # Without dimensions, accept first reasonable result
                        if len(boxes) >= 12:
                            best_boxes = boxes
                            break
            if best_boxes:
                break

        # If no cells detected, create artificial grid
        if not best_boxes and grid_rows is not None and grid_cols is not None:
            # Create evenly spaced grid
            cell_height = img.shape[0] / grid_rows
            cell_width = img.shape[1] / grid_cols
            best_boxes = []
            for row in range(grid_rows):
                for col in range(grid_cols):
                    x = int(col * cell_width)
                    y = int(row * cell_height)
                    w = int(cell_width)
                    h = int(cell_height)
                    best_boxes.append((x, y, w, h))

        if not best_boxes:
            raise ValueError("No cells detected in image")

        # Save debug image only if enabled
        if self.save_debug_images:
            debug_path = image_path + ".debug.png"
            self._save_debug_image(img, best_boxes, debug_path)
            self.debug(f"Saved debug visualization to: {debug_path}")

        # Sort contours by position
        best_boxes.sort(key=lambda b: (b[1], b[0]))  # Sort by y then x

        # Use provided grid dimensions or calculate from boxes
        if grid_rows is not None and grid_cols is not None:
            grid_width = grid_cols
            grid_height = grid_rows
        else:
            # Calculate grid dimensions from box positions
            x_coords = np.array([x + w / 2 for x, _, w, _ in best_boxes])
            y_coords = np.array([y + h / 2 for _, y, _, h in best_boxes])

            def find_clusters(coords: numpy.ndarray) -> int:
                if len(coords) == 0:
                    return 0
                sorted_coords = np.sort(coords)
                diffs = np.diff(sorted_coords)
                # Use smaller threshold and require minimum gaps
                threshold = np.median(diffs) * 1.2
                min_gap = np.mean(diffs) * 0.8
                gaps = np.where((diffs > threshold) & (diffs > min_gap))[0]
                return len(gaps) + 1

            grid_width = find_clusters(x_coords)
            grid_height = find_clusters(y_coords)

        # Calculate grid cell positions
        def get_grid_position(x: int, y: int, w: int, h: int) -> tuple[int, int]:
            # Calculate cell boundaries
            x_edges = np.linspace(0, img.shape[1], grid_width + 1)
            y_edges = np.linspace(0, img.shape[0], grid_height + 1)

            # Use cell center for position
            center_x = x + w / 2
            center_y = y + h / 2

            # Find which grid cell contains the center
            col = int(np.searchsorted(x_edges, center_x) - 1)
            row = int(np.searchsorted(y_edges, center_y) - 1)

            # Clamp to valid range
            col = max(0, min(col, grid_width - 1))
            row = max(0, min(row, grid_height - 1))

            return row, col

        # Update box positions
        positioned_boxes = []
        used_positions = set()

        for box in best_boxes:
            pos = get_grid_position(*box)
            if pos not in used_positions:  # Only keep first button for each position
                used_positions.add(pos)
                positioned_boxes.append((box, pos))

        # Sort by position and extract boxes
        positioned_boxes.sort(key=lambda x: (x[1][0], x[1][1]))  # Sort by row, col
        best_boxes = [box for box, _ in positioned_boxes]

        return grid_width, grid_height, best_boxes

    def detect_cell_content(
        self, img: numpy.ndarray, box: tuple[int, int, int, int]
    ) -> dict[str, Any]:
        """Detect text, colors, and other properties of a grid cell."""
        import re

        import cv2
        import pytesseract

        x, y, w, h = box
        cell = img[y : y + h, x : x + w]

        # Get dominant color
        avg_color = cv2.mean(cell)[:3]  # BGR format

        # Convert cell to grayscale for OCR
        gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)

        # Improve contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # Denoise with better parameters
        gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # Try both adaptive and Otsu thresholding
        thresh1 = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        _, thresh2 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Combine both thresholding results
        thresh = cv2.bitwise_and(thresh1, thresh2)

        # Scale up image for better OCR
        scale = 3  # Increased scale factor
        scaled = cv2.resize(
            thresh, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
        )

        # Use pytesseract with improved config for better results
        try:
            # Try single word mode first
            config = (
                "--psm 8 --oem 3 "
                "-c tessedit_char_whitelist="
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "abcdefghijklmnopqrstuvwxyz"
                "0123456789-. "
                "-c tessedit_min_confidence=60"
            )
            text = pytesseract.image_to_string(scaled, config=config).strip()

            # If no result, try single line mode
            if not text:
                config = (
                    "--psm 7 --oem 3 "
                    "-c tessedit_char_whitelist="
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-. "
                    "-c tessedit_min_confidence=60"
                )
                text = pytesseract.image_to_string(scaled, config=config).strip()

            # Clean up the text
            text = re.sub(r"[^\w\s.-]", "", text)  # Only keep allowed chars
            text = re.sub(r"\s+", " ", text)  # Normalize whitespace
            text = text.strip()

            # Skip likely false positives
            if len(text) < 2 or text.isspace():
                text = ""

        except Exception as e:
            self.debug(f"OCR failed: {str(e)}")
            text = ""

        return {
            "text": text,
            "color": {
                "b": int(avg_color[0]),
                "g": int(avg_color[1]),
                "r": int(avg_color[2]),
            },
        }

    def detect_text_regions(self, image_path: str) -> list[dict[str, Any]]:
        """Detect text regions in the image using EasyOCR."""
        import cv2
        import easyocr
        import numpy as np

        # Initialize EasyOCR
        reader = easyocr.Reader(["en"], gpu=False)

        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")

        # Get image dimensions
        img_height, img_width = img.shape[:2]

        # Detect text regions with better parameters
        results = reader.readtext(
            img,
            text_threshold=0.2,  # Lower threshold for detection
            low_text=0.1,  # Better for small text
            link_threshold=0.3,  # Less aggressive grouping
            add_margin=0.1,  # Add margin around text
        )

        # Process results
        text_regions = []

        for box_points, text, conf in results:
            if conf < 0.3:  # Minimum confidence
                continue

            # Convert box points to x,y,w,h format
            box = np.array(box_points)
            x = int(min(box[:, 0]))
            y = int(min(box[:, 1]))
            w = int(max(box[:, 0]) - x)
            h = int(max(box[:, 1]) - y)

            # More permissive size threshold for small text
            if (w * h) < (img_width * img_height * 0.0002):  # Even smaller threshold
                continue

            # Get color from region
            region_img = img[y : y + h, x : x + w]
            avg_color = cv2.mean(region_img)[:3]

            # Clean up text but preserve special characters
            text = text.strip()
            if not text:
                continue

            # Skip only specific operational buttons
            if text.lower() in ["vocab", "menu"]:
                continue

            text_regions.append(
                {
                    "box": (x, y, w, h),
                    "text": text,
                    "confidence": conf,
                    "color": {
                        "b": int(avg_color[0]),
                        "g": int(avg_color[1]),
                        "r": int(avg_color[2]),
                    },
                }
            )

        # More precise merging of nearby regions
        text_regions = self.merge_nearby_regions(
            text_regions, distance_threshold=10
        )  # Reduced threshold

        # Sort by position
        text_regions.sort(key=lambda r: (r["box"][1], r["box"][0]))

        return text_regions

    def merge_nearby_regions(
        self, regions: list[dict[str, Any]], distance_threshold: int = 15
    ) -> list[dict[str, Any]]:
        """Merge text regions that are close to each other and likely part of the same button."""
        if not regions:
            return []

        merged = []
        used = set()

        # Sort regions by position for better merging
        regions.sort(key=lambda r: (r["box"][1], r["box"][0]))  # Sort by y then x

        for i, region in enumerate(regions):
            if i in used:
                continue

            merged_region = region.copy()
            x1, y1, w1, h1 = region["box"]

            # Find nearby regions
            for j, other in enumerate(regions[i + 1 :], i + 1):
                if j in used:
                    continue

                x2, y2, w2, h2 = other["box"]

                # Only merge if boxes are very close and similar height
                height_ratio = min(h1, h2) / max(h1, h2)
                if height_ratio < 0.7:  # Height must be similar
                    continue

                # Check for horizontal merging (same line text)
                horizontal_merge = (
                    abs(y1 - y2) < h1 / 3  # Vertically aligned
                    and abs((y1 + h1) - (y2 + h2)) < h1 / 3  # Similar height
                    and abs(x1 + w1 - x2) < distance_threshold  # Horizontally adjacent
                )

                # We no longer do vertical stacking - let grid handle that
                if horizontal_merge:
                    # Merge boxes
                    min_x = min(x1, x2)
                    min_y = min(y1, y2)
                    max_x = max(x1 + w1, x2 + w2)
                    max_y = max(y1 + h1, y2 + h2)

                    merged_region["box"] = (min_x, min_y, max_x - min_x, max_y - min_y)

                    # For horizontal merges, check if special characters need spacing
                    text1 = merged_region["text"]
                    text2 = other["text"]
                    if text1[-1].isalnum() and text2[0].isalnum():
                        merged_region["text"] = f"{text1} {text2}"
                    else:
                        merged_region["text"] = f"{text1}{text2}"

                    merged_region["confidence"] = min(
                        merged_region["confidence"], other["confidence"]
                    )

                    used.add(j)
                    x1, y1, w1, h1 = merged_region["box"]

            merged.append(merged_region)
            used.add(i)

        return merged

    def create_page_from_screenshot(
        self,
        image_path: str,
        grid_rows: Optional[int] = None,
        grid_cols: Optional[int] = None,
        ignore_rows: int = 0,
    ) -> AACPage:
        """Create an AACPage object from a screenshot using grid-first detection."""
        import cv2
        import numpy as np

        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")

        # First detect grid to get cell boundaries
        detected_cols, detected_rows, grid_boxes = self.detect_grid(
            image_path, grid_rows, grid_cols
        )

        # Use provided dimensions or detected ones
        actual_rows = grid_rows if grid_rows is not None else detected_rows
        actual_cols = grid_cols if grid_cols is not None else detected_cols

        if actual_rows < 1 or actual_cols < 1:
            raise ValueError(f"Invalid grid dimensions: {actual_rows}x{actual_cols}")

        # Calculate grid origin and cell size from boxes
        x_coords = [x for x, _, _, _ in grid_boxes]
        y_coords = [y for _, y, _, _ in grid_boxes]
        grid_origin_x = min(x_coords)
        grid_origin_y = (
            min(y_coords) if not ignore_rows else sorted(y_coords)[ignore_rows]
        )

        # Calculate mode cell size (excluding outliers)
        widths = [w for _, _, w, _ in grid_boxes]
        heights = [h for _, _, _, h in grid_boxes]
        widths.sort()
        heights.sort()

        # Remove outliers (top/bottom 10%)
        trim = len(widths) // 10
        if trim > 0:
            widths = widths[trim:-trim]
            heights = heights[trim:-trim]

        mode_width = int(np.median(widths))
        mode_height = int(np.median(heights))

        # Create page
        page = AACPage(
            id=f"screenshot_{Path(image_path).stem}",
            name=f"Detected Page - {Path(image_path).stem}",
            grid_size=(actual_rows, actual_cols),
        )

        # Create debug image
        debug_img = img.copy()

        # Initialize EasyOCR
        import easyocr

        reader = easyocr.Reader(["en"], gpu=False)

        # For each expected cell position
        for row in range(actual_rows):
            for col in range(actual_cols):
                # Calculate expected cell position
                x = grid_origin_x + int(col * mode_width)
                y = grid_origin_y + int(row * mode_height)

                # Define search area (slightly larger than cell)
                margin = 5
                search_x = max(0, x - margin)
                search_y = max(0, y - margin)
                search_w = min(mode_width + 2 * margin, img.shape[1] - search_x)
                search_h = min(mode_height + 2 * margin, img.shape[0] - search_y)

                # Extract cell region
                cell_img = img[
                    search_y : search_y + search_h, search_x : search_x + search_w
                ]

                # Detect text in cell
                results = reader.readtext(
                    cell_img,
                    text_threshold=0.2,
                    low_text=0.2,
                    link_threshold=0.2,
                )

                # Process results
                cell_texts = []
                for _box_points, text, conf in results:
                    if conf < 0.3:
                        continue

                    # Clean up text but preserve special characters
                    text = text.strip()
                    if text and text.lower() not in ["vocab", "menu"]:
                        cell_texts.append(text)

                # If text found, create button
                if cell_texts:
                    # Get color from cell
                    avg_color = cv2.mean(cell_img)[:3]

                    # Create button
                    style = ButtonStyle(
                        body_color=f"#{int(avg_color[2]):02x}{int(avg_color[1]):02x}{int(avg_color[0]):02x}"
                    )

                    btn = AACButton(
                        id=f"btn_{len(page.buttons)}",
                        label=" ".join(cell_texts),
                        type=ButtonType.SPEAK,
                        position=(row, col),
                        style=style,
                    )
                    page.buttons.append(btn)

                # Draw cell and text regions in debug image
                cv2.rectangle(
                    debug_img,
                    (search_x, search_y),
                    (search_x + search_w, search_y + search_h),
                    (0, 255, 0),
                    1,
                )
                if cell_texts:
                    cv2.putText(
                        debug_img,
                        " ".join(cell_texts),
                        (search_x + 5, search_y + search_h - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 255),
                        1,
                    )

        # Save debug image only if enabled
        if self.save_debug_images:
            debug_path = image_path + ".text_debug.png"
            cv2.imwrite(debug_path, debug_img)

        return page

    def can_process(self, file_path: str) -> bool:
        """Check if processor can handle this file type.

        Args:
            file_path: Path to file to check

        Returns:
            True if file has a supported image extension
        """
        ext = Path(file_path).suffix.lower()
        return ext in [".png", ".jpg", ".jpeg", ".bmp"]

    def load_into_tree(self, file_path: str) -> AACTree:
        """Load screenshot into tree structure.

        Args:
            file_path: Path to screenshot file

        Returns:
            Tree structure with single page
        """
        # Detect grid dimensions from filename
        filename = Path(file_path).stem
        if "24" in filename:
            grid_rows, grid_cols = 6, 4
        elif "60" in filename:
            grid_rows, grid_cols = 6, 10
        else:
            grid_rows, grid_cols = None, None

        page = self.create_page_from_screenshot(
            file_path, grid_rows=grid_rows, grid_cols=grid_cols
        )
        tree = AACTree()
        tree.add_page(page)
        return tree

    def save_from_tree(self, tree: AACTree, output_path: str) -> None:
        """Save tree structure to file - not implemented for screenshots.

        Args:
            tree: Tree structure to save
            output_path: Path where to save the file
        """
        raise NotImplementedError("Saving to image is not supported")

    def extract_texts(self, file_path: str) -> list[str]:
        """Extract texts from screenshot.

        Args:
            file_path: Path to screenshot file

        Returns:
            List of detected texts
        """
        page = self.create_page_from_screenshot(file_path)
        return [btn.label for btn in page.buttons if btn.label]

    def create_translated_file(
        self, file_path: str, translations: dict[str, str]
    ) -> Optional[str]:
        """Create a translated version of the file - not supported for screenshots.

        Args:
            file_path: Path to source file
            translations: Dictionary of text translations

        Returns:
            None as translation is not supported
        """
        return None
