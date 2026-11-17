import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_engine
from app.models import AppUser, MemberRole, Project, ProjectMember


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit("usage: python scripts/add_member.py <email> <project_id> <owner|developer|client>")
    email, project_id, role = sys.argv[1].strip().lower(), int(sys.argv[2]), MemberRole(sys.argv[3])
    with Session(get_engine()) as session:
        user = session.scalar(select(AppUser).where(AppUser.email == email))
        if user is None or session.get(Project, project_id) is None:
            sys.exit("user or project not found: the user must register first")
        member = session.get(ProjectMember, (project_id, user.id))
        if member is None:
            session.add(ProjectMember(project_id=project_id, user_id=user.id, role=role))
        else:
            member.role = role
        session.commit()
    print(f"{email} is {role.value} of project {project_id}")


if __name__ == "__main__":
    main()
