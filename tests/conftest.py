import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from collections.abc import Generator
from typing import Any

import pytest
from lxml import etree as et


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test files"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def test_snap_db(temp_dir: str) -> str:
    """Create a test Snap database"""
    db_path = os.path.join(temp_dir, "test.sps")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript(
        """
        CREATE TABLE Page (
            id INTEGER PRIMARY KEY,
            Title TEXT
        );

        CREATE TABLE Button (
            id INTEGER PRIMARY KEY,
            page_id INTEGER,
            Label TEXT,
            Message TEXT,
            position_x INTEGER,
            position_y INTEGER,
            FOREIGN KEY (page_id) REFERENCES Page(id)
        );

        CREATE TABLE ButtonAction (
            id INTEGER PRIMARY KEY,
            button_id INTEGER,
            action_type TEXT,
            target_page_id INTEGER,
            FOREIGN KEY (button_id) REFERENCES Button(id)
        );
    """
    )

    # Add test pages
    cursor.execute("INSERT INTO Page (id, Title) VALUES (1, 'Test Page')")
    cursor.execute("INSERT INTO Page (id, Title) VALUES (2, 'Second Page')")

    # Add test buttons
    cursor.execute(
        """
        INSERT INTO Button (id, page_id, Label, Message, position_x, position_y)
        VALUES (1, 1, 'Speak Button', 'Hello', 0, 0)
    """
    )
    cursor.execute(
        """
        INSERT INTO Button (id, page_id, Label, Message, position_x, position_y)
        VALUES (2, 1, 'Navigate', NULL, 1, 0)
    """
    )

    # Add button action
    cursor.execute(
        """
        INSERT INTO ButtonAction (button_id, action_type, target_page_id)
        VALUES (2, 'navigate', 2)
    """
    )

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def test_gridset(temp_dir: str) -> str:
    """Create a test Grid3 gridset with realistic content"""
    gridset_dir = os.path.join(temp_dir, "test_gridset_dir")

    # Create Grids directory
    grids_dir = os.path.join(gridset_dir, "Grids")
    os.makedirs(grids_dir, exist_ok=True)

    # Create Settings0 directory
    settings_dir = os.path.join(gridset_dir, "Settings0")
    os.makedirs(settings_dir, exist_ok=True)

    # Create first grid directory and grid.xml
    grid1_dir = os.path.join(grids_dir, "Test Grid")
    os.makedirs(grid1_dir, exist_ok=True)

    grid1 = et.Element("Grid")
    grid1.set("Name", "Test Grid")
    grid1.set("GridGuid", "1")

    # Add row and column definitions
    row_defs = et.SubElement(grid1, "RowDefinitions")
    for _ in range(2):
        et.SubElement(row_defs, "RowDefinition")

    col_defs = et.SubElement(grid1, "ColumnDefinitions")
    for _ in range(2):
        et.SubElement(col_defs, "ColumnDefinition")

    # Add cells
    cells = et.SubElement(grid1, "Cells")
    cell = et.SubElement(cells, "Cell")
    cell.set("X", "0")
    cell.set("Y", "0")

    content = et.SubElement(cell, "Content")
    caption_and_image = et.SubElement(content, "CaptionAndImage")
    caption = et.SubElement(caption_and_image, "Caption")
    caption.text = "Test Button"

    grid1_path = os.path.join(grid1_dir, "grid.xml")
    et.ElementTree(grid1).write(grid1_path, encoding="utf-8", xml_declaration=True)

    # Create second grid directory (wordlist) and grid.xml
    grid2_dir = os.path.join(grids_dir, "Test List")
    os.makedirs(grid2_dir, exist_ok=True)

    grid2 = et.Element("Grid")
    grid2.set("Name", "Test List")
    grid2.set("GridGuid", "2")

    # Add row and column definitions
    row_defs = et.SubElement(grid2, "RowDefinitions")
    et.SubElement(row_defs, "RowDefinition")
    col_defs = et.SubElement(grid2, "ColumnDefinitions")
    et.SubElement(col_defs, "ColumnDefinition")

    # Add wordlist
    wordlist = et.SubElement(grid2, "WordList")
    wordlist.set("Name", "Test List")
    items = et.SubElement(wordlist, "Items")
    item = et.SubElement(items, "WordListItem")
    text = et.SubElement(item, "Text")
    text.text = "Test Word"

    grid2_path = os.path.join(grid2_dir, "grid.xml")
    et.ElementTree(grid2).write(grid2_path, encoding="utf-8", xml_declaration=True)

    # Create settings.xml
    settings = et.Element("GridSetSettings")
    start_grid = et.SubElement(settings, "StartGrid")
    start_grid.text = "Test Grid"

    settings_path = os.path.join(settings_dir, "settings.xml")
    et.ElementTree(settings).write(
        settings_path, encoding="utf-8", xml_declaration=True
    )

    # Create FileMap.xml
    filemap = et.Element("FileMap")
    entries = et.SubElement(filemap, "Entries")

    entry1 = et.SubElement(entries, "Entry")
    entry1.set("StaticFile", "Grids\\Test Grid\\grid.xml")

    entry2 = et.SubElement(entries, "Entry")
    entry2.set("StaticFile", "Grids\\Test List\\grid.xml")

    filemap_path = os.path.join(gridset_dir, "FileMap.xml")
    et.ElementTree(filemap).write(filemap_path, encoding="utf-8", xml_declaration=True)

    # Create gridset file
    zip_path = os.path.join(temp_dir, "test.gridset")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
        for root, _, files in os.walk(gridset_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, gridset_dir)
                zip_ref.write(file_path, arc_name)

    return zip_path


