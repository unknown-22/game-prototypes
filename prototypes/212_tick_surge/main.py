import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240
FPS = 30
NUM_CHARS = 6
CIRCLE_RADIUS = 75
CIRCLE_CENTER_X = 160
CIRCLE_CENTER_Y = 120
CHAR_SIZE = 16
BOMB_RADIUS = 8
SUPER_DURATION = 150
GAME_DURATION = 1800
HEAT_MAX = 100
HEAT_WRONG = 15
HEAT_DECAY = 0.05
HEAT_NATURAL = 0.1
COMBO_SUPER_THRESHOLD = 4

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


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class BombColor(Enum):
    RED = 0
    GREEN = 1
    BLUE = 2
    YELLOW = 3
    RAINBOW = 4


BOMB_COLORS: dict[BombColor, int] = {
    BombColor.RED: RED,
    BombColor.GREEN: GREEN,
    BombColor.BLUE: DARK_BLUE,
    BombColor.YELLOW: YELLOW,
    BombColor.RAINBOW: WHITE,
}

BOMB_COLOR_LIST = [BombColor.RED, BombColor.GREEN, BombColor.BLUE, BombColor.YELLOW]


@dataclass
class Character:
    x: float
    y: float
    color: BombColor
    color_timer: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class GhostTrail:
    x: float
    y: float
    life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


def _compute_char_positions() -> list[tuple[float, float]]:
    positions: list[tuple[float, float]] = []
    for i in range(NUM_CHARS):
        angle = math.radians(i * 60 - 90)
        x = CIRCLE_CENTER_X + CIRCLE_RADIUS * math.cos(angle)
        y = CIRCLE_CENTER_Y + CIRCLE_RADIUS * math.sin(angle)
        positions.append((x, y))
    return positions


