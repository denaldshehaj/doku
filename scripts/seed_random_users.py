"""Create random demo users (for testing the users table / pagination).

Run:  .venv\\Scripts\\python.exe scripts\\seed_random_users.py [count]
Default count = 25. Password for all: demo123. Idempotent on usernames.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import auth, database  # noqa: E402

FIRST = ["Arben", "Elira", "Besnik", "Mira", "Genti", "Albana", "Drini", "Teuta",
         "Fatjon", "Vera", "Ardit", "Iliriana", "Klodian", "Suela", "Endrit",
         "Blerta", "Gazmend", "Rovena", "Sokol", "Anila", "Edon", "Majlinda",
         "Ferdinand", "Donika", "Lulzim", "Erjona"]
LAST = ["Hoxha", "Krasniqi", "Shehu", "Berisha", "Gjoka", "Dervishi", "Leka",
        "Prifti", "Bardhi", "Zeqiri", "Marku", "Halili", "Nika", "Doci",
        "Rama", "Cela", "Kola", "Toska", "Vata", "Lleshi"]

PASSWORD = "demo123"


def main(count: int = 25):
    database.init_schema()
    auth.ensure_default_admin()
    created = 0
    used = set()
    attempts = 0
    while created < count and attempts < count * 20:
        attempts += 1
        first, last = random.choice(FIRST), random.choice(LAST)
        base = f"{first}.{last}".lower()
        uname = base if base not in used else f"{base}{random.randint(1, 999)}"
        used.add(uname)
        # ~1 in 6 is an admin, the rest are employees.
        role = auth.ADMIN if random.randint(1, 6) == 1 else auth.PUNONJES
        try:
            auth.create_user(uname, PASSWORD, f"{first} {last}", role,
                             must_change=False)
            created += 1
            print(f"  + {uname} ({role})")
        except ValueError:
            continue  # duplicate username, try another
    print(f"U krijuan {created} përdorues. Fjalëkalimi për të gjithë: {PASSWORD}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 25
    main(n)
