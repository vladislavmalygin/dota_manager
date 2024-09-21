import random
from invites import invites


def worldcup_system_draw(db_name):
    teams = invites(db_name)
    random.shuffle(teams)

    # Делим на 4 группы по 4 команды
    groups = [teams[i:i + 4] for i in range(0, len(teams), 4)]

    return groups


# Пример использования функции
if __name__ == "__main__":
    groups = worldcup_system_draw('test_database.db')
    for i, group in enumerate(groups):
        print(f"Группа {i + 1}: {group}")
