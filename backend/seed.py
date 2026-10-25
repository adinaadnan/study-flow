from werkzeug.security import generate_password_hash

import store


DEMO_ACCOUNTS = (
    ("adina@test.com", "studentplanner123"),
    ("sarah@test.com", "studentplanner123"),
)


def seed_demo_users() -> int:
    created_count = 0
    for email, password in DEMO_ACCOUNTS:
        password_hash = generate_password_hash(password)
        if store.create_user_if_missing(email, password_hash):
            created_count += 1
    return created_count


if __name__ == "__main__":
    created_count = seed_demo_users()
    print(f"Created {created_count} of {len(DEMO_ACCOUNTS)} demo accounts.")
