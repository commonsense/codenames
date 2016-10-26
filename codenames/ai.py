from conceptnet5.vectors.formats import load_hdf
from conceptnet5.vectors.transforms import l2_normalize_rows
from conceptnet5.vectors.query import VectorSpaceWrapper
from codenames import (
    tag_en, untag_en, clue_is_ok, OPPOSITE_PLAYER, UNKNOWN,
    NEUTRAL, ASSASSIN
)
from scipy.special import erf
import numpy as np
import pandas as pd
import wordfreq


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
            (POSITION_VALUES[theirs, ours - 1] * .99 +
             POSITION_VALUES[theirs, ours] * .01),
            (POSITION_VALUES[theirs, max(ours - 2, 0)] * .5 +
             POSITION_VALUES[theirs, ours - 1] * .3 +
             POSITION_VALUES[theirs, ours] * .2),
            (POSITION_VALUES[theirs, max(ours - 3, 0)] * .1 +
             POSITION_VALUES[theirs, max(ours - 2, 0)] * .4 +
             POSITION_VALUES[theirs, ours - 1] * .4 +
             POSITION_VALUES[theirs, ours] * .1)
        )


def _load_vectors():
    frame = load_hdf('/home/rspeer/code/conceptnet5/data/vectors/mini.h5')
    selections = [
        label for label in frame.index
        if label.startswith('/c/en/') and '_' not in label and '#' not in label
        and wordfreq.zipf_frequency(label[6:], 'en') > 3.0
    ]
    # Add the two-word phrases that appear in Codenames
    selections += ['/c/en/ice_cream', '/c/en/new_york', '/c/en/scuba_diver']
    frame = l2_normalize_rows(frame.loc[selections].astype('f'))
    return VectorSpaceWrapper(frame=frame)


VECTORS = _load_vectors()
CACHE = {}


def get_similarity(term1, term2):
    if (term1, term2) in CACHE:
        return CACHE[term1, term2]
    else:
        CACHE[term1, term2] = VECTORS.get_similarity(tag_en(term1), tag_en(term2))
        return CACHE[term1, term2]


def simframe_best_clue(simframe, values, log_stream=None):
    """
    `simframe` is a V x 25 matrix, where V is the vocabulary size, containing
    the similarity of all cluable words to the board.

    `values` is a vector of 25 payoffs for the words on the board.
    """
    neu_max = np.max(simframe.ix[:, values < 0], axis=1)
    neg_max = np.max(simframe.ix[:, values <= -2], axis=1)
    ded_max = np.max(simframe.ix[:, values <= -3], axis=1)
    neu_probs = margin_prob((simframe.T - neu_max).T).ix[:, values > 0]
    neg_probs = margin_prob((simframe.T - neg_max).T).ix[:, values > 0]
    ded_probs = margin_prob((simframe.T - ded_max).T).ix[:, values > 0]

    combined_probs = (neu_probs * neg_probs * ded_probs).fillna(0)

    prob_values = np.sort(combined_probs.values)[:, ::-1][:, :9]
    prob_frame = pd.DataFrame(prob_values, index=simframe.index)
    products = pd.DataFrame(np.cumprod(prob_values, axis=1), index=simframe.index)

    clue_choices = []
    for nclued in range(1, min(10, products.shape[1] + 1)):
        possible_clues = products[nclued - 1].nlargest(20)
        for clue in possible_clues.index:
            if clue_is_ok(simframe.columns, clue):
                probs = prob_frame.loc[clue, 0:(nclued-1)]
                min_prob = prob_frame.loc[clue, nclued - 1]
                row = combined_probs.loc[clue]
                explanation = row[row >= min_prob].sort_values()
                clue_choices.append((nclued, untag_en(clue), probs))
                print('explanation', file=log_stream)
                print(explanation, file=log_stream)
                print('clue chosen', file=log_stream)
                print(nclued, clue, min_prob, file=log_stream)
                break
    return clue_choices


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


def margin_prob(margin):
    balance = erf(margin / .18)
    return balance / 2 + 0.5
