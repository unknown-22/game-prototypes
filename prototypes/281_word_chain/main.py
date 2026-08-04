from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import cast

import pyxel


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    WORD_CLEAR = auto()
    GAME_OVER = auto()


@dataclass
class LetterTile:
    col: int
    row: int
    letter: str
    color: int
    selected: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


SCREEN_W = 320
SCREEN_H = 240
CELL = 24
GRID_COLS = 8
GRID_ROWS = 8
GRID_X = 64
GRID_Y = 32
TILE_SIZE = 22
COMBO_THRESHOLD = 4
SUPER_DURATION = 300
HEAT_MAX = 100
GAME_TIME = 3600

COLOR_RED = 8
COLOR_LIME = 11
COLOR_DARK_BLUE = 5
COLOR_YELLOW = 10
COLORS = (COLOR_RED, COLOR_LIME, COLOR_DARK_BLUE, COLOR_YELLOW)

WORDS_3 = [
    "ACE", "ACT", "AGE", "AIM", "AIR", "AND", "APE", "ARC", "ARM",
    "BAD", "BAG", "BAT", "BED", "BIG", "BIT", "BOW", "BOX", "BOY",
    "BUD", "BUG", "BUS", "CAB", "CAN", "CAP", "CAR", "COP", "COT",
    "COW", "CRY", "CUP", "CUT", "DAB", "DAM", "DAY", "DEN", "DIG",
    "DIM", "DIP", "DOG", "DOT", "DRY", "DUG", "DUO", "EGG",
    "ELF", "ELM", "FAT", "FED", "FEW", "FIG", "FIN", "FIT", "FIX",
    "FLY", "FOE", "FOG", "FOX", "FRY", "FUN", "GAP", "GAS", "GEM",
    "GIN", "GUM", "GUN", "GUT", "GYM", "HAT", "HEN", "HIT", "HOG",
    "HOP", "HOT", "HUB", "HUG", "ICE", "INK", "IVY", "JAB", "JET",
    "JOB", "JOG", "JOY", "JUG", "KEY", "KID", "KIT", "LAG", "LAP",
    "LAW", "LEG", "LID", "LIE", "LOG", "LOT", "MAD", "MAN", "MAP",
    "MAT", "MIX", "MOB", "MUD", "MUG", "NAP", "NET", "NEW", "NOD",
    "NUT", "OAK", "OAR", "OIL", "OLD", "OWL", "PAD", "PAN", "PAW",
    "PEA", "PEG", "PEN", "PET", "PIN", "PIT", "POD", "POT", "PUB",
    "PUG", "PUN", "PUT", "RAG", "RAT", "RAW", "RAY", "RED", "RIB",
    "RIG", "RIM", "RIP", "ROB", "ROD", "ROT", "ROW", "RUB", "RUG",
    "RUN", "RUT", "SAD", "SAP", "SAT", "SAW", "SET", "SEW", "SIP",
    "SIT", "SKY", "SLY", "SOB", "SOD", "SOP", "SOT", "SOW", "SPY",
    "STY", "SUM", "SUN", "TAB", "TAG", "TAP", "TAX", "TEN", "TIE",
    "TIN", "TOD", "TOE", "TON", "TOP", "TOW", "TOY", "TUG", "VAN",
    "VAT", "VET", "VOW", "WAD", "WAG", "WAR", "WAX", "WAY", "WED",
    "WET", "WIG", "WIN", "WIT", "WOE", "WOK", "WON", "YAK", "YAM",
    "YAP", "YEN", "YES", "YET", "YEW", "ZAP", "ZEN", "ZIP", "ZOO",
]

