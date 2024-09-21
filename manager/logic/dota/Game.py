import random

def determine_winner(team1, team2):
    """Определяет победителя между двумя командами случайным образом."""
    winner = random.choice([team1, team2])
    return winner