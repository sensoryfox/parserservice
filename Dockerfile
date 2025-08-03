# corporate-semantic-search/Dockerfile

# 1. Базовый образ
FROM python:3.11-slim

# 2. Установка системных зависимостей (если понадобятся, например, для lxml)
RUN apt-get update && apt-get install -y --no-install-recommends ... && rm -rf /var/lib/apt/lists/*

# 3. Установка рабочей директории внутри контейнера
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копирование исходного кода приложения
COPY ./src ./src

# 6. Команда для запуска приложения
# Запускаем uvicorn, слушая все интерфейсы (0.0.0.0) на порту 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]