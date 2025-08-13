# generate_protos.py
import subprocess
import sys
from pathlib import Path

def main():
    """Запускает генерацию Protobuf файлов."""
    
    # Определяем корень проекта (там, где лежит pyproject.toml)
    project_root = Path(__file__).parent
    
    # Пути для флага -I
    proto_source_paths = [
        project_root / "src/cloudapi",
        project_root / "src/cloudapi/third_party/googleapis",
    ]
    
    # Список .proto файлов для компиляции
    proto_files = [
        "google/api/http.proto",
        "google/api/annotations.proto",
        "google/rpc/status.proto",
        "yandex/cloud/api/operation.proto",
        "yandex/cloud/operation/operation.proto",
        "yandex/cloud/validation.proto",
        "yandex/cloud/ai/stt/v3/stt_service.proto",
        "yandex/cloud/ai/stt/v3/stt.proto",
    ]
    
    # Формируем команду для protoc
    command = [
        sys.executable,  # Используем текущий python-интерпретатор
        "-m", "grpc_tools.protoc",
    ]
    
    # Добавляем пути для поиска
    for path in proto_source_paths:
        command.append(f"-I{path}")
        
    # Добавляем флаги вывода
    output_dir = project_root / "src"
    command.extend([
        f"--python_out={output_dir}",
        f"--mypy_out={output_dir}",
        f"--grpc_python_out={output_dir}",
        f"--mypy_grpc_out={output_dir}",
    ])
    
    # Добавляем сами proto файлы
    command.extend(proto_files)
    
    print("Запуск команды кодогенерации:")
    # Используем list2cmdline для корректного отображения в логах
    print(subprocess.list2cmdline(command))
    
    # Запускаем процесс
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        print("Ошибка при генерации Protobuf файлов:", file=sys.stderr)
        print(result.stdout, file=sys.stdout)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    
    print("Protobuf файлы успешно сгенерированы.")
    print(result.stdout)


if __name__ == "__main__":
    main()