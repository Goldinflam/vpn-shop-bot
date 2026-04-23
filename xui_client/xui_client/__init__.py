"""Domain wrapper over py3xui.

Public API must satisfy `shared.contracts.xui.XUIClientProtocol`.
"""

from xui_client.client import XUIClient

__all__ = ["XUIClient"]
__version__ = "0.1.0"
