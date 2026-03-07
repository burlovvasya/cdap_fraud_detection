#!/usr/bin/env python3
"""
ETL Loader для загрузки данных о транзакциях в Redis.
Вариант №5 - Fraud Detection
"""

import os
import time
import logging
import pandas as pd
import redis
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
REDIS_DB = int(os.getenv('REDIS_DB', 0))
DATA_PATH = os.getenv('DATA_PATH', '/data/transactions.csv')

def wait_for_redis(max_retries=30, delay=2):
    """Ожидание готовности Redis"""
    for i in range(max_retries):
        try:
            client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                db=REDIS_DB,
                socket_connect_timeout=2
            )
            client.ping()
            logger.info(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            return client
        except redis.ConnectionError:
            logger.info(f"Waiting for Redis... attempt {i+1}/{max_retries}")
            time.sleep(delay)
    
    raise Exception("Could not connect to Redis after multiple attempts")

def load_transactions_to_redis(client, df):
    """Загрузка транзакций в Redis"""
    logger.info(f"Loading {len(df)} transactions to Redis")
    
    # Используем pipeline для batch-загрузки
    pipeline = client.pipeline()
    
    for idx, row in df.iterrows():
        # Преобразуем row в словарь с правильными типами
        data = {}
        for key, value in row.items():
            if hasattr(value, 'isoformat'):  # Для Timestamp, datetime
                data[key] = value.isoformat()
            elif isinstance(value, (int, float, str)):
                data[key] = value
            else:
                data[key] = str(value)
        
        # Ключ: transaction:{transaction_id}
        key = f"transaction:{data.get('transaction_id', idx)}"
        
        # Сохраняем как hash
        pipeline.hset(key, mapping=data)
        
        # Периодически выполняем pipeline
        if idx % 1000 == 0 and idx > 0:
            pipeline.execute()
            pipeline = client.pipeline()
            logger.info(f"Loaded {idx} transactions...")
    
    # Выполняем остаток
    if len(df) > 0:
        pipeline.execute()
    
    logger.info(f"Successfully loaded all transactions")

def main():
    logger.info("Starting data loader for Fraud Detection system")
    
    # Подключаемся к Redis
    redis_client = wait_for_redis()
    
    # Проверяем наличие данных
    data_file = Path(DATA_PATH)
    if not data_file.exists():
        logger.error(f"Data file not found: {DATA_PATH}")
        # Создаем тестовые данные для демонстрации
        logger.info("Creating sample data for demonstration")
        sample_data = pd.DataFrame({
            'transaction_id': range(1, 101),
            'amount': [x * 100 for x in range(1, 101)],
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='H'),
            'user_id': [f'user_{i%10}' for i in range(100)],
            'merchant': [f'merchant_{i%5}' for i in range(100)],
            'is_fraud': [1 if i%7 == 0 else 0 for i in range(100)]
        })
    else:
        # Загружаем реальные данные
        logger.info(f"Loading data from {DATA_PATH}")
        sample_data = pd.read_csv(data_file)
    
    # Загружаем данные в Redis
    load_transactions_to_redis(redis_client, sample_data)
    
    # Устанавливаем флаг, что загрузка завершена
    redis_client.set('data_loaded', 'true')
    redis_client.expire('data_loaded', 3600)  # Истекает через час
    
    logger.info("Data loader finished successfully")

if __name__ == "__main__":
    main()
