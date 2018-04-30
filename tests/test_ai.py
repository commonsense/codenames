from conceptnet5.vectors import standardized_uri
from nose.tools import ok_, with_setup, assert_not_equal
from pkg_resources import resource_filename

from codenames import ai, CodenamesBoard, Team
from codenames.ai import AISpymaster
from codenames.console import FileStreamChannel


def setup_board():
    global BOARD
    words = ['STATE', 'LOCK', 'GAME', 'ALPS', 'TAIL',
             'YARD', 'MICROSCOPE', 'CAP', 'MILK', 'SNOWMAN',
             'MATCH', 'SWING', 'AIR', 'ORGAN', 'SCHOOL',
             'NEEDLE', 'CROSS', 'TEMPLE', 'ARM', 'TAP',
             'PIN', 'BUCK', 'MINT', 'POLE', 'CENTER']
    spy_values = [Team.neutral, Team.blue, Team.red, Team.blue, Team.neutral,
             Team.red, Team.blue, Team.red, Team.red, Team.red,
             Team.blue, Team.red, Team.blue, Team.red, Team.red,
             Team.neutral, Team.neutral, Team.neutral, Team.blue, Team.neutral,
             Team.neutral, Team.blue, Team.red, Team.blue, Team.assassin]
    known_values = [Team.unknown] * 25
    BOARD = CodenamesBoard(words=words, spy_values=spy_values, known_values=known_values)

def setup_problematic_board():
    global BOARD
    """
    Remaining on board: WHIP, CORNER, EGYPT, CENTAUR, POISON, ROW, POUND
    Good: CENTAUR
    Neutral: WHIP, POISON, POUND
    Bad: CORNER, EGYPT
    Assassin: ROW
    """
    words = ['WHIP', 'CORNER', 'EGYPT', 'CENTAUR', 'POISON',
             'ROW', 'POUND']
    spy_values = [Team.neutral, Team.blue, Team.blue, Team.red, Team.neutral,
                  Team.assassin, Team.neutral]
    known_values = [Team.unknown] * 7
    BOARD = CodenamesBoard(words=words, spy_values=spy_values, known_values=known_values)


def test_load_vectors():
    vectors = ai._load_vectors()
    ok_(vectors.frame.index[0].startswith('/c/en/'))

    # Test we have vectors for all Codenames words
    wordlist = [
        standardized_uri('en', line.strip()) for line in open(
            resource_filename('codenames', 'data/codenames-words.txt')
        )
        ]
    for word in wordlist:
        ok_(word in vectors.frame.index)



@with_setup(setup_board)
def test_clue_is_ok():
    ok_(BOARD.clue_is_ok('carrot')) # Under previous code, one couldn't clue any words starting
    # with CA, TA, or PI.
    ok_(BOARD.clue_is_ok('baseball'))
    ok_(not BOARD.clue_is_ok('taps'))
    ok_(not BOARD.clue_is_ok('gaming'))
    ok_(not BOARD.clue_is_ok('centre'))
    ok_(not BOARD.clue_is_ok('needle'))


@with_setup(setup_problematic_board)
def test_problematic_board():
    spymaster_channel = FileStreamChannel.open_filename('/tmp/codenames_test.log')
    spymaster = AISpymaster(Team.red, spymaster_channel)
    clue_number, clue_word = spymaster.get_clue(BOARD)
    # Before, the problematic board would return the first word in the frame, "0"
    assert_not_equal(clue_word, '0')

