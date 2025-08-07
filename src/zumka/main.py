#coding=utf8

import argparse
from ast import Dict, Set
from ctypes import Array
import sys
import logging
import os
from pathlib import Path
from typing import Iterator, NoReturn

import sounddevice as sd
import queue

import grpc
from dotenv import load_dotenv

from yandex.cloud.ai.stt.v3 import stt_pb2
from yandex.cloud.ai.stt.v3 import stt_service_pb2_grpc

log = logging.getLogger("Test")

DEVICE_ID = None
SAMPLERATE = 8000
# BLOCK_SIZE = 4000
CHANNELS = 1
CHUNK_SIZE = 4000
RECORD_SECONDS = 14

AUDIO_PATH = "assets/sound/speech_00.pcm"
STT_HOST = 'stt.api.cloud.yandex.net'
STT_PORT = 443

audio_queue = queue.Queue()
is_recognition = False

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

def gen_mic(config: stt_pb2.StreamingOptions) -> Iterator[stt_pb2.StreamingRequest]:
    """
    Get data from microfone
    """
    global is_recognition, audio_queue
    
    def audio_queue_callback(indata, frames, time, status):
                audio_queue.put(bytes(indata))
    
    # Отправьте сообщение с настройками распознавания.
    yield stt_pb2.StreamingRequest(session_options=config)
    chunk_num = SAMPLERATE * RECORD_SECONDS / CHUNK_SIZE
    i = 0
    with sd.RawInputStream(samplerate=SAMPLERATE, 
                        blocksize=CHUNK_SIZE, 
                        device=DEVICE_ID, 
                        dtype='int16', 
                        channels=CHANNELS, 
                        callback=audio_queue_callback):
        while is_recognition:
            try:
                # Block until get audio data
                data = audio_queue.get(timeout=0.1) # таймаут, чтобы цикл мог завершиться
                yield stt_pb2.StreamingRequest(chunk=stt_pb2.AudioChunk(data=data))
                i += 1
                if i == chunk_num:
                    is_recognition = False
            except queue.Empty:
                # Если данных нет, просто продолжаем цикл, проверяя is_recognition
                continue

