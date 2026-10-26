# ИИ-ассистент: тесты, рефакторинг и риски

Ассистент — **Claude Code** (модель Claude Opus 5.5), агент в терминале, который работает с репозиторием. Общие правила применения ИИ в проекте описаны в [docs/quality/ai-assistants.md](../quality/ai-assistants.md). Главное из них: код от ассистента проходит те же проверки, что и написанный вручную, а автор должен уметь объяснить каждую строку.

Ниже две задачи. В обеих черновик ассистента сохранён как есть, а затем проверен вручную, тестами и мутациями.

## 1. Генерация тестов для `graph_status.py` (#76)

### Промпт

> Напиши pytest-тесты для app/services/graph_status.py: функции as_utc и block_statuses. Для БД используй фикстуру db из tests/conftest.py (sessionmaker на SQLite в памяти). Нужны позитивные и негативные сценарии и граничные случаи: блок без проверок, проверка без результатов, устаревший результат, несколько проверок у блока, наивное время. Модели — в app/models. Без комментариев и докстрингов, стиль как в tests/test_status.py.

Ассистент видел только код Pult: `graph_status.py`, `status.py`, модели, `conftest.py` и `test_status.py`. Секретов и данных пилотной системы в этом репозитории нет.

### Черновик

12 тестов, файл без изменений лежит в [ai/test_graph_status_draft.py](ai/test_graph_status_draft.py). Фрагмент:

```python
@pytest.fixture
def session(db: sessionmaker[Session]):
    with db() as session:
        project = Project(name="demo", repo_full_name="example/demo", probe_token_hash="x")
        session.add(project)
        session.flush()
        yield session, project


def test_as_utc_keeps_aware_datetime():
    krasnoyarsk = timezone(timedelta(hours=7))
    moment = datetime(2026, 10, 27, 19, 0, tzinfo=krasnoyarsk)
    assert as_utc(moment) is moment
    assert as_utc(moment) == NOW


def test_stale_result_is_unknown(session):
    s, project = session
    block = add_block(s, project)
    check = add_check(s, block, interval_sec=60)
    add_result(s, check, CheckStatus.ok, seconds_ago=181)
    assert block_statuses(s, [block.id], NOW) == {block.id: BlockStatus.unknown}
```

### Ручная проверка

**Галлюцинации.** Все импорты существуют, поля моделей настоящие, фикстура `db` есть в `conftest.py`, вызовы pytest верные. Выдуманных API нет. `probe_token_hash="x"` для теста не нужен, но и не мешает.

**Прогон.** Ruff без замечаний, 12 из 12 тестов прошли с первого раза, покрытие `graph_status.py` выросло с 92 % до 100 %.

**Мутации.** Прошедшие тесты ещё не значат, что они что-то проверяют. Поэтому в `graph_status.py` по очереди вносились ошибки и смотрелось, упадёт ли хоть один тест. Скрипт: [ai/mutate.py](ai/mutate.py), запуск `cd backend && python ../docs/module4/ai/mutate.py tests/test_graph_status.py`.

| Мутант | Что сломано | Черновик | После правок |
|---|---|---|---|
| M1 | проверка без результатов пропускается (`continue` вместо `append(None)`) | пойман 1 тестом | пойман |
| M2 | берётся самый старый результат (`asc` вместо `desc`) | пойман | пойман |
| M3 | наивное время считается местным (`astimezone` вместо `replace`) | пойман | пойман* |
| M4 | блоки без проверок выпадают из ответа | пойман | пойман |
| M5 | вместо интервала проверки берётся таймаут | **выжил** | пойман |

\* M3 ловится только при ненулевом смещении местного времени. На этом ПК UTC+8, а на раннере CI время в UTC, и там мутант выживет.

**Что нашлось при чтении:**

