import sys
from typing import List, Tuple, Optional, IO

from blessings import Terminal

from codenames import (Team, CodenamesBoard, Guesser, Channel)
from codenames.ai import AISpymaster, DummySpymaster
from codenames.gameplay import run_game


def justify(word):
    return ' ' + word.ljust(15)


class FileStreamChannel(Channel):
    def __init__(self, stream: IO[str]):
        self.stream = stream

    @staticmethod
    def open_filename(filename: str):
        stream = open(filename, 'w', encoding='utf-8')
        return FileStreamChannel(stream)

    @staticmethod
    def open_stdout():
        return FileStreamChannel(sys.stdout)

    def close(self):
        if self.stream is not sys.stdout:
            self.stream.close()

    def notify(self, tag: str, speaker: str, value):
        term = Terminal()
        if tag == 'board':
            self.show_board(value)
        elif tag == 'status':
            print('[%s] %s' % (speaker, value), file=self.stream)
        elif tag == 'winner':
            name = value.name.title()
            print('%s wins.' % name, file=self.stream)
        elif tag == 'clue':
            number, word = value
            print('[%s] Clue: %s %d' % (speaker, word, number), file=self.stream)
        elif tag == 'reveal':
            word, team = value
            if team is Team.red:
                shown_category = term.red('red')
            elif team is Team.blue:
                shown_category = term.blue('blue')
            elif team is Team.neutral:
                shown_category = term.yellow('neutral')
            elif team is Team.assassin:
                shown_category = term.reverse('the assassin')
            else:
                raise ValueError(team)
            status = '%s is %s.' % (word, shown_category)
            print('[%s] %s' % (speaker, status), file=self.stream)
        else:
            print('[%s] %s: %s' % (speaker, tag, value), file=self.stream)
        self.stream.flush()

    def show_board(self, items: List[Tuple[str, Team]]):
        term = Terminal()
        for i, (word, team) in enumerate(items):
            jword = word[:11]
            if team is Team.unknown:
                print(justify(jword), end='', file=self.stream)
            elif team is Team.red:
                print(term.red(justify(jword + ' [r]')), end='', file=self.stream)
            elif team is Team.blue:
                print(term.blue(justify(jword + ' [b]')), end='', file=self.stream)
            elif team is Team.neutral:
                print(term.yellow(justify(jword + ' [n]')), end='', file=self.stream)
            elif team is Team.assassin:
                print(term.reverse(justify(jword + ' [a]')), end='', file=self.stream)
            if i % 5 == 4:
                print('\n', file=self.stream)

    def await_input(self, prompt: str):
        print(prompt, file=self.stream)
        response = input('> ')
        return response


class HumanConsoleGuesser(Guesser):
    def name(self):
        return "%s guesser" % self.team.name.title()

    def get_guess(self, board: CodenamesBoard) -> Optional[str]:
        valid = board.valid_guesses()
        prompt = "%s, type a word or 'pass':" % self.name()
        while True:
            reply = self.channel.await_input(prompt).upper()
            if reply == 'PASS':
                return None
            elif reply in valid:
                return reply
            else:
                prompt = '%r is not an available word.' % reply


def custom_game(board):
    spymaster_channel = FileStreamChannel.open_filename('/tmp/codenames.log')
    spymasters = {
        Team.red: AISpymaster(Team.red, spymaster_channel),
        Team.blue: AISpymaster(Team.blue, spymaster_channel)
    }

    guesser_channel = FileStreamChannel.open_stdout()
    guessers = {
        Team.red: HumanConsoleGuesser(Team.red, guesser_channel),
        Team.blue: HumanConsoleGuesser(Team.blue, guesser_channel)
    }

    run_game(spymasters, guessers, board=board)


def main():
    spymaster_channel = FileStreamChannel.open_filename('/tmp/codenames.log')
    spymasters = {
        Team.red: AISpymaster(Team.red, spymaster_channel),
        Team.blue: AISpymaster(Team.blue, spymaster_channel)
    }

    guesser_channel = FileStreamChannel.open_stdout()
    guessers = {
        Team.red: HumanConsoleGuesser(Team.red, guesser_channel),
        Team.blue: HumanConsoleGuesser(Team.blue, guesser_channel)
    }

    run_game(spymasters, guessers)


def run_irl_game(words, colors):
    board = CodenamesBoard(words, colors, [Team.unknown for word in words])
    spymaster_channel = FileStreamChannel.open_filename('/tmp/codenames.log')
    spymasters = {
        Team.red: DummySpymaster(Team.red, spymaster_channel),
        Team.blue: AISpymaster(Team.blue, spymaster_channel)
    }

    guesser_channel = FileStreamChannel.open_stdout()
    guessers = {
        Team.red: HumanConsoleGuesser(Team.red, guesser_channel),
        Team.blue: HumanConsoleGuesser(Team.blue, guesser_channel)
    }

    run_game(spymasters, guessers, board)



if __name__ == '__main__':
    main()