@pytest.fixture
def test_touchchat_ce(temp_dir: str) -> str:
    """Create a test TouchChat CE file"""
    db_path = os.path.join(temp_dir, "test.c4v")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript(
        """
        CREATE TABLE resources (
            id INTEGER PRIMARY KEY,
            rid TEXT,
            name TEXT,
            type INTEGER
        );

        CREATE TABLE pages (
            id INTEGER PRIMARY KEY,
            resource_id INTEGER,
            FOREIGN KEY (resource_id) REFERENCES resources(id)
        );

        CREATE TABLE buttons (
            id INTEGER PRIMARY KEY,
            resource_id INTEGER,
            label TEXT,
            message TEXT,
            page_id INTEGER,
            FOREIGN KEY (resource_id) REFERENCES resources(id),
            FOREIGN KEY (page_id) REFERENCES pages(id)
        );

        CREATE TABLE button_boxes (
            id INTEGER PRIMARY KEY,
            init_size_x INTEGER,
            init_size_y INTEGER
        );

        CREATE TABLE button_box_instances (
            id INTEGER PRIMARY KEY,
            button_box_id INTEGER,
            page_id INTEGER,
            FOREIGN KEY (button_box_id) REFERENCES button_boxes(id),
            FOREIGN KEY (page_id) REFERENCES pages(id)
        );

        CREATE TABLE button_box_cells (
            id INTEGER PRIMARY KEY,
            button_box_id INTEGER,
            resource_id INTEGER,
            location INTEGER,
            span_x INTEGER DEFAULT 1,
            span_y INTEGER DEFAULT 1,
            FOREIGN KEY (button_box_id) REFERENCES button_boxes(id),
            FOREIGN KEY (resource_id) REFERENCES resources(id)
        );

        CREATE TABLE actions (
            id INTEGER PRIMARY KEY,
            resource_id INTEGER,
            code INTEGER,
            FOREIGN KEY (resource_id) REFERENCES resources(id)
        );

        CREATE TABLE action_data (
            id INTEGER PRIMARY KEY,
            action_id INTEGER,
            key INTEGER,
            value TEXT,
            FOREIGN KEY (action_id) REFERENCES actions(id)
        );

        CREATE TABLE special_pages (
            id INTEGER PRIMARY KEY,
            name TEXT,
            page_id INTEGER,
            FOREIGN KEY (page_id) REFERENCES pages(id)
        );
    """
    )

    # Add test page
    cursor.execute(
        "INSERT INTO resources (rid, name, type) VALUES ('page1', 'Test Page', 1)"
    )
    page_resource_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO pages (id, resource_id) VALUES (1, ?)", (page_resource_id,)
    )

    # Create button box for the page
    cursor.execute("INSERT INTO button_boxes (init_size_x, init_size_y) VALUES (2, 2)")
    button_box_id = cursor.lastrowid

    # Link button box to page
    cursor.execute(
        """
        INSERT INTO button_box_instances (button_box_id, page_id)
        VALUES (?, 1)
        """,
        (button_box_id,),
    )

    # Add test button
    cursor.execute(
        "INSERT INTO resources (rid, name, type) VALUES ('btn1', 'Test Button', 2)"
    )
    btn_resource_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO buttons (resource_id, label, message, page_id)
        VALUES (?, 'Test Button', 'Hello', 1)
        """,
        (btn_resource_id,),
    )

    # Add button cell
    cursor.execute(
        """
        INSERT INTO button_box_cells (button_box_id, resource_id, location)
        VALUES (?, ?, 0)
        """,
        (button_box_id, btn_resource_id),
    )

    # Set home page
    cursor.execute(
        """
        INSERT INTO special_pages (name, page_id)
        VALUES ('Home', 1)
        """
    )

    conn.commit()
    conn.close()

    # Create CE file
    ce_path = os.path.join(temp_dir, "test.ce")
    with zipfile.ZipFile(ce_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
        zip_ref.write(db_path, "test.c4v")

    return ce_path


@pytest.fixture
def test_coughdrop_obf(temp_dir: str) -> str:
    """Create a test CoughDrop OBF file"""
    obf_path = os.path.join(temp_dir, "test.obf")

    board_data = {
        "format": "open-board-0.1",
        "id": "home",
        "name": "Test Board",
        "grid": {"rows": 2, "columns": 2, "order": [["btn1", "btn2"], [None, None]]},
        "buttons": [
            {"id": "btn1", "label": "Test Button", "vocalization": "Hello"},
            {"id": "btn2", "label": "Navigate", "load_board": {"id": "page2"}},
        ],
    }

    with open(obf_path, "w") as f:
        json.dump(board_data, f, indent=2)

    return obf_path


@pytest.fixture
def test_coughdrop_obz(temp_dir: str, test_coughdrop_obf: str) -> str:
    """Create a test CoughDrop OBZ file"""
    obz_path = os.path.join(temp_dir, "test.obz")

    # Create boards directory
    boards_dir = os.path.join(temp_dir, "boards")
    os.makedirs(boards_dir, exist_ok=True)

    # Copy test board
    board_path = os.path.join(boards_dir, "home.obf")
    shutil.copy2(test_coughdrop_obf, board_path)

    # Create manifest
    manifest = {
        "format": "open-board-0.1",
        "root": "boards/home.obf",
        "paths": {"boards": {"home": "boards/home.obf"}},
    }

    # Create OBZ file
    with zipfile.ZipFile(obz_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
        # Add manifest
        manifest_path = os.path.join(temp_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        zip_ref.write(manifest_path, "manifest.json")

        # Add board file
        zip_ref.write(board_path, "boards/home.obf")

    return obz_path


def pytest_configure(config: Any) -> None:
    """Register custom marks"""
    config.addinivalue_line("markers", "integration: mark test as an integration test")