| Где | Проблема | Что сделано |
|---|---|---|
| `test_stale_result_is_unknown` | Граница устаревания проверена только с одной стороны (181 с). Поэтому выжил M5: при таймауте 10 с результат 181 с назад тоже устаревший | Параметризованный тест: 180 с — ok, 181 с — unknown |
| `test_check_without_results_is_unknown` | Покрывает строку 35, но M1 не ловит: блок без проверок тоже `unknown`. Покрытие есть, проверки нет | Оставлен как документирующий. M1 ловит `test_check_without_results_hides_ok_check` |
| `test_as_utc_keeps_aware_datetime` | `as_utc(moment) is moment` проверяет реализацию, а не поведение: переход на `astimezone(UTC)` сломал бы тест без изменения результата | Проверка `is` убрана, сравнивается момент времени |
| фикстура `session` | Возвращает кортеж `(session, project)`, в каждом тесте `s, project = session`. Читается плохо | Две фикстуры, `session` и `project` |
| помощники `add_block` и др. | Нет типов, хотя в `test_status.py` помощники типизированы | Типы добавлены |
| `test_naive_now_is_rejected` | `pytest.raises(ValueError)` без `match` пропустит любую другую `ValueError` | `match="timezone-aware"` |

Итог: [tests/test_graph_status.py](../../backend/tests/test_graph_status.py), 13 тестов, все пять мутантов пойманы. Весь backend: 84 теста, покрытие 99.39 %.

**Ещё одно наблюдение.** Тесты идут на SQLite, а он теряет смещение часового пояса:

```
записано:            2026-10-27T19:00:00+07:00 = 2026-10-27T12:00:00+00:00
прочитано из SQLite: 2026-10-27T19:00:00
```

После `as_utc` это 19:00 UTC, на семь часов позже. Ассистент тесты с поясами в БД не писал, но если бы написал, на SQLite они проверяли бы не то. Поэтому все времена в тестах заданы в UTC, а пояса проверяют тесты на PostgreSQL (`test_pg_*`).

## 2. Рефакторинг `submit_results` (#75)

### Промпт

> Pylint ругается на submit_results в backend/app/api/probe.py: too-many-locals (18/15) и два unnecessary-comprehension. Сделай функцию читаемее: вынеси шаги в отдельные функции. Поведение не менять: тот же ответ, те же коды ошибок, статусы «до» считаются до записи результатов, уведомления — только после commit. Без комментариев и докстрингов.

### До

Одна функция на 50 строк: аутентификация, проверка принадлежности проверок проекту, запись, расчёт изменений статусов и отправка уведомлений.

```python
    owned = {check_id: block_id for check_id, block_id in rows}
    ...
    if notable and notifier.enabled:
        name_rows = session.execute(
            select(Block.id, Block.name).where(Block.id.in_([change.block_id for change in notable]))
        ).all()
        names = {block_id: name for block_id, name in name_rows}
        for change in notable:
            notifier.send(...)
```

### Черновик ассистента

Три функции и короткий обработчик. Генераторы словарей заменены на `dict(...)`, как советует Pylint:

```python
def owned_checks(session: Session, project: Project, check_ids: set[int]) -> dict[int, int]:
    rows = session.execute(
        select(HealthCheck.id, HealthCheck.block_id)
        .join(Block, Block.id == HealthCheck.block_id)
        .where(HealthCheck.id.in_(check_ids), Block.project_id == project.id)
    ).all()
    owned = dict(rows)
    ...

def notify(session: Session, notifier: TelegramNotifier, project: Project, changes: list[StatusChange]) -> None:
    ...
```

### Ручная проверка

| Шаг | Результат |
|---|---|
| Тесты | 71 из 71 прошли, покрытие `probe.py` 100 % |
| Ruff | `E501`: подпись `notify` длиной 112 символов при пределе 110 |
| mypy strict | **4 ошибки**: `Argument 1 to "dict" has incompatible type "Sequence[Row[tuple[int, int]]]"`. В типах SQLAlchemy `Row` не является кортежем, хотя ведёт себя как кортеж |
| Первая правка: `dict(session.execute(...).tuples())` | mypy доволен, но **4 теста упали**: `TypeError: 'ChunkedIteratorResult' object is not subscriptable`. У объекта `Result` есть метод `keys()`, поэтому `dict()` считает его отображением и обращается по ключу, а не перебирает пары |
| Вторая правка: `dict(session.execute(...).tuples().all())` | список кортежей: mypy, Ruff, Pylint 10.00/10, все тесты зелёные |
| Порядок операций | Самое опасное место такого рефакторинга — статусы «до» должны считаться до `add_all`, иначе autoflush запишет новые результаты и «до» совпадёт с «после». Для проверки строка с `before` перенесена после `add_all`: упали `test_probe_reports_status_changes`, `test_probe_accepts_naive_time_as_utc` и `test_probe_failure_sends_message`. Значит, порядок защищён тестами |
| Ошибки и уведомления | 422 по-прежнему выбрасывается до любой записи, уведомления уходят после `commit`, запрос имён блоков делается только когда есть что отправить и Telegram настроен |

