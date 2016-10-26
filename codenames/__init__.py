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



def clue_is_ok(words_on_board, clue):
    clue = untag_en(clue)
    for word in words_on_board:
        word = untag_en(word)
        if word[:-1] in clue or clue in word:
            return False
    return True


def margin_prob(margin):
    stdevs = erf(margin / .18)
    prob = stdevs / 2 + 0.5
    return prob ** 2


def simframe_best_clue(simframe, values, log_stream=None):
    """
    `simframe` is a V x 25 matrix, where V is the vocabulary size, containing
    the similarity of all cluable words to the board.

    `values` is a vector of 25 payoffs for the words on the board.
    """
    neu_max = np.max(simframe.ix[:, values < 0], axis=1)
    #neg_max = np.max(simframe * (values <= -2), axis=1)
    #ded_max = np.max(simframe * (values <= -3), axis=1)
    neu_probs = margin_prob((simframe.T - neu_max).T).ix[:, values > 0]
    #neg_probs = margin_prob((simframe.T - neg_max).T) * pos_mask
    #ded_probs = margin_prob((simframe.T - ded_max).T) * pos_mask

    #combined_probs = ((neu_probs * neg_probs * ded_probs) ** (1 / 3)).fillna(0)
    combined_probs = neu_probs.fillna(0)

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
        prob_other = erf((other - best) / .2) / 2 + 0.5
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
