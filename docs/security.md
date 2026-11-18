# Безопасность (AppSec & Infrastructure Hardening)

Ниже приведена модель угроз для видеохостинга с ролевой моделью и приватным контентом, а также конкретные меры защиты, реализованные в StreamTube.

## 1. Аутентификация и управление сессиями
- **Хеширование паролей:** используется **Argon2id** (`argon2-cffi`, `memory_cost=65536`, `time_cost=2`) — стандарт OWASP, устойчивый к GPU/ASIC-перебору.
- **Короткоживущие Access JWT (30 мин, HS256)** + **ротируемые Refresh-токены (14 дней)**:
  - Refresh-токены хранятся в БД исключительно в виде `SHA-256` хеша.
  - Передаются в `HttpOnly; SameSite=Lax` cookie, при `/auth/refresh` старый токен немедленно отзывается (rotation), а при `/auth/logout` помечается `revoked = true`.
- **Защита от перебора учётных данных:** на `/auth/login` и `/auth/register` включён sliding-window rate limiter (Redis/in-memory); ошибка входа возвращает обобщённое сообщение `Invalid credentials` без раскрытия факта существования логина/email.

## 2. Авторизация: RBAC и защита от IDOR
- **Роли (`user`, `moderator`, `admin`)** проверяются через выделенные зависимости FastAPI (`get_current_user`, `require_moderator`, `require_admin`).
- **Централизованный модуль политик (`app/services/policies.py`):**
  - `can_view_video`, `can_stream_video`, `can_edit_video`, `can_delete_video`, `can_manage_grants`.
  - Все операции изменения/удаления видео, комментариев, плейлистов и списков доступа проверяют принадлежность объекта текущему пользователю или привилегированную роль.
  - Администратор не может случайно понизить или заблокировать собственную учётную запись.
  - Поля `role`, `owner_id`, `moderation_status` никогда не принимаются из пользовательского тела запроса.

## 3. Защита приватных видео (Zero-Trust Media Delivery)
- Бакет MinIO **не имеет публичного доступа** и не экспонируется наружу в `docker-compose.yml`.
- Все медиа-запросы (`stream`, `hls/*.m3u8`, `hls/*.ts`, `thumbnail`) проходят через FastAPI (`app/api/v1/media.py`).
- Подписанные playback-токены (`HMAC-SHA256`, проверка через `hmac.compare_digest`, TTL 15 минут) привязаны к `(video_id, user_id, exp)`.
- **Мгновенный отзыв прав:** при проверке токена для приватного/скрытого видео бэкенд повторно проверяет актуальную политику `can_stream_video(db, token_user, video)`. Если владелец отозвал доступ (`DELETE /videos/{id}/access/{user_id}`), даже ранее выданный подписанный URL перестаёт работать немедленно.
- Приватные ответы помечаются `Cache-Control: private` / `no-store`.

## 4. Безопасность загрузки файлов и FFmpeg
- **Потоковое чтение с жёстким лимитом размера** (500 MB для видео, 10 MB для превью) — защита от DoS по памяти и диску.
- **Проверка расширения + Magic Bytes** (`validate_video_magic_bytes`, `validate_image_magic_bytes`) — отклонение HTML/JS/скриптов, замаскированных под `.mp4` (`415 Unsupported Media Type`).
- **Изоляция имён файлов:** ключи в хранилище формируются строго из UUID (`videos/{uuid}/source{ext}`); для HLS-файлов действует строгий regex `^[a-zA-Z0-9_.-]+$` и запрет `..` (защита от Path Traversal).
- **Hardening FFmpeg/FFprobe:**
  - Запуск строго списком аргументов (`shell=False`) с таймаутами (защита от Command Injection и зависания воркера).
  - Передаётся флаг `-protocol_whitelist file,pipe`, блокирующий SSRF и чтение произвольных URI через вредоносные медиа-плейлисты (классическая CVE-категория FFmpeg).

## 5. Веб-безопасность и инфраструктура
- **HTTP Security Headers** (в FastAPI middleware и Nginx): `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`.
- **SQL Injection:** все запросы выполняются через параметризованный SQLAlchemy 2.0 ORM.
- **Контейнеры и секреты:** backend/worker запускаются под непривилегированным пользователем `appuser`; `deploy.sh` генерирует уникальные случайные секреты в `.env` с правами `chmod 600`.
- **Неизменяемый аудит-лог (`moderation_logs`):** фиксирует каждое действие модераторов и администраторов (скрытие/восстановление видео, отклонение жалоб, удаление комментариев, изменение ролей и блокировку аккаунтов).
