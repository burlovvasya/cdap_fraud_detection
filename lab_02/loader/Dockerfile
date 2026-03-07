# Используем фиксированную версию slim образа
FROM python:3.10-slim as builder

# Устанавливаем системные зависимости (объединяем команды RUN)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создаем непривилегированного пользователя
RUN useradd -m -u 1000 appuser

# Устанавливаем зависимости Python
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Финальный этап (можно использовать multi-stage, но для простого скрипта достаточно одного этапа)
FROM python:3.10-slim

# Копируем установленные пакеты из builder
COPY --from=builder /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Создаем пользователя
RUN useradd -m -u 1000 appuser

# Создаем рабочую директорию
WORKDIR /app

# Копируем скрипт загрузчика
COPY loader.py .
COPY --chown=appuser:appuser loader.py .

# Переключаемся на непривилегированного пользователя
USER appuser

# Команда по умолчанию
CMD ["python", "loader.py"]
