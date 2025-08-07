# [Yandex SpeechKit v3 Streaming STT Example](https://yandex.cloud/ru/docs/speechkit/stt/api/streaming-examples-v3)
This project demonstrates how to use the Yandex Cloud SpeechKit v3 API for streaming speech-to-text recognition.

Authentication is handled via a service account API key.

## Prerequisites

- Python 3.8+
- [Poetry](https://python-poetry.org/) for dependency management.

## Setup and Installation

Follow these steps to set up the project environment.

**1. Clone the repository:**

```bash
git clone https://github.com/imchrm/Zumka.git
cd zumka
```

**2. Initialize Dependencies:**

This project uses some Python dependecies which pointed in `pyproject.toml` file. To download them, and install the Python packages, run the following command in root directory of the project:
```bash
poetry install
```

**3. Generate gRPC Client Code for Yandex Cloud API:**

The gRPC client code (stub files) must be generated from the .proto files. All necessary .proto files you must add from [yandex-cloud/cloudapi/](https://github.com/yandex-cloud/cloudapi.git) repo.

  1. ***Управление зависимостями с помощью Git Submodule***

* Чтобы не хранить код стороннего репозитария yandex-cloud/cloudapi напрямую в нашем локальном репозитории проекта, мы используем git submodule. Это позволяет нам ссылаться на конкретную версию (коммит) cloudapi, сохраняя наш репозиторий чистым и упрощая обновления.
* Добавьте (склонируйте) репозиторий Yandex Cloud API, как submodule в ваш проект в папку `src/cloudapi`:

  ```bash
  git submodule add https://github.com/yandex-cloud/cloudapi.git src/cloudapi
  ```

  Чтобы в дальнейшем иметь последнюю версию файлов из репозитория yandex-cloud/cloudapi обновите его локальное содержимое командой: 
  
  ```bash
  git submodule update --init --recursive
  ```

  2. ***Generation of Python files (\*.py) and stub files (\*.pyi) from .proto.***

  Из корня проекта `zumka` выполните команду:

  ```bash
  python3 -m grpc_tools.protoc -I . -I src/cloudapi/third_party/googleapis \
    --python_out=src \
    --mypy_out=src \
    --grpc_python_out=src \
    --mypy_grpc_out=src \
      google/api/http.proto \
      google/api/annotations.proto \
      yandex/cloud/api/operation.proto \
      google/rpc/status.proto \
      yandex/cloud/operation/operation.proto \
      yandex/cloud/validation.proto \
      yandex/cloud/ai/stt/v3/stt_service.proto \
      yandex/cloud/ai/stt/v3/stt.proto
  ```
  В корне вашего проекта `zumka` будут созданы две папки: `/src/google` и `/src/yandex`, которые будут содержать внутри себя сгенерированные Python файлы (\*.py) с классами для работы по gRPC с Yandex SpeechKit API и stub-файлы (\*.pyi) с описанием интерфейса.  

## Configuration

To use the API, you need to authenticate with Yandex Cloud.

1. Follow the official documentation to create [a service account](https://yandex.cloud/ru/docs/iam/operations/sa/create).
2. Assign the ai.speechkit-stt.user role (or a higher one) to it.
3. Get an [API key](https://yandex.cloud/ru/docs/iam/concepts/authorization/api-key) for the service account or [IAM-token](https://yandex.cloud/ru/docs/iam/concepts/authorization/iam-token).
4. Add API key as parameter YANDEX_API_KEY in `.env` file in root directory of the project.

## Usage

Capture of speech data from a microphone.
Launch the application.
```bash
poetry run python -m zumka.main
```
<!-- By default zumka.main is using constant `AUDIO_PATH = "assets/sound/speech_00.pcm"` for speech recognition. -->