### После

```python
@router.post("/results", response_model=ProbeAccepted, status_code=202)
def submit_results(
    payload: ProbeBatchIn,
    session: SessionDep,
    notifier: NotifierDep,
    x_probe_token: Annotated[str | None, Header()] = None,
) -> ProbeAccepted:
    project = authenticate(session, x_probe_token)
    owned = owned_checks(session, project, {result.health_check_id for result in payload.results})
    changes = record_results(session, payload, sorted(set(owned.values())))
    notify(session, notifier, project, changes)
    return ProbeAccepted(accepted=len(payload.results), status_changes=changes)
```

Полный код — `backend/app/api/probe.py`, коммит 16610af.

Докстрингов и комментариев ассистент не добавлял: промпт это запрещал, и в проекте их нет, объяснения живут в `docs/` и ADR. Вариант «сгенерировать docstring» из задания поэтому не применялся, вместо него сделан рефакторинг для читаемости.

## Ограничения и риски

Что проявилось в этих двух задачах:

| Проблема | Как проявилась | Как ловить |
|---|---|---|
| Совет анализатора выполнен буквально | `dict(rows)` по подсказке Pylint сломал проверку типов | mypy strict в CI |
| Типы не гарантируют поведение | `dict(result.tuples())` прошёл mypy и упал при запуске | тесты на каждую правку, не только статический анализ |
| Покрытие не равно проверке | Строка 35 покрыта тестом, который ошибку в ней не ловит | мутации, чтение утверждений в тестах |
| Граница с одной стороны | Выжил мутант M5 | в промпте называть границы явно, проверять обе стороны |
| Тест привязан к реализации | `assert as_utc(moment) is moment` | на ревью спрашивать: «упадёт ли тест, если поведение не изменится?» |
| Зависимость от окружения | SQLite теряет пояс; M3 ловится только не в UTC | время в тестах в UTC, пояса — на PostgreSQL в CI |
| Неточный промпт | «Граничные случаи» без значений: ассистент выбрал одну сторону | перечислять в промпте конкретные значения и требования (FR-09) |

Общие риски:

- **Конфиденциальность.** Ассистент читает всё, что лежит в рабочей папке, и отправляет фрагменты в API Anthropic. Поэтому `.env` и ключи в репозиторий не попадают (`.gitignore`, хук `detect-private-key`), а код и данные пилотной системы лежат в отдельном закрытом репозитории и ассистенту не передаются.
- **Выдуманные API и устаревшие версии.** В этот раз не встретились, но риск остаётся: ассистент может предложить параметр из другой версии библиотеки. Версии зафиксированы в `requirements*.txt` и `package-lock.json`, сверять нужно с ними.
- **Правка шире задачи.** Агент может «заодно» поменять соседний код. Каждая правка смотрится через `git diff` до коммита. Здесь оба изменения затронули только `probe.py` и новый файл тестов.
- **Уязвимый код.** Ассистент может собрать SQL строкой или записать секрет в лог. Это ловят правила Ruff `S` (bandit), CodeQL и тест `test_bot_token_never_reaches_logs`.
- **Понимание собственного кода.** Принимать только то, что могу объяснить. Для обеих задач объяснение записано в этом файле.

## Вывод

Ассистент быстро делает рабочий черновик: 12 тестов, которые сразу прошли, и разумное разбиение функции. Но в обоих случаях черновик был неверным в мелочах, которые без проверки ушли бы в main: ошибка типов, ошибка при выполнении, тест, который ничего не ловит. Помогают три вещи: тесты на любую правку, мутации для оценки самих тестов и чтение каждого утверждения в коде.
