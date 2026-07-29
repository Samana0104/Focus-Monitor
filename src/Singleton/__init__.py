"""Shared singleton services."""

from Singleton.Camera import CameraManager
from Singleton.Settings import Settings
from Singleton.Singleton import Singleton

__all__ = ["CameraManager", "Settings", "Singleton"]
