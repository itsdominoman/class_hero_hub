import subprocess

import pytest

from app import message_voice_service as voice


def _audio_bytes(tmp_path, *, duration: float = 1.2, extension: str = "wav") -> bytes:
    target = tmp_path / f"tone.{extension}"
    result = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            str(duration),
            str(target),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    return target.read_bytes()


def test_normalizes_audio_to_bounded_metadata_free_aac_mp4(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "MESSAGE_MEDIA_ROOT", tmp_path / "media")
    raw = _audio_bytes(tmp_path)

    normalized, duration_ms = voice.normalize_voice_note(raw)

    output = tmp_path / "normalized.m4a"
    output.write_bytes(normalized)
    probe = voice._probe(output)
    audio = [row for row in probe["streams"] if row["codec_type"] == "audio"]
    assert len(audio) == 1
    assert audio[0]["codec_name"] == "aac"
    assert "mp4" in probe["format"]["format_name"]
    assert 1_100 <= duration_ms <= 1_300
    assert len(normalized) < len(raw)
    assert not list((tmp_path / "media" / ".processing").glob("voice-*"))


@pytest.mark.parametrize("raw", [b"", b"not-audio"])
def test_rejects_empty_or_malformed_audio(monkeypatch, tmp_path, raw):
    monkeypatch.setattr(voice, "MESSAGE_MEDIA_ROOT", tmp_path / "media")
    with pytest.raises(voice.MessageVoiceValidationError):
        voice.normalize_voice_note(raw)


def test_rejects_too_short_and_oversized_audio(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "MESSAGE_MEDIA_ROOT", tmp_path / "media")
    with pytest.raises(voice.MessageVoiceValidationError, match="too short"):
        voice.normalize_voice_note(_audio_bytes(tmp_path, duration=0.2))
    with pytest.raises(voice.MessageVoiceValidationError, match="too large"):
        voice.normalize_voice_note(b"0" * (voice.MAX_RAW_AUDIO_BYTES + 1))


def test_rejects_video_even_when_it_contains_audio(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "MESSAGE_MEDIA_ROOT", tmp_path / "media")
    target = tmp_path / "video.mp4"
    result = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=32x32:r=5",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            "1",
            "-c:v",
            "mpeg4",
            "-c:a",
            "aac",
            str(target),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    with pytest.raises(voice.MessageVoiceValidationError, match="audio only"):
        voice.normalize_voice_note(target.read_bytes())


def test_rejects_source_duration_above_three_minutes(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "MESSAGE_MEDIA_ROOT", tmp_path / "media")
    monkeypatch.setattr(
        voice,
        "_probe",
        lambda _path: {
            "streams": [{"index": 0, "codec_type": "audio", "codec_name": "opus", "duration": "181.0"}],
            "format": {"format_name": "webm", "duration": "181.0"},
        },
    )
    with pytest.raises(voice.MessageVoiceValidationError, match="3 minute"):
        voice.normalize_voice_note(b"audio-shaped-for-probe-stub")
