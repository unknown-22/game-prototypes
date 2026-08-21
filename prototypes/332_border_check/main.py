import random
from dataclasses import dataclass
from enum import Enum

import pyxel

# 16-color palette
BLACK = 0
NAVY = 1
PURPLE = 2
GREEN = 3
BROWN = 4
DARK_BLUE = 5
LIGHT_BLUE = 6
WHITE = 7
RED = 8
ORANGE = 9
YELLOW = 10
LIME = 11
CYAN = 12
GRAY = 13
PINK = 14
PEACH = 15

# Game constants
COUNTRIES = ["ATLANTIA", "BORAVIA", "CALEDON", "DURMSTRAL"]
COUNTRY_COLORS = (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW
VISA_TYPES = ["TOURIST", "BUSINESS", "TRANSIT", "DIPLOMAT"]
NAMES = ["ALEX", "BROOK", "CASEY", "DEVON", "EMERY", "FINLEY", "GRAY", "HARPER"]
LIVES_START = 3
GAME_DURATION = 3600  # 60s
RULE_COUNT = 3
PATIENCE_START = 300.0

# Button rectangles (x1, y1, x2, y2)
APPROVE_BUTTON = (30, 190, 150, 228)
DENY_BUTTON = (170, 190, 290, 228)


class RuleKind(Enum):
    BAN_COUNTRY = 0
    MIN_VISA_DAYS = 1
    MAX_DECLARED = 2
    BAN_VISA_TYPE = 3
    WANTED_NAME = 4


@dataclass(frozen=True)
class Rule:
    kind: RuleKind
    target: int

    @property
    def label(self) -> str:
        if self.kind is RuleKind.BAN_COUNTRY:
            return "BAN " + COUNTRIES[self.target]
        if self.kind is RuleKind.MIN_VISA_DAYS:
            return "VISA < " + str(self.target)
        if self.kind is RuleKind.MAX_DECLARED:
            return "DECL < $" + str(self.target)
        if self.kind is RuleKind.BAN_VISA_TYPE:
            return "NO " + VISA_TYPES[self.target]
        return "WANTED " + NAMES[self.target]


def rule_violated(rule: Rule, t: "Traveler") -> bool:
    if rule.kind is RuleKind.BAN_COUNTRY:
        return t.country == rule.target
    if rule.kind is RuleKind.MIN_VISA_DAYS:
        return t.visa_days < rule.target
    if rule.kind is RuleKind.MAX_DECLARED:
        return t.declared > rule.target
    if rule.kind is RuleKind.BAN_VISA_TYPE:
        return t.visa_type == rule.target
    return t.name_index == rule.target


@dataclass
class Traveler:
    name_index: int
    country: int
    visa_type: int
    visa_days: int
    declared: int
    patience: float = PATIENCE_START


def traveler_is_denied(t: Traveler, rules: list[Rule]) -> bool:
    return any(rule_violated(r, t) for r in rules)


def score_correct(streak: int, patience_ratio: float) -> int:
    base = 10 * min(streak, 5)
    bonus = 25 if patience_ratio > 0.75 else 0
    return base + bonus


def patience_start(frame: int) -> float:
    return max(150.0, 300.0 - frame * 150.0 / 3600.0)


def rule_interval(frame: int) -> int:
    return max(240, 720 - frame // 12)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class Floater:
    x: float
    y: float
    text: str
    color: int
    life: int


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


class Game:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.best_score = getattr(self, "best_score", 0)
        if getattr(self, "rng", None) is None:
            self.rng = random.Random()
        self.phase = Phase.TITLE
        self.score = 0
        self.streak = 0
        self.lives = LIVES_START
        self.frame = 0
        self.rules = [self.make_rule(self.rng) for _ in range(RULE_COUNT)]
        self.traveler: Traveler | None = None
        self.correct_total = 0
        self.missed = 0
        self.errors = 0
        self.rule_timer = rule_interval(0)
        self.rule_warn = 0
        self.mutate_index = self.rng.randrange(RULE_COUNT)
        self.particles: list[Particle] = []
        self.floaters: list[Floater] = []
        self.shake_frames = 0
        self.flash = 0
        self.last_outcome = ""
        self.end_reason = ""

    def make_rule(self, rng: random.Random) -> Rule:
        kind = RuleKind(rng.randrange(len(RuleKind)))
        if kind is RuleKind.BAN_COUNTRY:
            target = rng.randrange(len(COUNTRIES))
        elif kind is RuleKind.MIN_VISA_DAYS:
            target = rng.randrange(10, 61)
        elif kind is RuleKind.MAX_DECLARED:
            target = rng.randrange(200, 801, 50)
        elif kind is RuleKind.BAN_VISA_TYPE:
            target = rng.randrange(len(VISA_TYPES))
        else:
            target = rng.randrange(len(NAMES))
        return Rule(kind, target)

    def make_traveler(self, rng: random.Random) -> Traveler:
        t = Traveler(
            name_index=rng.randrange(len(NAMES)),
            country=rng.randrange(len(COUNTRIES)),
            visa_type=rng.randrange(len(VISA_TYPES)),
            visa_days=rng.randrange(1, 91),
            declared=rng.randrange(100, 901, 25),
            patience=PATIENCE_START,
        )
        return t

    def _spawn_traveler(self) -> None:
        t = self.make_traveler(self.rng)
        t.patience = patience_start(self.frame)
        self.traveler = t

    def _decide(self, approve: bool) -> None:
        t = self.traveler
        if t is None:
            return
        denied = traveler_is_denied(t, self.rules)
        correct = approve != denied
        if correct:
            self.streak += 1
            ratio = max(0.0, min(1.0, t.patience / patience_start(self.frame)))
            gained = score_correct(self.streak, ratio)
            self.score += gained
            self.correct_total += 1
            self.last_outcome = "CORRECT"
            cx, cy = 160.0, 110.0
            for _ in range(12):
                self.particles.append(
                    Particle(
                        x=cx,
                        y=cy,
                        vx=self.rng.uniform(-2.0, 2.0),
                        vy=self.rng.uniform(-2.5, 0.5),
                        color=GREEN if self.rng.random() < 0.7 else LIME,
                        life=self.rng.randint(15, 30),
                    )
                )
            self.floaters.append(Floater(cx, cy - 10, "+" + str(gained), LIME, 40))
            if ratio > 0.75:
                self.floaters.append(Floater(cx + 20, cy + 10, "QUICK!", YELLOW, 40))
        else:
            self.lives -= 1
            self.streak = 0
            self.errors += 1
            self.last_outcome = "ERROR"
            self.shake_frames = 12
            self.flash = 10
            self.floaters.append(Floater(160.0, 110.0, "WRONG!", RED, 40))
        self._spawn_traveler()

    def _update_patience(self) -> None:
        t = self.traveler
        if t is None:
            return
        t.patience -= 1
        if t.patience <= 0:
            self.streak = 0
            self.missed += 1
            self.last_outcome = "MISS"
            self.floaters.append(Floater(160.0, 110.0, "DENIED", ORANGE, 40))
            self._spawn_traveler()

    def _mutate_rules(self) -> None:
        self.rules[self.mutate_index] = self.make_rule(self.rng)
        self.mutate_index = self.rng.randrange(RULE_COUNT)

    def _check_game_over(self) -> None:
        if self.lives <= 0:
            self.phase = Phase.GAME_OVER
            self.end_reason = "DETAINED"
        elif self.frame >= GAME_DURATION:
            self.phase = Phase.GAME_OVER
            self.end_reason = "SHIFT OVER"
        if self.phase is Phase.GAME_OVER:
            self.best_score = max(self.best_score, self.score)

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_floaters(self) -> None:
        alive: list[Floater] = []
        for f in self.floaters:
            f.y -= 0.5
            f.life -= 1
            if f.life > 0:
                alive.append(f)
        self.floaters = alive

    def _button_hit(self, mx: int, my: int) -> bool | None:
        ax1, ay1, ax2, ay2 = APPROVE_BUTTON
        dx1, dy1, dx2, dy2 = DENY_BUTTON
        if ax1 <= mx <= ax2 and ay1 <= my <= ay2:
            return True
        if dx1 <= mx <= dx2 and dy1 <= my <= dy2:
            return False
        return None

    def update(self) -> None:
        if self.phase is Phase.TITLE:
            if (
                pyxel.btnp(pyxel.KEY_R)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.KEY_SPACE)
            ):
                self.reset()
                self.phase = Phase.PLAYING
            return

        if self.phase is Phase.GAME_OVER:
            if (
                pyxel.btnp(pyxel.KEY_R)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.KEY_SPACE)
            ):
                self.reset()
                self.phase = Phase.PLAYING
            return

        self.frame += 1

        self.rule_timer -= 1
        if self.rule_timer <= 60:
            self.rule_warn = self.rule_timer
        else:
            self.rule_warn = 0
        if self.rule_timer <= 0:
            self._mutate_rules()
            self.rule_timer = rule_interval(self.frame)
            self.rule_warn = 0

        self._update_patience()

        approve = pyxel.btnp(pyxel.KEY_A) or pyxel.btnp(pyxel.KEY_LEFT)
        deny = pyxel.btnp(pyxel.KEY_D) or pyxel.btnp(pyxel.KEY_RIGHT)
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            hit = self._button_hit(pyxel.mouse_x, pyxel.mouse_y)
            if hit is True:
                approve = True
            elif hit is False:
                deny = True

        if self.traveler is not None:
            if approve:
                self._decide(True)
            elif deny:
                self._decide(False)

        self._update_particles()
        self._update_floaters()
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if self.flash > 0:
            self.flash -= 1
        self._check_game_over()

    def _draw_heart(self, x: int, y: int, col: int) -> None:
        pyxel.rect(x, y, 2, 2, col)
        pyxel.rect(x + 3, y, 2, 2, col)
        pyxel.rect(x, y + 2, 5, 2, col)
        pyxel.tri(x, y + 4, x + 5, y + 4, x + 2, y + 8, col)

    def _draw_title(self) -> None:
        pyxel.text(96, 60, "BORDER CHECK", WHITE)
        pyxel.text(104, 76, "Customs Officer", GRAY)
        pyxel.text(60, 100, "A/LEFT = APPROVE   D/RIGHT = DENY", LIME)
        pyxel.text(104, 116, "SPACE = START", YELLOW)
        # sample document mock
        pyxel.rectb(60, 140, 200, 70, GRAY)
        pyxel.text(72, 150, "NAME: ALEX", WHITE)
        pyxel.text(72, 162, "COUNTRY: ATLANTIA", WHITE)
        pyxel.text(72, 174, "TYPE: TOURIST", WHITE)
        pyxel.text(72, 186, "VISA: 30d   DECL $400", WHITE)
        pyxel.rect(224, 148, 8, 8, RED)

    def _draw_playing(self) -> None:
        # camera shake
        ox = oy = 0
        if self.shake_frames > 0:
            ox = (self.frame % 5) - 2
            oy = (self.frame % 3) - 1
        try:
            pyxel.camera(ox, oy)
        except BaseException:
            pass

        # timer bar (top)
        pyxel.rect(0, 0, 320, 3, NAVY)
        remain = max(0.0, (GAME_DURATION - self.frame) / GAME_DURATION)
        pyxel.rect(0, 0, int(320 * remain), 3, CYAN)

        # rulebook panel
        box_w = 101
        for i in range(RULE_COUNT):
            bx = 4 + i * (box_w + 4)
            rule = self.rules[i]
            blink = self.rule_warn > 0 and i == self.mutate_index and (self.frame // 6) % 2 == 0
            border = YELLOW if blink else GRAY
            pyxel.rectb(bx, 6, bx + box_w, 34, border)
            label = rule.label
            tx = bx + (box_w - len(label) * 4) // 2
            pyxel.text(tx, 12, label, WHITE)
            if self.rule_warn > 0 and i == self.mutate_index:
                pyxel.text(bx + box_w - 6, 6, "!", YELLOW)

        # HUD
        pyxel.text(4, 38, "SCORE " + str(self.score), WHITE)
        if self.streak >= 2:
            pyxel.text(4, 46, "x" + str(self.streak), YELLOW)
        for i in range(self.lives):
            self._draw_heart(250 + i * 10, 38, RED)

        # traveler card
        t = self.traveler
        if t is not None:
            pyxel.rectb(20, 50, 300, 168, GRAY)
            pyxel.text(28, 56, NAMES[t.name_index], WHITE)
            pyxel.rect(28, 68, 8, 8, COUNTRY_COLORS[t.country])
            pyxel.text(42, 68, COUNTRIES[t.country], WHITE)
            pyxel.text(28, 82, "TYPE: " + VISA_TYPES[t.visa_type], LIGHT_BLUE)
            pyxel.text(28, 96, "VISA: " + str(t.visa_days) + "d", WHITE)
            pyxel.text(28, 110, "DECL $" + str(t.declared), WHITE)

            # patience bar
            frac = max(0.0, min(1.0, t.patience / patience_start(self.frame)))
            if frac > 0.5:
                pcol = LIME
            elif frac > 0.25:
                pcol = YELLOW
            elif frac > 0.12:
                pcol = ORANGE
            else:
                pcol = RED
            pyxel.rect(20, 176, 280, 6, GRAY)
            pyxel.rect(20, 176, int(280 * frac), 6, pcol)

        # buttons
        ax1, ay1, ax2, ay2 = APPROVE_BUTTON
        dx1, dy1, dx2, dy2 = DENY_BUTTON
        pyxel.rect(ax1, ay1, ax2, ay2, GREEN)
        pyxel.text(ax1 + 34, ay1 + 15, "APPROVE", BLACK)
        pyxel.rect(dx1, dy1, dx2, dy2, RED)
        pyxel.text(dx1 + 44, dy1 + 15, "DENY", WHITE)

        # particles
        for p in self.particles:
            pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)

        # floaters
        for f in self.floaters:
            pyxel.text(int(f.x) - len(f.text) * 2, int(f.y), f.text, f.color)

        # red flash overlay
        if self.flash > 0:
            pyxel.rectb(0, 0, 320, 240, RED)

        try:
            pyxel.camera(0, 0)
        except BaseException:
            pass

    def _draw_game_over(self) -> None:
        pyxel.text(120, 60, self.end_reason, RED)
        pyxel.text(104, 90, "SCORE " + str(self.score), WHITE)
        pyxel.text(104, 104, "BEST " + str(self.best_score), YELLOW)
        stats = (
            "CORRECT " + str(self.correct_total)
            + "  MISSED " + str(self.missed)
            + "  ERRORS " + str(self.errors)
        )
        pyxel.text(70, 130, stats, WHITE)
        pyxel.text(104, 160, "SPACE = RETRY", LIME)

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase is Phase.TITLE:
            self._draw_title()
        elif self.phase is Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_playing()


def main() -> None:
    game = Game()

    def update() -> None:
        game.update()

    def draw() -> None:
        game.draw()

    pyxel.init(320, 240, fps=60)
    pyxel.run(update, draw)


if __name__ == "__main__":
    main()
