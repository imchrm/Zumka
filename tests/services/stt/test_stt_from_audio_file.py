#coding=utf8

import argparse
import sys
import logging
import os
from pathlib import Path
from typing import Iterator, NoReturn

import grpc
from dotenv import load_dotenv

from yandex.cloud.ai.stt.v3 import stt_pb2
from yandex.cloud.ai.stt.v3 import stt_service_pb2_grpc

log = logging.getLogger("Test")

CHUNK_SIZE = 4000
AUDIO_PATH = "assets/sound/speech_00.pcm"
STT_HOST = 'stt.api.cloud.yandex.net'
STT_PORT = 443

def create_recognition_config() -> stt_pb2.StreamingOptions:
    """Создает и возвращает конфигурацию для потокового распознавания."""
    return stt_pb2.StreamingOptions(
        recognition_model=stt_pb2.RecognitionModelOptions(
            audio_format=stt_pb2.AudioFormatOptions(
                raw_audio=stt_pb2.RawAudio(
                    audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
                    sample_rate_hertz=8000,
                    audio_channel_count=1,
                ),
            ),
            text_normalization=stt_pb2.TextNormalizationOptions(
                text_normalization=stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_ENABLED,
                profanity_filter=True,
                literature_text=False,
            ),
            language_restriction=stt_pb2.LanguageRestrictionOptions(
                restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
                language_code=['ru-RU'],
            ),
            audio_processing_type=stt_pb2.RecognitionModelOptions.REAL_TIME,
        ),
    )

def gen(config: stt_pb2.StreamingOptions, audio_file_name: str) -> Iterator[stt_pb2.StreamingRequest]:
    """
    Генератор, который сначала отправляет настройки, а затем аудиоданные по частям.

    Args:
        config: Конфигурация для сессии распознавания.
        audio_file_name: Путь к аудиофайлу для распознавания.

    Yields:
        Объекты StreamingRequest для отправки на сервер.
    """
    # Отправьте сообщение с настройками распознавания.
    yield stt_pb2.StreamingRequest(session_options=config)

    # Прочитайте аудиофайл и отправьте его содержимое порциями.
    with open(audio_file_name, 'rb') as f:
        data = f.read(CHUNK_SIZE)
        while data != b'':
            yield stt_pb2.StreamingRequest(chunk=stt_pb2.AudioChunk(data=data))
            data = f.read(CHUNK_SIZE)

# Вместо iam_token передавайте api_key при авторизации с API-ключом
# от имени сервисного аккаунта.
def run(api_key: str, audio_file_path: str) -> None:  # noqa: C901
    """
    Запускает процесс потокового распознавания речи.

    Args:
        api_key: API-ключ сервисного аккаунта.
        audio_file_path: Путь к аудиофайлу для распознавания.
    """
    # Установите соединение с сервером.
    cred = grpc.ssl_channel_credentials()
    channel = grpc.secure_channel(f'{STT_HOST}:{STT_PORT}', cred)
    stub = stt_service_pb2_grpc.RecognizerStub(channel)

    recognition_config = create_recognition_config()
    # Отправьте данные для распознавания.
    it: Iterator[stt_pb2.StreamingResponse] = stub.RecognizeStreaming(gen(recognition_config, audio_file_path), metadata=(
        ## Параметры для авторизации с IAM-токеном
        ## ('authorization', f'Bearer {iam_token}'),
    # Параметры для авторизации с API-ключом от имени сервисного аккаунта
        ('authorization', f'Api-Key {api_key}'),
    ))

    # Обработайте ответы сервера и выведите результат в консоль.
    try:
        for r in it:
            event_type = r.WhichOneof('Event')
            if not event_type:
                continue

            event = getattr(r, event_type)
            alternatives_source = None

            if event_type in ('partial', 'final'):
                alternatives_source = event.alternatives
            elif event_type == 'final_refinement':
                alternatives_source = event.normalized_text.alternatives

            alternatives = [a.text for a in alternatives_source] if alternatives_source else []
            if alternatives:
                log.info('type=%s, alternatives=%s', event_type, alternatives)

    except grpc.RpcError as err:
        log.error("gRPC error: %s", err)
        # Проверяем статус-код. Например, `StatusCode.UNAUTHENTICATED`
        if err.code() == grpc.StatusCode.UNAUTHENTICATED:
            log.error("Authentication failed. Please check your API key.")
        # Можно добавить обработку других кодов
        sys.exit(1)

def main() -> NoReturn:
    """
    Точка входа в скрипт.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Recognize speech from an audio file using Yandex SpeechKit.")
    parser.add_argument(
        "audio_file",
        type=Path,
        nargs='?',
        default=Path(AUDIO_PATH),
        help=f"Path to the audio file (LPCM, 8kHz, 16-bit, mono). Defaults to {AUDIO_PATH}"
    )
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("YANDEX_API_KEY")
    if not api_key:
        log.error("YANDEX_API_KEY environment variable not set.")
        sys.exit(1)

    audio_path = args.audio_file
    if not audio_path.is_file():
        log.error(f"Audio file not found at: {audio_path}")
        sys.exit(1)

    log.info(f"Processing speech file: {audio_path}")
    run(api_key, str(audio_path))
    sys.exit(0)

if __name__ == '__main__':
    main()
