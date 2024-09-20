class Message:
    def __init__(self, text: str, date: str, author: str = "Владелец команды", team_name :str = 'Команда'):
        self.text = text
        self.date = date
        self.author = author
        self.team_name = team_name

    def __str__(self):
        return f'{self.author}', f'{self.date}', f'{self.text}'







