# ТЗ для Cursor: Migration Security Gate v2 (Production-Ready)

## 0. Цель

Развить текущий проект **Migration Security Gate** (control plane) от MVP к продово применимой схеме, где:

* большие артефакты (snapshot/WAL) **не передаются через UI/API напрямую**
* вместо этого используется **Artifact Store** (S3-совместимое хранилище MinIO)
* gate принимает **manifest + ссылки (URI) + ожидаемые хеши/подписи**, затем выполняет проверку и отдаёт решение **ALLOW/BLOCK**
* сохраняется принцип **Fail-Closed**, детерминизм и аудит

Проект должен оставаться:

* облако-агностичным
* воспроизводимым через `docker compose`
* понятным для демонстрации на экзамене (UI остаётся, но операторский)

---

## 1. Текущее состояние (как baseline)

В репозитории уже есть:

* API + валидаторы T1/T2
* Policy engine
* Integrity (sha256)
* Audit logging
* UI (формы)
* Dockerfile, compose, README
* примеры good/bad

Нужно расширить **процесс и архитектуру**, а не “перекрасить UI”.

---

## 2. Архитектура v2 (обязательные изменения)

### 2.1 Введение Artifact Store

Добавить в `docker-compose.yml` сервис **MinIO** (S3-совместимый):

* сервис `minio`
* bucket (например) `mig-artifacts`
* доступ из контейнера gate по внутренней сети
* креды через env (`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`)
* опционально `minio-console` порт для просмотра

### 2.2 Два режима проверки артефактов

Система должна поддерживать **оба режима**:

1. **Upload Mode** (как сейчас, для демо):

* multipart upload `snapshot.tar.gz`, `wal_files[]`
* gate проверяет локально

2. **Reference Mode** (продовый, обязателен):

* gate получает только manifest, где артефакты описаны ссылками:

  * `uri` (S3/HTTP)
  * `sha256`
  * (опционально) `signature`

Gate сам:

* скачивает артефакт по ссылке (из MinIO)
* проверяет sha256
* логирует
* возвращает ALLOW/BLOCK

---

## 3. Изменения в API (v2)

### 3.1 Не ломать существующий API

Текущие endpoints должны продолжать работать (backward compatibility).

### 3.2 Добавить Reference Mode endpoints (минимум)

**Требуется добавить:**

* `POST /api/v1/validate/replication/ref`

  * Content-Type: `application/json` или `application/yaml`
  * body включает replication manifest со ссылками на snapshot и WAL архив(ы)

* (опционально, если успеваем) `POST /api/v1/validate/migration/ref`

  * для T1: `app-config.yaml` может храниться в MinIO и проверяться по uri+hash

### 3.3 Canonical ответ (как в API_CONTRACT)

Независимо от режима:

* возвращать `decision: ALLOW|BLOCK`
* `scenario: T1|T2`
* `request_id`, `timestamp`
* `reasons[]` для BLOCK
* computed hashes (если применимо)

**Правило:** HTTP 200 не означает ALLOW — ALLOW только по `decision`.

---

## 4. Форматы данных для Reference Mode (строго)

### 4.1 replication_manifest (reference)

Пример (YAML):

```yaml
app_id: "billing"
env: "prod"
snapshot:
  uri: "s3://mig-artifacts/billing/snapshot_20260118.tar.gz"
  sha256: "<hex>"
wal:
  uri: "s3://mig-artifacts/billing/wal_20260118.tar.gz"
  sha256: "<hex>"
sync_mode: "async"
policy_version: "2026.01"
change_id: "CHG-12345"
```

**Обязательные поля** для MVP v2:

* app_id
* env
* snapshot.uri
* snapshot.sha256
* sync_mode

WAL можно оставить опциональным, но если указан — проверять sha256.

### 4.2 URI схемы

Поддержать минимум:

* `s3://bucket/key` (для MinIO)
* (опционально) `http(s)://...` (если захотим расширение)

---

## 5. Логика валидации v2 (обязательные проверки)

### 5.1 Общие правила (для всех)

* Любая ошибка → `BLOCK` (Fail-Closed)
* Невалидный формат/отсутствие полей → `BLOCK`
* Любая ошибка доступа к MinIO (timeout/404/403) → `BLOCK` + reason code

### 5.2 Для T2 (Replication)

Обязательные проверки:

1. Schema validation манифеста (Pydantic)
2. Валидация env/sync_mode
3. Скачивание snapshot по uri (MinIO)
4. Вычисление sha256
5. Сравнение с ожидаемым sha256
6. (Если есть WAL) — аналогично по WAL
7. Запись audit log

Reason codes (минимум):

* `INVALID_MANIFEST`
* `ARTIFACT_FETCH_FAILED`
* `SNAPSHOT_HASH_MISMATCH`
* `WAL_HASH_MISMATCH`
* `POLICY_VIOLATION`
* `INTERNAL_ERROR`

### 5.3 Для T1 (Migration)

