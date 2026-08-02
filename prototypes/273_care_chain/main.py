from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WIDTH = 320
HEIGHT = 240
FPS = 30

GAME_DURATION = 1800  # 60s * 30fps
SUPER_DURATION = 300  # 10s * 30fps
STAT_DECAY_INTERVAL = 30  # every 30 frames = 1 second
COMBO_THRESHOLD = 4
SUPER_MULT = 3.0

# Stat decay per interval
DECAY_HAPPINESS = 0.5
DECAY_HUNGER = 0.8
DECAY_ENERGY = 0.6
DECAY_STRESS = 0.3

STRESS_CAP = 100.0
STAT_MIN = 0.0
STAT_MAX = 100.0

# Color palette
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

RAINBOW = (RED, ORANGE, YELLOW, LIME, CYAN, PINK)

# Button layout
BUTTON_XS = (30, 100, 170, 240)
BUTTON_Y = 100
BUTTON_W = 60
BUTTON_H = 40

# Stat bar Y positions
STAT_BAR_YS = (155, 175, 195, 215)
STAT_BAR_H = 18
STAT_BAR_X = 40
STAT_BAR_W = 270

# CA spread chain ordering
STAT_NAMES = ("happiness", "hunger", "energy", "stress")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class ActionType(Enum):
    FEED = auto()
    PLAY = auto()
    REST = auto()
    TRAIN = auto()


ACTION_COLORS: dict[ActionType, int] = {
    ActionType.FEED: GRAY,
    ActionType.PLAY: LIME,
    ActionType.REST: CYAN,
    ActionType.TRAIN: ORANGE,
}

ACTION_LABELS: dict[ActionType, str] = {
    ActionType.FEED: "FEED",
    ActionType.PLAY: "PLAY",
    ActionType.REST: "REST",
    ActionType.TRAIN: "TRAIN",
}

# Stat effects: (happiness_change, hunger_change, energy_change, stress_change)
ACTION_EFFECTS: dict[ActionType, tuple[float, float, float, float]] = {
    ActionType.FEED: (5.0, 15.0, 5.0, 2.0),
    ActionType.PLAY: (15.0, -10.0, -5.0, 3.0),
    ActionType.REST: (3.0, -2.0, 15.0, -10.0),
    ActionType.TRAIN: (10.0, -5.0, -8.0, 8.0),
}

