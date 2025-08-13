# [Yandex SpeechKit v3 Streaming STT Example](https://yandex.cloud/ru/docs/speechkit/stt/api/streaming-examples-v3)
This project demonstrates how to use the Yandex Cloud SpeechKit v3 API for streaming speech-to-text recognition.

Authentication is handled via a service account API key.

## Prerequisites

- Python 3.8+
- [Poetry](https://python-poetry.org/) for dependency management.

## Setup and Installation

Follow these steps to set up the project environment.

**1. Clone the repository:**
  Чтобы не хранить код стороннего репозитария yandex-cloud/cloudapi напрямую в нашем локальном репозитории проекта, мы используем git submodule. Это позволяет нам ссылаться на конкретную версию (коммит) cloudapi, сохраняя наш репозиторий чистым и упрощая обновления.
  ***a) Для клонирования проекта и всех необходимых зависимостей (submodules) используйте команду:***
  ```bash
  git clone --recurse-submodules https://github.com/imchrm/Zumka.git
  cd zumka
  ```
  
  ***b) Если вы уже склонировали проект (без submodules):***
  
  Если вы ранее клонировали проект без флага `--recurse-submodules`, перейдите в его директорию и выполните команду для загрузки submodules:
  ```bash
  git submodule update --init
  ```

**2. Initialize Dependencies:**

This project uses some Python dependecies which pointed in `pyproject.toml` file. To download them, and install the Python packages, run the following command in root directory of the project:
```bash
poetry install
```

**3. Generate gRPC Client Code for Yandex Cloud API:**

The gRPC client code (stub files) must be generated from the .proto files. All necessary Python and stub-files, you must generate and run the following command in the root directory of the project (recommended):
```bash
poetry run generate-protos
```
This command will run python script `generated_protos.py` which generate \*.py and \*.pyi files from \*.proto files placed inside `src/cloudapi/` folder. The needed parameter `generate-protos` for Poetry was written inside the `pyproject.toml` file.

Or you can directly execute the generate command in the Linux terminal (not recomended):
  ```bash
  python3 -m grpc_tools.protoc -I src/cloudapi -I src/cloudapi/third_party/googleapis \
    --python_out=src \
    --mypy_out=src \
    --grpc_python_out=src \
    --mypy_grpc_out=src \
      google/api/http.proto \
      google/api/annotations.proto \
      google/rpc/status.proto \
      yandex/cloud/api/operation.proto \
      yandex/cloud/operation/operation.proto \
      yandex/cloud/validation.proto \
      yandex/cloud/ai/stt/v3/stt_service.proto \
      yandex/cloud/ai/stt/v3/stt.proto
  ```
  For Wimdows OS you must replace each symbol `\` on `` ` ``

  После запуска команды в корне вашего проекта `zumka` будут созданы две папки: `/src/google` и `/src/yandex`, которые будут содержать внутри себя сгенерированные Python файлы (\*.py) с классами для работы по gRPC с Yandex SpeechKit API и stub-файлы (\*.pyi) с определениями классов и типов вызываемых свойств и методов.

## Configuration

To use the API, you need to authenticate with Yandex Cloud.

1. Follow the official documentation to create [a service account](https://yandex.cloud/ru/docs/iam/operations/sa/create).
2. Assign the ai.speechkit-stt.user role (or a higher one) to it.
3. Get an [API key](https://yandex.cloud/ru/docs/iam/concepts/authorization/api-key) for the service account or [IAM-token](https://yandex.cloud/ru/docs/iam/concepts/authorization/iam-token).
4. Add API key as parameter YANDEX_API_KEY in `.env` file in root directory of the project.

## Usage

Capture of speech data from a microphone.

You can add some arguments:
  * `--device (-d)` - number of capture audio device (defaults to `-1` it means default audio capture device)
  * `--language (-l)` - language code like: ru-RU, en-US, uz-UZ etc. (defaults to `ru-RU`)

Launch the application.
```bash
poetry run python -m zumka.main -d -1 -l uz-UZ
```
<!-- By default zumka.main is using constant `AUDIO_PATH = "assets/sound/speech_00.pcm"` for speech recognition. -->