Остаётся как сейчас, но (опционально) расширить:

* reference mode для config.yaml, если указан `config.uri`

---

## 6. UI v2 (минимально, но полезно)

UI должен уметь:

* переключать режим проверки:

  * Upload Mode
  * Reference Mode
* для Reference Mode:

  * форма, где вставляется YAML/JSON манифест (textarea) или загрузка manifest файла
  * вывод результата: decision + reasons + computed hashes + request_id
* страницы audit/alerts остаются и показывают события от обоих режимов

UI не должен становиться “большим фронтендом”. Это operator console.

---

## 7. Конфигурация (env vars)

Добавить в `.env.example`:

* `API_TOKEN`
* `AUDIT_LOG_PATH`
* `MINIO_ENDPOINT` (например `http://minio:9000`)
* `MINIO_ACCESS_KEY`
* `MINIO_SECRET_KEY`
* `MINIO_BUCKET` (например `mig-artifacts`)
* (опционально) `MINIO_SECURE=false`

---

## 8. Тестирование под новую архитектуру (обязательный план)

### 8.1 Уровни тестирования

1. **Unit tests** (быстрые, без MinIO):

* hashing utils
* policy engine
* schema validation
* decision mapping и reason codes
* fail-closed обработка ошибок

2. **Integration tests** (обязательные, через docker compose + MinIO):

* загрузка артефактов в MinIO
* validate replication via reference endpoint
* проверка ALLOW/BLOCK

3. **E2E smoke** (через UI):

* минимальный сценарий ручной проверки (может быть в README)

### 8.2 Как делать integration tests (рекомендуемый механизм)

Добавить:

* `tests/integration/`
* отдельный compose профиль или отдельный compose файл:

  * `docker-compose.test.yml` (опционально)

Тестовый сценарий должен:

1. Поднять `gate + minio`
2. Создать bucket
3. Загрузить:

   * `snapshot_good.tar.gz`
   * `snapshot_bad.tar.gz` (поврежденный)
4. Сформировать манифесты `t2_ref_good.yaml` и `t2_ref_bad.yaml` с uri+hash
5. Вызвать endpoint `/validate/replication/ref`
6. Проверить:

   * good → ALLOW
   * bad → BLOCK с `SNAPSHOT_HASH_MISMATCH`
7. Проверить, что в audit logs есть записи

### 8.3 Инструменты для тестов

Для Python:

* `pytest`
* `requests` (или `httpx`)
* `boto3` или `minio` python client (любой один)

Для CI/локально:

* `make test`
* `make integration-test` (поднимает compose, прогоняет тесты, тушит)

### 8.4 Обязательные тест-кейсы (минимум)

**Reference Mode (T2)**

* ALLOW: корректный snapshot sha256
* BLOCK: неверный sha256
* BLOCK: uri не существует (404)
* BLOCK: MinIO недоступен
* BLOCK: manifest missing required field

**Upload Mode (T2)**

* существующие good/bad сохраняем

**T1**

* текущие good/bad сохраняем
* (опционально) policy violation в prod (tls disabled) → BLOCK

---

## 9. Deliverables (что должно быть в итоге)

Обязательные файлы/изменения:

1. `docker-compose.yml` + сервис `minio` + сеть/volume
2. Код:

   * S3/MinIO artifact fetcher module
   * новый endpoint `/validate/replication/ref`
   * reason codes для reference mode
3. `examples/`:

   * добавить `t2_ref_good/` и `t2_ref_bad/` с манифестами reference mode
4. `README.md`:

   * сценарий запуска
   * как загрузить артефакты в MinIO (скрипт)
   * как вызвать reference validation (curl)
5. `tests/`:

   * unit tests
   * integration tests с MinIO
6. `.env.example` обновлён

---

## 10. Порядок работ (строго)

1. Добавить MinIO в compose + проверка, что он доступен
2. Реализовать artifact fetcher (s3 uri → bytes/stream)
3. Добавить endpoint `/validate/replication/ref`
4. Добавить примеры `t2_ref_good/bad`
5. Добавить integration tests
6. Обновить UI для reference mode
7. Обновить README, make targets

---

## 11. Критерии приемки (Definition of Done)

Считается выполненным, если:

* `docker compose up --build` поднимает gate + minio
* Сценарий reference mode воспроизводим:

  * загрузка артефакта в MinIO
  * запрос на `/validate/replication/ref`
  * корректный артефакт → ALLOW
  * повреждённый/несовпадающий hash → BLOCK
* Все ошибки доступа/валидации → BLOCK (Fail-Closed)
* Audit log заполняется для всех запросов
* `pytest` проходит (unit)
* integration tests проходят

---

## 12. Ограничения (важно не разрастись)

Не делать сейчас:

* настоящий VPN/mTLS
* настоящий SIEM
* Kubernetes операторов
* сложный frontend

Фокус: **реальный процесс через artifact store + проверка + аудит.**

---
