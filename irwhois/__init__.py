"""irwhois — check .ir domain availability via whois.nic.ir."""

__version__ = "1.0.1"

from .core import batch_check, check_domain  # noqa: F401

__all__ = ["__version__", "batch_check", "check_domain"]
