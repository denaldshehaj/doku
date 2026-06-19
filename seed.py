"""Initialize the DOKU database (tables + migrations). Idempotent.

No default users are created — accounts are created via the registration form in
the app. The FIRST account registered becomes the administrator; later accounts
are employees.

Run:  .venv\\Scripts\\python.exe seed.py
"""
import doku  # noqa: F401  (sets sys.path)
from doku import auth, db


def main():
    db.init_db()
    print("Baza e të dhënave u inicializua.")
    if auth.has_admin():
        print("Ekziston tashmë një administrator.")
    else:
        print("Nuk ka ende administrator — regjistrohu te aplikacioni; "
              "llogaria e parë bëhet administrator.")


if __name__ == "__main__":
    main()
