from conceptnet5.vectors import standardized_uri


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


def tag_en(word):
    return standardized_uri('en', word)


def untag_en(term):
    return term[6:].replace('_', ' ')


def clue_is_ok(words_on_board, clue):
    clue = untag_en(clue)
    for word in words_on_board:
        word = untag_en(word)
        if word[:-1] in clue or clue in word:
            return False
    return True
