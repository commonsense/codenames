import numpy as np
import pandas as pd
import wordfreq
from conceptnet5.vectors.formats import load_hdf
from conceptnet5.vectors.query import VectorSpaceWrapper
from conceptnet5.vectors.transforms import l2_normalize_rows
from pkg_resources import resource_filename
from scipy.special import erf

from codenames import (
    tag_en, untag_en, CodenamesBoard, Spymaster
)

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
    frame = load_hdf(resource_filename('codenames', 'data/mini.h5'))
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


class DummySpymaster(Spymaster):
    def name(self):
        return "%s dummy spymaster" % self.team.name.title()

    def get_clue(self, board: CodenamesBoard) -> (int, str):
        return (9, 'dummy clue')



class AISpymaster(Spymaster):
    def __init__(self, team, channel):
        self.clued = set()
        super().__init__(team, channel)

    def name(self):
        return "%s AI spymaster" % self.team.name.title()

    def get_clue(self, board: CodenamesBoard) -> (int, str):
        scores = board.scores()
        my_score = scores[self.team]
        their_score = scores[self.team.opponent()]

        unrevealed = board.unrevealed_items()
        board_vocab = [tag_en(word) for (word, team) in unrevealed]
        simframe = VECTORS.frame.dot(VECTORS.frame.reindex(board_vocab).T)
        values = pd.Series(
            [team.value_for_team(self.team) for (word, team) in unrevealed],
            index=board_vocab
        )

        best = (0, 'dunno', 0., None)
        for nclued, clue, probs, explanation in self.solve_clue(board, simframe, values):
            if clue in self.clued:
                continue
            prob_left = 1.
            ev = 0.
            for idx, prob in enumerate(probs):
                prob_fail = 1. - prob
                opp_ev = POSITION_VALUES[their_score - 1, my_score - idx] * 0.5 + POSITION_VALUES[their_score, my_score - idx] * 0.4 + 0.1
                ev += prob_left * prob_fail * (1. - opp_ev)
                prob_left *= prob
            ev += prob_left * (1. - POSITION_VALUES[their_score, my_score - nclued])
            if ev > best[2]:
                best = (nclued, clue, ev, explanation)
        nclued, clue, ev, explanation = best
        if explanation is not None:
            describe_pieces = [
                "%s (%d%%)" % (untag_en(cn_term), prob * 100)
                for (cn_term, prob) in explanation[::-1].items()
            ]
            description = ", ".join(describe_pieces)
            self.channel.notify('notify', self.name(), "%s %d -> %s" % (clue, nclued, description))
        self.clued.add(clue)
        return (nclued, clue)

    def solve_clue(self, board: CodenamesBoard, simframe: pd.DataFrame, values: pd.Series):
        """
        `simframe` is a V x C matrix, where V is the vocabulary size and C is the
        number of unrevealed words on the board, containing the similarity of all
        cluable words to the board.

        `values` is a vector of payoffs for the unrevealed words on the board.
        """
        neu_max = np.max(simframe.ix[:, values < 0], axis=1)
        neg_max = np.max(simframe.ix[:, values <= -2], axis=1)
        ded_max = np.max(simframe.ix[:, values <= -3], axis=1)
        neu_probs = margin_prob((simframe.T - neu_max).T).ix[:, values > 0]
        neg_probs = margin_prob((simframe.T - neg_max).T).ix[:, values > 0]
        ded_probs = margin_prob((simframe.T - ded_max).T).ix[:, values > 0]

        combined_probs = (neu_probs * neu_probs * (neg_probs * ded_probs) ** 0.5).fillna(0)

        prob_values = np.sort(combined_probs.values)[:, ::-1][:, :9]
        prob_frame = pd.DataFrame(prob_values, index=simframe.index)
        products = pd.DataFrame(np.cumprod(prob_values, axis=1), index=simframe.index)

        clue_choices = []
        for nclued in range(1, min(10, products.shape[1] + 1)):
            possible_clues = products[nclued - 1].nlargest(50)
            for clue in possible_clues.index:
                word = untag_en(clue)
                if board.clue_is_ok(word):
                    probs = prob_frame.loc[clue, 0:(nclued-1)]
                    min_prob = prob_frame.loc[clue, nclued - 1]
                    row = combined_probs.loc[clue]
                    explanation = row[row >= min_prob].sort_values()
                    clue_choices.append((nclued, word, probs, explanation))
                    break
        return clue_choices


def margin_prob(margin):
    balance = erf(margin / .18)
    return balance / 2 + 0.5