WORDS_4 = [
    "ACID", "ALSO", "ARCH", "ARMY", "AUNT", "BACK", "BAIT", "BAKE",
    "BALD", "BALL", "BAND", "BANG", "BANK", "BARE", "BARK", "BARN",
    "BASE", "BATH", "BEAD", "BEAK", "BEAM", "BEAN", "BEAR", "BEAT",
    "BELT", "BEND", "BENT", "BEST", "BIKE", "BILL", "BIRD", "BITE",
    "BLUE", "BLUR", "BOAT", "BODY", "BOLD", "BOLT", "BOMB", "BOND",
    "BONE", "BOOK", "BORN", "BOSS", "BOWL", "BURN", "BURY", "BUSH",
    "BUSY", "CAGE", "CAKE", "CALF", "CALL", "CALM", "CAME", "CAMP",
    "CARD", "CARE", "CART", "CASE", "CASH", "CAST", "CAVE", "CHIP",
    "CLAY", "CLIP", "CLUB", "CLUE", "COAL", "COAT", "CODE", "COIN",
    "COLD", "COME", "COOK", "COOL", "COPY", "CORD", "CORE", "COST",
    "CREW", "CROP", "CUBE", "CURE", "CURL", "CUTE", "DALE", "DAMP",
    "DARE", "DARK", "DART", "DASH", "DATA", "DATE", "DAWN", "DEAD",
    "DEAF", "DEAL", "DEAR", "DEBT", "DECK", "DEED", "DEER", "DESK",
    "DIAL", "DICE", "DIET", "DIRT", "DISC", "DISH", "DISK", "DOCK",
    "DOME", "DONE", "DOSE", "DOWN", "DRAG", "DRAW", "DREW", "DROP",
    "DRUM", "DUAL", "DUCK", "DUEL", "DUKE", "DULL", "DUMB", "DUMP",
    "DUST", "DUTY", "EACH", "EARN", "EASE", "EAST", "EASY", "EDGE",
    "EDIT", "ELSE", "EMIT", "ENVY", "EVEN", "EVIL", "EXAM", "EXIT",
    "FACE", "FACT", "FADE", "FAIL", "FAIR", "FAKE", "FALL", "FAME",
    "FANG", "FARM", "FAST", "FATE", "FEAR", "FEED", "FEEL", "FELL",
    "FELT", "FILE", "FILL", "FILM", "FIND", "FINE", "FIRE", "FIRM",
    "FISH", "FIST", "FLAG", "FLAT", "FLEW", "FLIP", "FLOG", "FLOW",
    "FOAM", "FOLD", "FOLK", "FOND", "FOOD", "FOOL", "FOOT", "FORD",
    "FORE", "FORK", "FORM", "FORT", "FOUL", "FOUR", "FREE", "FROM",
    "FUEL", "FULL", "FUND", "FURY", "FUSE", "GAIN", "GALE", "GAME",
    "GANG", "GATE", "GAZE", "GEAR", "GIFT", "GIRL", "GIVE", "GLAD",
    "GLOW", "GLUE", "GOAL", "GOAT", "GOES", "GOLD", "GOLF", "GONE",
    "GOOD", "GRAB", "GRAY", "GREW", "GRID", "GRIN", "GRIP", "GROW",
    "GULF", "GUST", "GUTS", "HACK", "HAIL", "HAIR", "HALE", "HALF",
    "HALL", "HALT", "HAND", "HANG", "HARD", "HARM", "HARP", "HATE",
    "HAVE", "HAZE", "HEAD", "HEAL", "HEAP", "HEAR", "HEAT", "HEEL",
    "HEIR", "HELD", "HELM", "HELP", "HERB", "HERD", "HERE", "HERO",
    "HIDE", "HIGH", "HIKE", "HILL", "HINT", "HIRE", "HOLD", "HOLE",
    "HOME", "HOOD", "HOOF", "HOOK", "HOPE", "HORN", "HOST", "HOUR",
    "HOWL", "HUGE", "HULL", "HUNG", "HUNT", "HURT", "HUSH", "HYMN",
    "ICON", "IDEA", "IDLE", "INCH", "INTO", "IRON", "ISLE", "ITEM",
    "JACK", "JADE", "JAIL", "JAZZ", "JEAN", "JERK", "JEST", "JOIN",
    "JOKE", "JOLT", "JUMP", "JUNE", "JURY", "JUST", "KEEN", "KEEP",
    "KEPT", "KICK", "KILL", "KIND", "KING", "KISS", "KITE", "KNEE",
    "KNEW", "KNIT", "KNOB", "KNOT", "KNOW", "LACE", "LACK", "LADY",
    "LAID", "LAKE", "LAMB", "LAME", "LAMP", "LAND", "LANE", "LAST",
    "LATE", "LAWN", "LEAD", "LEAF", "LEAK", "LEAN", "LEAP", "LEFT",
    "LEND", "LENS", "LENT", "LESS", "LIAR", "LICK", "LIFE", "LIFT",
    "LIKE", "LIMB", "LIME", "LIMP", "LINE", "LINK", "LION", "LIST",
    "LIVE", "LOAD", "LOAF", "LOAN", "LOCK", "LOFT", "LONG", "LOOK",
    "LOOP", "LORD", "LORE", "LOSE", "LOSS", "LOST", "LOUD", "LOVE",
    "LUCK", "LULL", "LUNG", "LURE", "LURK", "LUSH", "LUST", "MACE",
    "MADE", "MAID", "MAIL", "MAIN", "MAKE", "MALE", "MALL", "MALT",
    "MANE", "MANY", "MARE", "MARK", "MASK", "MASS", "MAST", "MATE",
    "MAZE", "MEAL", "MEAN", "MEAT", "MEET", "MELD", "MELT", "MEMO",
    "MEND", "MENU", "MERE", "MESH", "MESS", "MILD", "MILE", "MILK",
    "MILL", "MIME", "MIND", "MINE", "MINT", "MISS", "MIST", "MOAN",
    "MOAT", "MOCK", "MODE", "MOLD", "MOLE", "MOOD", "MOON", "MOOR",
    "MORE", "MOSS", "MOST", "MOTH", "MOVE", "MUCH", "MULE", "MUST",
    "MYTH", "NAIL", "NAME", "NAVY", "NEAR", "NEAT", "NECK", "NEED",
    "NEST", "NEXT", "NICE", "NINE", "NODE", "NONE", "NOON", "NORM",
    "NOSE", "NOTE", "NOUN", "NUDE", "NUTS", "OATH", "OBEY", "ODDS",
    "OKAY", "ONCE", "ONLY", "ONTO", "OPEN", "ORAL", "OVEN", "OVER",
    "PACE", "PACK", "PAGE", "PAID", "PAIN", "PAIR", "PALE", "PALM",
    "PANE", "PARK", "PART", "PASS", "PAST", "PATH", "PAVE", "PAWN",
    "PEAK", "PEAR", "PEEL", "PEER", "PEST", "PICK", "PIER", "PIKE",
    "PILE", "PILL", "PINE", "PINK", "PIPE", "PLAN", "PLAY", "PLEA",
    "PLOT", "PLOW", "PLUG", "PLUM", "PLUS", "POEM", "POET", "POKE",
    "POLE", "POLL", "POND", "PONY", "POOL", "POOR", "POPE", "PORK",
    "PORT", "POSE", "POST", "POUR", "PRAY", "PREY", "PROP", "PULL",
    "PUMP", "PUNK", "PURE", "PUSH", "QUIT", "QUIZ", "RACE", "RACK",
    "RAGE", "RAID", "RAIL", "RAIN", "RAKE", "RANK", "RARE", "RASH",
    "RATE", "READ", "REAL", "REAR", "REEF", "REEL", "REIN", "RENT",
    "REST", "RICE", "RICH", "RIDE", "RIFT", "RING", "RIOT", "RISE",
    "RISK", "ROAD", "ROAM", "ROCK", "RODE", "ROLE", "ROLL", "ROOF",
    "ROOM", "ROOT", "ROPE", "ROSE", "RUIN", "RULE", "RUSH", "RUST",
    "SACK", "SAFE", "SAGA", "SAIL", "SAKE", "SALE", "SALT", "SAME",
    "SAND", "SANG", "SANK", "SAVE", "SCAN", "SEAL", "SEAT", "SEED",
    "SEEK", "SEEM", "SEEN", "SELF", "SELL", "SEND", "SENT", "SHED",
    "SHIN", "SHIP", "SHOP", "SHOT", "SHOW", "SHUT", "SICK", "SIDE",
    "SIFT", "SIGH", "SIGN", "SILK", "SINK", "SITE", "SIZE", "SKIN",
    "SKIP", "SLAM", "SLAP", "SLEW", "SLID", "SLIM", "SLIP", "SLIT",
    "SLOT", "SLOW", "SLUG", "SNAP", "SNOW", "SNUG", "SOAK", "SOAP",
    "SOAR", "SOCK", "SODA", "SOFA", "SOFT", "SOIL", "SOLD", "SOLE",
    "SOME", "SONG", "SOON", "SORE", "SORT", "SOUL", "SPAN", "SPIN",
    "SPIT", "SPOT", "STAR", "STAY", "STEM", "STEP", "STEW", "STIR",
    "STOP", "STUB", "STUD", "SUCH", "SUIT", "SUNG", "SUNK", "SURE",
    "SURF", "SWAN", "SWAP", "SWIM", "TAIL", "TAKE", "TALE", "TALK",
    "TALL", "TAME", "TANK", "TAPE", "TASK", "TAXI", "TEAM", "TEAR",
    "TELL", "TEND", "TENT", "TERM", "TEST", "TEXT", "THAN", "THEM",
    "THEN", "THEY", "THIN", "THIS", "THUS", "TICK", "TIDE", "TIDY",
    "TIED", "TIER", "TILE", "TILL", "TILT", "TIME", "TINY", "TIRE",
    "TOAD", "TOIL", "TOLD", "TOLL", "TONE", "TOOK", "TOOL", "TOPS",
    "TORE", "TORN", "TOUR", "TOWN", "TRAP", "TRAY", "TREE", "TRIM",
    "TRIO", "TRIP", "TROD", "TROT", "TRUE", "TUBE", "TUCK", "TUNA",
    "TUNE", "TURN", "TWIN", "TYPE", "UGLY", "UNIT", "UPON", "URGE",
    "USED", "USER", "VAIN", "VAST", "VEIL", "VEIN", "VENT", "VERB",
    "VERY", "VEST", "VIEW", "VINE", "VISIT", "VOID", "VOLT", "VOTE",
    "WADE", "WAGE", "WAIL", "WAIT", "WAKE", "WALK", "WALL", "WANT",
    "WARD", "WARM", "WARN", "WARP", "WARY", "WASH", "WAVE", "WAVY",
    "WEAK", "WEAR", "WEED", "WEEK", "WELD", "WELL", "WENT", "WERE",
    "WEST", "WHAT", "WHEN", "WHIM", "WHIP", "WHOM", "WICK", "WIDE",
    "WIFE", "WILD", "WILL", "WILT", "WILY", "WIND", "WINE", "WING",
    "WINK", "WIPE", "WIRE", "WISE", "WISH", "WITH", "WOKE", "WOLF",
    "WOOD", "WOOL", "WORD", "WORE", "WORK", "WORM", "WORN", "WRAP",
    "YARD", "YARN", "YEAR", "YELL", "YOGA", "YOKE", "YOUR", "ZEAL",
    "ZERO", "ZINC", "ZONE", "ZOOM",
]

