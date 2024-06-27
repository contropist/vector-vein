# @Author: Bi Ying
# @Date:   2024-06-09 15:53:58
import time
import json
import wave
import threading
from pathlib import Path
from datetime import datetime

import httpx
import pyaudio
import numpy as np
from openai._types import FileTypes

from utilities.general import mprint
from utilities.config import Settings, config


class TTSClient:
    def __init__(self, provider: str = "openai", model: str | None = None):
        self.audio_sample_rate = 24_000

        settings = Settings()
        self.provider = provider

        if self.provider == "openai":
            from utilities.ai_utils import get_openai_client_and_model

            if model is None:
                model = "tts-1"
            self.client, self.model_id = get_openai_client_and_model(is_async=False, model_id=model)
        elif self.provider == "minimax":
            if model is None:
                model = "speech-01"
            self.api_key = settings.minimax_api_key
            self.model_id = model
        elif self.provider == "piper":
            self.api_base = settings.get("tts.piper.api_base")
            self.model_id = model

    def create(self, text: str, voice: str | None = None, output_folder: str | None = None):
        datetime_string = datetime.now().strftime("%Y%m%d%H%M%S")
        if output_folder is None:
            audio_path = Path(config.data_path) / "audio"
            audio_path.mkdir(parents=True, exist_ok=True)
            output_file_path = audio_path / f"{datetime_string}.mp3"
        else:
            output_file_path = Path(output_folder) / f"{datetime_string}.mp3"

        if self.provider == "openai":
            response = self.client.audio.speech.create(model=self.model_id, voice=voice, input=text)
            response.write_to_file(output_file_path)
            return output_file_path
        elif self.provider == "minimax":
            url = "https://api.minimax.chat/v1/text_to_speech"
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self.api_key}",
            }
            data = {
                "voice_id": voice,
                "text": "你好",
                "model": self.model_id,
                "speed": 1.0,
                "vol": 1.0,
                "pitch": 0,
            }
            response = httpx.post(url, headers=headers, json=data)
            if response.status_code != 200 or "json" in response.headers["Content-Type"]:
                mprint.error("Minimax TTS failed", response.status_code, response.text)
                return None
            with open(output_file_path, "wb") as f:
                f.write(response.content)
            return output_file_path

    def _stream_audio(self, text: str, voice: str | None):
        p = pyaudio.PyAudio()
        stream = p.open(format=8, channels=1, rate=self.audio_sample_rate, output=True)
        if self.provider == "openai":
            with self.client.audio.speech.with_streaming_response.create(
                model=self.model_id, voice=voice, input=text, response_format="pcm"
            ) as response:
                for chunk in response.iter_bytes(1024):
                    stream.write(chunk)
        elif self.provider == "minimax":
            url = "https://api.minimax.chat/v1/tts/stream"
            headers = {
                "accept": "application/json, text/plain, */*",
                "content-type": "application/json",
                "authorization": f"Bearer {self.api_key}",
            }
            body = {
                "voice_id": voice,
                "text": text,
                "model": self.model_id,
                "speed": 1,
                "vol": 1,
                "pitch": 0,
                "audio_sample_rate": self.audio_sample_rate,
                "bitrate": 128000,
                "format": "pcm",
            }
            with httpx.stream("POST", url, headers=headers, json=body) as response:
                for chunk in response.iter_lines():
                    if not chunk.startswith("data:"):
                        continue
                    data = json.loads(chunk[5:])
                    if "data" not in data or "extra_info" not in data:
                        continue
                    if "audio" in data["data"]:
                        audio = bytes.fromhex(data["data"]["audio"])
                        stream.write(audio)
        elif self.provider == "piper":
            headers = {"content-type": "text/plain"}
            with httpx.stream("POST", self.api_base, headers=headers, data=text) as response:
                for chunk in response.iter_bytes():
                    stream.write(chunk)

        stream.stop_stream()
        stream.close()
        p.terminate()

    def stream(self, text: str, voice: str | None = None, non_block: bool = False):
        if non_block:
            thread = threading.Thread(target=self._stream_audio, args=(text, voice))
            thread.start()
            return thread
        else:
            self._stream_audio(text, voice)
            return True


