# seo-tools

Плагин для Claude Code, который даёт Claude доступ к живым поисковым данным ваших сайтов: Google Search Console, Яндекс.Вебмастеру и Вордстату. Вместо общих SEO-советов Claude отвечает по цифрам конкретного сайта: какие запросы растут, какая страница теряет показы, где две страницы делят один запрос и какой спрос у темы в нужном регионе.

Все инструменты только читают данные. Ключи хранятся у вас на компьютере, в репозиторий плагина не попадают.

## Что внутри

- **MCP-сервер `seo`**: 14 инструментов поверх API Google и Яндекса.
- **Агент `seo-specialist`**: SEO-специалист, который сначала смотрит данные, потом советует, и учитывает Яндекс наравне с Google.
- **Skills**, которые Claude подхватывает сам по смыслу запроса или которые можно вызвать командой:
  - `/seo-tools:seo-snapshot` — срез сайта в обоих поисковиках со сравнением с прошлым периодом;
  - `/seo-tools:cannibalization-audit` — поиск страниц, которые конкурируют за один запрос, и план, как их развести;
  - `/seo-tools:keyword-research` — семантика из Вордстата с кластерами и текущими позициями сайта;
  - `/seo-tools:seo-setup` — подключение ключей и разбор ошибок доступа.

## Установка

