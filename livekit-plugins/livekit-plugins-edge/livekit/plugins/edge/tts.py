# Copyright 2023 LiveKit, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from livekit import rtc
from livekit.agents import tts, utils

from .log import logger
from .models import AudioEncoding, Gender, SpeechLanguages

import edge_tts

LgType = Union[SpeechLanguages, str]
GenderType = Union[Gender, str]
AudioEncodingType = Union[AudioEncoding, str]


@dataclass
class _TTSOptions:
    voice: str
    rate: str
    volume: str
    pitch: str


class TTS(tts.TTS):
    def __init__(
        self,
        *,
        language: LgType = "en-US",
        gender: GenderType = "neutral",
        voice_name: str = "",  # Not required
        encoding: AudioEncodingType = "linear16",
        sample_rate: int = 24000,
        speaking_rate: float = 1.0,
    ) -> None:
        """
        Create a new instance of Edge TTS.
        """

        super().__init__(
            capabilities=tts.TTSCapabilities(
                streaming=False,
            ),
            sample_rate=sample_rate,
            num_channels=1,
        )

        self._client = edge_tts.Communicate()

        voice = voice_name if voice_name else f"{language}-{gender}"

        self._opts = _TTSOptions(
            voice=voice,
            rate=f"{speaking_rate:.2f}%",
            volume="0%",
            pitch="0%"
        )

    def synthesize(self, text: str) -> "ChunkedStream":
        return ChunkedStream(text, self._opts, self._client)


class ChunkedStream(tts.ChunkedStream):
    def __init__(
        self, text: str, opts: _TTSOptions, client: edge_tts.Communicate
    ) -> None:
        super().__init__()
        self._text, self._opts, self._client = text, opts, client

    @utils.log_exceptions(logger=logger)
    async def _main_task(self) -> None:
        request_id = utils.shortuuid()
        segment_id = utils.shortuuid()
        audio_stream = await self._client.run(
            self._text,
            voice=self._opts.voice,
            rate=self._opts.rate,
            volume=self._opts.volume,
            pitch=self._opts.pitch
        )

        async for data in audio_stream:
            if isinstance(data, bytes):
                self._event_ch.send_nowait(
                    tts.SynthesizedAudio(
                        request_id=request_id, segment_id=segment_id, frame=data
                    )
                )