class Game:
    SCREEN_W = SCREEN_W
    SCREEN_H = SCREEN_H
    FPS = FPS
    NUM_CHARS = NUM_CHARS
    CIRCLE_RADIUS = CIRCLE_RADIUS
    CIRCLE_CENTER_X = CIRCLE_CENTER_X
    CIRCLE_CENTER_Y = CIRCLE_CENTER_Y
    CHAR_SIZE = CHAR_SIZE
    BOMB_RADIUS = BOMB_RADIUS
    SUPER_DURATION = SUPER_DURATION
    GAME_DURATION = GAME_DURATION
    HEAT_MAX = HEAT_MAX
    HEAT_WRONG = HEAT_WRONG
    HEAT_DECAY = HEAT_DECAY
    HEAT_NATURAL = HEAT_NATURAL
    COMBO_SUPER_THRESHOLD = COMBO_SUPER_THRESHOLD
    GHOST_HEAT_RADIUS = 30
    GHOST_HEAT_AMOUNT = 2

    phase: Phase
    score: int
    combo: int
    max_combo: int
    heat: float
    bomb_color: BombColor
    bomb_holder: int
    target_idx: int
    characters: list[Character]
    pos_cache: list[tuple[float, float]]
    particles: list[Particle]
    ghosts: list[GhostTrail]
    floating_texts: list[FloatingText]
    super_timer: int
    game_timer: int
    tick_timer: int
    shake_frames: int
    frame: int
    rng: random.Random
    _stored_color: BombColor

    def __init__(self) -> None:
        self.rng = random.Random()
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.bomb_color = BombColor.RED
        self.bomb_holder = 0
        self.target_idx = 1
        self.pos_cache = _compute_char_positions()
        self.characters = []
        for i, (x, y) in enumerate(self.pos_cache):
            color = BOMB_COLOR_LIST[i % len(BOMB_COLOR_LIST)]
            timer = self.rng.randint(90, 150)
            self.characters.append(Character(x, y, color, timer))
        self.particles = []
        self.ghosts = []
        self.floating_texts = []
        self.super_timer = 0
        self.game_timer = GAME_DURATION
        self.tick_timer = 30
        self.shake_frames = 0
        self.frame = 0
        self._stored_color = BombColor.RED

    def _select_target(self, direction: int) -> None:
        if self.phase != Phase.PLAYING:
            return
        idx = self.target_idx
        while True:
            idx = (idx + direction) % NUM_CHARS
            if idx != self.bomb_holder:
                break
        self.target_idx = idx

    def _try_pass(self, target_idx: int) -> bool:
        if self.phase != Phase.PLAYING:
            return False
        if target_idx == self.bomb_holder:
            return False

        from_x, from_y = self.pos_cache[self.bomb_holder]
        to_x, to_y = self.pos_cache[target_idx]
        mid_x = (from_x + to_x) / 2
        mid_y = (from_y + to_y) / 2

        ghost_heat = 0
        for g in self.ghosts:
            dx = mid_x - g.x
            dy = mid_y - g.y
            if dx * dx + dy * dy < self.GHOST_HEAT_RADIUS * self.GHOST_HEAT_RADIUS:
                ghost_heat += self.GHOST_HEAT_AMOUNT
        if ghost_heat > 0:
            self.heat = min(HEAT_MAX, self.heat + ghost_heat)

        if self.super_timer > 0:
            is_match = True
        else:
            is_match = self.bomb_color == self.characters[target_idx].color

        if is_match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            multiplier = 3 if self.super_timer > 0 else 1
            gain = int(10 * (1 + self.combo * 0.5) * multiplier)
            self.score += gain
            self._spawn_pass_particles(mid_x, mid_y, True)
            color_int = BOMB_COLORS[BombColor.RAINBOW] if self.super_timer > 0 else BOMB_COLORS[self.bomb_color]
            self._spawn_ghost_midpoint(from_x, from_y, to_x, to_y, color_int)
            self.floating_texts.append(FloatingText(mid_x, mid_y, f"+{gain}", 40, YELLOW))
            if self.combo >= COMBO_SUPER_THRESHOLD and self.super_timer == 0:
                self.super_timer = SUPER_DURATION
                self._stored_color = self.bomb_color
                self.bomb_color = BombColor.RAINBOW
                self._spawn_super_burst()
                self.floating_texts.append(
                    FloatingText(CIRCLE_CENTER_X, CIRCLE_CENTER_Y, "SUPER!!", 60, WHITE)
                )
        else:
            self.heat = min(HEAT_MAX, self.heat + HEAT_WRONG)
            self.combo = 0
            self.shake_frames = 10
            self._spawn_pass_particles(mid_x, mid_y, False)
            color_int = BOMB_COLORS[self.bomb_color]
            self._spawn_ghost_midpoint(from_x, from_y, to_x, to_y, color_int)
            self.floating_texts.append(FloatingText(mid_x, mid_y, "MISS!", 30, RED))
            if self.super_timer > 0:
                self.super_timer = 0
                self.bomb_color = self._stored_color

        self._change_bomb_color()
        self.bomb_holder = target_idx
        self.target_idx = (target_idx + 1) % NUM_CHARS
        if self.target_idx == self.bomb_holder:
            self.target_idx = (self.target_idx + 1) % NUM_CHARS

        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
        return True

    def _change_bomb_color(self) -> None:
        if self.super_timer > 0:
            return
        keep_same = self.rng.random() < 0.4
        if keep_same:
            return
        choices = [c for c in BOMB_COLOR_LIST if c != self.bomb_color]
        self.bomb_color = self.rng.choice(choices)

    def _spawn_pass_particles(self, x: float, y: float, is_match: bool) -> None:
        if is_match:
            count = self.rng.randint(8, 12)
            for _ in range(count):
                vx = self.rng.uniform(-1.5, 1.5)
                vy = self.rng.uniform(-2.0, -0.5)
                life = self.rng.randint(20, 30)
                color = self.rng.choice([GREEN, LIME])
                self.particles.append(Particle(x, y, vx, vy, life, color))
        else:
            count = self.rng.randint(4, 6)
            for _ in range(count):
                vx = self.rng.uniform(-1.0, 1.0)
                vy = self.rng.uniform(-1.5, -0.5)
                life = self.rng.randint(15, 20)
                self.particles.append(Particle(x, y, vx, vy, life, RED))

    def _spawn_super_burst(self) -> None:
        for _ in range(20):
            vx = self.rng.uniform(-2.0, 2.0)
            vy = self.rng.uniform(-3.0, -1.0)
            life = self.rng.randint(30, 40)
            color = self.rng.choice([RED, GREEN, DARK_BLUE, YELLOW, WHITE, CYAN, LIME])
            self.particles.append(Particle(CIRCLE_CENTER_X, CIRCLE_CENTER_Y, vx, vy, life, color))

    def _spawn_ghost_midpoint(
        self, from_x: float, from_y: float, to_x: float, to_y: float, color: int
    ) -> None:
        mid_x = (from_x + to_x) / 2
        mid_y = (from_y + to_y) / 2
        self.ghosts.append(GhostTrail(mid_x, mid_y, 90, color))

    def _update_char_colors(self) -> None:
        for ch in self.characters:
            ch.color_timer -= 1
            if ch.color_timer <= 0:
                idx = BOMB_COLOR_LIST.index(ch.color)
                ch.color = BOMB_COLOR_LIST[(idx + 1) % len(BOMB_COLOR_LIST)]
                ch.color_timer = self.rng.randint(90, 150)

    def _update_heat(self) -> None:
        self.heat = min(HEAT_MAX, self.heat + HEAT_NATURAL)
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_timers(self) -> None:
        self.game_timer = max(0, self.game_timer - 1)
        self.tick_timer = max(0, self.tick_timer - 1)
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self.bomb_color = self._stored_color

    def _check_game_over(self) -> bool:
        return self.heat >= HEAT_MAX or self.game_timer <= 0

    def _update_particles(self) -> None:
        for p in self.particles:
            p.life -= 1
            p.x += p.vx
            p.y += p.vy
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_ghosts(self) -> None:
        for g in self.ghosts:
            g.life -= 1
        self.ghosts = [g for g in self.ghosts if g.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.life -= 1
            ft.y -= 0.5
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.PLAYING
                self.reset_playing()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if self.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.KEY_LEFT):
                self._select_target(-1)
            if pyxel.btnp(pyxel.KEY_RIGHT):
                self._select_target(1)
            if pyxel.btnp(pyxel.KEY_SPACE):
                self._try_pass(self.target_idx)

            self.frame += 1
            self._update_timers()
            self._update_heat()
            self._update_char_colors()
            self._update_particles()
            self._update_ghosts()
            self._update_floating_texts()

            if self.tick_timer <= 0:
                tick_interval = max(30 - int(self.heat / 5), 8)
                self.tick_timer = tick_interval

            if self.shake_frames > 0:
                self.shake_frames -= 1

            if self._check_game_over():
                self.phase = Phase.GAME_OVER

    def reset_playing(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.bomb_color = BombColor.RED
        self.bomb_holder = 0
        self.target_idx = 1
        self.pos_cache = _compute_char_positions()
        self.characters = []
        for i, (x, y) in enumerate(self.pos_cache):
            color = BOMB_COLOR_LIST[i % len(BOMB_COLOR_LIST)]
            timer = self.rng.randint(90, 150)
            self.characters.append(Character(x, y, color, timer))
        self.particles = []
        self.ghosts = []
        self.floating_texts = []
        self.super_timer = 0
        self.game_timer = GAME_DURATION
        self.tick_timer = 30
        self.shake_frames = 0
        self.frame = 0
        self._stored_color = BombColor.RED

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.shake_frames > 0:
            ox = self.rng.randint(-4, 4)
            oy = self.rng.randint(-4, 4)
        else:
            ox, oy = 0, 0

        try:
            pyxel.camera(ox, oy)
        except BaseException:
            pass

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        try:
            pyxel.camera(0, 0)
        except BaseException:
            pass

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 36, 80, "TICK SURGE", WHITE)
        pyxel.text(SCREEN_W // 2 - 60, 100, "HOT POTATO BOMB PASS", GRAY)
        pyxel.text(SCREEN_W // 2 - 64, 140, "LEFT/RIGHT: Select Target", GRAY)
        pyxel.text(SCREEN_W // 2 - 48, 150, "SPACE: Pass Bomb", GRAY)
        pyxel.text(SCREEN_W // 2 - 56, 170, "Match color = COMBO", GRAY)
        pyxel.text(SCREEN_W // 2 - 64, 180, "COMBO>=4 = SUPER PASS", GRAY)
        if (self.frame % 30) < 15:
            pyxel.text(SCREEN_W // 2 - 60, 220, "PRESS SPACE TO START", WHITE)
        self.frame += 1

    def _draw_playing(self) -> None:
        self._draw_ghosts()
        self._draw_characters()
        self._draw_bomb()
        self._draw_target_indicator()
        self._draw_hud()
        self._draw_super_indicator()
        self._draw_particles()
        self._draw_floating_texts()

    def _draw_characters(self) -> None:
        for i, ch in enumerate(self.characters):
            color = BOMB_COLORS[ch.color]
            cx = int(ch.x) - CHAR_SIZE // 2
            cy = int(ch.y) - CHAR_SIZE // 2
            if i == self.bomb_holder:
                pyxel.rectb(cx - 2, cy - 2, CHAR_SIZE + 4, CHAR_SIZE + 4, WHITE)
            pyxel.rect(cx, cy, CHAR_SIZE, CHAR_SIZE, color)
            pyxel.rectb(cx, cy, CHAR_SIZE, CHAR_SIZE, WHITE)

    def _draw_bomb(self) -> None:
        ch = self.characters[self.bomb_holder]
        bx = int(ch.x)
        by = int(ch.y)
        bomb_color_int = self._get_bomb_draw_color()

        tick_pulse = BOMB_RADIUS
        tick_interval = max(30 - int(self.heat / 5), 8)
        if self.tick_timer > tick_interval - 4:
            tick_pulse = BOMB_RADIUS + 2

        pyxel.circ(bx, by, tick_pulse, bomb_color_int)
        pyxel.circb(bx, by, tick_pulse, WHITE)

    def _get_bomb_draw_color(self) -> int:
        if self.bomb_color == BombColor.RAINBOW:
            idx = (self.frame // 4) % 4
            return BOMB_COLORS[BOMB_COLOR_LIST[idx]]
        return BOMB_COLORS[self.bomb_color]

    def _draw_target_indicator(self) -> None:
        if self.phase != Phase.PLAYING:
            return
        ch = self.characters[self.target_idx]
        cx = int(ch.x) - CHAR_SIZE // 2 - 2
        cy = int(ch.y) - CHAR_SIZE // 2 - 2
        pulse = (self.frame % 20) < 10
        if pulse:
            pyxel.rectb(cx, cy, CHAR_SIZE + 4, CHAR_SIZE + 4, WHITE)

    def _draw_hud(self) -> None:
        pyxel.text(10, 8, f"SCORE: {self.score}", WHITE)
        combo_color = WHITE if self.combo >= COMBO_SUPER_THRESHOLD else YELLOW
        pyxel.text(10, 20, f"COMBO: x{self.combo}", combo_color)

        bar_w = 160
        bar_h = 10
        bar_x = 80
        bar_y = 8
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_w = int(bar_w * self.heat / HEAT_MAX)
        heat_color = RED
        if self.heat >= 80:
            if (self.frame % 4) < 2:
                heat_color = RED
            else:
                heat_color = WHITE
        elif self.heat >= 60:
            heat_color = ORANGE
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_color)

        time_sec = self.game_timer // 30
        time_str = f"TIME: {time_sec}"
        time_color = RED if time_sec < 15 else WHITE
        pyxel.text(SCREEN_W - 60, 8, time_str, time_color)

    def _draw_super_indicator(self) -> None:
        if self.super_timer > 0:
            idx = (self.frame // 4) % 4
            color = BOMB_COLORS[BOMB_COLOR_LIST[idx]]
            pyxel.text(SCREEN_W // 2 - 24, 40, "SUPER!!", color)

    def _draw_ghosts(self) -> None:
        for g in self.ghosts:
            alpha = g.life / 90.0
            color = g.color
            if alpha < 0.3:
                color = max(color - 1, 0)
            pyxel.circb(int(g.x), int(g.y), BOMB_RADIUS + 2, color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 40.0
            color = ft.color
            if alpha < 0.3:
                color = GRAY
            pyxel.text(int(ft.x) - 12, int(ft.y), ft.text, color)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 28, 60, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 40, 100, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 48, 120, f"MAX COMBO: x{self.max_combo}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 60, 160, f"FINAL HEAT: {self.heat:.1f}%", ORANGE)
        if (self.frame % 30) < 15:
            pyxel.text(SCREEN_W // 2 - 60, 200, "PRESS SPACE TO RETRY", WHITE)
        self.frame += 1


def main() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="Tick Surge")
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
