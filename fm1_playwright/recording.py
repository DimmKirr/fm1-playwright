# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Dmitry Kireev
"""Audio capture and video recording for FM-1 emulator sessions."""

import base64
import contextlib
import os
import shutil
import subprocess
import tempfile

_AUDIO_PATCH_JS = r"""(function() {
    var OrigAC = window.AudioContext || window.webkitAudioContext;
    window.__fm1_ac_instances = [];
    window.__fm1_audio_dests = [];
    window.__fm1_audio_chunks = [];
    window.__fm1_audio_recorder = null;

    var origConnect = AudioNode.prototype.connect;
    AudioNode.prototype.connect = function(dest) {
        var result = origConnect.apply(this, arguments);
        var dests = window.__fm1_audio_dests;
        for (var i = 0; i < dests.length; i++) {
            if (dest === dests[i].dest) {
                try { origConnect.call(this, dests[i].msDest); } catch(e) {}
            }
        }
        return result;
    };

    function PatchedAC() {
        var ac = new OrigAC();
        window.__fm1_ac_instances.push(ac);
        var msDest = ac.createMediaStreamDestination();
        window.__fm1_audio_dests.push({ dest: ac.destination, msDest: msDest });
        return ac;
    }
    PatchedAC.prototype = OrigAC.prototype;
    window.AudioContext = PatchedAC;
    if (window.webkitAudioContext) window.webkitAudioContext = PatchedAC;
})();
"""


@contextlib.contextmanager
def audio_patch(web_dir):
    """Inject AudioContext interceptor into the emulator HTML.

    Must be applied before page navigation. Patches index.html to load a
    script that intercepts AudioContext creation and AudioNode.connect calls,
    routing audio to a MediaStreamDestination for recording.

    Usage::

        with audio_patch(web_dir):
            page.goto(emu_url)
            # ... boot, interact ...
            start_audio_recording(page)
            # ... play notes ...
            stop_audio_recording(page, 'output.webm')
    """
    from pathlib import Path
    web_dir = Path(web_dir)
    patch_path = web_dir / '__fm1_audio_patch.js'
    index_path = web_dir / 'index.html'

    patch_path.write_text(_AUDIO_PATCH_JS)
    original_html = index_path.read_text()
    patched_html = original_html.replace(
        '<head>',
        '<head><script src="__fm1_audio_patch.js"></script>',
        1,
    )
    if patched_html != original_html:
        index_path.write_text(patched_html)
    try:
        yield
    finally:
        index_path.write_text(original_html)
        patch_path.unlink(missing_ok=True)


def start_audio_recording(page):
    """Start recording audio from the intercepted AudioContext.

    Returns True if recording started, False if no AudioContext was captured.
    Requires audio_patch() to have been active before page navigation.
    """
    return page.evaluate('''() => {
        try {
            const dests = window.__fm1_audio_dests || [];
            if (dests.length === 0) return false;
            const entry = dests[0];
            const mr = new MediaRecorder(entry.msDest.stream, {
                mimeType: 'audio/webm;codecs=opus'
            });
            window.__fm1_audio_chunks = [];
            mr.ondataavailable = (e) => {
                if (e.data.size > 0) window.__fm1_audio_chunks.push(e.data);
            };
            mr.start(100);
            window.__fm1_audio_recorder = mr;
            return true;
        } catch(e) { return false; }
    }''')


def stop_audio_recording(page, output_path):
    """Stop audio recording and save to output_path (webm format).

    Returns the file size in bytes, or 0 if no audio was captured.
    """
    audio_b64 = page.evaluate('''() => {
        return new Promise((resolve) => {
            const mr = window.__fm1_audio_recorder;
            if (!mr) { resolve(null); return; }
            mr.onstop = () => {
                const blob = new Blob(window.__fm1_audio_chunks,
                    {type: 'audio/webm'});
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.readAsDataURL(blob);
            };
            mr.stop();
        });
    }''')
    if not audio_b64 or ',' not in audio_b64:
        return 0
    audio_data = base64.b64decode(audio_b64.split(',', 1)[1])
    with open(output_path, 'wb') as f:
        f.write(audio_data)
    return len(audio_data)


def frames_to_video(frames_dir, pattern, output_path, fps=4):
    """Stitch PNG frames into a webm video using ffmpeg.

    Returns True if the video was created successfully.
    """
    if not shutil.which('ffmpeg'):
        return False
    result = subprocess.run([
        'ffmpeg', '-y',
        '-framerate', str(fps),
        '-i', os.path.join(frames_dir, pattern),
        '-c:v', 'libvpx-vp9', '-crf', '30', '-b:v', '0',
        '-pix_fmt', 'yuva420p',
        output_path,
    ], capture_output=True)
    return os.path.exists(output_path) and os.path.getsize(output_path) > 0


def video_to_gif(video_path, gif_path, fps=4):
    """Convert a video file to an animated GIF using ffmpeg.

    Returns True if the GIF was created successfully.
    """
    if not shutil.which('ffmpeg'):
        return False
    subprocess.run([
        'ffmpeg', '-y', '-i', video_path,
        '-vf', f'fps={fps},split[s0][s1];[s0]palettegen=max_colors=128[p];'
               '[s1][p]paletteuse=dither=bayer:bayer_scale=3',
        '-loop', '0',
        gif_path,
    ], capture_output=True)
    return os.path.exists(gif_path) and os.path.getsize(gif_path) > 0
