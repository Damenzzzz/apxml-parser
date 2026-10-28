# apxml-parser

Парсер учебных курсов с [apxml.com/courses](https://apxml.com/courses): курсы, главы и тексты уроков сохраняются в SQLite.

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Запуск

```bash
python -m apxml catalog     # список курсов и обложки, Playwright, ~30 сек
python -m apxml courses     # главы и уроки каждого курса, httpx, ~1.5 мин
python -m apxml lessons     # тексты уроков, httpx в 4 потока, ~50 мин
python -m apxml extract     # код, диаграммы, графики и таблицы из уроков, без интернета
python -m apxml stats       # что уже есть в базе
python -m apxml export      # data/lessons.jsonl вместе с блоками
```

Полезные флаги:

```bash
python -m apxml lessons --limit 100
python -m apxml lessons --course basics-model-evaluation-metrics
python -m apxml lessons --workers 2
python -m apxml courses --slug advanced-pytorch
```

Каждый шаг можно остановить через Ctrl+C и запустить снова: парсер продолжит с того места, где остановился. Уроки с ошибкой скачиваются повторно при следующем запуске.

## Как это работает

| Шаг | Инструмент | Почему |
|---|---|---|
| Каталог `/courses?page=N` | Playwright | карточки курсов рисуются в браузере через JavaScript |
| Страница курса | httpx | сервер отдаёт готовый HTML, в боковом меню всё дерево глав и уроков |
| Страница урока | httpx + 4 потока | текст урока лежит в `div.course-content`, сервер отвечает ~1.7 сек, поэтому качаем параллельно |

| Блоки урока | `extract` по сохранённому HTML | всё уже лежит в `content_html`, повторно качать не нужно |
| Обложки курсов | httpx | ссылки на S3 живут около часа, поэтому качаются сразу в `catalog` |

Квизы (`/quiz`) пропускаются: они интерактивные и без текста.

Диаграммы и графики на сайте не картинки, а исходники, которые браузер рисует сам:

| Блок | Где на странице | Что сохраняется в `content` |
|---|---|---|
| `code` | `<pre><code class="language-python">` | код, язык в `language` |
| `diagram` | `div.graphviz-container[data-graph-definition]` | исходник Graphviz (DOT) |
| `chart` | `div.plotly-container[data-plot-definition]` | JSON Plotly с данными и осями |
| `table` | `<table>` | строки таблицы в JSON |

Подпись диаграммы или графика берётся из `<blockquote>` сразу после него и лежит в `caption`.

## Структура

```
apxml/
  config.py     настройки: адрес сайта, база, потоки, задержки
  fetcher.py    httpx с повторами и Playwright для каталога
  parsers.py    разбор каталога, курса и урока
  db.py         таблицы SQLite и сохранение
  commands.py   команды catalog, courses, lessons, stats, export
  __main__.py   CLI
```

## База `data/apxml.db`

- `courses` — slug, название, описание, категория, уровень, длительность, пререквизиты, автор, `cover_path`
- `chapters` — главы курса по порядку
- `lessons` — уроки: `content_html`, `content_text` (формулы как `$...$`), `word_count`, `status` (`pending` / `done` / `empty` / `error`)
- `blocks` — код, диаграммы, графики и таблицы урока: `kind`, `language`, `content`, `caption`, `position`

Обложки лежат в `data/images/covers/`.

```bash
sqlite3 data/apxml.db "SELECT level, COUNT(*) FROM courses GROUP BY level"
sqlite3 data/apxml.db "SELECT language, COUNT(*) FROM blocks WHERE kind = 'code' GROUP BY language"
```
