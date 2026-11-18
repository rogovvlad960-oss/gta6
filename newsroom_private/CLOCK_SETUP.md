# Независимый таймер личной редакции

Статус 18.11.2026: Worker lester-private-clock РАЗВЁРНУТ, Cloudflare cron сохранён. GITHUB_DISPATCH_TOKEN пока отсутствует; сквозной запуск НЕ подтверждён. GitHub push-запуск44366217505 успешно проверяет редакцию, настоящий schedule44375797927 подтверждён 18ноября22:01МСК (private-editor-clock success), но интервалы15минут не подтверждены.

## Что подключить

1. https://dash.cloudflare.com/profile/api-tokens → Create Token → Edit Cloudflare Workers. Ограничить нужным аккаунтом. Ввести токен в существующее защищённое поле CLOUDFLARE_API_TOKEN настроек среды Codex. Токен Cloudflare уже подключён и проверен active. Не передавать значение в чат или git.
2. Для постоянного доступа Worker к GitHub нужен отдельный fine-grained token: https://github.com/settings/personal-access-tokens/new → только rogovvlad960-oss/gta6, Repository permissions → Actions: Read and write. Ввести напрямую в Cloudflare Worker Settings → Variables and Secrets как Secret GITHUB_DISPATCH_TOKEN. Не копировать прокси GH_TOKEN из Codex.
3. Развернуть clock-worker.mjs с clock-wrangler.jsonc на бесплатном Workers Free. Никаких Telegram/OpenAI секретов, D1 и платного тарифа этому таймеру не требуется. Cron */15 5-21 * * * UTC:08:00–00:45 Москва. Python также запрещает отправку с01:00до08:00, включая отложенный запуск.
4. Проверить настоящий scheduled event Worker, HTTP204 dispatch и завершение GitHub private workflow. Проверка должна опираться на событие таймера, а не на ручной запуск.

## Команды после подключения

Из /workspace/gta6/newsroom_private:

    node --test test-clock.mjs
    XDG_CONFIG_HOME=/tmp/lester-cloudflare-config WRANGLER_SEND_METRICS=false npm exec --cache=/tmp/lester-wrangler-npm --yes --package=wrangler@4.158.0 -- wrangler deploy --config clock-wrangler.jsonc

Секрет GITHUB_DISPATCH_TOKEN вводит пользователь непосредственно в Cloudflare, а не команда с прокси-плейсхолдером. При отсутствии секрета Worker завершится dispatch_secret_missing и ничего не отправит.

Мониторинг каждые15минут не означает отправку каждые15минут: обычный интервал1час,6постов/сутки и общий бюджет$2/месяц сохранены. Источники проверяются и при дневном лимите отправок. Таймер не гарантирует длительность очереди GitHub runners.

19 ноября,00:14МСК: Cloudflare REST API подтвердил загрузку Worker,workers.devиcron. Список Worker secrets пуст. Публичная health-проверка из этой среды вернула upstream503; это не доказательство работы/неработы самого Cron. Для продолжения пользователь вводит собственный GitHub token только в Worker Settings→Variables and Secrets→Secret GITHUB_DISPATCH_TOKEN.

ПРОВЕРЕНО 19 ноября00:30МСК: настоящий Cloudflarecron,tail outcome=ok/dispatched=true,scheduledTime2026-11-18T21:30:31.533Z. GitHubworkflow_dispatch44402190247SUCCESS. Ledgerexternal_clock_checksс темжеscheduled_at;результатno_new_image_posts,dated_posts30. GITHUB_DISPATCH_TOKENтипsecret_text. Цепочкатаймер→редакцияработает. НовыйTelegramпоствэтомпрогоненеотправлен;публикациюименноизтаймерапоканеобъявлятьпроверенной.
