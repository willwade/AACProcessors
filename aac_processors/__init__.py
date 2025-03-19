from typing import TYPE_CHECKING

from . import viewer
from .coughdrop_processor import CoughDropProcessor
from .dot_processor import DotProcessor
from .gridset_processor import GridsetProcessor
from .opml_processor import OPMLProcessor
from .snap_processor import SnapProcessor
from .touchchat_processor import TouchChatProcessor
from .tree_structure import AACButton, AACPage, AACTree, ButtonType

if TYPE_CHECKING:
    from .optional.screenshot_processor import ScreenshotProcessor

__all__ = [
    "GridsetProcessor",
    "TouchChatProcessor",
    "SnapProcessor",
    "CoughDropProcessor",
    "OPMLProcessor",
    "DotProcessor",
    "AACTree",
    "AACPage",
    "AACButton",
    "ButtonType",
    "viewer",
    "ScreenshotProcessor",
    "get_screenshot_processor",
]


def get_screenshot_processor() -> "ScreenshotProcessor":
    """Lazy load the screenshot processor.

    Returns:
        Initialized ScreenshotProcessor instance

    Raises:
        ImportError: If screenshot dependencies are not installed
    """
    try:
        from .optional.screenshot_processor import ScreenshotProcessor

        return ScreenshotProcessor()
    except ImportError as e:
        raise ImportError(
            "Screenshot processing requires additional dependencies. "
            "Install them with: pip install aac-processors[screenshot]"
        ) from e
