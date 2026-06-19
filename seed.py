"""Initialize the database and seed default users. Idempotent.

Default credentials (CHANGE in a real deployment):
    admin    / ***REMOVED-CREDENTIAL***     (role: admin)
    punonjes / punonjes123  (role: employee)

Run:  .venv\\Scripts\\python.exe seed.py
"""
import doku  # noqa: F401  (sets sys.path)
from doku import auth, db

# (username, password, role, must_change_on_first_login)
DEFAULTS = [
    ("admin", "***REMOVED-CREDENTIAL***", auth.ADMIN, True),       # admin must set a new password
    ("punonjes", "punonjes123", auth.EMPLOYEE, False),
]


def main():
    db.init_db()
    created = []
    for username, password, role, must_change in DEFAULTS:
        if auth.get_user(username) is None:
            auth.create_user(username, password, role, must_change=must_change)
            created.append(f"{username} ({role})")
    print("Baza e të dhënave u inicializua.")
    if created:
        print("U krijuan përdoruesit: " + ", ".join(created))
    else:
        print("Përdoruesit ekzistojnë tashmë — asgjë nuk u ndryshua.")


if __name__ == "__main__":
    main()
