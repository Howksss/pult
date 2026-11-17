import { useCallback, useEffect, useState } from "react";
import { defaultMembersApi, type Member, type MemberRole, type MembersApi } from "../api";
import { Icon } from "./Icon";

const ROLE_LABELS: Record<MemberRole, string> = {
  owner: "владелец",
  developer: "разработчик",
  client: "заказчик",
};

const ROLES: MemberRole[] = ["owner", "developer", "client"];

const MESSAGES: Record<string, string> = {
  "no user with this email: ask them to register first":
    "Такого пользователя нет: пусть сначала зарегистрируется",
  "already a member of the project": "Уже участник проекта",
  "the project must keep at least one owner": "В проекте должен остаться хотя бы один владелец",
};

interface MembersPanelProps {
  projectId: number;
  myRole: MemberRole;
  onClose: () => void;
  api?: MembersApi;
}

export function MembersPanel({
  projectId,
  myRole,
  onClose,
  api = defaultMembersApi,
}: MembersPanelProps) {
  const [members, setMembers] = useState<Member[] | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<MemberRole>("client");
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((value) => value + 1), []);
  const owner = myRole === "owner";

  useEffect(() => {
    api
      .list(projectId)
      .then(setMembers)
      .catch(() => setError("Не удалось загрузить участников"));
  }, [api, projectId, version]);

  const run = (action: () => Promise<unknown>) => {
    setError(null);
    action()
      .then(reload)
      .catch((reason: unknown) => {
        const text = reason instanceof Error ? reason.message : String(reason);
        setError(MESSAGES[text] ?? text);
      });
  };

  return (
    <div className="members" role="dialog" aria-label="Участники проекта">
      <header className="members__head">
        <h2 className="members__title">Участники</h2>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Закрыть">
          <Icon name="close" size={18} />
        </button>
      </header>
      <ul className="members__list">
        {(members ?? []).map((member) => (
          <li key={member.user_id} className="members__item">
            <span className="members__who">
              <span className="members__name">{member.full_name}</span>
              <span className="members__email">{member.email}</span>
            </span>
            {owner ? (
              <>
                <select
                  className="scope__access"
                  value={member.role}
                  aria-label={`Роль ${member.email}`}
                  onChange={(event) =>
                    run(() =>
                      api.update(projectId, member.user_id, event.target.value as MemberRole),
                    )
                  }
                >
                  {ROLES.map((value) => (
                    <option key={value} value={value}>
                      {ROLE_LABELS[value]}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="icon-button scope__remove"
                  aria-label={`Убрать ${member.email}`}
                  onClick={() => run(() => api.remove(projectId, member.user_id))}
                >
                  <Icon name="close" size={16} />
                </button>
              </>
            ) : (
              <span className="members__role">{ROLE_LABELS[member.role]}</span>
            )}
          </li>
        ))}
      </ul>
      {owner && (
        <form
          className="scope-form"
          aria-label="Добавить участника"
          onSubmit={(event) => {
            event.preventDefault();
            if (email.trim()) {
              run(() => api.add(projectId, email.trim(), role).then(() => setEmail("")));
            }
          }}
        >
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="email участника"
            aria-label="Email участника"
          />
          <select
            value={role}
            onChange={(event) => setRole(event.target.value as MemberRole)}
            aria-label="Роль"
          >
            {ROLES.map((value) => (
              <option key={value} value={value}>
                {ROLE_LABELS[value]}
              </option>
            ))}
          </select>
          <button type="submit" className="text-button">
            Добавить
          </button>
        </form>
      )}
      {error && (
        <p className="check-form__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
