#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Dmitry Kireev
"""E2E demo: generate screenshots, GIFs, video, and audio artifacts.

Run with:
    FM1_WEB_DIR=$HOME/.fm1-emulator/web FIRMWARE_NAME=felucca \
    python3 -m pytest tests/test_demo.py -v

Or with unittest:
    python3 -m unittest tests.test_demo -v
"""
import os
import unittest

from fm1_playwright import FirmwareUITest
from fm1_playwright.recording import (
    audio_patch,
    start_audio_recording,
    stop_audio_recording,
    video_to_gif,
)
from fm1_playwright.testing import FIRMWARE_NAME, FM1_WEB_DIR, RESULTS_DIR


class DemoTest(FirmwareUITest):
    """Generate demo artifacts: screenshots, GIFs, video, and audio."""

    _audio_patch_ctx = None

    @classmethod
    def setUpClass(cls):
        cls._audio_patch_ctx = audio_patch(FM1_WEB_DIR)
        cls._audio_patch_ctx.__enter__()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if cls._audio_patch_ctx:
            cls._audio_patch_ctx.__exit__(None, None, None)

    def _artifact(self, name):
        return self._screenshot_dir / name

    def test_01_boot_screenshot(self):
        self._get_page()
        self._screenshot('home')
        path = self._artifact(f'{FIRMWARE_NAME}-home.png')
        self.assertTrue(path.exists(), f'{path} not created')
        self.assertGreater(path.stat().st_size, 10_000)

    def test_02_preset_scroll_gif(self):
        self.press_button('home', delay_ms=500)
        with self.record_gif('preset-scroll', fps=2) as snap:
            for _ in range(6):
                snap()
                self.rotate_encoder('k2', direction=1, steps=1, delay_ms=600)
        path = self._artifact(f'{FIRMWARE_NAME}-preset-scroll.gif')
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
        path = self._artifact(f'{FIRMWARE_NAME}-play-note.gif')
        self.assertTrue(path.exists())
        self.assertGreater(path.stat().st_size, 50_000)

    def test_04_demo_video(self):
        self.press_button('home', delay_ms=500)
        with self.record_video('demo', fps=4) as snap:
            snap()
            for _ in range(4):
                self.rotate_encoder('k2', direction=1, steps=1, delay_ms=600)
                snap()
            self.press_button('home', delay_ms=500)
            snap()
            for note in ['C4', 'E4', 'G4', 'C5', 'G4', 'E4', 'C4']:
                self.play_note(note, hold_ms=300, delay_ms=100)
                snap()

        video = self._artifact(f'{FIRMWARE_NAME}-demo.webm')
        self.assertTrue(video.exists(), f'{video} not created')
        self.assertGreater(video.stat().st_size, 10_000)

        gif = self._artifact(f'{FIRMWARE_NAME}-demo.gif')
        video_to_gif(str(video), str(gif), fps=4)
        self.assertTrue(gif.exists(), f'{gif} not created')

    def test_05_audio_recording(self):
        page = self._get_page()
        self.press_button('home', delay_ms=500)

        started = start_audio_recording(page)
        self.assertTrue(started, 'audio recording failed to start')

        melody = [
            ('C4', 400), ('E4', 400), ('G4', 400), ('C5', 600),
            ('G4', 300), ('E4', 300), ('C4', 600),
        ]
        for note, hold_ms in melody:
            self.play_note(note, hold_ms=hold_ms, delay_ms=100)

        page.wait_for_timeout(500)
        audio_path = self._artifact(f'{FIRMWARE_NAME}-demo.webm')
        # avoid collision with the video webm
        audio_path = self._artifact(f'{FIRMWARE_NAME}-audio.webm')
        size = stop_audio_recording(page, str(audio_path))
        self.assertGreater(size, 1000, 'audio file too small or empty')

    def test_06_final_screenshot(self):
        self._screenshot('final')
        path = self._artifact(f'{FIRMWARE_NAME}-final.png')
        self.assertTrue(path.exists())


if __name__ == '__main__':
    unittest.main()
