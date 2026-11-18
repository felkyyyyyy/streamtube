# Проектирование базы данных (PostgreSQL)

## Разделение данных: что и где хранится

| Хранилище | Данные | Обоснование |
| :--- | :--- | :--- |
| **PostgreSQL 16** | Пользователи, роли, refresh-токены, метаданные видео, ACL приватного доступа, реакции, комментарии, подписки, плейлисты, жалобы, журнал аудита | ACID-транзакции, реляционная целостность (`FK`, `UNIQUE`, `CHECK`), быстрые выборки по составным индексам |
| **MinIO (S3)** | Исходные видеофайлы (`source.*`), HLS-плейлисты (`.m3u8`), видео-сегменты (`.ts`), превью (`.jpg/.png/.webp`) | Горизонтально масштабируемое объектное хранилище, byte-range чтение, не раздувает БД |
| **Redis 7** | Очередь транскодирования (`streamtube:transcode`), счётчики rate-limiting | Низкая задержка, атомарные операции `BLPOP` и скользящего окна `ZSET` |

## ER-диаграмма

```mermaid
erDiagram
    USERS ||--o{ REFRESH_TOKENS : has
    USERS ||--o{ VIDEOS : owns
    USERS ||--o{ COMMENTS : writes
    USERS ||--o{ PLAYLISTS : owns
    USERS ||--o{ SUBSCRIPTIONS : subscribes
    USERS ||--o{ VIDEO_ACCESS_GRANTS : granted
    USERS ||--o{ VIDEO_REACTIONS : reacts
    USERS ||--o{ REPORTS : submits
    USERS ||--o{ MODERATION_LOGS : performs

    VIDEOS ||--o{ VIDEO_ACCESS_GRANTS : restricts_to
    VIDEOS ||--o{ VIDEO_REACTIONS : receives
    VIDEOS ||--o{ COMMENTS : has
    VIDEOS ||--o{ PLAYLIST_ITEMS : included_in
    VIDEOS ||--o{ REPORTS : flagged_by

    PLAYLISTS ||--o{ PLAYLIST_ITEMS : contains
    COMMENTS ||--o{ COMMENTS : replies_to

    USERS {
        varchar id PK
        varchar username UK
        varchar email UK
        varchar password_hash
        varchar role
        varchar channel_name
        boolean is_active
        timestamptz created_at
    }

    VIDEOS {
        varchar id PK
        varchar owner_id FK
        varchar title
        varchar category
        varchar visibility
        varchar status
        varchar moderation_status
        varchar storage_key
        varchar hls_master_key
        varchar thumbnail_key
        bigint file_size_bytes
        int duration_seconds
        int views_count
        int likes_count
        int dislikes_count
        timestamptz created_at
    }

    VIDEO_ACCESS_GRANTS {
        varchar id PK
        varchar video_id FK
        varchar user_id FK
        varchar granted_by_id FK
        timestamptz created_at
    }

    VIDEO_REACTIONS {
        varchar id PK
        varchar video_id FK
        varchar user_id FK
        smallint value
    }

    COMMENTS {
        varchar id PK
        varchar video_id FK
        varchar author_id FK
        varchar parent_id FK
        text content
        boolean is_deleted
    }

    SUBSCRIPTIONS {
        varchar id PK
        varchar subscriber_id FK
        varchar channel_id FK
    }

    PLAYLISTS {
        varchar id PK
        varchar owner_id FK
        varchar title
        varchar visibility
    }

    PLAYLIST_ITEMS {
        varchar id PK
        varchar playlist_id FK
        varchar video_id FK
        int position
    }

    REPORTS {
        varchar id PK
        varchar video_id FK
        varchar reporter_id FK
        varchar reason
        varchar status
        varchar reviewed_by_id FK
    }

    MODERATION_LOGS {
        varchar id PK
        varchar actor_id FK
        varchar action
        varchar target_type
        varchar target_id
        text reason
    }
```

## Ключевые проектные решения

1. **Индексирование ленты:** составной индекс `ix_videos_feed (visibility, moderation_status, created_at)` ускоряет основной запрос главной страницы, отсекая приватные и скрытые видео на уровне индекса.
2. **Строгая целостность на уровне СУБД:**
   - `uq_video_access_grant (video_id, user_id)` — исключает дублирование прав доступа.
   - `uq_video_reaction (video_id, user_id)` + `CHECK (value IN (1, -1))` — гарантирует одну реакцию пользователя на видео.
   - `uq_subscription_pair (subscriber_id, channel_id)` + `CHECK (subscriber_id != channel_id)` — запрещает дубли и подписку на самого себя.
   - `uq_playlist_video (playlist_id, video_id)` — исключает дубли видео в плейлисте.
   - Каскадное удаление (`ON DELETE CASCADE`) очищает зависимые сущности без «висячих» записей, а для аудита и модерации используется `ON DELETE SET NULL` на `actor_id` / `reviewed_by_id`, чтобы история модерации сохранялась.
3. **Денормализованные счётчики (`likes_count`, `dislikes_count`, `views_count`):** хранятся в `videos` для быстрого рендера карточек ленты и пересчитываются/инкрементируются атомарно при изменении реакций и просмотров.
4. **Миграции:** схема версионируется через **Alembic** (`backend/migrations/versions/0001_initial_schema.py`).
