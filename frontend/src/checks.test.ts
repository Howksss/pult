import { describe, expect, it } from "vitest";
import {
  buildConfig,
  checksCount,
  cronLine,
  excerpt,
  facts,
  formatAgo,
  formatDuration,
  plural,
} from "./checks";

const NOW = new Date("2026-11-17T08:00:00Z");

describe("plural", () => {
  const forms: [string, string, string] = ["проверка", "проверки", "проверок"];

  it.each([
    [1, "проверка"],
    [2, "проверки"],
    [5, "проверок"],
    [11, "проверок"],
    [21, "проверка"],
    [24, "проверки"],
  ])("%i — %s", (count, word) => {
    expect(plural(count, forms)).toBe(word);
  });
});

describe("checksCount", () => {
  it("коротко для блока и полностью для подсказки", () => {
    expect(checksCount(1, 3)).toEqual({ short: "1 из 3", full: "Проблемы в 1 из 3 проверок" });
    expect(checksCount(0, 2)).toEqual({ short: "2 проверки", full: "Все 2 проверки проходят" });
  });
});

describe("formatDuration", () => {
  it.each([
    [180, "180 мс"],
    [2400, "2,4 с"],
    [48210, "48,2 с"],
    [72_000, "1 мин 12 с"],
    [120_000, "2 мин"],
  ])("%i мс — %s", (ms, text) => {
    expect(formatDuration(ms)).toBe(text);
  });
});

describe("formatAgo", () => {
  it.each([
    ["2026-11-17T07:59:40Z", "только что"],
    ["2026-11-17T07:35:00Z", "25 мин назад"],
    ["2026-11-17T05:00:00Z", "3 ч назад"],
    ["2026-11-17T08:00:30Z", "только что"],
  ])("%s — %s", (iso, text) => {
    expect(formatAgo(iso, NOW)).toBe(text);
  });

  it("давнее показывает датой", () => {
    expect(formatAgo("2026-11-10T08:00:00Z", NOW)).toBe("10.11.2026");
  });
});

describe("facts", () => {
  it("раскладывает подробности HTTP по-человечески", () => {
    expect(
      facts({
        url: "https://pos.example/old",
        final_url: "https://pos.example/new",
        status_code: 502,
        reason: "Bad Gateway",
        latency_ms: 1234,
        method: "GET",
      }),
    ).toEqual([
      { label: "Код ответа", value: "502 Bad Gateway" },
      { label: "Адрес", value: "https://pos.example/old → https://pos.example/new" },
      { label: "Метод", value: "GET" },
      { label: "Время ответа", value: "1,2 с" },
    ]);
  });

  it("сертификат: хост с портом, дата и выпускающий", () => {
    expect(
      facts({
        host: "pos.example",
        port: 443,
        not_after: "2026-11-26T08:00:00+00:00",
        days_left: 9,
      }),
    ).toEqual([
      { label: "Хост", value: "pos.example:443" },
      { label: "Осталось дней", value: "9" },
      { label: "Действует до", value: "26.11.2026" },
    ]);
  });

  it("незнакомые поля показывает как есть, выдержки и пустые пропускает", () => {
    expect(
      facts({ host: "db", queue: { size: 3 }, stderr_tail: "boom", empty: null, not_after: "x" }),
    ).toEqual([
      { label: "Хост", value: "db" },
      { label: "Действует до", value: "x" },
      { label: "queue", value: '{"size":3}' },
    ]);
  });

  it("без подробностей пусто", () => {
    expect(facts(null)).toEqual([]);
  });
});

describe("excerpt", () => {
  it("берёт stderr, ответ сервера или строки лога", () => {
    expect(excerpt({ stderr_tail: "KeyError: 'store_id'" })).toEqual({
      label: "Вывод stderr",
      text: "KeyError: 'store_id'",
    });
    expect(excerpt({ body_excerpt: "upstream error" })?.label).toBe("Ответ сервера");
    expect(excerpt({ lines: ["ConfigError: a", "ConfigError: b"] })).toEqual({
      label: "Строки лога",
      text: "ConfigError: a\nConfigError: b",
    });
  });

  it("пустые выдержки не показывает", () => {
    expect(excerpt({ lines: [], stderr_tail: "  " })).toBeNull();
    expect(excerpt(null)).toBeNull();
  });
});

describe("buildConfig и cronLine", () => {
  const empty = {
    contains: "",
    warn_latency_ms: "",
    expect_status: "",
    warn_days: "",
    fail_days: "",
  };

  it("пустые поля HTTP не попадают в настройки", () => {
    expect(buildConfig("http", empty)).toEqual({});
    expect(buildConfig("tcp", empty)).toEqual({});
  });

  it("строка для cron по типу проверки", () => {
    expect(cronLine({ id: 3, method: "exit_code", target: "python main.py" })).toBe(
      "pult-run 3 python main.py",
    );
    expect(cronLine({ id: 9, method: "log_pattern", target: "ConfigError" })).toBe(
      `pult-run 9 sh -c '! grep -q "ConfigError" /var/log/app.log'`,
    );
    expect(cronLine({ id: 1, method: "heartbeat", target: "cron" })).toBe("pult-run 1 true");
  });
});
