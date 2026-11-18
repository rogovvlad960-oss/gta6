# Личный Telegram и премиум-эмодзи

Статус: код и проверки готовы; вход пользователя НЕ выполнен, отправка с аккаунта НЕ включена. Рабочая редакция продолжает использовать бота. Эмодзи — настоящие MessageEntityCustomEmoji из GamingEmoji_by_MoiStikiBot, не картинки/наклейки. Проверены логотип GTA VI5282847372223740079 и молния5222430393688432601. Расположение entities считается в UTF16, жирные участки сохраняются.

## Однократное подключение владельцем

1. На https://my.telegram.org/apps создать приложение (любое своё название, Desktop), получить API ID и API Hash. Не присылать их в чат.
2. На СВОЁМ компьютере скачать login_local.py и установить Telethon1.46.0:

       python -m pip install Telethon==1.46.0
       python login_local.py

   API Hash, номер, код и облачный пароль вводятся скрыто только в локальном терминале. Скрипт не отправляет секреты разработчику и не печатает сессию. Файлы создаются в telegram-user-private/ с ограничением доступа, где ОС это поддерживает.
3. GitHub https://github.com/rogovvlad960-oss/gta6/settings/secrets/actions → New repository secret: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_USER_SESSION. Ввести содержимое одноимённых локальных .txt. НЕ загружать эти файлы в git/чат/архив передачи.
4. После сохранения запустить workflow Telegram account premium emoji test (workflow_dispatch). Он не генерирует платный текст, не читает контакты/чаты, не пишет в каналы: единственный тест отправляется в «Избранное». Проверяет совпадение владельца с ранее одобренным получателем (salted hash), Premium, наличие custom-emoji document, целевой чат и возвращённые entities.
5. Пользователь проверяет отображение. Только после успешного теста переключить config delivery_backend=telegram_user, добавить три существующих Actions secrets в оба private job(main и legacy-clock) и установку requirements-user.txt. Один активный backend, без fallback на бота при сбое аккаунта. Текущий монитор уже содержит выключенную по умолчанию ветку аккаунта.

## Не считать подключённым заранее

Наличие библиотеки/кода не равно авторизации или успешной отправке. Live-тест до входа не запускать. Сессионная строка даёт доступ к аккаунту; хранить только в Secrets. При желании отключить интеграцию завершить её сеанс в Telegram Settings→Devices и вернуть backend bot после сверки pending/uncertain. При FloodWait не спать весь runner и не повторять отправку автоматически: код оставляет неопределённую отправку для сверки, прежняя защита от дублей действует.

## Проверки

    PYTHONPATH=/tmp/post-style-deps:/tmp/telegram-user-deps python -m unittest newsroom_private.test_monitor newsroom_private.telegram_user.test_transport -q

6 проверок аккаунта и 15 основных проверок прошли19ноября. Вход/доставка аккаунтом пока не проверены.
