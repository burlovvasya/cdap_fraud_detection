# Лабораторная работа №3
## Развертывание простого приложения в Kubernetes

**Студент:** Бурлов Василий Тимофеевич  
**Группа:** БД-251м  
**Вариант:** 5

---

## 1. Описание архитектуры

| Компонент | В Docker Compose | В Kubernetes |
|-----------|-----------------|--------------|
| Redis (БД) | Service + named volume | Deployment + hostPath + Service (ClusterIP) |
| Loader | depends_on + condition | Job |
| App (API) | healthcheck + depends_on | Deployment + InitContainer + Probes + Service (NodePort) |
| Конфигурация | .env | ConfigMap + Secret |

**Особенности варианта 5:**  
Для БД Redis используется hostPath (привязка к папке /tmp/redis-fraud-data на ноде).

---

## 2. Листинги манифестов

Все манифесты Kubernetes находятся в директории `lab_03/manifests/` репозитория:

- `secret.yaml` — секрет с паролем Redis
- `configmap.yaml` — конфигурация приложения
- `redis-deployment.yaml` — Deployment Redis с hostPath
- `redis-service.yaml` — Service Redis (ClusterIP)
- `loader-job.yaml` — Job для загрузки данных
- `app-deployment.yaml` — Deployment приложения с InitContainer и Probes
- `app-service.yaml` — Service приложения (NodePort)

---

## 3. Скриншоты

### 3.1. Статус Minikube
![minikube status](screenshots/minikube_status.jpg)

### 3.2. Загруженные образы
![minikube image](screenshots/minikube_image.jpg)

### 3.3. kubectl get all
![kubectl get all](screenshots/kubectl_get_all.jpg)

### 3.4. Логи Job (загрузка данных)
![logs job](screenshots/Logs_Job.jpg)

### 3.5. Доказательство доступа к приложению (curl)
![curl health](screenshots/curl.jpg)

### 3.6. Подтверждение hostPath (kubectl describe)
![kubectl describe hostPath](screenshots/kubectl_describe_pod.jpg)

### 3.7. Доказательство персистентности (данные до и после удаления пода)
![persistence proof](screenshots/Proof_of_persistence.jpg)

### 3.8. InitContainer и Probes
![initcontainer and probes](screenshots/InitContainer_Probes.jpg)

---

## 4. Вывод
- Манифесты корректно описаны  
- Конфигурация вынесена в ConfigMap и Secret  
- Данные сохраняются при перезапуске пода (hostPath)  
- Настроены LivenessProbe, ReadinessProbe и InitContainer  
- Реализована специфика варианта 5
