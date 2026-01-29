"""Frontend support: serve embedded JS files and auto-register Lovelace resources.

This avoids needing register_static_path/async_register_static_paths, which may be missing
depending on HA version/build.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from ..const import DOMAIN, URL_BASE, JSMODULES

_LOGGER = logging.getLogger(__name__)

_FRONTEND_KEY = f"{DOMAIN}_frontend_registered"


class _FrontendView(HomeAssistantView):
    """Serve JS files from the integration's frontend directory."""

    requires_auth = False
    cors_allowed = True

    # /room_power_aggregator/<filename>
    url = rf"{URL_BASE}/{{filename}}"
    name = f"{DOMAIN}:frontend"

    async def get(self, request: web.Request, filename: str) -> web.StreamResponse:
        wanted = {m["filename"] for m in JSMODULES}
        if filename not in wanted:
            raise web.HTTPNotFound()

        file_path = Path(__file__).parent / filename
        if not file_path.exists():
            raise web.HTTPNotFound()

        return web.FileResponse(
            path=str(file_path),
            headers={
                "Content-Type": "application/javascript; charset=utf-8",
                "Cache-Control": "public, max-age=31536000, immutable",
            },
        )


class JSModuleRegistration:
    """Registers the embedded card JS as Lovelace resources (storage mode)."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.lovelace = self.hass.data.get("lovelace")

    async def async_register(self) -> None:
        """Register the HTTP view and (if possible) Lovelace resources."""
        self._register_view()

        if not self.lovelace:
            _LOGGER.debug("Lovelace not loaded; skipping auto resource registration")
            return

        if getattr(self.lovelace, "mode", None) != "storage":
            _LOGGER.debug("Lovelace not in storage mode; resources must be added manually")
            return

        await self._async_wait_for_lovelace_resources()

    def _register_view(self) -> None:
        if self.hass.data.get(_FRONTEND_KEY):
            return
        self.hass.http.register_view(_FrontendView())
        self.hass.data[_FRONTEND_KEY] = True
        _LOGGER.info("Registered frontend view at %s/*", URL_BASE)

    async def _async_wait_for_lovelace_resources(self) -> None:
        @callback
        async def _check_loaded(_now: Any) -> None:
            try:
                loaded = bool(self.lovelace.resources.loaded)
            except Exception:
                loaded = True

            if loaded:
                await self._async_register_modules()
            else:
                _LOGGER.debug("Lovelace resources not loaded yet, retrying in 5s")
                async_call_later(self.hass, 5, _check_loaded)

        await _check_loaded(0)

    async def _async_register_modules(self) -> None:
        resources = list(self.lovelace.resources.async_items())
        existing = [r for r in resources if str(r.get("url", "")).startswith(URL_BASE + "/")]

        def _path(url: str) -> str:
            return url.split("?")[0]

        def _version(url: str) -> str:
            parts = url.split("?")
            if len(parts) > 1 and parts[1].startswith("v="):
                return parts[1][2:]
            return "0"

        for module in JSMODULES:
            base_url = f"{URL_BASE}/{module['filename']}"
            desired_url = f"{base_url}?v={module['version']}"

            matched = None
            for r in existing:
                if _path(r["url"]) == base_url:
                    matched = r
                    break

            if matched:
                if _version(matched["url"]) != module["version"]:
                    _LOGGER.info("Updating Lovelace resource %s -> v%s", module["filename"], module["version"])
                    await self.lovelace.resources.async_update_item(
                        matched["id"],
                        {"res_type": "module", "url": desired_url},
                    )
            else:
                _LOGGER.info("Adding Lovelace resource %s v%s", module["filename"], module["version"])
                await self.lovelace.resources.async_create_item(
                    {"res_type": "module", "url": desired_url}
                )
