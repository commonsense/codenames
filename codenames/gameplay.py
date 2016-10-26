import random
import pandas as pd
import numpy as np
from codenames import best_clue, tag_en, simframe_best_clue, VECTORS
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


POSITION_VALUES = np.ones(shape=(10, 10), dtype='f')
POSITION_VALUES[0, :] = 1.
POSITION_VALUES[1, :] = .99
POSITION_VALUES[:, 0] = 0.
for isum in range(3, 19):
    for ours in range(1, min(10, isum)):
        theirs = isum - ours
        if theirs >= 10:
            continue
        POSITION_VALUES[ours, theirs] = 1 - min(
            POSITION_VALUES[theirs, ours - 1] * .99 + POSITION_VALUES[theirs, ours] * .01,
            POSITION_VALUES[theirs, max(ours - 2, 0)] * .5 + POSITION_VALUES[theirs, ours - 1] * .3 + POSITION_VALUES[theirs, ours] * .2,
            POSITION_VALUES[theirs, max(ours - 3, 0)] * .1 + POSITION_VALUES[theirs, max(ours - 2, 0)] * .4 + POSITION_VALUES[theirs, ours - 1] * .4 + POSITION_VALUES[theirs, ours] * .1
        )


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


def get_ai_clue(simframe, board, known_board, scores, current_player, log):
    my_score = scores[current_player]
    their_score = scores[OPPOSITE_PLAYER[current_player]]
    values = pd.Series(index=simframe.columns).fillna(0.)
    for i, (word, category) in enumerate(board):
        if known_board[i][1] == UNKNOWN:
            if category == current_player:
                values.loc[tag_en(word)] = 1.
            elif category == OPPOSITE_PLAYER[current_player]:
                values.loc[tag_en(word)] = -2.
            elif category == NEUTRAL:
                values.loc[tag_en(word)] = -1.
            elif category == ASSASSIN:
                values.loc[tag_en(word)] = -3.

    best = (0, 'dunno', 0.)
    for nclued, clue, probs in simframe_best_clue(simframe, values, log_stream=log):
        prob_left = 1.
        ev = 0.
        for idx, prob in enumerate(probs):
            prob_fail = 1. - prob
            opp_ev = POSITION_VALUES[their_score - 1, my_score - idx] * 0.5 + POSITION_VALUES[their_score, my_score - idx] * 0.4 + 0.1
            ev += prob_left * prob_fail * (1. - opp_ev)
            prob_left *= prob
        ev += prob_left * (1. - POSITION_VALUES[their_score, my_score - nclued])
        if ev > best[2]:
            best = (nclued, clue, ev)
    return best[:2]


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

