# Независимый планировщик публикаций — подготовлен, НЕ развёрнут

Назначение: отделить подготовку новости от отправки в 09:00, 15:00, 21:00 Europe/Moscow. Редакция GitHub готовит подтверждённые тексты и существующие авторские карточки заранее; Cloudflare Workers Cron отправляет готовую карточку напрямую через Bot API. Но отсутствие подходящей новости не заменяется выдуманным или повторным постом.

Cron вызывается каждую минуту; обычная отправка разрешена в первые две минуты слота (00–01). После успешной отправки уникальный слот в D1 блокирует повтор. Нельзя обещать точность до секунды: внешние сервисы и сеть могут задерживать запрос. Полная готовность требует успешной реальной публикации из Worker.

## Что уже проверено локально

- Московские слоты, переход дня, подготовка за 40 минут, срочные проверки каждые 10 минут.
- Запрет непроверенных/истёкших карточек, проверка SHA-256 изображения.
- Подготовка не отправляет пост напрямую в Telegram.
- Неоднозначный ответ Telegram/очереди блокирует автоматический повтор до сверки.
- Предыдущие лимиты: 3 обычных поста, дополнительный срочный; интервалы 4 часа / 15 минут.
- Ни аккаунта Cloudflare, ни развёрнутой базы сейчас нет. Активный старый GitHub cron оставлен без смены backend.

## Бесплатный тариф

Workers Free: 100 000 запросов в день и 10 мс CPU на вызов по официальной документации Cloudflare, проверенной 08.11.2026 в исходнике `cloudflare/cloudflare-docs`, `workers/platform/pricing.mdx`. При одном cron в минуту — около 1440 вызовов в день плюс небольшое число запросов очереди. D1 Free: 5 миллионов прочитанных строк/день, 100 000 записанных строк/день, 5 GB суммарного хранения (проверено в официальном `partials/workers/d1-pricing.mdx`). CPU фактической карточки проверяется при развёртывании. Платный Workers Standard не подключать автоматически. API-генерация текста остаётся в существующем бюджете $2/месяц. Превышение бесплатного CPU надо исправлять/обсуждать, не включать платный тариф без согласия.

Ссылки: https://developers.cloudflare.com/workers/platform/pricing/ и https://developers.cloudflare.com/d1/platform/pricing/ . В среде прямые страницы вернули403; текст Workers Free/D1 доступен через официальный GitHub документации. Финальный Free-план подтвердить в аккаунте.

## Подключение

Нужен аккаунт Cloudflare и доступ развёртывания к нему. Секреты вводятся только в защищённые настройки, не в чат и не в git.

1. Создать D1 `lesterdossier-newsroom`, подставить настоящий database_id в wrangler.jsonc. Применить schema.sql к remote D1.
2. Развернуть Worker с `PUBLISH_ENABLED=false`.
3. Секреты Worker:
   - TELEGRAM_BOT_TOKEN — существующий бот @GTA6NewsHustleBot.
   - NEWSROOM_QUEUE_KEY — новый случайный общий секрет только для приёма очереди.
   - GITHUB_DISPATCH_TOKEN — отдельный fine-grained GitHub token, только репозиторий gta6, Actions write; нужен для workflow_dispatch подготовки. Не переносить прокси-значение GH_TOKEN из Codex.
4. GitHub Actions secret NEWSROOM_QUEUE_KEY — тот же общий секрет. Variables NEWSROOM_PUBLISHER_URL — HTTPS URL *.workers.dev, NEWSROOM_DELIVERY_BACKEND — сначала оставить `github`.
5. Проверить авторизованный GET /api/verify: правильный бот, канал, can_post_messages=true. Проверить /api/status.
6. Запустить workflow operation=prepare. Проверить, что в D1 появилась полная проверенная карточка и image hash, а в GitHub ledger status=queued. При отсутствии подтверждённого материала заполнение очереди НЕ считать успешным.
7. GET /api/preview — безопасная проба без отправки. Проверить содержимое карточки и время. При необходимости согласовать тестовый пост.
8. Для переключения установить GitHub variable NEWSROOM_DELIVERY_BACKEND=cloudflare, дождаться окончания текущего direct-cycle, проверить, что прямых pending/uncertain отправок нет. Только затем установить PUBLISH_ENABLED=true в Worker и развернуть. Два отправителя одновременно включать нельзя.
9. Проверить настоящую публикацию из scheduled Worker, Telegram message_id, строку sent и событие published с нужным slot. Только после этого объявлять автопубликацию по часам работающей.

Отключение: PUBLISH_ENABLED=false у Worker. На время возврата к старому backend сначала отключить Worker и сверить pending/uncertain, затем менять GitHub backend.

## Команды после подключения аккаунта

Из этой папки, используя проверенный Cloudflare CLI и защищённый вход:

```sh
npx --yes wrangler@4.158.0 d1 create lesterdossier-newsroom
npx --yes wrangler@4.158.0 d1 execute lesterdossier-newsroom --remote --file=schema.sql
npx --yes wrangler@4.158.0 secret put TELEGRAM_BOT_TOKEN
npx --yes wrangler@4.158.0 secret put NEWSROOM_QUEUE_KEY
npx --yes wrangler@4.158.0 secret put GITHUB_DISPATCH_TOKEN
npx --yes wrangler@4.158.0 deploy
```

Запуск тестов из корня: `python3 -m unittest discover -s newsroom/tests -q` и `node --test newsroom/scheduler/test-worker.mjs`.

Журнал: /api/status (Bearer auth) содержит последние события. `pending` или `uncertain` запрещают любые новые отправки, пока оператор не сверит Telegram и D1. Не сбрасывать запись ради повтора. Статус queued в GitHub означает подготовку, а не публикацию; реальный message_id хранится в D1.
