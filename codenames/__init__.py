from conceptnet5.vectors.formats import *
from conceptnet5.vectors.transforms import *
from conceptnet5.vectors.query import *
from conceptnet5.vectors import standardized_uri
from scipy.special import erf
import wordfreq
from itertools import combinations


def tag_en(word):
    return standardized_uri('en', word)


def untag_en(term):
    return term[6:].replace('_', ' ')


def _load_vectors():
    frame = load_hdf('/home/rspeer/code/conceptnet5/data/vectors/mini.h5')
    selections = [
        label for label in frame.index
        if label.startswith('/c/en/') and '_' not in label
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



def clue_is_ok(words_on_board, clue):
    clue = untag_en(clue)
    for word in words_on_board:
        word = untag_en(word)
        if word[:-1] in clue or clue in word:
            return False
    return True


def simframe_best_clue(simframe, values, safety=0.1, log_stream=None):
    """
    `simframe` is a V x 25 matrix, where V is the vocabulary size, containing
    the similarity of all cluable words to the board.

    `values` is a vector of 25 payoffs for the words on the board.
    """
    pos_mask = simframe * (values > 0)
    neu_max = np.max(simframe * (values <= 0), axis=1)
    neg_max = np.max(simframe * (values <= -1), axis=1)
    ded_max = np.max(simframe * (values <= -2), axis=1)
    neu_margins = np.maximum(0, (pos_mask.T - neu_max - safety).T)
    neg_margins = np.maximum(0, (pos_mask.T - neg_max - safety).T)
    ded_margins = np.maximum(0, (pos_mask.T - ded_max - safety).T)
    combined_margins = (neu_margins * neg_margins * ded_margins) ** (1/8) * (neu_margins > 0)
    values = combined_margins.sum(axis=1)

    possible_clues = values.nlargest(20)
    print(possible_clues, file=log_stream)
    for clue in possible_clues.index:
        if clue_is_ok(simframe.columns, clue):
            row = combined_margins.loc[clue]
            count = (row > 0).sum()
            explanation = row[row > 0]
            print(explanation, file=log_stream)
            return untag_en(clue), count
    raise RuntimeError('all clues are bad')


def best_clue(word_values, log_stream=None):
    weighted_terms = []
    pos_weight = sum(v for v in word_values.values() if v >= 0.)
    neg_weight = sum(-v for v in word_values.values() if v < 0.)
    for word, word_value in word_values.items():
        if word_value >= 0.:
            weighted_terms.append((tag_en(word), word_value * 2 / pos_weight))
        else:
            weighted_terms.append((tag_en(word), word_value / neg_weight))

    clue_possibilities = []
    pos_terms = [tag_en(word) for word in word_values if word_values[word] > 0]
    for nterms in (3, 2, 1):
        for combo in combinations(pos_terms, nterms):
            weighted_terms = [(term, 1) for term in combo]
            similar = VECTORS.similar_terms(weighted_terms, limit=500).index

            nfound = 0
            for term in similar:
                ok_clue = True
                for word in word_values:
                    # ugly approximation to 'is this word a form of this other word'
                    # TODO: make it better using ConceptNet
                    if word[:-1] in term or term[6:] in word.replace(' ', '_') or '_' in word:
                        ok_clue = False
                if ok_clue:
                    number, payoff, words = best_clue_number(term, word_values)
                    if payoff > 0:
                        clue_possibilities.append((untag_en(term), number, payoff, words))
                        nfound += 1
                        if nterms == 1 or nfound >= 10:
                            break

    clue_possibilities.sort(key=lambda x: (-x[2], x[1], x[0]))
    if log_stream is not None:
        for i in range(min(10, len(clue_possibilities))):
            print(i, clue_possibilities[i], file=log_stream)
    if not clue_possibilities:
        print('Weighted terms:', weighted_terms)
        raise ValueError("Can't make a clue for %s" % weighted_terms)
    return clue_possibilities[0]



def best_clue_number(term, word_values):
    ranked_values = [(get_similarity(term, tag_en(word)), word_value, word)
                     for word, word_value in word_values.items()]
    ranked_values.sort(reverse=True)
    value_so_far = 0.
    for rank in range(len(ranked_values)):
        cutoff_value = ranked_values[rank][1]
        if cutoff_value < 0.:
            break
        # The game value of successfully cluing this number of words. For now
        # we assume that each additional clued word triples your win
        # probability, which is a very rough assumption.
        score_value = 3 ** rank
        payoff = clue_payoff(ranked_values[rank], ranked_values[rank + 1:]) * score_value
        if payoff <= 0.:
            break
        else:
            value_so_far += payoff
    return (rank, value_so_far, [word for (_, _, word) in ranked_values[:rank]])


def clue_payoff(intended_clue, distractors):
    """
    `intended_clue` is a triple of (similarity, payoff, word), and
    `distractors` is a list of such triples for words that you don't want
    the clue to refer to.

    Return the value of a clue that matches `intended_clue` compared
    to the distractors.
    """
    payoff_rest = 0.0
    weight_rest = 0.0
    prob_best = 1.0
    best, payoff_best, _ = intended_clue
    for other, payoff_other, _ in distractors:
        # Calculate the probability of guessing an unintended word
        prob_other = erf((other - best) / .18) / 2 + 0.5
        prob_best *= (1.0 - prob_other)
        weight_rest += prob_other
        payoff_rest += prob_other * payoff_other

    ev_rest = payoff_rest / weight_rest
    payoff = (payoff_best * prob_best) + (ev_rest * (1 - prob_best))
    return payoff


# People's assessments of word similarity form a distribution around
# Numberbatch's assessments (or vice versa) with a standard deviation of .18

# Cards remaining after your turn:
# 0:x = 100%
# x:1 = < 1%
# 1:2 = 50% ?
