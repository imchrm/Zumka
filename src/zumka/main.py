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

STT_HOST = 'stt.api.cloud.yandex.net'
STT_PORT = 443

DEVICE_ID = -1
LANGUAGE_CODE = 'ru-RU' # uz-UZ

AUDIO_ENCODING = stt_pb2.RawAudio.LINEAR16_PCM
AUDIO_CHANNEL_COUNT = 1
TEXT_NORMALIZATION = stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_ENABLED
RESTRICTION_TYPE = stt_pb2.LanguageRestrictionOptions.WHITELIST
AUDIO_PROCESSING_TYPE = stt_pb2.RecognitionModelOptions.REAL_TIME

SAMPLERATE = 8000
CHANNELS = 1
CHUNK_SIZE = 4000 # or block size, it's same
RECORD_SECONDS = 14 # Time limit for recognition process 

audio_queue = queue.Queue()
is_recognition = False

def create_recognition_options(language:str) -> stt_pb2.StreamingOptions:
    """Создает и возвращает конфигурацию для потокового распознавания."""
    audio_encoding = "LINEAR16_PCM" if AUDIO_ENCODING == 1 else "MULAW"
    normalization_enabled = "enabled" if TEXT_NORMALIZATION == 1 else "disabled"
    log.debug("Options of speech recognition: audio encoding: %s, language: %s, text normalization: %s", audio_encoding, language, normalization_enabled)
    return stt_pb2.StreamingOptions(
        recognition_model=stt_pb2.RecognitionModelOptions(
            audio_format=stt_pb2.AudioFormatOptions(
                raw_audio=stt_pb2.RawAudio(
                    audio_encoding=AUDIO_ENCODING,
                    sample_rate_hertz=SAMPLERATE,
                    audio_channel_count=AUDIO_CHANNEL_COUNT,
                ),
            ),
            text_normalization=stt_pb2.TextNormalizationOptions(
                text_normalization=TEXT_NORMALIZATION,
                profanity_filter=True,
                literature_text=False,
            ),
            language_restriction=stt_pb2.LanguageRestrictionOptions(
                restriction_type=RESTRICTION_TYPE,
                language_code=[language],
            ),
            audio_processing_type=AUDIO_PROCESSING_TYPE,
        ),
    )

def gen_mic(config: stt_pb2.StreamingOptions, device_id:int) -> Iterator[stt_pb2.StreamingRequest]:
    """
    Get data from microfone
    """
    global is_recognition, audio_queue
    
    def audio_queue_callback(indata, frames, time, status):
                audio_queue.put(bytes(indata))
    
    # Отправка сообщения с настройками распознавания.
    yield stt_pb2.StreamingRequest(session_options=config)
    chunk_num = SAMPLERATE * RECORD_SECONDS / CHUNK_SIZE
    i = 0
    with sd.RawInputStream(samplerate=SAMPLERATE,
                        blocksize=CHUNK_SIZE,
                        device=device_id,
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
                    log.info("Interrupt on time out: %s seconds", RECORD_SECONDS)
                    is_recognition = False
            except queue.Empty:
                # Если данных нет, просто продолжаем цикл, проверяя is_recognition
                continue

def run_capture_audio_data_from_microphone(api_key: str, device_id: int, language: str) -> None:
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
    
    recognition_config = create_recognition_options(language)
    
    is_recognition = True
    
    it: Iterator[stt_pb2.StreamingResponse] = stub.RecognizeStreaming(
        gen_mic(recognition_config, device_id), 
        metadata=(
        ## Параметры для авторизации с IAM-токеном
        ## ('authorization', f'Bearer {iam_token}'),
    # Параметры для авторизации с API-ключом от имени сервисного аккаунта
        ('authorization', f'Api-Key {api_key}'),
    ))
    was_exception = False
    # Обработка ответов сервера и вывед результата.
    final_prop = 'final'
    final_refinement_prop = 'final_refinement'
    partial_prop = 'partial'
    alternatives_prop = 'alternatives'
    text_prop = 'text'
    
    try:
        response:stt_pb2.StreamingResponse
        for response in it:
            # Checking for the existence of the following properties:
            if hasattr(response, final_prop):
                if hasattr(response.final, alternatives_prop):
                    a = response.final.alternatives
                    if a:
                        if hasattr(a[0], text_prop):
                            log.info('    final %s', a[0].text)
            if hasattr(response, partial_prop):
                if hasattr(response.partial, alternatives_prop):
                    if response.partial.alternatives:
                        if hasattr(response.partial.alternatives[0], text_prop):
                            log.info('    partial %s', response.partial.alternatives[0].text)
            if hasattr(response, final_refinement_prop):
                if hasattr(response.final_refinement, "normalized_text"):
                    if hasattr(response.final_refinement.normalized_text, alternatives_prop):
                        if response.final_refinement.normalized_text.alternatives:
                            if hasattr(response.final_refinement.normalized_text.alternatives[0], text_prop):
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

def get_audio_capture_device_id(device_id: int) ->int:
        id = -1
        name:str = ""
        devices = sd.query_devices()
        log.debug(f"Available list of c/p audio devices:") # c/p where 'c' is capture and 'p' is playback
        if devices:
            for i, device in enumerate(devices):
                name = device.get("name", "") if isinstance(device, dict) else str(device)
                log.debug(f"{i}: {name}")
        if device_id >= len(devices):
            raise ValueError(f"Device with ID {device_id} not found!")
        # Change number of default device to None if device_id == -1
        current_device = sd.query_devices(device_id if device_id != -1 else None, 'input') 
        if current_device:
            name = current_device.get("name", "") if isinstance(current_device, dict) else str(current_device)
            id = current_device.get("index", 0) if isinstance(current_device, dict) else 0
            log.info(f"The device is in use: {name if device_id > -1 else 'Default device id: ' + str(id) + ' name: ' + name}")
            
        log.debug(f"Parameters of speech capturing: "
                f"Samplerate: {SAMPLERATE}, "
                f"Block size: {CHUNK_SIZE}, "
                f"Channels: {CHANNELS}, ")
        return id

def main() -> NoReturn:
    """
    Точка входа в скрипт.
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Stupid, untyped module
    parser = argparse.ArgumentParser(description="Recognize speech from an audio file using Yandex SpeechKit.")

    device_prop = "device"
    language_prop = "language"
    
    parser.add_argument(
        "-d",
        f"--{device_prop}",
        type=int,
        default=DEVICE_ID,
        help=f"Number of microphone. Defaults to {DEVICE_ID}"
    )
    parser.add_argument(
        "-l",
        f"--{language_prop}",
        type=str,
        default=LANGUAGE_CODE,
        help=f"Language code. Defaults to {LANGUAGE_CODE}"
    )

    args = parser.parse_args()
    
    
    device = getattr(args, device_prop, DEVICE_ID)
    language = getattr(args, language_prop, LANGUAGE_CODE)
    
    log.debug("Number of audio capture device: %s and language: %s", device, language)
    
    load_dotenv()
    api_key = os.getenv("YANDEX_API_KEY")
    if not api_key:
        log.error("YANDEX_API_KEY environment variable not set in .env file. Set it and try again.")
        sys.exit(1)
    
    try:
        log.info("Start the speech recognition process \n\
on secure channel: '%s:%s' ...", STT_HOST, STT_PORT)
        run_capture_audio_data_from_microphone(
            api_key, 
            get_audio_capture_device_id(device), 
            language
        )
    except Exception as e:
        log.critical("Critiacal Exception %s", e)
        sys.exit(1)
    log.info("The speech recognition process is complete.")
    sys.exit(0)

if __name__ == '__main__':
    main()
