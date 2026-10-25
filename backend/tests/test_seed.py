from unittest.mock import patch

from werkzeug.security import check_password_hash

from seed import DEMO_ACCOUNTS, seed_demo_users


def test_seed_demo_users_hashes_passwords_and_reports_created_accounts():
    with patch(
        "seed.store.create_user_if_missing", side_effect=[True, False]
    ) as create:
        created_count = seed_demo_users()

    assert created_count == 1
    assert create.call_count == len(DEMO_ACCOUNTS)
    for (email, password), recorded_call in zip(
        DEMO_ACCOUNTS, create.call_args_list
    ):
        stored_email, password_hash = recorded_call.args
        assert stored_email == email
        assert password_hash != password
        assert check_password_hash(password_hash, password)
