from getpass import getpass

from app.services.auth_service import (
    create_initial_admin,
)


def main():
    print(
        "初期管理者ユーザーを作成します。"
    )

    username = input(
        "ユーザーID: "
    ).strip()

    display_name = input(
        "表示名: "
    ).strip()

    password = getpass(
        "パスワード: "
    )

    password_confirm = getpass(
        "パスワード確認: "
    )

    if password != password_confirm:
        print(
            "パスワードが一致しません。"
        )
        return

    try:
        user = create_initial_admin(
            username=username,
            password=password,
            display_name=(
                display_name
                or None
            ),
        )

    except Exception as e:
        print(
            f"作成に失敗しました: {e}"
        )
        return

    print()
    print(
        "管理者ユーザーを作成しました。"
    )
    print(
        f"ID: {user['id']}"
    )
    print(
        f"ユーザーID: {user['username']}"
    )
    print(
        f"Role: {user['role']}"
    )


if __name__ == "__main__":
    main()