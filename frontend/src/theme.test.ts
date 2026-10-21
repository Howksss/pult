import { describe, expect, it } from "vitest";
import { resolveTheme } from "./theme";

describe("resolveTheme", () => {
  it("берёт тему, выбранную пользователем", () => {
    expect(resolveTheme("light", false)).toBe("light");
    expect(resolveTheme("dark", true)).toBe("dark");
  });

  it("без выбора следует системной настройке", () => {
    expect(resolveTheme(null, true)).toBe("light");
    expect(resolveTheme(null, false)).toBe("dark");
  });

  it("игнорирует мусор в хранилище", () => {
    expect(resolveTheme("purple", true)).toBe("light");
  });
});
