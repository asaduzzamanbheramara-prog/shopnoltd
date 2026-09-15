"""Capability contract for the platform-wide admin database control plane."""

from .contract import DatabaseCapability, DatabaseTableCapability, DdlCapabilities

__all__ = ["DatabaseCapability", "DatabaseTableCapability", "DdlCapabilities"]
