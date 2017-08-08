from codenames import (CodenamesBoard, Team, Spymaster, Guesser)
from typing import Dict


def notify_all(channels, tag, speaker, value):
    for channel in channels:
        channel.notify(tag, speaker, value)


def run_game(spymasters: Dict[Team, Spymaster], guessers: Dict[Team, Guesser], board=None):
    if board is None:
        board = CodenamesBoard.generate()
    spymaster_channels = set(spymaster.channel for spymaster in spymasters.values())
    guesser_channels = set(guesser.channel for guesser in guessers.values())
    all_channels = spymaster_channels | guesser_channels
    current_team = Team.red
    while True:
        # If there's a winner, notify players and end the game
        winner = board.winner()
        if winner in (Team.red, Team.blue):
            notify_all(all_channels, 'board', 'Host', board.spy_items())
            notify_all(all_channels, 'winner', 'Host', winner)
            return winner

        # Update the board and get a clue from the spymaster
        spymaster = spymasters[current_team]
        notify_all(all_channels, 'board', 'Host', board.known_items())
        notify_all(all_channels, 'status', 'Host',
                   "%s's turn to give a clue." % spymaster.name())
        clue_number, clue_word = spymaster.get_clue(board)
        notify_all(all_channels, 'clue', spymaster.name(), (clue_number, clue_word))

        # Now it's the guesser's turn.
        guesser = guessers[current_team]
        for guess_number in range(clue_number + 1):
            guess_word = guesser.get_guess(board)
            if guess_word is None:
                notify_all(all_channels, 'status', 'Host',
                           '%s passes.' % guesser.name())
                break
            else:
                notify_all(spymaster_channels, 'status', 'Host',
                           '%s guesses %s.' % (guesser.name(), guess_word))
                picked_color = board.get_word_team(guess_word)
                board.reveal_word(guess_word)
                notify_all(all_channels, 'reveal', 'Host', (guess_word, picked_color))

                if picked_color is Team.assassin:
                    winner = current_team.opponent()
                    notify_all(all_channels, 'board', 'Host', board.spy_items())
                    notify_all(all_channels, 'winner', 'Host', winner)
                    return winner
                elif picked_color != current_team:
                    break

        current_team = current_team.opponent()