class SpeechRecognitionClient:
    def __init__(self, provider: str = "openai", model: str = "whisper-1"):
        self.provider = provider

        if self.provider == "openai":
            from utilities.ai_utils import get_openai_client_and_model

            self.client, self.model_id = get_openai_client_and_model(is_async=False, model_id=model)

    def batch_transcribe(self, files: list, output_type: str = "text"):
        outputs = []
        for file_data in files:
            outputs.append(self.transcribe(file_data, output_type))
        return outputs

    def transcribe(self, file: FileTypes, output_type: str = "text"):
        if output_type == "text":
            transcription = self.client.audio.transcriptions.create(
                model=self.model_id, file=file, response_format="text"
            )
            return transcription
        elif output_type == "list":
            transcription = self.client.audio.transcriptions.create(
                model=self.model_id,
                file=file,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
            return [segment["text"] for segment in transcription.segments]
        elif output_type == "srt":
            transcription = self.client.audio.transcriptions.create(
                model=self.model_id, file=file, response_format="srt"
            )
            return transcription


class Microphone:
    def __init__(self, device_index: int = 0, output_folder: str | Path | None = None):
        self.chunk = 1024
        self.sample_format = pyaudio.paInt16
        self.channels = 1
        self.fs = 44100
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.is_recording = False
        self.thread = None
        self.device_index = device_index
        self.latest_saved_file = ""
        self._stop_signal = threading.Event()
        self._sound_player = SoundPlayer()
        if output_folder is None:
            self.output_folder = Path(config.data_path) / "audio"
            self.output_folder.mkdir(parents=True, exist_ok=True)
        else:
            self.output_folder = Path(output_folder)

    def start(self, auto_stop=False, silence_threshold: int | None = None, silence_duration=2):
        self.auto_stop = auto_stop
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.silence_buffer = 0
        self.__start_recording_time = time.time()
        self.__latest_chunks_amplitude = []
        self.__max_recording_amplitude = 0
        self._stop_signal.clear()

        if not self.is_recording:
            self.is_recording = True
            self.frames = []
            self.stream = self.p.open(
                format=self.sample_format,
                channels=self.channels,
                rate=self.fs,
                frames_per_buffer=self.chunk,
                input=True,
                input_device_index=self.device_index,
            )
            self._sound_player.play("recording-start.wav")
            self.thread = threading.Thread(target=self._record)
            self.thread.start()

    def stop(self):
        if self.is_recording:
            self.is_recording = False
            self._stop_signal.set()
            self.thread.join()
            self._sound_player.play("recording-end.wav")
            return self._stop_stream()

    def _stop_stream(self):
        self.stream.stop_stream()
        self.stream.close()
        self.latest_saved_file = self._save_to_file()
        return self.latest_saved_file

    def _record(self):
        while self.is_recording and not self._stop_signal.is_set():
            data = self.stream.read(self.chunk)
            self.frames.append(data)

            if self.auto_stop:
                audio_data = np.frombuffer(data, dtype=np.int16)
                max_amplitude = np.max(np.abs(audio_data))
                if max_amplitude > self.__max_recording_amplitude:
                    self.__max_recording_amplitude = max_amplitude
                self.__latest_chunks_amplitude.append(max_amplitude)
                if len(self.__latest_chunks_amplitude) > self.silence_duration:
                    self.__latest_chunks_amplitude.pop(0)
                latest_chunks_average_amplitude = np.mean(self.__latest_chunks_amplitude)

                if time.time() - self.__start_recording_time < 2:
                    continue

                threshold = (
                    self.__max_recording_amplitude * 0.3 if self.silence_threshold is None else self.silence_threshold
                )

                if latest_chunks_average_amplitude < threshold:
                    self.silence_buffer += 1
                else:
                    self.silence_buffer = 0

                if self.silence_buffer > (self.fs / self.chunk) * self.silence_duration:
                    self._stop_signal.set()

        self.is_recording = False
        self._stop_stream()

    def _save_to_file(self):
        datetime_string = datetime.now().strftime("%Y%m%d%H%M%S")
        self.output_file = self.output_folder / f"{datetime_string}.wav"
        wf = wave.open(str(self.output_file.resolve()), "wb")
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.sample_format))
        wf.setframerate(self.fs)
        wf.writeframes(b"".join(self.frames))
        wf.close()
        return str(self.output_file.resolve())

    def list_devices(self):
        device_count = self.p.get_device_count()
        devices = []
        for i in range(device_count):
            info = self.p.get_device_info_by_index(i)
            if info.get("maxInputChannels") > 0:
                devices.append(
                    {"index": i, "name": info.get("name"), "maxInputChannels": info.get("maxInputChannels")}
                )
        return devices

    def set_device(self, device_index):
        self.device_index = device_index


class SoundPlayer:
    def __init__(self, sound_folder: str | Path = "./assets/sound/"):
        self.sound_folder = Path(sound_folder)
        self.p = pyaudio.PyAudio()

    def play(self, sound_name: str, non_block: bool = True):
        sound_path = self.sound_folder / sound_name
        if not sound_path.exists():
            mprint.error(f"Sound file {sound_path} not found.")
            return

        if non_block:
            thread = threading.Thread(target=self._play_sound, args=(sound_path,))
            thread.start()
            return thread
        else:
            self._play_sound(sound_path)
            return True

    def _play_sound(self, sound_path: str | Path):
        sound_path = Path(sound_path)
        mprint(sound_path)
        wf = wave.open(str(sound_path.resolve()), "rb")
        stream = self.p.open(
            format=self.p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True,
        )

        data = wf.readframes(1024)
        while data:
            stream.write(data)
            data = wf.readframes(1024)

        stream.stop_stream()
        stream.close()
        wf.close()

    def __del__(self):
        self.p.terminate()