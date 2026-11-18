# Независимый таймер личной редакции

Статус 18.11.2026: код проверен, но Worker НЕ развёрнут. GitHub push-запуск44366217505 успешно проверяет редакцию, настоящий schedule44375797927 подтверждён 18ноября22:01МСК (private-editor-clock success), но интервалы15минут не подтверждены.

## Что подключить

1. https://dash.cloudflare.com/profile/api-tokens → Create Token → Edit Cloudflare Workers. Ограничить нужным аккаунтом. Ввести токен в существующее защищённое поле CLOUDFLARE_API_TOKEN настроек среды Codex. Сейчас поле объявлено, но has_saved_binding=false. Не передавать значение в чат или git.
2. Для постоянного доступа Worker к GitHub нужен отдельный fine-grained token: https://github.com/settings/personal-access-tokens/new → только rogovvlad960-oss/gta6, Repository permissions → Actions: Read and write. Ввести напрямую в Cloudflare Worker Settings → Variables and Secrets как Secret GITHUB_DISPATCH_TOKEN. Не копировать прокси GH_TOKEN из Codex.
3. Развернуть clock-worker.mjs с clock-wrangler.jsonc на бесплатном Workers Free. Никаких Telegram/OpenAI секретов, D1 и платного тарифа этому таймеру не требуется. Cron */15 5-21 * * * UTC:08:00–00:45 Москва. Python также запрещает отправку с01:00до08:00, включая отложенный запуск.
4. Проверить настоящий scheduled event Worker, HTTP204 dispatch и завершение GitHub private workflow. Проверка должна опираться на событие таймера, а не на ручной запуск.

## Команды после подключения

Из /workspace/gta6/newsroom_private:

    node --test test-clock.mjs
    XDG_CONFIG_HOME=/tmp/lester-cloudflare-config WRANGLER_SEND_METRICS=false npm exec --cache=/tmp/lester-wrangler-npm --yes --package=wrangler@4.158.0 -- wrangler deploy --config clock-wrangler.jsonc

Секрет GITHUB_DISPATCH_TOKEN вводит пользователь непосредственно в Cloudflare, а не команда с прокси-плейсхолдером. При отсутствии секрета Worker завершится dispatch_secret_missing и ничего не отправит.

Мониторинг каждые15минут не означает отправку каждые15минут: обычный интервал1час,6постов/сутки и общий бюджет$2/месяц сохранены. Источники проверяются и при дневном лимите отправок. Таймер не гарантирует длительность очереди GitHub runners.
