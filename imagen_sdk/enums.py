from enum import Enum


class PhotographyType(Enum):
    """Photography types for AI optimization (from API spec)."""

    NO_TYPE = "NO_TYPE"
    OTHER = "OTHER"
    PORTRAITS = "PORTRAITS"
    WEDDING = "WEDDING"
    REAL_ESTATE = "REAL_ESTATE"
    LANDSCAPE_NATURE = "LANDSCAPE_NATURE"
    EVENTS = "EVENTS"
    FAMILY_NEWBORN = "FAMILY_NEWBORN"
    BOUDOIR = "BOUDOIR"
    SPORTS = "SPORTS"


class CropAspectRatio(Enum):
    """Crop aspect ratios (from API spec)."""

    RATIO_2X3 = "2X3"
    RATIO_4X5 = "4X5"
    RATIO_5X7 = "5X7"
