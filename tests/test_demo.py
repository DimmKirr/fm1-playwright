#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Dmitry Kireev
"""E2E demo: generate screenshots, GIFs, video, and audio artifacts.

Run with:
    FM1_WEB_DIR=$HOME/.fm1-emulator/web FIRMWARE_NAME=felucca \
    python3 -m pytest tests/test_demo.py -v

Or with unittest:
    python3 -m unittest tests.test_demo -v

Artifacts are written to tests/results/<datetimeISO>/{screenshots,video,audio}/
and never wiped between runs.
"""
import datetime
import unittest
from pathlib import Path

from fm1_playwright import FirmwareUITest
from fm1_playwright.recording import (
    audio_patch,
    mux_video_audio,
    start_audio_recording,
    stop_audio_recording,
    video_to_gif,
    video_to_mp4,
    webm_to_mp3,
)
from fm1_playwright.testing import FIRMWARE_NAME, FM1_WEB_DIR

TESTS_DIR = Path(__file__).resolve().parent
RUN_TS = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
RUN_DIR = TESTS_DIR / 'results' / RUN_TS

# "Happy Birthday to You" in FM-1 note names (C4-F5 range)
HAPPY_BIRTHDAY = [
    # Happy birth-day to you
    ('C4', 200, 50), ('C4', 200, 50), ('D4', 400, 50), ('C4', 400, 50),
    ('F4', 400, 50), ('E4', 600, 200),
    # Happy birth-day to you
    ('C4', 200, 50), ('C4', 200, 50), ('D4', 400, 50), ('C4', 400, 50),
    ('G4', 400, 50), ('F4', 600, 200),
    # Happy birth-day dear friend
    ('C4', 200, 50), ('C4', 200, 50), ('C5', 400, 50), ('A4', 400, 50),
    ('F4', 400, 50), ('E4', 400, 50), ('D4', 600, 200),
    # Happy birth-day to you
    ('A#4', 200, 50), ('A#4', 200, 50), ('A4', 400, 50), ('F4', 400, 50),
    ('G4', 400, 50), ('F4', 800, 100),
]