def run_capture_audio_data_from_micrphone(api_key: str) -> None:
    """
    Запускает процесс потокового распознавания речи.
    
    Args:
        api_key: API-ключ сервисного аккаунта.
    """
    global is_recognition
    # Установка соединение с сервером.
    cred = grpc.ssl_channel_credentials()
    channel = grpc.secure_channel(f'{STT_HOST}:{STT_PORT}', cred)
    stub = stt_service_pb2_grpc.RecognizerStub(channel)
    
    recognition_config = create_recognition_config()
    
    is_recognition = True
    
    it: Iterator[stt_pb2.StreamingResponse] = stub.RecognizeStreaming(
        gen_mic(recognition_config), 
        metadata=(
        ## Параметры для авторизации с IAM-токеном
        ## ('authorization', f'Bearer {iam_token}'),
    # Параметры для авторизации с API-ключом от имени сервисного аккаунта
        ('authorization', f'Api-Key {api_key}'),
    ))
    was_exception = False
    # Обработайте ответы сервера и выведите результат в консоль.
    evn_final = 'final'
    evn_final_refinement = 'final_refinement'
    evn_partial = 'partial'
    prop_alternatives = 'alternatives'
    prop_text = 'text'
    try:
        
        response:stt_pb2.StreamingResponse
        for response in it:
            # Checking for the existence of the following properties:
            # response.final.alternatives[0].text
            # response.partial.alternatives[0].text
            # response.final_refinement.normalized_text.alternatives[0].text
            # response.eou_update.time_ms
            # if hasattr(response, "eou_update"):
            #     if response.eou_update:
            #         log.info("EOU upd t:%s", response.eou_update.time_ms)
            
            if hasattr(response, evn_final):
                if hasattr(response.final, prop_alternatives):
                    a = response.final.alternatives
                    if a:
                        if hasattr(a[0], prop_text):
                            log.info('    final %s', a[0].text)
            if hasattr(response, evn_partial):
                if hasattr(response.partial, prop_alternatives):
                    if response.partial.alternatives:
                        if hasattr(response.partial.alternatives[0], prop_text):
                            log.info('    partial %s', response.partial.alternatives[0].text)
            if hasattr(response, evn_final_refinement):
                if hasattr(response.final_refinement, "normalized_text"):
                    if hasattr(response.final_refinement.normalized_text, prop_alternatives):
                        if response.final_refinement.normalized_text.alternatives:
                            if hasattr(response.final_refinement.normalized_text.alternatives[0], prop_text):
                                log.info('    final_refinement %s', response.final_refinement.normalized_text.alternatives[0].text)
                                
    except KeyboardInterrupt:
        log.info("User interruption by Ctrl+C")
    except grpc.RpcError as err:
        log.error("gRPC error: %s", err)
        # Проверяем статус-код. Например, `StatusCode.UNAUTHENTICATED`
        if err.code() == grpc.StatusCode.UNAUTHENTICATED:
            log.error("Authentication failed. Please check your API key.")
        was_exception = True
        # Можно добавить обработку других кодов
    except Exception as e:
        log.error(f'Error: {e}')
        was_exception = True
        
    finally:
        is_recognition = False
        channel.close()
        log.info("Secure channel on: '%s:%s' was closed.", STT_HOST, STT_PORT)
        if was_exception:
            sys.exit(1)

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
    # Установка соединение с сервером.
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

    was_exception = False
    # Обработайте ответы сервера и выведите результат в консоль.
    try:
        response:stt_pb2.StreamingResponse
        for response in it:
            event_type = response.WhichOneof('Event') # partial, final, final_refinement
            if not event_type:
                continue

            event = getattr(response, event_type) # r
            alternatives_source = None

            if event_type in ('partial', 'final'):
                alternatives_source = event.alternatives
            elif event_type == 'final_refinement':
                alternatives_source = event.normalized_text.alternatives

            alternatives = [a.text for a in alternatives_source] if alternatives_source else None
            
            if alternatives:
                log.info('type=%s, alternatives=%s', event_type, alternatives)
                
    except grpc.RpcError as err:
        log.error("gRPC error: %s", err)
        # Проверяем статус-код. Например, `StatusCode.UNAUTHENTICATED`
        if err.code() == grpc.StatusCode.UNAUTHENTICATED:
            log.error("Authentication failed. Please check your API key.")
        was_exception = True
        # Можно добавить обработку других кодов
    except Exception as e:
        log.error(f'Error: {e}')
        was_exception = True
        
    # except grpc.Channel._Rendezvous as err:
    #     log.error(f'Error code {err._state.code}, message: {err._state.details}')
    finally:
        channel.close()
        log.info(f"f'Secure channel on:{STT_HOST}:{STT_PORT}' was closed.")
        if was_exception:
            sys.exit(1)

def _check_capture_device(device_id):
        devices = sd.query_devices()
        name:str = ""
        log.debug(f"Available speech capture devices:")
        if devices:
            for i, device in enumerate(devices):
                name = device.get("name", "") if isinstance(device, dict) else str(device)
                log.info(f"{i}: {name}")
        if device_id is not None and device_id >= len(devices):
            log.error(f"Device with ID {device_id} not found!")
            exit(1)
        current_device = sd.query_devices(device_id, 'input')
        if current_device:
            name = current_device.get("name", "") if isinstance(current_device, dict) else str(current_device)
            log.debug(f"The device is in use: {name if device_id else 'Default device: ' + name}")
            
        log.debug(f"Parameters of speech capturing: "
                f"Samplerate: {SAMPLERATE}, "
                f"Block size: {CHUNK_SIZE}, "
                f"Channels: {CHANNELS}, ")

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
        log.error("Audio file not found at: %s", audio_path)
        sys.exit(1)

    _check_capture_device(DEVICE_ID)
    
    # log.info("Processing speech file: %s", audio_path)
    # run(api_key, {audio_path}")
    # run(api_key, str(audio_path))
    try:
        log.info("Start the speech recognition process...")
        run_capture_audio_data_from_micrphone(api_key)
    except Exception as e:
        log.critical("Critiacal Exception %s", e)
        sys.exit(1)
    log.info("The speech recognition process is complete.")
    sys.exit(0)

if __name__ == '__main__':
    main()
