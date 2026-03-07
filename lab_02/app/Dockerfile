# Базовый образ с фиксированной версией
FROM python:3.10-slim AS builder

# Устанавливаем build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя
RUN useradd -m -u 1000 appuser

# Копируем и устанавливаем зависимости
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --user -r /tmp/requirements.txt

# Финальный образ
FROM python:3.10-slim

# Создаем пользователя
RUN useradd -m -u 1000 appuser

# Копируем установленные пакеты от builder
COPY --from=builder /root/.local /home/appuser/.local
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

# Делаем пользователя владельцем
RUN chown -R appuser:appuser /home/appuser

# Рабочая директория
WORKDIR /app

# Копируем код приложения
COPY --chown=appuser:appuser app.py .

# Переключаемся на пользователя appuser
USER appuser

# Добавляем пользовательский bin в PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Healthcheck для приложения
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Команда запуска
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
