# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Dmitry Kireev
"""fm1_playwright: Playwright test harness for FM-1 emulator firmware."""

from fm1_playwright.testing import FirmwareUITest, VIEW_MODE
from fm1_playwright.recording import (
    audio_patch,
    start_audio_recording,
    stop_audio_recording,
    frames_to_video,
    mux_video_audio,
    video_to_gif,
    video_to_mp4,
    webm_to_mp3,
)

__all__ = [
    'FirmwareUITest',
    'VIEW_MODE',
    'audio_patch',
    'start_audio_recording',
    'stop_audio_recording',
    'frames_to_video',
    'mux_video_audio',
    'video_to_gif',
    'video_to_mp4',
    'webm_to_mp3',
]
