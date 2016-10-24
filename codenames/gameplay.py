import random
from codenames import best_clue
from blessings import Terminal
from pkg_resources import resource_filename
from collections import Counter


WORDLIST = [line.strip() for line in open(resource_filename('codenames', 'data/codenames-words.txt'))]

# Enumerate possible categories for cards
UNKNOWN, RED, BLUE, NEUTRAL, ASSASSIN = range(5)
OPPOSITE_PLAYER = {
    RED: BLUE,
    BLUE: RED
}
PLAYER_NAMES = {
    RED: 'Red',
    BLUE: 'Blue'
}


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
    print(term.clear())
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


def get_ai_clue(board, known_board, current_player, log):
    values = {}
    for i, (word, category) in enumerate(board):
        word = word.lower()
        if known_board[i][1] == UNKNOWN:
            if category == current_player:
                values[word] = 1.
            elif category == OPPOSITE_PLAYER[current_player]:
                values[word] = -1.
            elif category == NEUTRAL:
                values[word] = -0.2
            elif category == ASSASSIN:
                values[word] = -5.
    return best_clue(values, log)


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

            print(diff)
            show_board(known_board, status)
            print("%s spymaster is thinking of a clue..." % PLAYER_NAMES[current_player])
            clue_word, clue_number, _, _ = get_ai_clue(board, known_board, current_player, log)
            print("Clue: %s %d" % (clue_word, clue_number))

            picked_category = current_player
            while picked_category == current_player:
                choice = get_human_guess(board, current_player)
                if choice == 'PASS':
                    status = '%s passes.' % PLAYER_NAMES[current_player]
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

