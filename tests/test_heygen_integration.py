"""Offline HeyGen v3 contract regression tests. Never call a paid API."""
import asyncio
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from services.heygen_service import HeyGenService


class HeyGenV3Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"HEYGEN_API_KEY": "unit-test-key"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.previous_cwd = Path.cwd()
        os.chdir(self.temp.name)
        self.addCleanup(os.chdir, self.previous_cwd)
        self.calls = []
        self.handler = self.default_handler
        real_client = httpx.AsyncClient

        def dispatch(request):
            self.calls.append(request)
            if request.url.host == "api.heygen.com":
                self.assertTrue(request.url.path.startswith("/v3/"))
                self.assertEqual(request.headers["X-Api-Key"], "unit-test-key")
            else:
                self.assertNotIn("X-Api-Key", request.headers)
            return self.handler(request)

        transport = httpx.MockTransport(dispatch)
        p = patch("services.heygen_service.httpx.AsyncClient", side_effect=lambda **kw: real_client(transport=transport, **kw))
        p.start()
        self.addCleanup(p.stop)
        self.sleep = patch("services.heygen_service.asyncio.sleep", new_callable=AsyncMock)
        self.sleep.start()
        self.addCleanup(self.sleep.stop)
        self.demo_patch = patch.object(HeyGenService, "_create_demo_video", new_callable=AsyncMock, return_value="local-demo.mp4")
        self.demo = self.demo_patch.start()
        self.addCleanup(self.demo_patch.stop)
        self.output = io.StringIO()
        capture = contextlib.redirect_stdout(self.output)
        capture.__enter__()
        self.addCleanup(capture.__exit__, None, None, None)
        self.service = HeyGenService()

    def default_handler(self, request):
        path = request.url.path
        if path == "/v3/voices":
            return httpx.Response(200, json={"data": [{"voice_id": "tr-voice", "name": "Türkçe", "language": "Turkish", "gender": "female"}], "has_more": False, "next_token": None})
        if path == "/v3/videos" and request.method == "POST":
            return httpx.Response(200, json={"data": {"video_id": "v-test", "status": "waiting"}})
        if path == "/v3/videos/v-test":
            return httpx.Response(200, json={"data": {"id": "v-test", "status": "completed", "video_url": "https://files.example/video.mp4"}})
        if request.url.host == "files.example":
            return httpx.Response(200, content=b"mock-mp4")
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    async def test_create_payload_uses_v3_and_preserves_studio_engine_and_dimensions(self):
        result = await self.service.create_avatar_video("Merhaba", "professional_male")
        self.assertEqual(Path(result).read_bytes(), b"mock-mp4")
        posts = [r for r in self.calls if r.method == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(json.loads(posts[0].content), {
            "type": "avatar", "avatar_id": self.service.avatars["professional_male"],
            "script": "Merhaba", "voice_id": "tr-voice",
            "background": {"type": "color", "value": "#FFFFFF"},
            "aspect_ratio": "16:9", "resolution": "720p", "engine": {"type": "avatar_iii"},
        })
        self.assertRegex(posts[0].headers["Idempotency-Key"], r"^[0-9a-f-]{36}$")
        self.demo.assert_not_awaited()

    async def test_turkish_voice_pagination_and_cache(self):
        def handler(r):
            self.assertEqual(r.url.params["language"], "Turkish")
            self.assertEqual(r.url.params["limit"], "100")
            if "token" not in r.url.params:
                return httpx.Response(200, json={"data": [{"voice_id": "male", "name": "Erkek", "language": "Turkish", "gender": "male"}], "has_more": True, "next_token": "cursor+2/="})
            self.assertEqual(r.url.params["token"], "cursor+2/=")
            return httpx.Response(200, json={"data": [
                {"voice_id": "female", "name": "Kadın", "language": "Turkish", "gender": "female"},
                {"voice_id": "en", "language": "English"},
                {"voice_id": "unknown", "language": None},
            ], "has_more": False, "next_token": None})
        self.handler = handler
        voices = await self.service.get_turkish_voices()
        self.assertEqual([v["voice_id"] for v in voices], ["male", "female"])
        self.assertEqual(self.service.turkish_voice_id, "female")
        self.assertEqual(await self.service.get_turkish_voices(), voices)
        self.assertEqual(len(self.calls), 2)

    async def test_empty_voice_list_is_cached_and_never_submits_video(self):
        self.handler = lambda r: httpx.Response(200, json={"data": [], "has_more": False})
        self.assertEqual(await self.service.get_turkish_voices(), [])
        self.assertEqual(await self.service.get_turkish_voices(), [])
        self.assertEqual(await self.service.create_avatar_video("Merhaba", "professional_female"), "local-demo.mp4")
        self.assertEqual(len(self.calls), 1)
        self.demo.assert_awaited_once()

    async def test_repeated_voice_cursor_terminates_without_a_generation(self):
        self.handler = lambda r: httpx.Response(200, json={"data": [], "has_more": True, "next_token": "same"})
        self.assertEqual(await self.service.get_turkish_voices(), [])
        self.assertEqual(len(self.calls), 2)
        self.assertIsNone(self.service.voices_cache)

    async def test_pending_and_processing_v3_statuses_need_no_legacy_success_code(self):
        statuses = iter(["pending", "processing", "completed"])
        def handler(r):
            if r.url.path == "/v3/videos/v-test":
                status = next(statuses)
                return httpx.Response(200, json={"data": {"id": "v-test", "status": status, "video_url": "https://files.example/video.mp4" if status == "completed" else None}})
            return self.default_handler(r)
        self.handler = handler
        result = await self.service.create_avatar_video("Merhaba", "professional_female")
        self.assertEqual(Path(result).read_bytes(), b"mock-mp4")
        self.assertEqual(len([r for r in self.calls if r.url.path == "/v3/videos/v-test"]), 3)
        self.demo.assert_not_awaited()

    async def test_failed_generation_uses_v3_failure_message_and_existing_demo_fallback(self):
        def handler(r):
            if r.url.path == "/v3/videos/v-test":
                return httpx.Response(200, json={"data": {"status": "failed", "failure_message": "render failed", "failure_code": "rendering_failed"}})
            return self.default_handler(r)
        self.handler = handler
        self.assertEqual(await self.service.create_avatar_video("Merhaba", "professional_female"), "local-demo.mp4")
        self.assertIn("render failed", self.output.getvalue())
        self.assertEqual(len([r for r in self.calls if r.method == "POST"]), 1)
        self.demo.assert_awaited_once()

    async def test_missing_video_id_does_not_poll_or_resubmit(self):
        def handler(r):
            if r.method == "POST":
                return httpx.Response(200, json={"data": {"status": "pending"}})
            return self.default_handler(r)
        self.handler = handler
        self.assertEqual(await self.service.create_avatar_video("Merhaba", "professional_female"), "local-demo.mp4")
        self.assertEqual(len(self.calls), 2)
        self.assertIn("No video_id", self.output.getvalue())

    async def test_missing_download_url_falls_back_without_another_paid_call(self):
        def handler(r):
            if r.url.path == "/v3/videos/v-test":
                return httpx.Response(200, json={"data": {"status": "completed", "video_url": None}})
            return self.default_handler(r)
        self.handler = handler
        self.assertEqual(await self.service.create_avatar_video("Merhaba", "professional_female"), "local-demo.mp4")
        self.assertEqual(len([r for r in self.calls if r.method == "POST"]), 1)
        self.assertIn("No video URL", self.output.getvalue())

    async def test_ambiguous_post_timeout_never_resubmits(self):
        def handler(r):
            if r.method == "POST":
                raise httpx.ReadTimeout("uncertain generation outcome", request=r)
            return self.default_handler(r)
        self.handler = handler
        self.assertEqual(await self.service.create_avatar_video("Merhaba", "professional_female"), "local-demo.mp4")
        self.assertEqual(len([r for r in self.calls if r.method == "POST"]), 1)
        self.assertEqual(len(self.calls), 2)

    async def test_http_error_in_status_stops_without_a_generation_retry(self):
        def handler(r):
            if r.url.path == "/v3/videos/v-test":
                return httpx.Response(401, json={"error": {"message": "invalid key"}})
            return self.default_handler(r)
        self.handler = handler
        self.assertEqual(await self.service.create_avatar_video("Merhaba", "professional_female"), "local-demo.mp4")
        self.assertEqual(len(self.calls), 3)
        self.demo.assert_awaited_once()

    async def test_status_helper_uses_encoded_v3_resource_path(self):
        self.handler = lambda r: httpx.Response(200, json={"data": {"id": "v/1", "status": "pending"}})
        self.assertEqual((await self.service.get_video_status("v/1"))["data"]["status"], "pending")
        self.assertEqual(self.calls[0].url.raw_path, b"/v3/videos/v%2F1")
        self.assertNotIn("video_id", self.calls[0].url.params)

    async def test_no_api_key_keeps_demo_local(self):
        del os.environ["HEYGEN_API_KEY"]
        service = HeyGenService()
        self.assertFalse(service.enabled)
        self.assertEqual(await service.get_turkish_voices(), [])
        self.assertEqual(await service.create_avatar_video("Merhaba", "professional_female"), "local-demo.mp4")
        self.assertEqual(self.calls, [])
        self.demo.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