Нужны Claude Code и [uv](https://docs.astral.sh/uv/getting-started/installation/). Python ставить отдельно не нужно: uv скачает подходящую версию и зависимости при первом запуске сервера.

В Claude Code:

```
/plugin marketplace add starArsonist/ai-seo-tools
/plugin install seo-tools@ai-seo-tools
```

Или из терминала:

```bash
claude plugin marketplace add starArsonist/ai-seo-tools
claude plugin install seo-tools@ai-seo-tools
```

При включении плагин спросит ключи. Любое поле можно оставить пустым, тогда сервер возьмёт значение из `~/.seo-tools/` (см. ниже).

## Ключи

Каждый источник подключается отдельно: можно начать с одного Google и добавить Яндекс позже.

| Источник | Что нужно | Куда положить |
|---|---|---|
| Google Search Console | JSON-ключ сервисного аккаунта; сам аккаунт добавлен пользователем в каждый сайт в Search Console | `~/.seo-tools/*.json` или опция плагина |
| Яндекс.Вебмастер | OAuth-токен | `YANDEX_OAUTH_TOKEN` в `~/.seo-tools/.env` или опция плагина |
| Вордстат | API-ключ сервисного аккаунта Yandex Cloud с ролью `search-api.webSearch.user` и id каталога | `YANDEX_CLOUD_API_KEY`, `YANDEX_CLOUD_FOLDER_ID` в `.env` или опции плагина |

Пошаговая инструкция для каждого кабинета есть в [skills/seo-setup/SKILL.md](skills/seo-setup/SKILL.md). Проще всего попросить Claude: «подключи seo-tools», и он проведёт по шагам.

Пример `~/.seo-tools/.env`:

```dotenv
YANDEX_CLIENT_ID=...          # приложение на oauth.yandex.ru, нужно только для получения токена
YANDEX_CLIENT_SECRET=...
YANDEX_OAUTH_TOKEN=...        # запишется сам после seo-tools yandex-token
YANDEX_CLOUD_API_KEY=...
YANDEX_CLOUD_FOLDER_ID=b1g...
# YANDEX_WEBMASTER_USER_ID=... необязательно, сервер узнает сам
# GOOGLE_SERVICE_ACCOUNT_FILE=C:\keys\gsc.json  если ключ лежит не в ~/.seo-tools
# SEO_TOOLS_REPORTS=D:\seo-reports              по умолчанию ~/.seo-tools/reports
```

Опции плагина важнее файла. Папку `~/.seo-tools` можно сменить переменной `SEO_TOOLS_HOME`.

Проверить подключение:

```bash
uv run --project <папка плагина> seo-tools doctor
```

```
seo-tools 0.1.0, ключи: C:\Users\you\.seo-tools
  [ok]   Google Search Console: sc-domain:example.ru
  [ok]   Яндекс.Вебмастер: https:example.ru:443
  [ok]   Вордстат: «сайт» = 98529636 показов за 30 дней
```

Токен Яндекса живёт около года. Обновить: `seo-tools yandex-token`, затем `seo-tools yandex-token <код>`.

## Как пользоваться

Просто спрашивайте Claude о сайте:

- «Сделай срез по example.ru и сравни с прошлым месяцем»
- «Почему у example.ru упали клики в Google с начала ноября?»
- «Хочу переписать title на странице /catalog/divany, проверь, не отберёт ли она запросы у других»
- «Собери семантику под страницу „ремонт ноутбуков“ для Москвы»
- «Запусти seo-specialist и сделай полный аудит example.ru»

Большие выгрузки Claude сохраняет в CSV: `~/.seo-tools/reports/<домен>/<дата>/`. Срезы остаются там же, и следующий срез сравнивается с предыдущим.

## Инструменты

| Инструмент | Что возвращает |
|---|---|
| `gsc_sites` | ресурсы Search Console, доступные ключу |
| `gsc_query` | клики, показы, CTR, позиция в любых разрезах: запрос, страница, дата, страна, устройство |
| `gsc_cannibalization` | запросы, по которым видны 2+ страницы, с владельцем запроса |
| `gsc_sitemaps` | sitemap в Google: ошибки, дата загрузки |
| `gsc_inspect_url` | индексация страницы, canonical по версии Google, rich results |
| `ya_hosts` | сайты в Вебмастере |
| `ya_summary` | ИКС, страницы в поиске и исключённые, диагностика |
| `ya_search_queries` | запросы в Яндексе: показы, клики, CTR, позиции |
| `ya_indexing_history` | число страниц в поиске и обход роботом по дням |
| `ya_search_events` | страницы, которые появились в поиске или выпали, и причина |
| `ya_sitemaps` | sitemap в Яндексе |
| `wordstat_top` | частотность, вложенные и похожие запросы |
| `wordstat_dynamics` | динамика спроса по месяцам, неделям, дням |
| `wordstat_regions` | спрос по регионам и городам |

Сайт везде можно передавать просто доменом: `example.ru`. Сервер сам найдёт нужный ресурс в GSC (доменный в приоритете) и хост в Вебмастере.

## Устройство

```
.claude-plugin/
  plugin.json            манифест: запуск сервера через uv run, опции → переменные
                         окружения, хосты, метаданные
  marketplace.json       этот же репозиторий как маркетплейс из одного плагина
agents/seo-specialist.md
skills/<имя>/SKILL.md
src/seo_tools/
  server.py              MCP-инструменты: описания и аргументы, без логики
  gsc.py                 Search Console
  webmaster.py           Яндекс.Вебмастер
  wordstat.py            Вордстат (Yandex Cloud)
  config.py              где искать ключи: env → ~/.seo-tools/.env
  sites.py               домен → ресурс GSC / хост Вебмастера
  periods.py             расчёт периодов
  reports.py             сохранение CSV
  http.py                HTTP-клиент на urllib
  cli.py                 seo-tools doctor | paths | yandex-token
tests/
```

Слой `server.py` только описывает инструменты. Клиенты API ничего не знают о MCP, их можно использовать и из обычного скрипта. Чистая логика (разбор адресов, периоды, поиск каннибализации) вынесена в функции без сети и покрыта тестами.

Сервер запускается как дочерний процесс Claude Code по stdio: портов не открывает, в фоне не висит, закрывается вместе с сессией.

## Разработка

```bash
git clone https://github.com/starArsonist/ai-seo-tools
cd ai-seo-tools
uv sync
uv run pytest
uv run seo-tools doctor
```

Поставить плагин из локальной папки, чтобы проверить изменения:

```bash
claude plugin marketplace add ./
claude plugin install seo-tools@ai-seo-tools
```

После правок в коде сервера достаточно переподключить его через `/mcp` или открыть новую сессию. Перед публикацией: `claude plugin validate .`

Если меняется список инструментов, обновите `tools` в [agents/seo-specialist.md](agents/seo-specialist.md) и таблицу выше. Тест `tests/test_server.py` упадёт, если забыть.

## Ограничения

- Только чтение: отправить sitemap, запросить переобход или изменить настройки плагин не может.
- В API Вебмастера нет связки страница-запрос, поэтому каннибализация по Яндексу проверяется косвенно, через title и H1.
- Вордстат показывает спрос Яндекса. Частотности Google у плагина нет.
- GSC отдаёт данные с задержкой 2-3 дня, Вебмастер хранит запросы примерно за 3 месяца.

## Лицензия

MIT, см. [LICENSE](LICENSE).
