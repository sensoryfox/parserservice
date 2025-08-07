# corporate-semantic-search/Dockerfile
######################################################################
#  CUDA 12.3  •  FastAPI-service из PyPI  •  минимальный размер      #
######################################################################
FROM nvidia/cuda:12.3.2-cudnn9-devel-ubuntu22.04

# ---------- базовые системные зависимости ----------
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-pip python3-dev build-essential \
        ffmpeg libsndfile1 libarchive13 libleptonica-dev \
        git curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*
# 2. Установка системных зависимостей (если понадобятся, например, для lxml)
#RUN apt-get update && apt-get install -y --no-install-recommends ... && rm -rf /var/lib/apt/lists/*

# 3. Установка рабочей директории внутри контейнера
WORKDIR /app
# --- СЛОЙ 1: ТЯЖЕЛЫЕ ЗАВИСИМОСТИ (будет закеширован навсегда) ---
# Копируем ТОЛЬКО список тяжелых библиотек
COPY base-requirements.txt .

# Устанавливаем их. Этот слой пересоберется, только если вы измените base-requirements.txt
# (что будет происходить крайне редко).
RUN pip install --no-cache-dir -r base-requirements.txt


# --- СЛОЙ 2: ЛЕГКИЕ ЗАВИСИМОСТИ (будет пересобираться часто, но быстро) ---
# Копируем список легких и часто обновляемых библиотек
COPY app-requirements.txt .

# Устанавливаем их. Если вы обновите версию sensory-data-client в этом файле,
# Docker начнет пересборку с этого места. Предыдущий слой с marker-pdf останется в кеше!
RUN pip install --no-cache-dir -r app-requirements.txt

# --- СЛОЙ 3: КОД ПРИЛОЖЕНИЯ (самый динамичный слой) ---
# Копируем исходный код только после установки всех зависимостей.
COPY ./src ./src

#RUN sensory_data_client init
# Команда для запуска (без изменений)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]