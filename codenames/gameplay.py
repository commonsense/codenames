import random
from codenames import (
    tag_en, OPPOSITE_PLAYER, PLAYER_NAMES, UNKNOWN, RED, BLUE,
    NEUTRAL, ASSASSIN
)
from codenames.ai import get_ai_clue, VECTORS
from blessings import Terminal
from pkg_resources import resource_filename
from collections import Counter


WORDLIST = [line.strip() for line in open(resource_filename('codenames', 'data/codenames-words.txt'))]


def make_board():
    words = random.sample(WORDLIST, 25)
    categories = (
        [(word, RED) for word in words[:9]] +
        [(word, BLUE) for word in words[9:17]] +
        [(word, NEUTRAL) for word in words[17:24]] +
        [(word, ASSASSIN) for word in words[24:25]]
    )
    random.shuffle(categories)
    return categories


def justify(word):
    return ' ' + word.ljust(15)


def show_board(board, status=''):
    term = Terminal()
    for i, (word, category) in enumerate(board):
        jword = word[:11]
        if category == UNKNOWN:
            print(justify(jword), end='')
        elif category == RED:
            print(term.bright_red(justify(jword + ' [r]')), end='')
        elif category == BLUE:
            print(term.bright_blue(justify(jword + ' [b]')), end='')
        elif category == NEUTRAL:
            print(term.yellow(justify(jword + ' [n]')), end='')
        elif category == ASSASSIN:
            print(term.reverse(justify(jword + ' [a]')), end='')
        if i % 5 == 4:
            print('\n')
    print(status)


def get_human_guess(board, current_player):
    while True:
        prompt = "%s team's guess: " % PLAYER_NAMES[current_player]
        guess = input(prompt).strip().upper()
        if guess == 'PASS':
            return guess
        elif any(word == guess for (word, category) in board):
            return guess
        else:
            print('%s is not an available word.' % guess)


def main():
    term = Terminal()
    board = make_board()
    board_indices = {word: i for (i, (word, category)) in enumerate(board)}
    known_board = [(word, UNKNOWN) for (word, category) in board]
    current_player = RED
    status = ''

    board_vocab = [tag_en(word) for (word, category) in board]
    simframe = VECTORS.frame.dot(VECTORS.frame.loc[board_vocab].T)

    with open('/tmp/codenames.log', 'w') as log:
        print(board, file=log)
        while True:
            real_counts = Counter(category for (word, category) in board)
            known_counts = Counter(category for (word, category) in known_board)
            diff = real_counts - known_counts
            if diff[RED] == 0:
                show_board(board, "Red team wins.")
                return RED
            if diff[BLUE] == 0:
                show_board(board, "Blue team wins.")
                return BLUE

            show_board(known_board, '')
            print("%s spymaster is thinking of a clue..." % PLAYER_NAMES[current_player])
            clue_number, clue_word = get_ai_clue(simframe, board, known_board, diff, current_player, log)
            print("Clue: %s %d" % (clue_word, clue_number))

            picked_category = current_player
            while picked_category == current_player:
                choice = get_human_guess(board, current_player)
                if choice == 'PASS':
                    status = '%s passes.' % PLAYER_NAMES[current_player]
                    print(status)
                    break

                idx = board_indices[choice]
                word, picked_category = board[idx]
                known_board[idx] = board[idx]

                if picked_category == RED:
                    shown_category = term.bright_red('red')
                elif picked_category == BLUE:
                    shown_category = term.bright_blue('blue')
                elif picked_category == NEUTRAL:
                    shown_category = term.yellow('neutral')
                elif picked_category == ASSASSIN:
                    shown_category == term.reverse('the assassin')
                else:
                    raise ValueError(picked_category)
                status = '%s is %s.' % (choice, shown_category)
                print(status)

                if picked_category == ASSASSIN:
                    if current_player == RED:
                        show_board(board, "Blue team wins.")
                        return BLUE
                    else:
                        show_board(board, "Red team wins.")
                        return RED
            current_player = OPPOSITE_PLAYER[current_player]


if __name__ == '__main__':
    main()
