"""
Checks that text-to-speech actually works on THIS machine before you rely
on the bot's 🔊 button.

Run it on the VPS:

    source venv/bin/activate
    python3 check_tts.py

It tries the configured engine, reports the size of the audio it produced,
and checks whether ffmpeg is available for Telegram voice messages.

Why this exists: both TTS backends talk to undocumented endpoints that can
be blocked or changed without notice. This tells you in ten seconds whether
the problem is the network, the engine, or the bot.
"""
import asyncio
import os
import shutil
import subprocess
import sys

SAMPLE = "修理"  # a real word from the bot's vocabulary
ENGINE = os.getenv("TTS_ENGINE", "edge").lower()
VOICE = os.getenv("TTS_VOICE", "ja-JP-NanamiNeural")


async def try_edge(path):
    import edge_tts
    communicate = edge_tts.Communicate(SAMPLE, VOICE)
    await communicate.save(path)


def try_gtts(path):
    from gtts import gTTS
    gTTS(SAMPLE, lang="ja").save(path)


def main():
    print(f"Engine:  {ENGINE}")
    print(f"Sample:  {SAMPLE}")
    print()

    out = "/tmp/tts_check.mp3"
    if os.path.exists(out):
        os.remove(out)

    # --- engine ---
    try:
        if ENGINE == "edge":
            asyncio.run(try_edge(out))
        else:
            try_gtts(out)
    except ImportError as e:
        print(f"❌ Library missing: {e}")
        print("   Install it:  pip install edge-tts   (or: pip install gTTS)")
        return 1
    except Exception as e:
        print(f"❌ {ENGINE} failed: {type(e).__name__}: {e}")
        print()
        print("   Try the other engine:")
        other = "gtts" if ENGINE == "edge" else "edge"
        print(f"     TTS_ENGINE={other} python3 check_tts.py")
        print("   If both fail, the droplet probably can't reach the TTS")
        print("   endpoint — check outbound network/firewall.")
        return 1

    size = os.path.getsize(out) if os.path.exists(out) else 0
    if size == 0:
        print(f"❌ {ENGINE} ran but produced no audio.")
        return 1
    print(f"✅ {ENGINE} produced {size} bytes of audio → {out}")

    # --- ffmpeg (needed for proper Telegram voice messages) ---
    print()
    if not shutil.which("ffmpeg"):
        print("⚠️  ffmpeg not installed.")
        print("   The bot still works — it sends MP3 as an audio file instead")
        print("   of a voice bubble. For the nicer voice-message look:")
        print("     apt install ffmpeg")
        return 0

    ogg = "/tmp/tts_check.ogg"
    result = subprocess.run(
        ["ffmpeg", "-i", out, "-c:a", "libopus", "-b:a", "32k", "-y", ogg],
        capture_output=True
    )
    if result.returncode == 0 and os.path.getsize(ogg) > 0:
        print(f"✅ ffmpeg converted it to OGG/OPUS ({os.path.getsize(ogg)} bytes)")
        print("   Voice messages will render as proper voice bubbles.")
    else:
        print("⚠️  ffmpeg is installed but the conversion failed.")
        print("   The bot will fall back to sending MP3 audio files.")

    print()
    print("All good — the 🔊 button should work.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