class DemoTest(FirmwareUITest):
    """Generate demo artifacts: screenshots, GIFs, video, and audio."""

    _audio_patch_ctx = None
    _screenshots_dir = None
    _video_dir = None
    _audio_dir = None

    @classmethod
    def setUpClass(cls):
        cls._audio_patch_ctx = audio_patch(FM1_WEB_DIR)
        cls._audio_patch_ctx.__enter__()

        cls._screenshots_dir = RUN_DIR / 'screenshots'
        cls._video_dir = RUN_DIR / 'video'
        cls._audio_dir = RUN_DIR / 'audio'
        for d in (cls._screenshots_dir, cls._video_dir, cls._audio_dir):
            d.mkdir(parents=True, exist_ok=True)

        super().setUpClass()
        cls._screenshot_dir = cls._screenshots_dir

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if cls._audio_patch_ctx:
            cls._audio_patch_ctx.__exit__(None, None, None)
        print(f'\n  Artifacts: {RUN_DIR}', flush=True)

    def test_01_boot_screenshot(self):
        self._get_page()
        self._screenshot('home')
        path = self._screenshots_dir / f'{FIRMWARE_NAME}-home.png'
        self.assertTrue(path.exists(), f'{path} not created')
        self.assertGreater(path.stat().st_size, 10_000)

    def test_02_preset_scroll_gif(self):
        self.press_button('home', delay_ms=500)
        with self.record_gif('preset-scroll', fps=2) as snap:
            for _ in range(6):
                snap()
                self.rotate_encoder('k2', direction=1, steps=1, delay_ms=600)
        path = self._screenshots_dir / f'{FIRMWARE_NAME}-preset-scroll.gif'
        self.assertTrue(path.exists(), f'{path} not created')
        self.assertGreater(path.stat().st_size, 50_000)

    def test_03_play_note_gif(self):
        self.press_button('home', delay_ms=500)
        notes = ['C4', 'C#4', 'D4', 'D#4', 'E4', 'F4', 'F#4',
                 'G4', 'G#4', 'A4', 'A#4', 'B4', 'C5']
        with self.record_gif('play-note', fps=4) as snap:
            for note in notes:
                snap()
                self.play_note(note, hold_ms=200, delay_ms=100)
        path = self._screenshots_dir / f'{FIRMWARE_NAME}-play-note.gif'
        self.assertTrue(path.exists())
        self.assertGreater(path.stat().st_size, 50_000)

    def test_04_demo_video(self):
        self.press_button('home', delay_ms=500)
        with self.record_video('demo', fps=4, output_dir=self._video_dir) as snap:
            snap()
            for _ in range(4):
                self.rotate_encoder('k2', direction=1, steps=1, delay_ms=600)
                snap()
            self.press_button('home', delay_ms=500)
            snap()
            for note in ['C4', 'E4', 'G4', 'C5', 'G4', 'E4', 'C4']:
                self.play_note(note, hold_ms=300, delay_ms=100)
                snap()

        video = self._video_dir / f'{FIRMWARE_NAME}-demo.webm'
        self.assertTrue(video.exists(), f'{video} not created')
        self.assertGreater(video.stat().st_size, 10_000)

        mp4 = self._video_dir / f'{FIRMWARE_NAME}-demo.mp4'
        video_to_mp4(str(video), str(mp4))
        self.assertTrue(mp4.exists(), f'{mp4} not created')

        gif = self._video_dir / f'{FIRMWARE_NAME}-demo.gif'
        video_to_gif(str(video), str(gif), fps=4)
        self.assertTrue(gif.exists(), f'{gif} not created')

    def test_05_happy_birthday(self):
        """Play 'Happy Birthday' on ANALOG instrument via Playwright."""
        page = self._get_page()

        # Reset to track 1 (ANALOG) since previous tests may have changed
        # presets. Select encoder switches tracks; rotate left to track 1.
        self.rotate_encoder('select', direction=-1, steps=10, delay_ms=50)
        self.press_button('home', delay_ms=500)
        # Rotate presets back to first preset (ACID on ANALOG)
        self.rotate_encoder('k2', direction=-1, steps=20, delay_ms=50)
        self.press_button('home', delay_ms=500)
        self._screenshot('happy-birthday-instrument')

        started = start_audio_recording(page)
        self.assertTrue(started, 'audio recording failed to start')

        with self.record_video('happy-birthday', fps=4,
                               output_dir=self._video_dir) as snap:
            snap()
            for note, hold_ms, rest_ms in HAPPY_BIRTHDAY:
                self.play_note(note, hold_ms=hold_ms, delay_ms=rest_ms)
                snap()

        page.wait_for_timeout(500)

        # Save audio
        audio_webm = self._audio_dir / f'{FIRMWARE_NAME}-happy-birthday.webm'
        size = stop_audio_recording(page, str(audio_webm))
        self.assertGreater(size, 1000, 'audio file too small or empty')

        mp3_path = self._audio_dir / f'{FIRMWARE_NAME}-happy-birthday.mp3'
        self.assertTrue(
            webm_to_mp3(str(audio_webm), str(mp3_path)),
            'MP3 conversion failed')

        # Convert video to MP4 (with audio) and GIF
        video = self._video_dir / f'{FIRMWARE_NAME}-happy-birthday.webm'
        self.assertTrue(video.exists(), f'{video} not created')

        mp4 = self._video_dir / f'{FIRMWARE_NAME}-happy-birthday.mp4'
        self.assertTrue(
            mux_video_audio(str(video), str(audio_webm), str(mp4)),
            'video+audio mux to MP4 failed')

        gif = self._video_dir / f'{FIRMWARE_NAME}-happy-birthday.gif'
        video_to_gif(str(video), str(gif), fps=4)
        self.assertTrue(gif.exists(), f'{gif} not created')

    def test_06_final_screenshot(self):
        self._screenshot('final')
        path = self._screenshots_dir / f'{FIRMWARE_NAME}-final.png'
        self.assertTrue(path.exists())


if __name__ == '__main__':
    unittest.main()
