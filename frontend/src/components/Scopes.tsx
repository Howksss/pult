import { useCallback, useEffect, useState, type FormEvent } from "react";
import { defaultScopesApi, type Scope, type ScopeAccess, type ScopesApi } from "../api";
import { Icon } from "./Icon";

const ACCESS_LABELS: Record<ScopeAccess, string> = {
  read: "чтение",
  write: "запись",
};

interface ScopesPanelProps {
  blockId: number;
  api?: ScopesApi;
}

export function ScopesPanel({ blockId, api = defaultScopesApi }: ScopesPanelProps) {
  const [scopes, setScopes] = useState<Scope[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [path, setPath] = useState("");
  const [access, setAccess] = useState<ScopeAccess>("read");
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((value) => value + 1), []);

  useEffect(() => {
    setScopes(null);
    setFailed(false);
    setError(null);
  }, [blockId]);

  useEffect(() => {
    const controller = new AbortController();
    api
      .load(blockId, controller.signal)
      .then((result) => {
        setScopes(result);
        setFailed(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setFailed(true);
        }
      });
    return () => controller.abort();
  }, [blockId, api, version]);

  const run = (action: () => Promise<unknown>) => {
    setError(null);
    action()
      .then(reload)
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : String(reason)),
      );
  };

  const add = (event: FormEvent) => {
    event.preventDefault();
    if (path.trim()) {
      run(() => api.create(blockId, path.trim(), access).then(() => setPath("")));
    }
  };

  return (
    <section className="inspector__section">
      <h3 className="inspector__heading">
        Область агента
        {scopes && <span className="inspector__heading-count">{scopes.length}</span>}
      </h3>
      {failed && !scopes && <p className="inspector__empty">Не удалось загрузить область</p>}
      {scopes && scopes.length === 0 && (
        <p className="inspector__empty">Путей нет: агенту этот блок недоступен</p>
      )}
      {scopes && scopes.length > 0 && (
        <ul className="scope-list">
          {scopes.map((scope) => (
            <li key={scope.id} className="scope">
              <code className="scope__path">{scope.path_glob}</code>
              <select
                className="scope__access"
                value={scope.access}
                aria-label={`Право на ${scope.path_glob}`}
                onChange={(event) =>
                  run(() => api.update(scope.id, event.target.value as ScopeAccess))
                }
              >
                <option value="read">{ACCESS_LABELS.read}</option>
                <option value="write">{ACCESS_LABELS.write}</option>
              </select>
              <button
                type="button"
                className="icon-button scope__remove"
                aria-label={`Убрать ${scope.path_glob}`}
                onClick={() => run(() => api.remove(scope.id))}
              >
                <Icon name="close" size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}
      <form className="scope-form" onSubmit={add} aria-label="Добавить путь">
        <input
          value={path}
          onChange={(event) => setPath(event.target.value)}
          placeholder="pipeline/** или config.yaml"
          aria-label="Путь в репозитории"
          maxLength={300}
        />
        <select
          value={access}
          onChange={(event) => setAccess(event.target.value as ScopeAccess)}
          aria-label="Право"
        >
          <option value="read">{ACCESS_LABELS.read}</option>
          <option value="write">{ACCESS_LABELS.write}</option>
        </select>
        <button type="submit" className="text-button">
          Добавить
        </button>
      </form>
      {error && (
        <p className="check-form__error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
