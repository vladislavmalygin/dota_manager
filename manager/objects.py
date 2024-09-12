import sqlite3

class Team:
    def __init__(self, id, name, country, fame, owner_character, logo_id, achievements, budget):
        self.id = id
        self.name = name
        self.country = country
        self.fame = fame
        self.owner_character = owner_character
        self.logo_id = logo_id
        self.achievements = achievements
        self.budget = budget

    def save_to_db(self):
        conn = sqlite3.connect('game_database.db')
        cursor = conn.cursor()

        if self.id is None:  # Новый объект команды
            cursor.execute('''
            INSERT INTO Teams (name, country, fame, owner_character, logo_id, achievements, budget)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (self.name, self.country, self.fame, self.owner_character, self.logo_id, self.achievements, self.budget))
            self.id = cursor.lastrowid  # Получаем последний вставленный id
        else:  # Обновление существующей команды
            cursor.execute('''
            UPDATE Teams SET name=?, country=?, fame=?, owner_character=?, logo_id=?, achievements=?, budget=?
            WHERE id=?
            ''', (self.name, self.country, self.fame, self.owner_character, self.logo_id, self.achievements, self.budget, self.id))

        conn.commit()
        conn.close()


class Manager:
    def __init__(self, id, team_id, name, surname, nickname, fame):
        self.id = id
        self.team_id = team_id
        self.name = name
        self.surname = surname
        self.nickname = nickname
        self.fame = fame

    def save_to_db(self):
        conn = sqlite3.connect('game_database.db')
        cursor = conn.cursor()

        if self.id is None:  # Новый менеджер
            cursor.execute('''
            INSERT INTO Managers (team_id, name, surname, nickname, fame)
            VALUES (?, ?, ?, ?, ?)
            ''', (self.team_id, self.name, self.surname, self.nickname, self.fame))
            self.id = cursor.lastrowid  # Получаем последний вставленный id
        else:  # Обновление существующего менеджера
            cursor.execute('''
            UPDATE Managers SET team_id=?, name=?, surname=?, nickname=?, fame=?
            WHERE id=?
            ''', (self.team_id, self.name, self.surname, self.nickname, self.fame, self.id))

        conn.commit()
        conn.close()


class GameSave:
    def __init__(self, id, team_id, save_data):
        self.id = id
        self.team_id = team_id
        self.save_data = save_data

    def save_to_db(self):
        conn = sqlite3.connect('game_database.db')
        cursor = conn.cursor()

        if self.id is None:  # Новая игра
            cursor.execute('''
            INSERT INTO GameSaves (team_id, save_data)
            VALUES (?, ?)
            ''', (self.team_id, self.save_data))
            self.id = cursor.lastrowid  # Получаем последний вставленный id
        else:  # Обновление существующей игры
            cursor.execute('''
            UPDATE GameSaves SET team_id=?, save_data=?
            WHERE id=?
            ''', (self.team_id, self.save_data, self.id))

        conn.commit()
        conn.close()


class Logo:
    def __init__(self, id):
        self.id = id

    def save_to_db(self):
        # Реализация сохранения логотипа в базу данных (если необходимо)
        pass


class Sponsor:
    def __init__(self, id, money, fame, expected_results):
        self.id = id
        self.money = money
        self.fame = fame
        self.expected_results = expected_results

    def save_to_db(self):
        conn = sqlite3.connect('game_database.db')
        cursor = conn.cursor()

        if self.id is None:  # Новый спонсор
            cursor.execute('''
            INSERT INTO Sponsors (money, fame, expected_results)
            VALUES (?, ?, ?)
            ''', (self.money, self.fame, self.expected_results))
            self.id = cursor.lastrowid  # Получаем последний вставленный id
        else:  # Обновление существующего спонсора
            cursor.execute('''
            UPDATE Sponsors SET money=?, fame=?, expected_results=?
            WHERE id=?
            ''', (self.money, self.fame, self.expected_results, self.id))

        conn.commit()
        conn.close()