ACTIONS_ORDERED: list[ActionType] = [
    ActionType.FEED,
    ActionType.PLAY,
    ActionType.REST,
    ActionType.TRAIN,
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------


class Game:
    phase: Phase
    score: int
    best_score: int
    combo: int
    max_combo: int
    last_action: ActionType | None
    timer: int
    super_timer: int
    stress: float
    happiness: float
    hunger: float
    energy: float
    particles: list[Particle]
    floating_texts: list[FloatingText]
    frame: int
    shake_frames: int
    pet_frame: int
    _rng: random.Random

    def __new__(cls) -> Game:
        obj = object.__new__(cls)
        obj.phase = Phase.TITLE
        obj.score = 0
        obj.best_score = 0
        obj.combo = 0
        obj.max_combo = 0
        obj.last_action = None
        obj.timer = GAME_DURATION
        obj.super_timer = 0
        obj.stress = 0.0
        obj.happiness = 50.0
        obj.hunger = 50.0
        obj.energy = 50.0
        obj.particles = []
        obj.floating_texts = []
        obj.frame = 0
        obj.shake_frames = 0
        obj.pet_frame = 0
        obj._rng = random.Random()
        return obj

    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, "CARE CHAIN", fps=FPS, display_scale=2)
        pyxel.mouse(True)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.last_action = None
        self.timer = GAME_DURATION
        self.super_timer = 0
        self.stress = 0.0
        self.happiness = 50.0
        self.hunger = 50.0
        self.energy = 50.0
        self.particles.clear()
        self.floating_texts.clear()
        self.frame = 0
        self.shake_frames = 0
        self.pet_frame = 0

    # ------------------------------------------------------------------
    # Action detection
    # ------------------------------------------------------------------

    def _get_action_at(self, mx: int, my: int) -> ActionType | None:
        for i, action in enumerate(ACTIONS_ORDERED):
            x = BUTTON_XS[i]
            if x <= mx < x + BUTTON_W and BUTTON_Y <= my < BUTTON_Y + BUTTON_H:
                return action
        return None

    # ------------------------------------------------------------------
    # Combo bonus
    # ------------------------------------------------------------------

    def _combo_bonus(self) -> float:
        return 1.0 + self.combo * 0.25

    # ------------------------------------------------------------------
    # Do action
    # ------------------------------------------------------------------

    def _do_action(self, action: ActionType) -> None:
        h_eff, hu_eff, e_eff, s_eff = ACTION_EFFECTS[action]

        is_same = self.last_action is not None and action == self.last_action
        is_super = self.super_timer > 0

        if is_same or is_super or self.last_action is None:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            mult = self._combo_bonus()
            if is_super:
                mult *= SUPER_MULT

            old_happiness = self.happiness

            if is_super:
                self.happiness += h_eff * SUPER_MULT
                self.hunger += hu_eff * SUPER_MULT
                self.energy += e_eff * SUPER_MULT
                self.stress += 1.0
            else:
                self.happiness += h_eff
                self.hunger += hu_eff
                self.energy += e_eff
                self.stress += s_eff

            self._clamp_stats()
            happiness_gain = max(0.0, self.happiness - old_happiness)
            score_gained = int(happiness_gain * mult)
            self.score += score_gained

            if self.combo >= COMBO_THRESHOLD and self.combo % COMBO_THRESHOLD == 0:
                self.super_timer = SUPER_DURATION
                self._spawn_floating_text(WIDTH // 2, 60, "SUPER!", YELLOW)
                self._spawn_particles(WIDTH // 2, 55, YELLOW, 20)

            idx = ACTIONS_ORDERED.index(action)
            bx = BUTTON_XS[idx]
            self._spawn_floating_text(
                float(bx + BUTTON_W // 2), float(BUTTON_Y - 8),
                f"+{score_gained}", WHITE,
            )
            if self.combo > 1:
                self._spawn_floating_text(
                    float(bx + BUTTON_W // 2), float(BUTTON_Y - 22),
                    f"COMBO x{self.combo}", YELLOW,
                )

        else:
            self.combo = 1
            self.stress += 5.0

            old_happiness = self.happiness
            self.happiness += h_eff
            self.hunger += hu_eff
            self.energy += e_eff
            self.stress += s_eff
            self._clamp_stats()

            happiness_gain = max(0.0, self.happiness - old_happiness)
            score_gained = int(happiness_gain * self._combo_bonus())
            self.score += score_gained

            self.shake_frames = 8
            idx = ACTIONS_ORDERED.index(action)
            bx = BUTTON_XS[idx]
            self._spawn_floating_text(
                float(bx + BUTTON_W // 2), float(BUTTON_Y - 8),
                "RESET!", RED,
            )

        self.last_action = action

        idx = ACTIONS_ORDERED.index(action)
        self._spawn_particles(
            float(BUTTON_XS[idx] + BUTTON_W // 2),
            float(BUTTON_Y + BUTTON_H // 2),
            ACTION_COLORS[action], 8,
        )

    def _clamp_stats(self) -> None:
        self.happiness = max(STAT_MIN, min(STAT_MAX, self.happiness))
        self.hunger = max(STAT_MIN, min(STAT_MAX, self.hunger))
        self.energy = max(STAT_MIN, min(STAT_MAX, self.energy))
        self.stress = max(STAT_MIN, min(STRESS_CAP, self.stress))

    # ------------------------------------------------------------------
    # Stat update and CA spread
    # ------------------------------------------------------------------

    def _update_stats(self) -> None:
        self.happiness -= DECAY_HAPPINESS
        self.hunger -= DECAY_HUNGER
        self.energy -= DECAY_ENERGY
        self.stress += DECAY_STRESS
        self._clamp_stats()
        self._check_ca_spread()

    def _check_ca_spread(self) -> None:
        stats: list[float] = [self.happiness, self.hunger, self.energy, self.stress]
        for i, val in enumerate(stats):
            if val <= STAT_MIN or val >= STAT_MAX:
                bad = val <= STAT_MIN
                # Right neighbor
                if i < 3:
                    delta = -3.0 if bad else 3.0
                    stats[i + 1] += delta
                # Left neighbor
                if i > 0:
                    delta = -2.0 if bad else 2.0
                    stats[i - 1] += delta
                # 50% chance 2 steps away
                if i < 2 and self._rng.random() < 0.5:
                    delta = -1.0 if bad else 1.0
                    stats[i + 2] += delta
                if i > 1 and self._rng.random() < 0.5:
                    delta = -1.0 if bad else 1.0
                    stats[i - 2] += delta

        self.happiness, self.hunger, self.energy, self.stress = stats
        self._clamp_stats()

    # ------------------------------------------------------------------
    # Timer
    # ------------------------------------------------------------------

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score

    # ------------------------------------------------------------------
    # Particles
    # ------------------------------------------------------------------

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x, y=y,
                    vx=self._rng.uniform(-1.5, 1.5),
                    vy=self._rng.uniform(-3.0, -1.0),
                    life=self._rng.randint(15, 30),
                    color=color,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.1
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ------------------------------------------------------------------
    # Floating texts
    # ------------------------------------------------------------------

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=30, color=color)
        )

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self) -> None:
        if self.phase is Phase.TITLE:
            self._update_title()
            return
        if self.phase is Phase.PLAYING:
            self._update_playing()
            return
        if self.phase is Phase.GAME_OVER:
            self._update_game_over()
            return

    def _update_title(self) -> None:
        if (
            pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.KEY_RETURN)
            or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
        ):
            self.phase = Phase.PLAYING
            self.score = 0
            self.combo = 0
            self.max_combo = 0
            self.last_action = None
            self.timer = GAME_DURATION
            self.super_timer = 0
            self.stress = 0.0
            self.happiness = 50.0
            self.hunger = 50.0
            self.energy = 50.0
            self.particles.clear()
            self.floating_texts.clear()
            self.frame = 0
            self.shake_frames = 0
            self.pet_frame = 0

    def _update_playing(self) -> None:
        self.frame += 1
        self.pet_frame += 1

        if self.shake_frames > 0:
            self.shake_frames -= 1

        self._update_timer()
        if self.phase is Phase.GAME_OVER:
            return

        if self.super_timer > 0:
            self.super_timer -= 1

        if self.frame % STAT_DECAY_INTERVAL == 0:
            self._update_stats()

        self._update_particles()
        self._update_floating_texts()

        if self.stress >= STRESS_CAP:
            self.stress = STRESS_CAP
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
            return

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            action = self._get_action_at(pyxel.mouse_x, pyxel.mouse_y)
            if action is not None:
                self._do_action(action)

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.phase = Phase.TITLE
            self.reset()

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.shake_frames > 0:
            sx = self._rng.randint(-3, 3)
            sy = self._rng.randint(-3, 3)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        if self.phase is Phase.TITLE:
            self._draw_title()
        elif self.phase is Phase.PLAYING:
            self._draw_playing()
        elif self.phase is Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)
        cx = WIDTH // 2
        pyxel.text(cx - 36, 36, "CARE CHAIN", YELLOW)
        pyxel.text(cx - 54, 52, "Virtual Pet Care Game", WHITE)

        self._draw_pet_face(cx, 80, 20)

        pyxel.text(cx - 64, 116, "Click same-color actions", LIME)
        pyxel.text(cx - 60, 130, "to build COMBO chain!", CYAN)
        pyxel.text(cx - 54, 144, "COMBO x4 = SUPER MODE", YELLOW)
        pyxel.text(cx - 42, 158, "(rainbow!), 3x effect!", PINK)
        pyxel.text(cx - 64, 172, "Mismatch resets COMBO + stress", RED)
        pyxel.text(cx - 58, 186, "Balance all 4 stats!", GRAY)

        if self.best_score > 0:
            pyxel.text(cx - 40, 204, f"BEST: {self.best_score}", PINK)

        pyxel.text(cx - 52, 224, "SPACE to START", WHITE)

    def _draw_playing(self) -> None:
        # HUD
        secs = max(0, self.timer // FPS)
        tc = RED if secs <= 10 else WHITE
        pyxel.text(4, 2, f"TIME:{secs}", tc)
        pyxel.text(100, 2, f"SCORE:{self.score}", WHITE)
        pyxel.text(196, 2, f"COMBO:x{self.combo}", YELLOW)
        if self.super_timer > 0:
            s = self.super_timer / FPS
            pyxel.text(268, 2, f"S:{s:.1f}", PINK)

        # Pet face
        self._draw_pet_face(WIDTH // 2, 55, 22)

        # Action buttons
        for i, action in enumerate(ACTIONS_ORDERED):
            x = BUTTON_XS[i]
            y = BUTTON_Y
            color = ACTION_COLORS[action]
            label = ACTION_LABELS[action]

            pyxel.rect(x, y, BUTTON_W, BUTTON_H, color)
            pyxel.rectb(x, y, BUTTON_W, BUTTON_H, WHITE)

            if self.super_timer > 0:
                rc = RAINBOW[self.frame // 4 % 6]
                pyxel.rectb(x - 1, y - 1, BUTTON_W + 2, BUTTON_H + 2, rc)
            elif (
                x <= pyxel.mouse_x < x + BUTTON_W
                and y <= pyxel.mouse_y < y + BUTTON_H
            ):
                pyxel.rectb(x - 1, y - 1, BUTTON_W + 2, BUTTON_H + 2, WHITE)

            tw = len(label) * 4
            pyxel.text(x + (BUTTON_W - tw) // 2, y + BUTTON_H // 2 - 3, label, WHITE)

        # Stat bars
        stat_data: list[tuple[str, float, int]] = [
            ("HAPY", self.happiness, self._happy_color()),
            ("HNGR", self.hunger, self._hunger_color()),
            ("ENRG", self.energy, self._energy_color()),
            ("STRS", self.stress, self._stress_color()),
        ]
        for i, (label, value, color) in enumerate(stat_data):
            y = STAT_BAR_YS[i]
            pyxel.text(6, y + 3, label, WHITE)
            pyxel.rectb(STAT_BAR_X - 1, y - 1, STAT_BAR_W + 2, STAT_BAR_H + 2, WHITE)
            fill = int(STAT_BAR_W * value / STAT_MAX)
            pyxel.rect(STAT_BAR_X, y, STAT_BAR_W, STAT_BAR_H, NAVY)
            if fill > 0:
                pyxel.rect(STAT_BAR_X, y, fill, STAT_BAR_H, color)
            val_text = f"{int(value)}"
            tw = len(val_text) * 4
            pyxel.text(STAT_BAR_X + STAT_BAR_W // 2 - tw // 2, y + 3, val_text, WHITE)

        # Particles
        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), 2, p.color)

        # Floating texts
        for ft in self.floating_texts:
            x_pos = int(ft.x - len(ft.text) * 2)
            pyxel.text(x_pos, int(ft.y), ft.text, ft.color)

        # Mouse cursor
        pyxel.circ(pyxel.mouse_x, pyxel.mouse_y, 3, WHITE)
        pyxel.circb(pyxel.mouse_x, pyxel.mouse_y, 4, BLACK)

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)
        cx = WIDTH // 2

        if self.stress >= STRESS_CAP:
            pyxel.text(cx - 56, 60, "STRESS OVERLOAD!", RED)
        else:
            pyxel.text(cx - 48, 60, "TIME'S UP!", YELLOW)

        pyxel.text(cx - 40, 90, f"SCORE: {self.score}", WHITE)
        pyxel.text(cx - 48, 110, f"MAX COMBO: x{self.max_combo}", PINK)

        if self.best_score > 0 and self.score >= self.best_score:
            pyxel.text(cx - 46, 130, "NEW BEST!", YELLOW)
        pyxel.text(cx - 40, 150, f"BEST: {self.best_score}", WHITE)

        pyxel.text(cx - 48, 200, "R to RETRY", WHITE)

    # ------------------------------------------------------------------
    # Pet face drawing
    # ------------------------------------------------------------------

    def _draw_pet_face(self, cx: int, cy: int, size: int) -> None:
        is_super = self.super_timer > 0

        if is_super:
            head_color = RAINBOW[self.pet_frame // 6 % 6]
            head_size = size + 4
        else:
            head_color = WHITE
            head_size = size

        # Head outline
        pyxel.rect(
            cx - head_size, cy - head_size,
            head_size * 2, head_size * 2, head_color,
        )
        pyxel.rectb(
            cx - head_size - 1, cy - head_size - 1,
            head_size * 2 + 2, head_size * 2 + 2, WHITE,
        )

        # Ears
        pyxel.rect(cx - head_size, cy - head_size - 4, 6, 6, head_color)
        pyxel.rect(cx + head_size - 6, cy - head_size - 4, 6, 6, head_color)
        pyxel.rectb(cx - head_size, cy - head_size - 4, 6, 6, WHITE)
        pyxel.rectb(cx + head_size - 6, cy - head_size - 4, 6, 6, WHITE)

        if is_super:
            self._draw_star(cx - 6, cy - 4, 5, YELLOW)
            self._draw_star(cx + 6, cy - 4, 5, YELLOW)
            pyxel.circ(cx, cy + 3, 4, BLACK)
            pyxel.rect(cx - 4, cy + 3, 8, 2, head_color)
        else:
            if self.energy < 25:
                pyxel.rect(cx - 7, cy - 5, 5, 2, BLACK)
                pyxel.rect(cx + 2, cy - 5, 5, 2, BLACK)
            else:
                pyxel.rect(cx - 7, cy - 5, 4, 4, BLACK)
                pyxel.rect(cx + 3, cy - 5, 4, 4, BLACK)

            if self.hunger < 25:
                pyxel.rect(cx - 4, cy + 3, 8, 6, BLACK)
            elif self.happiness > 70:
                pyxel.circ(cx, cy + 3, 4, BLACK)
                pyxel.rect(cx - 4, cy + 3, 8, 2, head_color)
            else:
                pyxel.rect(cx - 3, cy + 4, 6, 2, BLACK)

            if self.stress > 60:
                pyxel.tri(cx - head_size - 3, cy + 1, cx - head_size - 5, cy - 3, cx - head_size - 1, cy - 3, CYAN)

    def _draw_star(self, cx: int, cy: int, size: int, color: int) -> None:
        pyxel.line(cx, cy - size, cx, cy + size, color)
        pyxel.line(cx - size, cy, cx + size, cy, color)
        h = size // 2
        pyxel.line(cx - h, cy - h, cx + h, cy + h, color)
        pyxel.line(cx + h, cy - h, cx - h, cy + h, color)

    # ------------------------------------------------------------------
    # Stat color helpers
    # ------------------------------------------------------------------

    def _happy_color(self) -> int:
        if self.happiness > 50:
            return YELLOW
        if self.happiness > 25:
            return ORANGE
        return RED

    def _hunger_color(self) -> int:
        if self.hunger > 50:
            return GREEN
        if self.hunger > 25:
            return YELLOW
        return RED

    def _energy_color(self) -> int:
        if self.energy > 50:
            return CYAN
        if self.energy > 25:
            return LIME
        return ORANGE

    def _stress_color(self) -> int:
        if self.stress < 30:
            return GREEN
        if self.stress < 60:
            return ORANGE
        return RED


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    Game()
