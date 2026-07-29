from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

SCREEN_W = 320
SCREEN_H = 240
NUM_DICE = 5
DIE_SIZE = 48
DIE_GAP = 12
DICE_START_X = (SCREEN_W - (NUM_DICE * DIE_SIZE + (NUM_DICE - 1) * DIE_GAP)) // 2
DICE_Y = 80
MAX_ROLLS = 3
HEAT_MAX = 100.0
HEAT_DECAY = 0.02
HEAT_MISMATCH = 15.0
SUPER_DURATION = 300
SUPER_COMBO_THRESHOLD = 4
GAME_TIME = 1800
SCORE_ANIM_FRAMES = 30
ROLL_ANIM_FRAMES = 15
FPS = 30

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

DIE_COLORS: tuple[int, int, int, int] = (RED, LIME, DARK_BLUE, YELLOW)
COLOR_NAMES: dict[int, str] = {RED: "RED", LIME: "LIME", DARK_BLUE: "BLUE", YELLOW: "YELLOW"}


class Phase(Enum):
    TITLE = auto()
    ROLLING = auto()
    SCORING = auto()
    GAME_OVER = auto()


@dataclass
class Die:
    color: int = RED
    held: bool = False
    x: int = 0
    y: int = 0
    roll_frame: int = 0
    target_color: int = RED


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


def evaluate_hand(dice: list[Die]) -> tuple[int, str, int]:
    counts: Counter[int] = Counter(d.color for d in dice)
    most_common_color, count = counts.most_common(1)[0]

    if count == 5:
        return (100, "YAHTZEE!", most_common_color)
    elif count == 4:
        return (60, "FOUR KIND", most_common_color)
    elif count == 3:
        has_pair = any(c == 2 for c in counts.values())
        if has_pair:
            return (50, "FULL HOUSE", most_common_color)
        return (30, "THREE KIND", most_common_color)
    elif count == 2:
        pairs = sum(1 for c in counts.values() if c == 2)
        if pairs == 2:
            return (20, "TWO PAIR", most_common_color)
        return (10, "ONE PAIR", most_common_color)
    else:
        return (5, "NO MATCH", most_common_color)


