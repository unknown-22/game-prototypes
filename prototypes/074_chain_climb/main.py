"""CHAIN CLIMB — Color-match vertical climbing game.

Core fun moment: chasing same-color platforms to build COMBO,
triggering SYNTHESIS super jump with 3x score burst and visual flash.
Risk/reward: same-color platforms build COMBO but may be far away;
nearby wrong-color platforms are safe but reset COMBO.
Falling off screen bottom = GAME OVER.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 30

PLAYER_W = 12
PLAYER_H = 16
PLAYER_DX = 2.0

PLATFORM_W = 40
PLATFORM_H = 8

GRAVITY = 0.18
JUMP_VELOCITY = -4.5
SYNTHESIS_JUMP_VELOCITY = -7.0
MAX_FALL_SPEED = 8.0

INITIAL_SCROLL_SPEED = 0.8
SPEED_INCREASE = 0.02
MAX_SCROLL_SPEED = 2.5
SPEED_SCORE_STEP = 100

BASE_SCORE = 10
COMBO_BONUS = 15
SYNTHESIS_MULTIPLIER = 3
COMBO_THRESHOLD = 3

SYNTHESIS_FRAMES = 60
SYNTHESIS_FLASH_INTERVAL = 8

PLATFORM_SPAWN_MIN = 30
PLATFORM_SPAWN_MAX = 50
PLATFORM_SPAWN_X_RANGE = 80
MIN_VISIBLE_PLATFORMS = 5
MAX_VISIBLE_PLATFORMS = 8

PARTICLE_COUNT_NORMAL = 6
PARTICLE_COUNT_SYNTHESIS = 12
PARTICLE_LIFE_MIN = 15
PARTICLE_LIFE_MAX = 25
PARTICLE_GRAVITY = 0.08

# ── Color Constants ────────────────────────────────────────────────────
COLOR_BLACK = 0
COLOR_NAVY = 1
COLOR_PURPLE = 2
COLOR_GREEN = 3
COLOR_BROWN = 4
COLOR_DARK_BLUE = 5
COLOR_LIGHT_BLUE = 6
COLOR_WHITE = 7
COLOR_RED = 8
COLOR_ORANGE = 9
COLOR_YELLOW = 10
COLOR_LIME = 11
COLOR_CYAN = 12
COLOR_GRAY = 13
COLOR_PINK = 14
COLOR_PEACH = 15

# ── Enums ──────────────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class PlatformColor(Enum):
    RED = auto()
    GREEN = auto()
    DARK_BLUE = auto()
    YELLOW = auto()


PLATFORM_COLORS: list[PlatformColor] = [
    PlatformColor.RED,
    PlatformColor.GREEN,
    PlatformColor.DARK_BLUE,
    PlatformColor.YELLOW,
]

COLOR_INT_MAP: dict[PlatformColor, int] = {
    PlatformColor.RED: COLOR_RED,
    PlatformColor.GREEN: COLOR_GREEN,
    PlatformColor.DARK_BLUE: COLOR_DARK_BLUE,
    PlatformColor.YELLOW: COLOR_YELLOW,
}

# ── Data Classes ───────────────────────────────────────────────────────


@dataclass
class Platform:
    x: float
    y: float
    width: float
    height: float
    color: PlatformColor


@dataclass
class Player:
    x: float
    y: float
    vy: float
    width: int
    height: int
    on_ground: bool


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ── Game Class ─────────────────────────────────────────────────────────


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHAIN CLIMB", display_scale=DISPLAY_SCALE, fps=FPS)
        pyxel.mouse(False)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player: Player = Player(
            x=float(SCREEN_W / 2),
            y=float(SCREEN_H - PLAYER_H - 20),
            vy=0.0,
            width=PLAYER_W,
            height=PLAYER_H,
            on_ground=False,
        )
        self.platforms: list[Platform] = []
        self.particles: list[Particle] = []
        self.score: int = 0
        self.high_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.prev_color: PlatformColor | None = None
        self.synthesis_timer: int = 0
        self.camera_y: float = 0.0
        self.scroll_speed: float = INITIAL_SCROLL_SPEED
        self._platform_spawn_y: float = 0.0
        self._frame: int = 0

    def _start_game(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.prev_color = None
        self.synthesis_timer = 0
        self.camera_y = 0.0
        self.scroll_speed = INITIAL_SCROLL_SPEED
        self._frame = 0
        self.platforms.clear()
        self.particles.clear()
        self._init_platforms()
        self.player.x = float(SCREEN_W / 2)
        self.player.y = float(SCREEN_H - PLAYER_H - 20)
        self.player.vy = 0.0
        self.player.on_ground = False
        self.phase = Phase.PLAYING

    def _init_platforms(self) -> None:
        y: float = 20.0
        for _ in range(8):
            color = self._rng.choice(PLATFORM_COLORS)
            x = self._rng.uniform(PLATFORM_W / 2, SCREEN_W - PLATFORM_W / 2)
            self.platforms.append(Platform(
                x=float(x),
                y=y,
                width=float(PLATFORM_W),
                height=float(PLATFORM_H),
                color=color,
            ))
            y += self._rng.uniform(PLATFORM_SPAWN_MIN, PLATFORM_SPAWN_MAX)
        self._platform_spawn_y = y

    # ── Pure Logic (Testable) ──────────────────────────────────────

    @staticmethod
    def _compute_score(combo: int) -> int:
        return BASE_SCORE + combo * COMBO_BONUS

    def _apply_gravity(self) -> None:
        self.player.vy += GRAVITY
        if self.player.vy > MAX_FALL_SPEED:
            self.player.vy = MAX_FALL_SPEED
        self.player.y += self.player.vy

    def _move_player(self, dx: float) -> None:
        self.player.x += dx
        if self.player.x > SCREEN_W:
            self.player.x -= SCREEN_W
        elif self.player.x < 0:
            self.player.x += SCREEN_W
        self._apply_gravity()

    def _check_platform_collision(self) -> tuple[bool, PlatformColor | None]:
        if self.player.vy < 0:
            self.player.on_ground = False
            return False, None

        px = self.player.x
        py = self.player.y
        ph = float(self.player.height)
        pw = float(self.player.width)

        player_left = px - pw / 2
        player_right = px + pw / 2
        player_bottom = py + ph

        for plat in self.platforms:
            plat_left = plat.x - plat.width / 2
            plat_right = plat.x + plat.width / 2
            plat_top = plat.y
            plat_bottom = plat.y + plat.height

            if (player_right > plat_left and player_left < plat_right
                    and player_bottom >= plat_top
                    and player_bottom <= plat_top + plat.height + abs(self.player.vy) + 2
                    and py < plat_bottom):
                self.player.y = plat_top - ph
                self.player.vy = JUMP_VELOCITY
                self.player.on_ground = True
                return True, plat.color

        self.player.on_ground = False
        return False, None

    def _handle_landing(self, color: PlatformColor) -> None:
        is_synthesis = self.synthesis_timer > 0

        if is_synthesis:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = self._compute_score(self.combo) * SYNTHESIS_MULTIPLIER
            self.score += points
            self.player.vy = SYNTHESIS_JUMP_VELOCITY
            self._spawn_landing_particles(self.player.x, self.player.y, color, PARTICLE_COUNT_SYNTHESIS)
            return

        if self.prev_color is None or self.prev_color != color:
            self.combo = 1
            self.prev_color = color
            self.score += BASE_SCORE
        else:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self.score += self._compute_score(self.combo)

        if self.combo >= COMBO_THRESHOLD and self.synthesis_timer == 0:
            self.synthesis_timer = SYNTHESIS_FRAMES
            self.player.vy = SYNTHESIS_JUMP_VELOCITY

        count = PARTICLE_COUNT_SYNTHESIS if self.synthesis_timer > 0 else PARTICLE_COUNT_NORMAL
        self._spawn_landing_particles(self.player.x, self.player.y, color, count)

    def _update_camera(self) -> None:
        self.camera_y += self.scroll_speed

    def _spawn_platforms(self) -> None:
        self.platforms = [
            p for p in self.platforms
            if p.y - self.camera_y > -PLATFORM_H - 50
        ]

        buffer_bottom = self.camera_y + SCREEN_H + 100
        in_zone = sum(1 for p in self.platforms if p.y <= buffer_bottom)

        while in_zone < MAX_VISIBLE_PLATFORMS:
            color = self._rng.choice(PLATFORM_COLORS)
            x = self._rng.uniform(PLATFORM_W / 2, SCREEN_W - PLATFORM_W / 2)
            self.platforms.append(Platform(
                x=float(x),
                y=self._platform_spawn_y,
                width=float(PLATFORM_W),
                height=float(PLATFORM_H),
                color=color,
            ))
            gap = self._rng.uniform(PLATFORM_SPAWN_MIN, PLATFORM_SPAWN_MAX)
            self._platform_spawn_y += gap
            in_zone += 1

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += PARTICLE_GRAVITY
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _spawn_landing_particles(self, x: float, y: float, color: PlatformColor, count: int) -> None:
        color_int = COLOR_INT_MAP[color]
        for _ in range(count):
            self.particles.append(Particle(
                x=float(x),
                y=float(y),
                vx=(self._rng.random() * 3.0 - 1.5),
                vy=(self._rng.random() * -2.5 - 0.5),
                life=self._rng.randint(PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX),
                color=color_int,
            ))

    def _check_fall_death(self) -> bool:
        player_screen_y = self.player.y - self.camera_y
        return player_screen_y > SCREEN_H + PLAYER_H * 2

    def _update_scroll_speed(self) -> None:
        steps = self.score // SPEED_SCORE_STEP
        self.scroll_speed = min(INITIAL_SCROLL_SPEED + steps * SPEED_INCREASE, MAX_SCROLL_SPEED)

    def _update_synthesis_timer(self) -> None:
        if self.synthesis_timer > 0:
            self.synthesis_timer -= 1
            if self.synthesis_timer == 0:
                self.prev_color = None

    # ── Update ─────────────────────────────────────────────────────

    def update(self) -> None:
        self._frame += 1

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self._start_game()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.TITLE
                self.reset()
            return

        # PLAYING
        dx: float = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -PLAYER_DX
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = PLAYER_DX

        self._move_player(dx)
        landed, color = self._check_platform_collision()
        if landed and color is not None:
            self._handle_landing(color)

        self._update_camera()
        self._spawn_platforms()

        if self._check_fall_death():
            if self.score > self.high_score:
                self.high_score = self.score
            self.phase = Phase.GAME_OVER

        self._update_scroll_speed()
        self._update_particles()
        self._update_synthesis_timer()

    # ── Draw ────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(COLOR_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        # Platforms
        for plat in self.platforms:
            sx = int(plat.x - plat.width / 2)
            sy = int(plat.y - self.camera_y)
            if sy < -PLATFORM_H or sy > SCREEN_H:
                continue
            color_int = COLOR_INT_MAP[plat.color]
            pyxel.rect(sx, sy, int(plat.width), int(plat.height), color_int)
            pyxel.rectb(sx, sy, int(plat.width), int(plat.height), COLOR_WHITE)
            if self.synthesis_timer > 0:
                glow_x = sx - 1
                glow_y = sy - 1
                glow_w = int(plat.width) + 2
                glow_h = int(plat.height) + 2
                if (self._frame // SYNTHESIS_FLASH_INTERVAL) % 2 == 0:
                    pyxel.rectb(glow_x, glow_y, glow_w, glow_h, COLOR_CYAN)

        # Player
        psx = int(self.player.x - self.player.width / 2)
        psy = int(self.player.y - self.camera_y)
        player_color = COLOR_YELLOW if self.synthesis_timer > 0 else COLOR_RED
        pyxel.rect(psx, psy, self.player.width, self.player.height, player_color)
        pyxel.rectb(psx, psy, self.player.width, self.player.height, COLOR_WHITE)

        # Particles
        for p in self.particles:
            screen_y = int(p.y - self.camera_y)
            if 0 <= screen_y <= SCREEN_H:
                pyxel.pset(int(p.x), screen_y, p.color)

        # SYNTHESIS overlay
        if self.synthesis_timer > 0 and (self._frame // 4) % 2 == 0:
            for y in range(0, SCREEN_H, 2):
                for x in range(0, SCREEN_W, 2):
                    if (x // 2 + y // 2) % 2 == 0:
                        pyxel.pset(x, y, COLOR_CYAN)

        # HUD
        self._draw_hud()

    def _draw_title(self) -> None:
        title = "CHAIN  CLIMB"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 60, title, COLOR_WHITE)

        instructions = [
            "ARROWS / A,D :  Move",
            "Land on SAME color = COMBO!",
            "COMBO x3 = SYNTHESIS!",
            "Super jump + 3x score",
            "",
            "Fall off screen = GAME OVER",
            "",
            "SPACE or ENTER to Start",
        ]
        y_off = 95
        for line in instructions:
            lw = len(line) * 4
            pyxel.text(SCREEN_W // 2 - lw // 2, y_off, line, COLOR_GRAY)
            y_off += 12

        color_labels = ["RED", "GREEN", "BLUE", "YELLOW"]
        color_ints = [COLOR_RED, COLOR_GREEN, COLOR_DARK_BLUE, COLOR_YELLOW]
        for i in range(4):
            bx = SCREEN_W // 2 - 42 + i * 22
            by = y_off + 5
            pyxel.rect(bx, by, 16, 8, color_ints[i])
            pyxel.rectb(bx, by, 16, 8, COLOR_WHITE)
            label = color_labels[i]
            lw = len(label) * 4
            pyxel.text(bx + 8 - lw // 2, by + 12, label, COLOR_WHITE)

    def _draw_game_over(self) -> None:
        go_text = "GAME OVER"
        tw = len(go_text) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 50, go_text, COLOR_RED)

        lines = [
            f"SCORE: {self.score}",
            f"HIGH SCORE: {self.high_score}",
            f"MAX COMBO: {self.max_combo}",
            "",
            "SPACE or ENTER to Retry",
        ]
        y_off = 90
        for line in lines:
            lw = len(line) * 4
            color = COLOR_ORANGE if "COMBO" in line else COLOR_WHITE
            pyxel.text(SCREEN_W // 2 - lw // 2, y_off, line, color)
            y_off += 14

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 20, COLOR_BLACK)

        score_text = f"SCORE: {self.score}"
        pyxel.text(4, 2, score_text, COLOR_WHITE)

        if self.combo > 0:
            combo_text = f"COMBO: {self.combo}"
            combo_color = COLOR_WHITE
            if self.combo >= COMBO_THRESHOLD:
                combo_color = COLOR_ORANGE
            if self.synthesis_timer > 0:
                combo_color = COLOR_YELLOW
            pyxel.text(100, 2, combo_text, combo_color)

        speed_text = f"SPD: {self.scroll_speed:.1f}"
        pyxel.text(200, 2, speed_text, COLOR_GRAY)

        if self.synthesis_timer > 0:
            synth_text = "SYNTHESIS!"
            lw = len(synth_text) * 4
            flash = (self._frame // SYNTHESIS_FLASH_INTERVAL) % 2 == 0
            if flash:
                pyxel.text(SCREEN_W // 2 - lw // 2, 2, synth_text, COLOR_CYAN)

            bar_w = 80
            bar_x = SCREEN_W - bar_w - 4
            bar_fill = int(bar_w * self.synthesis_timer / SYNTHESIS_FRAMES)
            pyxel.rect(bar_x, 14, bar_w, 4, COLOR_DARK_BLUE)
            pyxel.rect(bar_x, 14, bar_fill, 4, COLOR_YELLOW)


# ── Entry Point ────────────────────────────────────────────────────────


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
