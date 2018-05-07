import json
from enum import Enum
from typing import List, Tuple, Dict, Set

import random
from conceptnet5.db.query import AssertionFinder
from conceptnet5.vectors import standardized_uri
from pkg_resources import resource_filename

WORDLIST = [
    line.strip() for line in open(
        resource_filename('codenames', 'data/codenames-words.txt')
    )
]


# Enumerate possible categories for cards
class Team(Enum):
    unknown = 0
    red = 1
    blue = 2
    neutral = 3
    assassin = 4

    def opponent(self):
        if self is Team.red:
            return Team.blue
        elif self is Team.blue:
            return Team.red
        else:
            raise ValueError(self)

    def value_for_team(self, team):
        if self is team:
            return 1
        elif self is Team.neutral:
            return -1
        elif self is Team.assassin:
            return -3
        else:
            return -2


class CodenamesBoard:
    def __init__(self, words: List[str], spy_values: List[Team], known_values: List[Team]):
        self.words = words

        # Make sure we're not accidentally putting ConceptNet labels into
        # the game state
        assert not self.words[0].startswith('/c/en/')
        self.spy_values = spy_values
        self.known_values = known_values
        self.finder = AssertionFinder()

    @staticmethod
    def generate():
        words = random.sample(WORDLIST, 25)
        teams = [Team.red] * 9 + [Team.blue] * 8 + [Team.neutral] * 7 + [Team.assassin]
        random.shuffle(teams)
        return CodenamesBoard(words, teams, [Team.unknown] * 25)

    def _is_form_of(self, word: str, clue: str) -> bool:
        return self.finder.query({'node': tag_en(word), 'other': tag_en(clue),
                                    'rel': '/r/FormOf', 'sources': '/s/resource/wiktionary/en/'})

    def clue_is_ok(self, clue: str) -> bool:
        assert not clue.startswith('/c/en/')
        clue = clue.upper()
        for word in self.words:
            if word == clue:
                return False
            elif word in clue:
                return False
            elif self._is_form_of(word, clue):
                return False
        return True

    def get_word_team(self, word: str) -> Team:
        idx = self.words.index(word)
        return self.spy_values[idx]

    def reveal_word(self, word: str) -> None:
        idx = self.words.index(word)
        self.known_values[idx] = self.spy_values[idx]

    def scores(self) -> Dict[Team, int]:
        return {
            Team.red: self.spy_values.count(Team.red) - self.known_values.count(Team.red),
            Team.blue: self.spy_values.count(Team.blue) - self.known_values.count(Team.blue)
        }

    def winner(self) -> Team:
        scores = self.scores()
        if scores[Team.red] == 0:
            return Team.red
        elif scores[Team.blue] == 0:
            return Team.blue
        else:
            return Team.unknown

    def known_items(self) -> List[Tuple[str, Team]]:
        return list(zip(self.words, self.known_values))

    def spy_items(self) -> List[Tuple[str, Team]]:
        return list(zip(self.words, self.spy_values))

    def unrevealed_items(self) -> List[Tuple[str, Team]]:
        items = []
        for i in range(len(self.words)):
            if self.known_values[i] == Team.unknown:
                items.append((self.words[i], self.spy_values[i]))
        return items

    def valid_guesses(self) -> Set[str]:
        return {word for (word, team) in self.unrevealed_items()}

    def to_json(self):
        items = [
            (self.words[i], self.spy_values[i].name, self.known_values[i].name)
            for i in range(len(self.words))
        ]
        return json.dumps(items)

    @staticmethod
    def from_json(jsondata):
        items = json.loads(jsondata)
        words, spy_texts, known_texts = zip(*items)
        spy_values = [Team[name] for name in spy_texts]
        known_values = [Team[name] for name in known_texts]
        return CodenamesBoard(words, spy_values, known_values)


class Channel:
    def notify(self, tag, value):
        raise NotImplementedError

    def await_input(self, prompt):
        raise NotImplementedError


class Player:
    def __init__(self, team: Team, channel: Channel):
        self.team = team
        self.channel = channel


class Spymaster(Player):
    pass


class Guesser(Player):
    pass


def tag_en(word):
    return standardized_uri('en', word)


def untag_en(term):
    return term[6:].replace('_', ' ')