WORDS_5 = [
    "ABOUT", "ABOVE", "ACTOR", "ADMIT", "ADOPT", "AFFIX", "AFTER",
    "AGAIN", "AGENT", "AGREE", "ALBUM", "ALIEN", "ALIGN", "ALIVE",
    "ALLOW", "ALONG", "ALTER", "AMBER", "AMONG", "ANGEL", "ANGER",
    "ANGLE", "ANGRY", "ANKLE", "ANVIL", "APART", "APPLE", "APPLY",
    "ARGUE", "ARISE", "ARMOR", "ARRAY", "ARROW", "ASSET", "AVOID",
    "BADGE", "BASIN", "BATCH", "BEACH", "BEAST", "BEGIN", "BENCH",
    "BIRTH", "BLACK", "BLADE", "BLAME", "BLAND", "BLANK", "BLAST",
    "BLAZE", "BLEED", "BLEND", "BLESS", "BLIND", "BLINK", "BLISS",
    "BLOCK", "BLOOM", "BLOWN", "BOARD", "BOAST", "BONUS", "BOOTH",
    "BOUND", "BRAIN", "BRAND", "BRASS", "BRAVE", "BREAD", "BREAK",
    "BREED", "BRICK", "BRIEF", "BRING", "BROAD", "BROWN", "BRUSH",
    "BUILD", "BUNCH", "BURST", "BUYER", "CABIN", "CABLE", "CAMEL",
    "CARRY", "CATCH", "CAUSE", "CEASE", "CHAIN", "CHAIR", "CHALK",
    "CHARM", "CHART", "CHASE", "CHEAP", "CHECK", "CHEER", "CHESS",
    "CHEST", "CHIEF", "CHILD", "CHILL", "CHORD", "CIVIL", "CLAIM",
    "CLASH", "CLASS", "CLEAN", "CLEAR", "CLERK", "CLICK", "CLIFF",
    "CLIMB", "CLING", "CLOAK", "CLOCK", "CLONE", "CLOSE", "CLOTH",
    "CLOUD", "COACH", "COAST", "COLOR", "CORAL", "COULD", "COUNT",
    "COURT", "COVER", "CRACK", "CRAFT", "CRANE", "CRASH", "CRAWL",
    "CRAZY", "CREAM", "CREEK", "CRIME", "CROOK", "CROSS", "CROWD",
    "CROWN", "CRUEL", "CRUSH", "CURVE", "CYCLE", "DAILY", "DANCE",
    "DEBUT", "DECAY", "DELAY", "DELTA", "DENSE", "DEPTH", "DEVIL",
    "DIARY", "DIRTY", "DITCH", "DODGE", "DONOR", "DOUBT", "DRAFT",
    "DRAIN", "DRAMA", "DRANK", "DREAM", "DRESS", "DRIED", "DRIFT",
    "DRINK", "DRIVE", "DROWN", "DRUNK", "DWELL", "EAGER", "EAGLE",
    "EARLY", "EARTH", "ELBOW", "ELDER", "ELECT", "ELITE", "EMPTY",
    "ENEMY", "ENJOY", "ENTER", "EQUAL", "EQUIP", "ERROR", "EVENT",
    "EVERY", "EXACT", "EXIST", "EXTRA", "FAINT", "FAIRY", "FAITH",
    "FALSE", "FANCY", "FATAL", "FAULT", "FEAST", "FENCE", "FERRY",
    "FETCH", "FEVER", "FIBER", "FIELD", "FIFTH", "FIFTY", "FIGHT",
    "FINAL", "FIRST", "FIXED", "FLAME", "FLASH", "FLEET", "FLESH",
    "FLOAT", "FLOOD", "FLOOR", "FLOUR", "FLUID", "FLUSH", "FOCUS",
    "FORCE", "FORTH", "FORUM", "FOUND", "FRAME", "FRANK", "FRAUD",
    "FRESH", "FRONT", "FRUIT", "FUNNY", "GHOST", "GIANT", "GIVEN",
    "GLARE", "GLASS", "GLOBE", "GLOOM", "GLORY", "GLOVE", "GRACE",
    "GRADE", "GRAIN", "GRAND", "GRANT", "GRAPE", "GRASP", "GRASS",
    "GRAVE", "GREAT", "GREEN", "GREET", "GRIEF", "GRIND", "GROAN",
    "GROSS", "GROUP", "GUARD", "GUESS", "GUEST", "GUIDE", "GUILD",
    "GUILT", "HAPPY", "HARSH", "HAVEN", "HEART", "HEAVY", "HEDGE",
    "HENCE", "HONOR", "HORSE", "HOTEL", "HOUSE", "HUMAN", "IDEAL",
    "IDIOM", "IMAGE", "IMPLY", "INDEX", "INNER", "INPUT", "IRONY",
    "IVORY", "JEWEL", "JOINT", "JOKER", "JUDGE", "JUICE", "KEBAB",
    "KNIFE", "KNOCK", "KNOWN", "LABEL", "LARGE", "LASER", "LATER",
    "LAYER", "LEARN", "LEASE", "LEAVE", "LEGAL", "LEMON", "LEVEL",
    "LEVER", "LIGHT", "LIMIT", "LINER", "LIVER", "LOCAL", "LOGIC",
    "LOOSE", "LORD", "LOUSE", "LOVER", "LOWER", "LOYAL", "LUCKY",
    "LUNAR", "LYRIC", "MAGIC", "MAJOR", "MARCH", "MATCH", "MAYOR",
    "MEDAL", "MEDIA", "MERCY", "MERGE", "MERIT", "METAL", "METER",
    "MIGHT", "MINOR", "MIRACLE", "MODEL", "MONEY", "MONTH", "MOUNT",
    "MOUSE", "MOUTH", "MOVIE", "MUSIC", "NAVAL", "NERVE", "NIGHT",
    "NOBLE", "NOISE", "NORTH", "NOTED", "NOVEL", "NURSE", "NYLON",
    "OCCUR", "OCEAN", "OFFER", "OFTEN", "OLIVE", "OPERA", "ORDER",
    "ORGAN", "OTHER", "OZONE", "PACE", "PAINT", "PANIC", "PANEL",
    "PAPER", "PARTY", "PASTE", "PATCH", "PATIO", "PAUSE", "PEACH",
    "PENAL", "PENNY", "PHASE", "PHONE", "PHOTO", "PIANO", "PIECE",
    "PILOT", "PINCH", "PIXEL", "PIZZA", "PLACE", "PLAIN", "PLANE",
    "PLANT", "PLATE", "PLAZA", "PLEAD", "PLUCK", "PLUMB", "PLUME",
    "POINT", "POLAR", "POSER", "POUND", "POWER", "PRESS", "PRICE",
    "PRIDE", "PRIME", "PRINT", "PRIOR", "PRIZE", "PROBE", "PRONE",
    "PROOF", "PROUD", "PROVE", "PSALM", "PULSE", "PUNCH", "PUPIL",
    "PURSE", "QUEEN", "QUERY", "QUEST", "QUEUE", "QUICK", "QUIET",
    "QUOTA", "QUOTE", "RADAR", "RADIO", "RAISE", "RALLY", "RANGE",
    "RAPID", "RATIO", "REACH", "REACT", "REALM", "REBEL", "REFER",
    "REIGN", "RELAX", "REPLY", "RIDER", "RIDGE", "RIFLE", "RIGHT",
    "RIGID", "RIVAL", "RIVER", "ROBIN", "ROCKY", "ROGUE", "ROMAN",
    "ROUGE", "ROUND", "ROUTE", "ROYAL", "RUGBY", "RULER", "RURAL",
    "SADLY", "SAINT", "SALAD", "SCALE", "SCARE", "SCENE", "SCOPE",
    "SCORE", "SCOUT", "SCRAP", "SEIZE", "SENSE", "SERVE", "SEVEN",
    "SHADE", "SHAFT", "SHAKE", "SHALL", "SHAME", "SHAPE", "SHARE",
    "SHARK", "SHARP", "SHAVE", "SHEEP", "SHEER", "SHEET", "SHELF",
    "SHELL", "SHIFT", "SHINE", "SHIRT", "SHOCK", "SHOOT", "SHORE",
    "SHORT", "SHOUT", "SIGHT", "SINCE", "SIXTH", "SIXTY", "SKILL",
    "SKULL", "SLATE", "SLAVE", "SLEEP", "SLICE", "SLIDE", "SLOPE",
    "SMALL", "SMART", "SMELL", "SMILE", "SMITH", "SMOKE", "SNAKE",
    "SOLAR", "SOLID", "SOLVE", "SORRY", "SOUND", "SOUTH", "SPACE",
    "SPADE", "SPARE", "SPEAK", "SPEAR", "SPEED", "SPELL", "SPEND",
    "SPICE", "SPINE", "SPITE", "SPLIT", "SPOKE", "SPOON", "SPORT",
    "SPRAY", "SQUAD", "STACK", "STAFF", "STAGE", "STAKE", "STALE",
    "STAND", "STARK", "START", "STATE", "STEAK", "STEAM", "STEEL",
    "STEEP", "STEER", "STERN", "STICK", "STILL", "STING", "STOCK",
    "STONE", "STOOD", "STORE", "STORM", "STORY", "STRAW", "STRIP",
    "STUCK", "STUDY", "STUFF", "STYLE", "SUGAR", "SUITE", "SUNNY",
    "SWAMP", "SWARM", "SWEAR", "SWEEP", "SWEET", "SWEPT", "SWIFT",
    "SWING", "SWORD", "SWORE", "SYRUP", "TABLE", "TASTE", "TEACH",
    "TERRA", "THICK", "THING", "THINK", "THIRD", "THORN", "THOSE",
    "THREE", "THREW", "THROW", "THUMB", "TIGER", "TIMER", "TITLE",
    "TODAY", "TOKEN", "TOPIC", "TORCH", "TOTAL", "TOUCH", "TOUGH",
    "TOWEL", "TOWER", "TOXIC", "TRACE", "TRACK", "TRADE", "TRAIL",
    "TRAIN", "TRAIT", "TRASH", "TREAT", "TREND", "TRIAL", "TRIBE",
    "TRICK", "TROOP", "TROUT", "TRULY", "TRUMP", "TRUNK", "TRUST",
    "TRUTH", "TUTOR", "TWICE", "TWIST", "UNCLE", "UNDER", "UNION",
    "UNITE", "UNITY", "UPPER", "UPSET", "URBAN", "USAGE", "USUAL",
    "VALID", "VALUE", "VAULT", "VENUE", "VERSE", "VIDEO", "VIGOR",
    "VISTA", "VITAL", "VOCAL", "VOICE", "VOTER", "WAGON", "WASTE",
    "WATCH", "WATER", "WEARY", "WEAVE", "WEDGE", "WEIGH", "WEIRD",
    "WHEAT", "WHEEL", "WHERE", "WHICH", "WHILE", "WHITE", "WHOLE",
    "WHOSE", "WIDER", "WIDOW", "WIDTH", "WINDS", "WITCH", "WOMAN",
    "WORLD", "WORRY", "WORSE", "WORST", "WORTH", "WOULD", "WOUND",
    "WRATH", "WRIST", "WRITE", "WRONG", "WROTE", "YACHT", "YIELD",
    "YOUNG", "YOUTH", "ZEBRA",
]


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, "WORD CHAIN", fps=60)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.grid: list[list[LetterTile | None]] = self._empty_grid()
        elapsed = GAME_TIME * 0.2 if self.phase == Phase.TITLE else 0
        self._pick_target_word(elapsed)
        self.target_word_idx = 0
        self.traced_cells: list[tuple[int, int]] = []
        self.traced_letters = ""
        self.last_color: int | None = None
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat: float = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.timer = GAME_TIME
        self.word_clear_timer = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames = 0
        self.words_found = 0
        self._color_cycle_timer = 0
        self._grid_refresh_timer = 0
        self._best_score: int = max(getattr(self, "_best_score", 0), 0)

    def _empty_grid(self) -> list[list[LetterTile | None]]:
        return [[None] * GRID_COLS for _ in range(GRID_ROWS)]

    def _pick_target_word(self, elapsed_frames: int | float = 0) -> None:
        elapsed_seconds = (GAME_TIME - self.timer) / 60.0 if hasattr(self, "timer") else elapsed_frames / 60.0
        if elapsed_seconds < 30:
            pool = WORDS_3
        elif elapsed_seconds < 45:
            pool = WORDS_3 + WORDS_4
        else:
            pool = WORDS_3 + WORDS_4 + WORDS_5
        self.target_word = self._rng.choice(pool)

    def _generate_grid(self, target_word: str) -> list[list[LetterTile | None]]:
        for _ in range(100):
            grid = self._empty_grid()
            start_col = self._rng.randint(0, GRID_COLS - 1)
            start_row = self._rng.randint(0, GRID_ROWS - 1)
            path = [(start_col, start_row)]
            used: set[tuple[int, int]] = {path[0]}
            ok = True
            for _ in target_word[1:]:
                adj = self._find_valid_adjacent(path[-1][0], path[-1][1])
                free = [(c, r) for c, r in adj if (c, r) not in used]
                if not free:
                    ok = False
                    break
                nxt = self._rng.choice(free)
                path.append(nxt)
                used.add(nxt)
            if not ok or len(path) != len(target_word):
                continue
            for i, (c, r) in enumerate(path):
                color = self._rng.choice(COLORS)
                grid[r][c] = LetterTile(col=c, row=r, letter=target_word[i], color=color)
            for row in range(GRID_ROWS):
                for col in range(GRID_COLS):
                    if grid[row][col] is None:
                        letter = self._rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                        color = self._rng.choice(COLORS)
                        grid[row][col] = LetterTile(col=col, row=row, letter=letter, color=color)
            return grid
        return self._generate_grid_fallback(target_word)

    def _generate_grid_fallback(self, target_word: str) -> list[list[LetterTile | None]]:
        grid = self._empty_grid()
        for i, (c, r) in enumerate(zip(range(GRID_COLS), range(GRID_ROWS), strict=False)):
            letter = target_word[i] if i < len(target_word) else self._rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            color = self._rng.choice(COLORS)
            grid[r][c] = LetterTile(col=c, row=r, letter=letter, color=color)
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                if grid[row][col] is None:
                    letter = self._rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                    color = self._rng.choice(COLORS)
                    grid[row][col] = LetterTile(col=col, row=row, letter=letter, color=color)
        return grid

    def _find_valid_adjacent(self, col: int, row: int) -> list[tuple[int, int]]:
        candidates = [(col - 1, row), (col + 1, row), (col, row - 1), (col, row + 1)]
        return [(c, r) for c, r in candidates if 0 <= c < GRID_COLS and 0 <= r < GRID_ROWS]

    def _handle_click(self, col: int, row: int) -> bool:
        if not (0 <= col < GRID_COLS and 0 <= row < GRID_ROWS):
            return False
        tile = self.grid[row][col]
        if tile is None:
            return False
        if tile.selected:
            return False
        if tile.letter != self.target_word[self.target_word_idx]:
            self.combo = 0
            self.heat = min(self.heat + 10, HEAT_MAX)
            self._spawn_wrong_particles(tile)
            self._add_floating_text("WRONG!", 8, col, row)
            self.shake_frames = 8
            return False
        is_first = self.target_word_idx == 0
        if not is_first and not self.super_mode:
            last_c, last_r = self.traced_cells[-1]
            if not self._is_adjacent(last_c, last_r, col, row):
                self.combo = 0
                self.heat = min(self.heat + 10, HEAT_MAX)
                self._add_floating_text("NOT ADJ!", 8, col, row)
                return False
        if is_first:
            pass
        elif self.super_mode:
            self.combo += 1
        elif tile.color == self.last_color:
            self.combo += 1
            self._add_floating_text(f"COMBO x{self.combo}", COLOR_LIME, col, row)
            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self.super_mode = True
                self.super_timer = SUPER_DURATION
                self._add_floating_text("SUPER!", COLOR_YELLOW, col, row)
        else:
            self.combo = 0
            self.heat = min(self.heat + 15, HEAT_MAX)
            self.shake_frames = 5
        tile.selected = True
        self.traced_cells.append((col, row))
        self.traced_letters += tile.letter
        self.last_color = tile.color
        self.target_word_idx += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        if self.target_word_idx >= len(self.target_word):
            self._on_word_complete()
        return True

    def _on_word_complete(self) -> None:
        word_len = len(self.target_word)
        score_gain = 10 * word_len * max(1, self.combo)
        self.score += score_gain
        self.words_found += 1
        self.heat = max(0.0, self.heat - 20.0)
        self._spawn_burst_particles()
        self._add_floating_text(f"+{score_gain}", COLOR_YELLOW, 4, 3, center=True)
        self._clear_word()

    def _clear_word(self) -> None:
        elapsed = GAME_TIME - self.timer
        self._pick_target_word(elapsed)
        self.grid = self._generate_grid(self.target_word)
        self.traced_cells.clear()
        self.traced_letters = ""
        self.last_color = None
        self.target_word_idx = 0
        self.combo = 0
        self.phase = Phase.WORD_CLEAR
        self.word_clear_timer = 60

    def _is_adjacent(self, c1: int, r1: int, c2: int, r2: int) -> bool:
        return (abs(c1 - c2) + abs(r1 - r2)) == 1

    def _deselect_all(self) -> None:
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                tile = self.grid[row][col]
                if tile is not None:
                    tile.selected = False
        self.traced_cells.clear()
        self.traced_letters = ""
        self.target_word_idx = 0
        self.last_color = None
        self.combo = 0

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            self._best_score = max(self._best_score, self.score)
            return
        self.heat = max(0.0, self.heat - 0.02)

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER
            self._best_score = max(self._best_score, self.score)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _spawn_burst_particles(self) -> None:
        cx = GRID_X + GRID_COLS * CELL / 2
        cy = GRID_Y + GRID_ROWS * CELL / 2
        for _ in range(12):
            color = self._rng.choice(COLORS)
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-2.0, 2.0)
            self.particles.append(Particle(x=cx, y=cy, vx=vx, vy=vy, color=color, life=20))

    def _spawn_super_particles(self) -> None:
        cx = GRID_X + GRID_COLS * CELL / 2
        cy = GRID_Y + GRID_ROWS * CELL / 2
        rainbow = (8, 9, 10, 11, 12, 14)
        for _ in range(20):
            color = self._rng.choice(rainbow)
            vx = self._rng.uniform(-2.5, 2.5)
            vy = self._rng.uniform(-2.5, 2.5)
            self.particles.append(Particle(x=cx, y=cy, vx=vx, vy=vy, color=color, life=15))

    def _spawn_wrong_particles(self, tile: LetterTile) -> None:
        x = GRID_X + tile.col * CELL + CELL / 2
        y = GRID_Y + tile.row * CELL + CELL / 2
        for _ in range(4):
            vx = self._rng.uniform(-1.5, 1.5)
            vy = self._rng.uniform(-1.5, 1.5)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, color=13, life=10))

    def _add_floating_text(self, text: str, color: int, col: int, row: int, *, center: bool = False) -> None:
        if center:
            x = float(SCREEN_W // 2 - len(text) * 2)
            y = float(SCREEN_H // 2 - 40)
        else:
            x = float(GRID_X + col * CELL + 2)
            y = float(GRID_Y + row * CELL - 4)
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=30))

    def _refresh_recolor_tiles(self) -> None:
        elapsed = self.timer if hasattr(self, "timer") else GAME_TIME
        remaining = max(0, GAME_TIME - elapsed)
        if remaining > GAME_TIME * 0.5:
            interval = 120
        else:
            interval = 60
        self._color_cycle_timer += 1
        if self._color_cycle_timer >= interval:
            self._color_cycle_timer = 0
            count = self._rng.randint(3, 8)
            for _ in range(count):
                row = self._rng.randint(0, GRID_ROWS - 1)
                col = self._rng.randint(0, GRID_COLS - 1)
                tile = self.grid[row][col]
                if tile is not None and not tile.selected:
                    tile.color = self._rng.choice(COLORS)

    def _refresh_grid_cells(self) -> None:
        elapsed = self.timer if hasattr(self, "timer") else GAME_TIME
        remaining = max(0, GAME_TIME - elapsed)
        if remaining > GAME_TIME * 0.5:
            interval = 90
        else:
            interval = 45
        self._grid_refresh_timer += 1
        if self._grid_refresh_timer >= interval:
            self._grid_refresh_timer = 0
            count = self._rng.randint(1, 4)
            for _ in range(count):
                row = self._rng.randint(0, GRID_ROWS - 1)
                col = self._rng.randint(0, GRID_COLS - 1)
                tile = self.grid[row][col]
                if tile is not None and not tile.selected:
                    tile.letter = self._rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                    tile.color = self._rng.choice(COLORS)

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                elapsed = 0
                self._pick_target_word(elapsed)
                self.grid = self._generate_grid(self.target_word)
                self.timer = GAME_TIME
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                elapsed = 0
                self._pick_target_word(elapsed)
                self.grid = self._generate_grid(self.target_word)
                self.timer = GAME_TIME
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.WORD_CLEAR:
            self._update_particles()
            self._update_floating_texts()
            self.word_clear_timer -= 1
            if self.word_clear_timer <= 0:
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.PLAYING:
            self._update_timer()
            self._update_heat()
            self._update_particles()
            self._update_floating_texts()
            if self.shake_frames > 0:
                self.shake_frames -= 1
            if self.super_mode:
                self.super_timer -= 1
                if self.super_timer <= 0:
                    self.super_mode = False
            self._refresh_recolor_tiles()
            self._refresh_grid_cells()
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                mx, my = pyxel.mouse_x, pyxel.mouse_y
                if GRID_X <= mx < GRID_X + GRID_COLS * CELL and GRID_Y <= my < GRID_Y + GRID_ROWS * CELL:
                    col = (mx - GRID_X) // CELL
                    row = (my - GRID_Y) // CELL
                    self._handle_click(col, row)
            if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT) or pyxel.btnp(pyxel.KEY_ESCAPE):
                self._deselect_all()
            return

    def draw(self) -> None:
        shake_x, shake_y = 0, 0
        if self.shake_frames > 0 and self.phase == Phase.PLAYING:
            amp = min(6, int(self.heat / HEAT_MAX * 8))
            shake_x = self._rng.randint(-amp, amp)
            shake_y = self._rng.randint(-amp, amp)
        pyxel.cls(1)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        with _apply_offset(shake_x, shake_y):
            self._draw_grid()
            self._draw_traced_path()
            self._draw_target_word()
            self._draw_hud()
            self._draw_particles()
            self._draw_floating_texts()
            if self.super_mode:
                self._draw_super_border()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 32, 60, "WORD CHAIN", 10)
        pyxel.text(SCREEN_W // 2 - 48, 100, "Trace letters to spell words!", 7)
        pyxel.text(SCREEN_W // 2 - 44, 120, "Same color chain = COMBO", 7)
        pyxel.text(SCREEN_W // 2 - 48, 140, "COMBO x4 triggers SUPER MODE!", 14)
        pyxel.text(SCREEN_W // 2 - 40, 180, "Left Click: select letter", 7)
        pyxel.text(SCREEN_W // 2 - 40, 196, "Right Click / ESC: deselect", 7)
        pyxel.text(SCREEN_W // 2 - 52, 220, "CLICK or SPACE to START", 11)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 32, 40, "GAME OVER", 8)
        pyxel.text(SCREEN_W // 2 - 48, 80, f"SCORE: {self.score}", 7)
        pyxel.text(SCREEN_W // 2 - 48, 96, f"BEST:  {self._best_score}", 10)
        pyxel.text(SCREEN_W // 2 - 48, 112, f"WORDS: {self.words_found}", 7)
        pyxel.text(SCREEN_W // 2 - 48, 128, f"MAX COMBO: {self.max_combo}", 11)
        pyxel.text(SCREEN_W // 2 - 48, 180, "CLICK or SPACE to retry", 7)

    def _draw_grid(self) -> None:
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x = GRID_X + col * CELL
                y = GRID_Y + row * CELL
                tile = self.grid[row][col]
                if tile is None:
                    pyxel.rect(x, y, TILE_SIZE, TILE_SIZE, 0)
                    continue
                border = 10 if tile.selected else 7
                pyxel.rect(x, y, TILE_SIZE, TILE_SIZE, tile.color)
                pyxel.rectb(x, y, TILE_SIZE, TILE_SIZE, border)
                lx = x + TILE_SIZE // 2 - 2
                ly = y + TILE_SIZE // 2 - 3
                text_color = 7 if tile.color != 10 else 0
                pyxel.text(lx, ly, tile.letter, text_color)
            if row == GRID_ROWS - 1:
                pyxel.line(GRID_X + GRID_COLS * CELL, GRID_Y, GRID_X + GRID_COLS * CELL, GRID_Y + GRID_ROWS * CELL, 0)

    def _draw_traced_path(self) -> None:
        if len(self.traced_cells) < 2:
            return
        for i in range(len(self.traced_cells) - 1):
            c1, r1 = self.traced_cells[i]
            c2, r2 = self.traced_cells[i + 1]
            x1 = GRID_X + c1 * CELL + TILE_SIZE // 2
            y1 = GRID_Y + r1 * CELL + TILE_SIZE // 2
            x2 = GRID_X + c2 * CELL + TILE_SIZE // 2
            y2 = GRID_Y + r2 * CELL + TILE_SIZE // 2
            pyxel.line(x1, y1, x2, y2, COLOR_LIME)
        if self.traced_cells:
            last_c, last_r = self.traced_cells[-1]
            lx = GRID_X + last_c * CELL + TILE_SIZE // 2
            ly = GRID_Y + last_r * CELL + TILE_SIZE // 2
            pyxel.circ(lx, ly, 3, 10)

    def _draw_target_word(self) -> None:
        x = 32
        y = 8
        pyxel.text(x - 24, y, "TARGET:", 7)
        for i, ch in enumerate(self.target_word):
            tx = x + i * 8
            color = 3 if i < self.target_word_idx else 7
            pyxel.text(tx, y, ch, color)

    def _draw_hud(self) -> None:
        pyxel.text(SCREEN_W - 64, 8, f"TIME:{self.timer // 60:02d}", 7)
        pyxel.text(8, SCREEN_H - 16, f"SCORE:{self.score}", 7)
        pyxel.text(8, SCREEN_H - 8, f"COMBO:{self.combo}/{self.max_combo}", COLOR_LIME)
        bar_x = SCREEN_W - 108
        bar_y = SCREEN_H - 14
        bar_w = 100
        bar_h = 6
        pyxel.rectb(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, 7)
        fill_w = int(bar_w * self.heat / HEAT_MAX)
        heat_color = 8
        if self.heat > 70:
            heat_color = (pyxel.frame_count // 4 % 2) * 8 + 7
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_color)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, "HEAT", 8)
        if self.super_mode:
            pyxel.text(8, 32, f"SUPER! {self.super_timer // 60 + 1}s", COLOR_YELLOW)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = max(0, min(7, p.life * 7 // 20))
            if alpha == 0:
                continue
            col = p.color if alpha >= 4 else 13
            pyxel.pset(int(p.x), int(p.y), col)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life
            if alpha <= 0:
                continue
            pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_super_border(self) -> None:
        bx = GRID_X - 3
        by = GRID_Y - 3
        bw = GRID_COLS * CELL + 6
        bh = GRID_ROWS * CELL + 6
        rainbow = (8, 9, 10, 11, 12, 14)
        color = rainbow[(pyxel.frame_count // 4) % len(rainbow)]
        pyxel.rectb(bx, by, bw, bh, color)

    def run_standalone(self) -> None:
        pyxel.run(self.update, self.draw)


class _ApplyOffset:
    def __init__(self, ox: int, oy: int) -> None:
        self.ox = ox
        self.oy = oy
        cam = cast(tuple[int, int], pyxel.camera())
        self._orig_cam_x: int = cam[0]
        self._orig_cam_y: int = cam[1]

    def __enter__(self) -> None:
        pyxel.camera(self.ox, self.oy)

    def __exit__(self, *args: object) -> None:
        pyxel.camera(self._orig_cam_x, self._orig_cam_y)


def _apply_offset(ox: int, oy: int) -> _ApplyOffset:
    return _ApplyOffset(ox, oy)


if __name__ == "__main__":
    Game()
