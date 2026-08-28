"""
Sarvam AI Audio Integration Layer (Saaras v3 STT + Bulbul v3 TTS).
Provides authentic Indian code-switching transcription and native voice synthesis.
"""
import os
import time
import base64
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class SarvamAudioClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self.has_key = bool(self.api_key and len(self.api_key) > 5 and not self.api_key.startswith("your_"))
        self.stt_url = "https://api.sarvam.ai/speech-to-text"
        self.tts_url = "https://api.sarvam.ai/text-to-speech"
        self.total_chars_synthesized = 0
        self.total_seconds_transcribed = 0.0

    def transcribe_audio(self, audio_file_path: str, language_code: str = "hi-IN") -> Dict[str, Any]:
        """
        Transcribes speech using Sarvam Saaras v3 code-switching model.
        """
        if not self.has_key:
            return {
                "transcript": "[Simulated STT: Customer responded in Hinglish]",
                "language": language_code,
                "provider": "mock_saaras_v3",
                "simulated": True
            }

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        headers = {"api-subscription-key": self.api_key}
        data = {"model": "saaras:v3", "language_code": language_code}

        for attempt in range(3):
            try:
                with open(audio_file_path, "rb") as f:
                    files = {"file": (os.path.basename(audio_file_path), f, "audio/wav")}
                    resp = requests.post(self.stt_url, headers=headers, data=data, files=files, timeout=20)

                if resp.status_code == 200:
                    payload = resp.json()
                    transcript = payload.get("transcript", "")
                    self.total_seconds_transcribed += 3.0
                    return {
                        "transcript": transcript,
                        "language": language_code,
                        "provider": "sarvam_saaras_v3",
                        "raw": payload
                    }
                elif resp.status_code == 429:
                    sleep_time = (2 ** attempt) * 2
                    print(f"[Sarvam STT] Rate limit (429). Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    print(f"[Sarvam STT] Error {resp.status_code}: {resp.text}")
                    break
            except Exception as e:
                print(f"[Sarvam STT] Network exception: {e}")
                time.sleep(1.5)

        return {
            "transcript": "",
            "language": language_code,
            "provider": "sarvam_error_fallback"
        }

    def synthesize_speech(
        self,
        text: str,
        target_language_code: str = "hi-IN",
        speaker: str = "aditya",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes Hinglish text to speech using Sarvam Bulbul v3.
        """
        self.total_chars_synthesized += len(text)

        if not self.has_key:
            return {
                "audio_bytes": b"",
                "char_count": len(text),
                "speaker": speaker,
                "provider": "mock_bulbul_v3",
                "simulated": True
            }

        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": [text],
            "target_language_code": target_language_code,
            "speaker": speaker,
            "model": "bulbul:v3"
        }

        for attempt in range(3):
            try:
                resp = requests.post(self.tts_url, headers=headers, json=payload, timeout=25)
                if resp.status_code == 200:
                    data = resp.json()
                    if "audios" in data and len(data["audios"]) > 0:
                        audio_bytes = base64.b64decode(data["audios"][0])
                        dest = output_path
                        if dest:
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            with open(dest, "wb") as f:
                                f.write(audio_bytes)
                        return {
                            "audio_bytes": audio_bytes,
                            "audio_path": dest,
                            "char_count": len(text),
                            "speaker": speaker,
                            "provider": "sarvam_bulbul_v3",
                            "size_bytes": len(audio_bytes)
                        }
                elif resp.status_code == 429:
                    sleep_time = (2 ** attempt) * 2
                    print(f"[Sarvam TTS] Rate limit (429). Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    print(f"[Sarvam TTS] Error {resp.status_code}: {resp.text}")
                    break
            except Exception as e:
                print(f"[Sarvam TTS] Network exception: {e}")
                time.sleep(1.5)

        return {
            "audio_bytes": b"",
            "audio_path": None,
            "char_count": len(text),
            "speaker": speaker,
            "provider": "fallback_error"
        }

    def get_usage_metrics(self) -> Dict[str, Any]:
        estimated_cost_inr = (self.total_chars_synthesized / 10000.0) * 30.0 + (self.total_seconds_transcribed / 60.0) * 1.5
        return {
            "total_chars_synthesized": self.total_chars_synthesized,
            "total_seconds_transcribed": round(self.total_seconds_transcribed, 2),
            "estimated_cost_inr": round(estimated_cost_inr, 2)
        }