class Game:
    COLORS: ClassVar[tuple[int, ...]] = DIE_COLORS

    def __new__(cls, headless: bool = False) -> Game:
        obj = object.__new__(cls)
        obj._set_defaults()
        obj._headless = headless
        return obj

    def _set_defaults(self) -> None:
        self._headless: bool = False
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.best_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = GAME_TIME
        self.super_timer: int = 0
        self.best_hand: str = ""
        self.best_hand_score: int = 0
        self.rolls_left: int = MAX_ROLLS
        self.prev_dominant_color: int = -1
        self.dice: list[Die] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.score_anim_frame: int = 0
        self.last_hand_name: str = ""
        self.last_hand_score: int = 0
        self.last_dominant_color: int = -1
        self.yahtzee_flash: int = 0
        self.button_hover: bool = False
        self.frame: int = 0
        self._rng: random.Random = random.Random()
        self._init_dice()

    def __init__(self, headless: bool = False) -> None:
        if not headless:
            pyxel.init(SCREEN_W, SCREEN_H, title="YACHT CHAIN", fps=FPS)
            self.reset()
            pyxel.run(self._update, self._draw)

    def _init_dice(self) -> None:
        self.dice = []
        for i in range(NUM_DICE):
            d = Die(
                color=RED,
                held=False,
                x=DICE_START_X + i * (DIE_SIZE + DIE_GAP) + DIE_SIZE // 2,
                y=DICE_Y + DIE_SIZE // 2,
                roll_frame=0,
                target_color=RED,
            )
            self.dice.append(d)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_TIME
        self.super_timer = 0
        self.best_hand = ""
        self.best_hand_score = 0
        self.rolls_left = MAX_ROLLS
        self.prev_dominant_color = -1
        self.particles.clear()
        self.floating_texts.clear()
        self.score_anim_frame = 0
        self.last_hand_name = ""
        self.last_hand_score = 0
        self.last_dominant_color = -1
        self.yahtzee_flash = 0
        self.button_hover = False
        self.frame = 0
        for d in self.dice:
            d.color = RED
            d.held = False
            d.roll_frame = 0
            d.target_color = RED

    def _get_input(self) -> dict:
        if self._headless:
            return {
                "space_p": False,
                "space": False,
                "r_p": False,
                "mouse_x": 0,
                "mouse_y": 0,
                "mouse_pressed": False,
            }
        return {
            "space_p": pyxel.btnp(pyxel.KEY_SPACE),
            "space": pyxel.btn(pyxel.KEY_SPACE),
            "r_p": pyxel.btnp(pyxel.KEY_R),
            "mouse_x": pyxel.mouse_x,
            "mouse_y": pyxel.mouse_y,
            "mouse_pressed": pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT),
        }

    def _update(self) -> None:
        inp = self._get_input()
        if self.phase == Phase.TITLE:
            self._update_title(inp)
        elif self.phase == Phase.ROLLING:
            self._update_rolling(inp)
        elif self.phase == Phase.SCORING:
            self._update_scoring(inp)
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over(inp)

    def _update_title(self, inp: dict) -> None:
        if inp["mouse_pressed"] or inp["space_p"]:
            self.phase = Phase.ROLLING
            self.score = 0
            self.combo = 0
            self.max_combo = 0
            self.heat = 0.0
            self.timer = GAME_TIME
            self.super_timer = 0
            self.best_hand = ""
            self.best_hand_score = 0
            self.rolls_left = MAX_ROLLS
            self.prev_dominant_color = -1
            self.particles.clear()
            self.floating_texts.clear()
            self.score_anim_frame = 0
            self.last_hand_name = ""
            self.last_hand_score = 0
            self.last_dominant_color = -1
            self.yahtzee_flash = 0
            self.button_hover = False
            self.frame = 0
            for d in self.dice:
                d.color = RED
                d.held = False
                d.roll_frame = 0
                d.target_color = RED

    def _update_rolling(self, inp: dict) -> None:
        self.frame += 1

        if self._is_super():
            self.super_timer -= 1
            if self.super_timer == 0:
                self.combo = 0

        self._update_roll_animation()

        if self._is_rolling():
            self._update_particles()
            self._update_floating_texts()
            return

        if self.heat >= HEAT_MAX:
            self.heat = HEAT_MAX
            if self.score > self.best_score:
                self.best_score = self.score
            self.phase = Phase.GAME_OVER
            return

        if self.timer > 0:
            self.timer -= 1

        if self.timer <= 0:
            self.timer = 0
            if self.score > self.best_score:
                self.best_score = self.score
            self.phase = Phase.GAME_OVER
            return

        if not self._is_super():
            self.heat = max(0.0, self.heat - HEAT_DECAY)

        if inp["mouse_pressed"]:
            mx, my = inp["mouse_x"], inp["mouse_y"]
            if self._hit_roll_button(mx, my):
                self._do_roll()
                return
            if self.rolls_left < MAX_ROLLS and self._hit_score_button(mx, my):
                self._do_score()
                return
            for d in self.dice:
                if self._hit_die(mx, my, d):
                    d.held = not d.held
                    try:
                        pyxel.play(3, d.held and 1 or 0)
                    except BaseException:
                        pass

        if inp["space_p"]:
            self._do_roll()

        self.button_hover = self._hit_roll_button(inp["mouse_x"], inp["mouse_y"])

        if self.rolls_left <= 0 and not self._is_rolling():
            self._do_score()

    def _is_rolling(self) -> bool:
        return any(d.roll_frame > 0 for d in self.dice)

    def _update_roll_animation(self) -> None:
        for d in self.dice:
            if d.roll_frame > 0:
                d.color = self._rng.choice(DIE_COLORS)
                d.roll_frame -= 1
                if d.roll_frame == 0:
                    d.color = d.target_color
                if d.roll_frame == 0 and self.rolls_left <= 0:
                    pass

    def _do_roll(self) -> None:
        if self.rolls_left <= 0:
            return
        if self._is_rolling():
            return
        self.rolls_left -= 1
        for d in self.dice:
            if not d.held:
                d.target_color = self._rng.choice(DIE_COLORS)
                d.roll_frame = ROLL_ANIM_FRAMES

    def _do_score(self) -> None:
        try:
            pyxel.play(0, 2)
        except BaseException:
            pass
        base_score, hand_name, dominant_color = evaluate_hand(self.dice)

        if hand_name == "YAHTZEE!":
            self.yahtzee_flash = 15

        super_multiplier = 3 if self._is_super() else 1

        if self.prev_dominant_color == -1:
            self.combo = 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
        elif self.prev_dominant_color == dominant_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
        else:
            if not self._is_super():
                self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
            self.combo = 0
            if self._is_super():
                self.combo += 1

        final_score = int(base_score * (1 + self.combo * 0.5) * super_multiplier)
        self.score += final_score
        self.last_hand_name = hand_name
        self.last_hand_score = final_score
        self.last_dominant_color = dominant_color
        self.prev_dominant_color = dominant_color

        if final_score > self.best_hand_score:
            self.best_hand_score = final_score
            self.best_hand = f"{hand_name} ({final_score})"

        for d in self.dice:
            d.held = False

        if self.combo >= SUPER_COMBO_THRESHOLD and self.super_timer == 0:
            self.super_timer = SUPER_DURATION

        cx = DICE_START_X + (NUM_DICE * DIE_SIZE + (NUM_DICE - 1) * DIE_GAP) // 2
        cy = DICE_Y + DIE_SIZE // 2

        pcount = 30 if hand_name == "YAHTZEE!" else (20 if hand_name == "FOUR KIND" else 12)
        self._spawn_particles(float(cx), float(cy), pcount, -1)

        self._spawn_floating_text(float(cx) - 20, float(cy) - DIE_SIZE // 2 - 10, f"+{final_score}", LIME, 30)
        if self.combo >= 2:
            self._spawn_floating_text(float(cx) + 20, float(cy) - DIE_SIZE // 2 - 25, f"COMBO x{self.combo}", YELLOW, 30)
        if self._is_super():
            self._spawn_floating_text(float(cx) - 30, float(cy) - DIE_SIZE // 2 - 40, "SUPER x3!", ORANGE, 30)

        self.score_anim_frame = SCORE_ANIM_FRAMES
        self.phase = Phase.SCORING

    def _update_scoring(self, inp: dict) -> None:
        self.frame += 1

        if self._is_super():
            self.super_timer -= 1
            if self.super_timer == 0:
                self.combo = 0

        self._update_particles()
        self._update_floating_texts()

        if self.yahtzee_flash > 0:
            self.yahtzee_flash -= 1

        self.score_anim_frame -= 1

        if self.heat >= HEAT_MAX:
            self.heat = HEAT_MAX
            if self.score > self.best_score:
                self.best_score = self.score
            self.phase = Phase.GAME_OVER
            return

        if self.timer > 0:
            self.timer -= 1

        if self.timer <= 0:
            self.timer = 0
            if self.score > self.best_score:
                self.best_score = self.score
            self.phase = Phase.GAME_OVER
            return

        if not self._is_super():
            self.heat = max(0.0, self.heat - HEAT_DECAY)

        if self.score_anim_frame <= 0:
            self.rolls_left = MAX_ROLLS
            for d in self.dice:
                d.held = False
                d.roll_frame = 0
            self.phase = Phase.ROLLING

    def _update_game_over(self, inp: dict) -> None:
        if inp["mouse_pressed"] or inp["space_p"] or inp["r_p"]:
            self.reset()
            self.phase = Phase.TITLE

    def _is_super(self) -> bool:
        return self.super_timer > 0

    def _hit_die(self, mx: int, my: int, d: Die) -> bool:
        left = d.x - DIE_SIZE // 2
        top = d.y - DIE_SIZE // 2
        return left <= mx <= left + DIE_SIZE and top <= my <= top + DIE_SIZE

    def _hit_roll_button(self, mx: int, my: int) -> bool:
        bx = (SCREEN_W - 100) // 2
        by = 160
        return bx <= mx <= bx + 100 and by <= my <= by + 30

    def _hit_score_button(self, mx: int, my: int) -> bool:
        bx = 260
        by = 160
        return bx <= mx <= bx + 50 and by <= my <= by + 30

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            pcolor = color if color != -1 else self._rng.choice(DIE_COLORS)
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-2.5, -0.5)
            life = self._rng.randint(15, 25) if color == -1 else self._rng.randint(12, 20)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, color=pcolor, life=life))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=life))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.05
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.ROLLING, Phase.SCORING):
            self._draw_hud()
            self._draw_dice()
            self._draw_buttons()
            self._draw_hand_eval()
            self._draw_particles()
            self._draw_floating_texts()
            if self._is_super():
                self._draw_super_border()
            if self.phase == Phase.SCORING:
                self._draw_score_overlay()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)
        pyxel.text(SCREEN_W // 2 - 48, 40, "YACHT CHAIN", WHITE)
        pyxel.text(SCREEN_W // 2 - 72, 58, "Poker Dice x Color Match", LIME)
        pyxel.text(SCREEN_W // 2 - 60, 82, "Click dice to HOLD", WHITE)
        pyxel.text(SCREEN_W // 2 - 60, 94, "Press SPACE or click ROLL to roll", WHITE)
        pyxel.text(SCREEN_W // 2 - 60, 106, "Hold good dice, re-roll the rest", GRAY)
        pyxel.text(SCREEN_W // 2 - 60, 118, "Same-color consecutive = COMBO chain", LIME)
        pyxel.text(SCREEN_W // 2 - 60, 130, "Color mismatch = COMBO reset + HEAT", RED)
        pyxel.text(SCREEN_W // 2 - 60, 142, "COMBO x4 = SUPER ROLL (3x score!)", YELLOW)
        pyxel.text(SCREEN_W // 2 - 60, 154, "YAHTZEE = all 5 same color (100pts)", ORANGE)
        pyxel.text(SCREEN_W // 2 - 60, 166, "HEAT 100 or 60s time up = GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 50, 190, "Click or SPACE to start", CYAN)
        if self.best_score > 0:
            pyxel.text(SCREEN_W // 2 - 30, 210, f"BEST: {self.best_score}", YELLOW)

    def _draw_hud(self) -> None:
        pyxel.text(4, 2, f"SCORE: {self.score}", WHITE)
        pyxel.text(4, 12, f"COMBO: {self.combo}", YELLOW if self.combo >= 3 else WHITE)
        pyxel.text(4, 22, f"MAX: {self.max_combo}", LIME)

        secs = max(0, self.timer // FPS)
        timer_color = WHITE
        if secs <= 10:
            timer_color = RED
        elif secs <= 20:
            timer_color = ORANGE
        pyxel.text(SCREEN_W // 2 - 20, 2, f"TIME: {secs}s", timer_color)

        if self.best_hand:
            pyxel.text(SCREEN_W - 100, 2, "BEST:", WHITE)
            pyxel.text(SCREEN_W - 100, 12, self.best_hand, ORANGE)

        pyxel.text(4, SCREEN_H - 40, "HEAT", WHITE)
        heat_w = 80
        heat_h = 6
        pyxel.rectb(4, SCREEN_H - 32, heat_w, heat_h, WHITE)
        heat_fill = int(heat_w * self.heat / HEAT_MAX)
        heat_color = LIME if self.heat <= 60 else ORANGE if self.heat <= 80 else RED
        pyxel.rect(4, SCREEN_H - 32, heat_fill, heat_h, heat_color)

        if self._is_super():
            super_secs = self.super_timer // FPS
            rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
            col = rainbow[(pyxel.frame_count // 3) % len(rainbow)]
            pyxel.text(SCREEN_W // 2 - 40, 18, f"SUPER ROLL! {super_secs}s", col)

    def _draw_dice(self) -> None:
        for d in self.dice:
            left = d.x - DIE_SIZE // 2
            top = d.y - DIE_SIZE // 2

            die_color = d.color
            if self._is_super():
                rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
                die_color = rainbow[(pyxel.frame_count // 4 + d.x) % len(rainbow)]

            pyxel.rect(left, top, DIE_SIZE, DIE_SIZE, die_color)
            pyxel.rectb(left, top, DIE_SIZE, DIE_SIZE, BLACK)

            if d.held:
                pyxel.rectb(left - 2, top - 2, DIE_SIZE + 4, DIE_SIZE + 4, WHITE)

            self._draw_pips(die_color, left, top)

    def _draw_pips(self, die_color: int, left: int, top: int) -> None:
        pip_color = WHITE if die_color != WHITE else BLACK
        s = DIE_SIZE
        r = s // 8
        cx = left + s // 2
        cy = top + s // 2

        color_idx = DIE_COLORS.index(die_color) if die_color in DIE_COLORS else 0
        pip_count = color_idx + 1

        positions: dict[int, list[tuple[int, int]]] = {
            1: [(cx, cy)],
            2: [(cx - r * 2, cy - r * 2), (cx + r * 2, cy + r * 2)],
            3: [(cx - r * 2, cy - r * 2), (cx, cy), (cx + r * 2, cy + r * 2)],
            4: [(cx - r * 2, cy - r * 2), (cx + r * 2, cy - r * 2), (cx - r * 2, cy + r * 2), (cx + r * 2, cy + r * 2)],
        }

        for px, py in positions.get(pip_count, [(cx, cy)]):
            pyxel.circ(px, py, 3, pip_color)

    def _draw_buttons(self) -> None:
        bx = (SCREEN_W - 100) // 2
        by = 160

        btn_color = GREEN if self.button_hover else GRAY
        if self.rolls_left <= 0:
            btn_color = DARK_BLUE
        pyxel.rect(bx, by, 100, 30, btn_color)
        pyxel.text(bx + 10, by + 12, f"ROLL ({self.rolls_left})", WHITE)

        if self.rolls_left < MAX_ROLLS and self.phase == Phase.ROLLING:
            sx, sy = 260, 160
            pyxel.rect(sx, sy, 50, 30, ORANGE)
            pyxel.rectb(sx, sy, 50, 30, WHITE)
            pyxel.text(sx + 10, sy + 12, "SCORE", WHITE)

    def _draw_hand_eval(self) -> None:
        if self.phase == Phase.SCORING and self.last_hand_name:
            hand_color = ORANGE if self.last_hand_name == "YAHTZEE!" else WHITE
            tx = SCREEN_W // 2 - len(self.last_hand_name) * 2
            pyxel.text(tx, DICE_Y - 16, self.last_hand_name, hand_color)
            score_tx = SCREEN_W // 2 - 20
            pyxel.text(score_tx, DICE_Y - 8, f"+{self.last_hand_score}", LIME)
        elif self.phase == Phase.ROLLING:
            if self.rolls_left < MAX_ROLLS:
                _, hand_name, _ = evaluate_hand(self.dice)
                tx = SCREEN_W // 2 - len(hand_name) * 2
                pyxel.text(tx, DICE_Y - 16, hand_name, GRAY)

    def _draw_score_overlay(self) -> None:
        if self.score_anim_frame > 20:
            alpha = (self.score_anim_frame - 20) / 10
            if alpha > 0.3:
                return
            pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)
        if self.yahtzee_flash > 0 and self.yahtzee_flash % 4 < 2:
            pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2, "YAHTZEE!!!", ORANGE)

    def _draw_super_border(self) -> None:
        rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
        idx = (pyxel.frame_count // 4) % len(rainbow)
        col = rainbow[idx]
        pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, col)
        idx2 = (idx + 3) % len(rainbow)
        col2 = rainbow[idx2]
        if pyxel.frame_count % 8 < 4:
            pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, col2)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 8:
                pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)
            else:
                pyxel.circ(int(p.x), int(p.y), 1, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_game_over(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)
        pyxel.text(SCREEN_W // 2 - 65, 40, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 50, 60, f"SCORE: {self.score}", WHITE)
        if self.score >= self.best_score and self.score > 0:
            pyxel.text(SCREEN_W // 2 - 35, 72, "NEW BEST!", YELLOW)
        pyxel.text(SCREEN_W // 2 - 60, 90, f"Best Hand: {self.best_hand}", ORANGE)
        pyxel.text(SCREEN_W // 2 - 50, 106, f"Max Combo: {self.max_combo}", LIME)
        pyxel.text(SCREEN_W // 2 - 40, 122, f"Final Heat: {int(self.heat)}", RED)
        pyxel.text(SCREEN_W // 2 - 55, 160, "Click or SPACE to retry", CYAN)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
