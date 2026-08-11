class PlatformBookError(Exception):
    """Base class for expected, user-actionable failures."""


class ManifestError(PlatformBookError):
    """Manifest is missing or invalid."""


class InputError(PlatformBookError):
    """Source pages cannot be read."""


class ValidationError(PlatformBookError):
    """Generated package failed validation."""
