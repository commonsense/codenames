from codenames import (Team, CodenamesBoard, FileLog)
from codenames.ai import AISpymaster
from blessings import Terminal


def justify(word):
    return ' ' + word.ljust(15)


def show_board_items(items, status=''):
    term = Terminal()
    for i, (word, team) in enumerate(items):
        jword = word[:11]
        if team is Team.unknown:
            print(justify(jword), end='')
        elif team is Team.red:
            print(term.bright_red(justify(jword + ' [r]')), end='')
        elif team is Team.blue:
            print(term.bright_blue(justify(jword + ' [b]')), end='')
        elif team is Team.neutral:
            print(term.yellow(justify(jword + ' [n]')), end='')
        elif team is Team.assassin:
            print(term.reverse(justify(jword + ' [a]')), end='')
        if i % 5 == 4:
            print('\n')
    print(status)


def get_human_guess(board: CodenamesBoard, current_team: Team):
    valid = board.valid_guesses()
    while True:
        prompt = "%s team's guess: " % current_team.name.title()
        guess = input(prompt).strip().upper()
        if guess == 'PASS':
            return guess
        elif guess in valid:
            return guess
        else:
            print('%r is not an available word.' % guess)


def main():
    term = Terminal()
    board = CodenamesBoard.generate()
    current_team = Team.red
    status = ''
    log = FileLog('/tmp/codenames.log')
    spymasters = {
        Team.red: AISpymaster(Team.red, log),
        Team.blue: AISpymaster(Team.blue, log)
    }

    while True:
        winner = board.winner()
        if winner is Team.red:
            show_board_items(board.spy_items(), "Red team wins.")
            return Team.red
        if winner is Team.blue:
            show_board_items(board.spy_items(), "Blue team wins.")
            return Team.blue

        show_board_items(board.known_items(), '')
        spymaster = spymasters[current_team]
        print("%s is thinking of a clue..." % spymaster.name())
        clue_number, clue_word = spymaster.get_clue(board)
        print("Clue: %s %d" % (clue_word, clue_number))

        picked_team = current_team
        while picked_team == current_team:
            choice = get_human_guess(board, current_team)
            if choice == 'PASS':
                status = '%s passes.' % current_team.name.title()
                print(status)
                break

            picked_team = board.get_word_team(choice)
            board.reveal_word(choice)

            if picked_team is Team.red:
                shown_category = term.bright_red('red')
            elif picked_team is Team.blue:
                shown_category = term.bright_blue('blue')
            elif picked_team is Team.neutral:
                shown_category = term.yellow('neutral')
            elif picked_team is Team.assassin:
                shown_category == term.reverse('the assassin')
            else:
                raise ValueError(picked_team)
            status = '%s is %s.' % (choice, shown_category)
            print(status)

            if picked_team is Team.assassin:
                if current_team is Team.red:
                    show_board_items(board.spy_items(), "Blue team wins.")
                    return Team.blue
                else:
                    show_board_items(board.spy_items(), "Red team wins.")
                    return Team.red
        current_team = current_team.opponent()


if __name__ == '__main__':
    main()
