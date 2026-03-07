"""
FastAPI приложение для проверки транзакций на мошенничество.
Вариант №5 - Fraud Detection с Redis в качестве кэша.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import redis
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация Redis
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# Pydantic модели
class Transaction(BaseModel):
    transaction_id: str
    amount: float = Field(gt=0, description="Сумма транзакции должна быть положительной")
    timestamp: datetime
    user_id: str
    merchant: str
    card_last4: Optional[str] = None
    location: Optional[str] = None

class FraudCheckRequest(BaseModel):
    transaction: Transaction
    check_rules: Optional[List[str]] = ["amount", "velocity", "history"]

class FraudCheckResponse(BaseModel):
    transaction_id: str
    is_fraudulent: bool
    fraud_score: float = Field(ge=0, le=1)
    reasons: List[str]
    timestamp: datetime

class HealthResponse(BaseModel):
    status: str
    redis_connected: bool
    transactions_loaded: bool
    total_transactions: int

# Инициализация FastAPI
app = FastAPI(
    title="Fraud Detection API",
    description="API для проверки транзакций на мошенничество",
    version="1.0.0"
)

# Подключение к Redis
def get_redis_client():
    """Dependency для получения Redis клиента"""
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=3
        )
        # Проверяем соединение
        client.ping()
        return client
    except redis.ConnectionError:
        logger.error(f"Failed to connect to Redis at {REDIS_HOST}:{REDIS_PORT}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service unavailable"
        )

@app.on_event("startup")
async def startup_event():
    """Действия при запуске приложения"""
    logger.info("Starting Fraud Detection API")
    # Проверяем наличие данных при старте
    try:
        client = get_redis_client()
        if client.exists('data_loaded'):
            logger.info("Data loader has completed successfully")
        else:
            logger.warning("Data may not be loaded yet. Waiting for loader...")
    except:
        logger.error("Redis not available at startup")

@app.get("/", response_class=JSONResponse)
async def root():
    return {
        "message": "Fraud Detection API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check(client: redis.Redis = Depends(get_redis_client)):
    """Проверка здоровья сервиса"""
    try:
        # Проверяем Redis
        client.ping()
        redis_ok = True
        
        # Проверяем наличие данных
        transactions_count = client.dbsize()
        data_loaded = client.exists('data_loaded')
        
        return HealthResponse(
            status="healthy",
            redis_connected=redis_ok,
            transactions_loaded=bool(data_loaded),
            total_transactions=transactions_count
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="degraded",
            redis_connected=False,
            transactions_loaded=False,
            total_transactions=0
        )

@app.get("/transactions/{transaction_id}", response_model=Dict[str, Any])
async def get_transaction(
    transaction_id: str, 
    client: redis.Redis = Depends(get_redis_client)
):
    """Получение информации о транзакции по ID"""
    key = f"transaction:{transaction_id}"
    transaction = client.hgetall(key)
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found"
        )
    
    return transaction

@app.post("/check-fraud", response_model=FraudCheckResponse)
async def check_fraud(
    request: FraudCheckRequest,
    client: redis.Redis = Depends(get_redis_client)
):
    """
    Проверка транзакции на мошенничество
    """
    transaction = request.transaction
    reasons = []
    fraud_score = 0.0
    
    # Правило 1: Проверка на аномально большую сумму
    if "amount" in request.check_rules:
        # Получаем средние суммы для пользователя
        user_key = f"user:{transaction.user_id}:transactions"
        avg_amount = 100.0  # В реальности брали бы из Redis
        
        if transaction.amount > avg_amount * 3:
            fraud_score += 0.3
            reasons.append(f"Amount {transaction.amount} exceeds typical by 3x")
    
    # Правило 2: Проверка на частоту транзакций (velocity)
    if "velocity" in request.check_rules:
        # Проверяем количество транзакций за последний час
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_count = 0  # В реальности запрос к Redis
        
        if recent_count > 5:
            fraud_score += 0.4
            reasons.append("Unusual transaction velocity")
    
    # Правило 3: Проверка истории пользователя
    if "history" in request.check_rules:
        # Проверяем, был ли пользователь ранее замечен в мошенничестве
        fraud_history_key = f"user:{transaction.user_id}:fraud_history"
        if client.exists(fraud_history_key):
            fraud_score += 0.2
            reasons.append("User has fraud history")
    
    # Правило 4: Проверка на подозрительных мерчантов
    risky_merchants = client.smembers("risky_merchants")
    if transaction.merchant in risky_merchants:
        fraud_score += 0.2
        reasons.append(f"Merchant {transaction.merchant} is flagged as risky")
    
    # Определяем финальный вердикт
    is_fraudulent = fraud_score > 0.5
    
    # Логируем результат
    logger.info(f"Transaction {transaction.transaction_id} checked: fraud={is_fraudulent}, score={fraud_score}")
    
    # Сохраняем результат проверки
    result_key = f"check:{transaction.transaction_id}"
    client.hset(result_key, mapping={
        "timestamp": datetime.now().isoformat(),
        "is_fraudulent": str(is_fraudulent),
        "score": str(fraud_score),
        "reasons": json.dumps(reasons)
    })
    client.expire(result_key, 86400)  # Храним 24 часа
    
    return FraudCheckResponse(
        transaction_id=transaction.transaction_id,
        is_fraudulent=is_fraudulent,
        fraud_score=fraud_score,
        reasons=reasons,
        timestamp=datetime.now()
    )

@app.post("/transactions/batch-check")
async def batch_check(
    transactions: List[Transaction],
    client: redis.Redis = Depends(get_redis_client)
):
    """Пакетная проверка нескольких транзакций"""
    results = []
    
    for transaction in transactions:
        request = FraudCheckRequest(transaction=transaction)
        result = await check_fraud(request, client)
        results.append(result)
    
    return {
        "checked": len(results),
        "fraudulent": sum(1 for r in results if r.is_fraudulent),
        "results": results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
