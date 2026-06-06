from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Constants ---
SCREEN_W = 320
SCREEN_H = 240
ROPE_Y = 160
CHAR_W = 8
CHAR_H = 16
BALANCE_RANGE = 60
MAX_HEAT = 100
SUPER_COMBO_THRESHOLD = 4
SUPER_DURATION = 300  # frames (5s at 60fps)
SPEED_INITIAL = 0.8
SPEED_MAX = 2.0
SPEED_INCREMENT = 0.0001
GEM_SPAWN_MIN = 40
GEM_SPAWN_MAX = 60
GEM_SPAWN_DIST = 320
GEM_SPAWN_DIST_RANGE = 80
WIND_INTERVAL_MIN = 120
WIND_INTERVAL_MAX = 200
WIND_DURATION_MIN = 30
WIND_DURATION_MAX = 60
WIND_STRENGTH_MIN = 0.01
WIND_STRENGTH_MAX = 0.03
BALANCE_DRIFT = 0.005
BALANCE_INPUT = 0.03
HEAT_DECAY = 0.3
HEAT_PER_MISS = 15
NUM_GEM_COLORS = 4

# Color constants
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

GEM_COLORS: list[int] = [GREEN, DARK_BLUE, ORANGE, YELLOW]


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Gem:
    x: float  # world x position (scrolls left as player walks)
    y: int  # y on rope (160, or +/- offset for variety)
    color_index: int  # 0-3 maps to gem_colors
    collected: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    gravity: float = 0.0
    size: int = 2


@dataclass
class WindGust:
    direction: int  # -1 (left) or 1 (right)
    strength: float
    duration: int  # frames remaining
    color: int


@dataclass
class Star:
    x: int
    y: int
    brightness: int = 0  # 0-2


class Game:
    """TIGHTROPE SURGE — Color-match tightrope walking game."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, "TIGHTROPE SURGE", display_scale=2)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0  # 0-100
        self.balance: float = 0.0  # -1.0 to 1.0
        self.distance: float = 0.0
        self.speed: float = SPEED_INITIAL
        self.super_timer: int = 0
        self.gems: list[Gem] = []
        self.particles: list[Particle] = []
        self.winds: list[WindGust] = []
        self.player_color_index: int = 0  # current target color (last collected, or 0)
        self.player_y_offset: float = 0.0
        self.shake_frames: int = 0
        self.shake_intensity: int = 0
        self.wind_timer: int = self._rng.randint(WIND_INTERVAL_MIN, WIND_INTERVAL_MAX)
        self.last_gem_x: float = 0.0
        self.frame: int = 0
        self.game_over_flash: int = 0

        # Starfield
        self.stars: list[Star] = [
            Star(self._rng.randint(0, SCREEN_W), self._rng.randint(0, ROPE_Y - 20))
            for _ in range(40)
        ]

        # Title particle effect
        self.title_particles: list[Particle] = []

    # --- Gem Spawning ---
    def _spawn_gems(self) -> None:
        while self.last_gem_x < self.distance + GEM_SPAWN_DIST + GEM_SPAWN_DIST_RANGE:
            self.last_gem_x += self._rng.randint(GEM_SPAWN_MIN, GEM_SPAWN_MAX)
            color_index = self._rng.randint(0, NUM_GEM_COLORS - 1)
            y_offset = self._rng.choice([-4, -2, 0, 0, 0, 2, 4])
            self.gems.append(
                Gem(x=self.last_gem_x + GEM_SPAWN_DIST, y=ROPE_Y + y_offset, color_index=color_index)
            )

    # --- Gem Collection ---
    def _collect_gem(self, gem: Gem) -> None:
        gem.collected = True
        multiplier = 3 if self.super_timer > 0 else 1

        if gem.color_index == self.player_color_index:
            # Same color: combo up
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = (10 + self.combo * 5) * multiplier
            self.score += points
            self._spawn_particles(
                self._player_screen_x(),
                ROPE_Y + int(self.player_y_offset) - CHAR_H // 2,
                GEM_COLORS[gem.color_index],
                6 + min(self.combo, 4),
            )
            # Activate SUPER if combo threshold reached
            if self.combo >= SUPER_COMBO_THRESHOLD and self.super_timer == 0:
                self._activate_super()
        else:
            # Wrong color: reset combo, add heat
            self.combo = 0
            self.heat += HEAT_PER_MISS
            if self.heat > MAX_HEAT:
                self.heat = MAX_HEAT
            self._spawn_particles(
                self._player_screen_x(),
                ROPE_Y + int(self.player_y_offset) - CHAR_H // 2,
                RED,
                10,
            )
            self.shake_frames = 8
            self.shake_intensity = 3

        self.player_color_index = gem.color_index

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION

    def _deactivate_super(self) -> None:
        self.super_timer = 0

    # --- Gem Update ---
    def _update_gems(self) -> None:
        # Scroll gems and check for collection
        player_x = self._player_screen_x()
        remaining: list[Gem] = []
        for gem in self.gems:
            screen_x = gem.x - self.distance
            if screen_x < -20:
                # Gem passed behind player — only counts as miss if uncollected
                if not gem.collected:
                    # Missed gem — no combo change, no heat
                    pass
                continue
            if gem.collected:
                continue
            # Check if player stepped on it
            if (
                not gem.collected
                and abs(screen_x - player_x) < 9
                and abs(gem.y - (ROPE_Y + int(self.player_y_offset) - CHAR_H // 2)) < 10
            ):
                self._collect_gem(gem)
            remaining.append(gem)
        self.gems = remaining

    # --- Wind System ---
    def _update_winds(self) -> None:
        self.wind_timer -= 1
        if self.wind_timer <= 0:
            self.wind_timer = self._rng.randint(WIND_INTERVAL_MIN, WIND_INTERVAL_MAX)
            direction = self._rng.choice([-1, 1])
            strength = self._rng.uniform(WIND_STRENGTH_MIN, WIND_STRENGTH_MAX)
            duration = self._rng.randint(WIND_DURATION_MIN, WIND_DURATION_MAX)
            color = RED if direction == -1 else CYAN if direction == 1 else WHITE
            self.winds.append(WindGust(direction=direction, strength=strength, duration=duration, color=color))

        active_winds: list[WindGust] = []
        for wind in self.winds:
            wind.duration -= 1
            if self.super_timer > 0:
                # Wind immunity during SUPER
                if wind.duration > 0:
                    active_winds.append(wind)
                continue
            if wind.duration > 0:
                self.balance += wind.direction * wind.strength
                active_winds.append(wind)
        self.winds = active_winds

    # --- Balance ---
    def _update_balance(self, left_held: bool, right_held: bool) -> None:
        if left_held:
            self.balance -= BALANCE_INPUT
        if right_held:
            self.balance += BALANCE_INPUT
        # Natural drift toward center
        if not left_held and not right_held:
            if self.balance > 0:
                self.balance = max(0.0, self.balance - BALANCE_DRIFT)
            elif self.balance < 0:
                self.balance = min(0.0, self.balance + BALANCE_DRIFT)
        self.balance = max(-1.0, min(1.0, self.balance))

    # --- Heat ---
    def _update_heat(self) -> None:
        # Check game over BEFORE decay (otherwise 100 → 99.7 never triggers)
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            self.game_over_flash = 30
            self._spawn_particles(
                self._player_screen_x(),
                ROPE_Y + int(self.player_y_offset) - CHAR_H // 2,
                RED,
                25,
            )
            return
        # Decay heat over time
        if self.heat > 0 and self.super_timer == 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    # --- Speed ---
    def _update_speed(self) -> None:
        self.speed = min(SPEED_MAX, SPEED_INITIAL + self.frame * SPEED_INCREMENT)

    # --- Particles ---
    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2, 2)
            vy = self._rng.uniform(-4, -1)
            life = self._rng.randint(12, 25)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color)
            )

    def _spawn_super_trail(self, x: float, y: float) -> None:
        color = [CYAN, YELLOW, LIME, PINK, ORANGE][self.frame // 4 % 5]
        self.particles.append(
            Particle(
                x=x + self._rng.uniform(-3, 3),
                y=y,
                vx=-self.speed * 0.3,
                vy=self._rng.uniform(-1, 1),
                life=10,
                color=color,
                size=1,
            )
        )

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += p.gravity
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    # --- Core World Update ---
    def _update_world(self, left_held: bool, right_held: bool) -> None:
        self.frame += 1
        self.distance += self.speed
        self.player_y_offset = math.sin(self.frame * 0.15) * 2

        self._spawn_gems()
        self._update_gems()
        self._update_winds()
        self._update_balance(left_held, right_held)
        self._update_heat()
        self._update_speed()
        self._update_particles()

        # SUPER timer
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self._deactivate_super()

        # SUPER trail particles
        if self.super_timer > 0 and self.frame % 3 == 0:
            self._spawn_super_trail(
                self._player_screen_x(),
                ROPE_Y + int(self.player_y_offset) - CHAR_H // 2,
            )

        # Screen shake decay
        if self.shake_frames > 0:
            self.shake_frames -= 1

    def _should_game_over(self) -> bool:
        return self.heat >= MAX_HEAT

    # --- Player Screen Position ---
    def _player_screen_x(self) -> float:
        return SCREEN_W // 2 - self.balance * BALANCE_RANGE

    # --- Update (Pyxel callback) ---
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            # Animate title particles
            if self.frame % 8 == 0:
                self.title_particles.append(
                    Particle(
                        x=self._rng.randint(0, SCREEN_W),
                        y=ROPE_Y,
                        vx=0,
                        vy=self._rng.uniform(-1.5, -0.5),
                        life=self._rng.randint(20, 40),
                        color=self._rng.choice([GREEN, DARK_BLUE, ORANGE, YELLOW]),
                        size=1,
                    )
                )
            alive: list[Particle] = []
            for p in self.title_particles:
                p.y += p.vy
                p.life -= 1
                if p.life > 0:
                    alive.append(p)
            self.title_particles = alive

            self.frame += 1
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.GAME_OVER:
            if self.game_over_flash > 0:
                self.game_over_flash -= 1
            # Particles still update
            self._update_particles()
            if pyxel.btnp(pyxel.KEY_RETURN) and self.game_over_flash <= 0:
                self.reset()
                self.phase = Phase.TITLE
            return

        if self.phase == Phase.PLAYING:
            if self._should_game_over():
                self.phase = Phase.GAME_OVER
                self.game_over_flash = 30
                # Spawn game over particles
                for _ in range(30):
                    px = self._player_screen_x()
                    py = ROPE_Y + int(self.player_y_offset) - CHAR_H // 2
                    self.particles.append(
                        Particle(
                            x=px + self._rng.uniform(-10, 10),
                            y=py + self._rng.uniform(-5, 5),
                            vx=self._rng.uniform(-3, 3),
                            vy=self._rng.uniform(-5, -2),
                            life=self._rng.randint(30, 60),
                            color=self._rng.choice([RED, ORANGE, YELLOW]),
                            gravity=0.15,
                        )
                    )
                return

            left_held = pyxel.btn(pyxel.KEY_LEFT)
            right_held = pyxel.btn(pyxel.KEY_RIGHT)
            self._update_world(left_held, right_held)

    # --- Drawing ---
    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_starfield(self) -> None:
        for star in self.stars:
            twinkle = (self.frame // 30 + star.x) % 3
            if twinkle == 0:
                pyxel.pset(star.x, star.y, WHITE)
            elif twinkle == 1:
                pyxel.pset(star.x, star.y, PURPLE)

    def _draw_title(self) -> None:
        self._draw_starfield()

        # Title text
        title = "TIGHTROPE SURGE"
        tx = SCREEN_W // 2 - len(title) * 2
        pyxel.text(tx, 60, title, WHITE)

        # Subtitle / instructions
        instructions = [
            "Balance on the high-wire!",
            "",
            "LEFT / RIGHT : Balance",
            "Step on same-color gems",
            "to build COMBO chain!",
            "COMBO x4 = SUPER MODE",
            "Wrong color = HEAT up",
            "HEAT 100% = YOU FALL",
            "",
            "Press ENTER to start",
        ]
        for i, line in enumerate(instructions):
            color = WHITE
            if "ENTER" in line:
                color = YELLOW if (self.frame // 15) % 2 else WHITE
            pyxel.text(SCREEN_W // 2 - len(line) * 2, 100 + i * 10, line, color)

        # Rope line
        pyxel.line(0, ROPE_Y, SCREEN_W, ROPE_Y, WHITE)

        # Animated title particles rising from rope
        for p in self.title_particles:
            alpha = min(p.life, 15)
            if alpha > 0:
                pyxel.pset(int(p.x), int(p.y), p.color)

        # Small character silhouette on rope center
        cx = SCREEN_W // 2
        cy = ROPE_Y - CHAR_H + 4
        pyxel.rect(cx - CHAR_W // 2, cy, CHAR_W, CHAR_H, RED)
        pyxel.tri(
            cx - CHAR_W // 2 - 2, cy,
            cx + CHAR_W // 2 + 2, cy,
            cx, cy - 6,
            ORANGE if (self.frame // 20) % 2 else YELLOW,
        )

    def _draw_game(self) -> None:
        # Apply screen shake
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self._rng.randint(-self.shake_intensity, self.shake_intensity)
            shake_y = self._rng.randint(-self.shake_intensity, self.shake_intensity)
        pyxel.camera(shake_x, shake_y)

        self._draw_starfield()

        # Rope
        pyxel.line(0, ROPE_Y, SCREEN_W, ROPE_Y, WHITE)
        # Rope shadow/glow
        pyxel.line(0, ROPE_Y + 1, SCREEN_W, ROPE_Y + 1, DARK_BLUE)

        # Draw rope energy flow (moving light particles along rope)
        for i in range(6):
            flow_x = (self.frame * 2 + i * 50) % SCREEN_W
            color_idx = (self.frame // 20 + i) % NUM_GEM_COLORS
            pyxel.pset(flow_x, ROPE_Y, GEM_COLORS[color_idx])

        # Draw gems
        for gem in self.gems:
            if gem.collected:
                continue
            sx = int(gem.x - self.distance)
            if -10 <= sx <= SCREEN_W + 10:
                color = GEM_COLORS[gem.color_index]
                # Diamond shape
                pyxel.tri(sx, gem.y - 4, sx - 4, gem.y, sx, gem.y + 4, color)
                pyxel.tri(sx, gem.y - 4, sx + 4, gem.y, sx, gem.y + 4, color)

        # Draw particles
        for p in self.particles:
            alpha = min(p.life * 2, 13)
            if alpha > 0:
                pyxel.pset(int(p.x), int(p.y), p.color)

        # Wind indicators
        for wind in self.winds:
            if wind.duration > 0:
                arrow_x = SCREEN_W - 40 if wind.direction > 0 else 40
                arrow_y = 20
                if wind.direction > 0:
                    pyxel.tri(arrow_x - 8, arrow_y, arrow_x, arrow_y + 6, arrow_x, arrow_y - 6, wind.color)
                else:
                    pyxel.tri(arrow_x + 8, arrow_y, arrow_x, arrow_y + 6, arrow_x, arrow_y - 6, wind.color)

        # Draw character
        char_x = int(self._player_screen_x())
        char_y = ROPE_Y + int(self.player_y_offset) - CHAR_H + 4
        # Body
        body_color = CYAN if self.super_timer > 0 else RED
        pyxel.rect(char_x - CHAR_W // 2, char_y, CHAR_W, CHAR_H, body_color)
        # Hat (triangle)
        hat_color = YELLOW if self.super_timer > 0 else ORANGE
        pyxel.tri(
            char_x - CHAR_W // 2 - 1, char_y,
            char_x + CHAR_W // 2 + 1, char_y,
            char_x, char_y - 6,
            hat_color,
        )
        # SUPER glow ring
        if self.super_timer > 0:
            glow_radius = 10 + int(math.sin(self.frame * 0.3) * 2)
            pyxel.circb(char_x, char_y + CHAR_H // 2, glow_radius, CYAN)

        # Balance meter (top)
        bar_x = SCREEN_W // 2 - 50
        bar_y = 8
        bar_w = 100
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_w = int(abs(self.balance) * 50)
        if fill_w > 0:
            if abs(self.balance) < 0.33:
                fill_color = GREEN
            elif abs(self.balance) < 0.66:
                fill_color = YELLOW
            else:
                fill_color = RED
            if self.balance < 0:
                pyxel.rect(bar_x + 50 - fill_w, bar_y, fill_w, bar_h, fill_color)
            else:
                pyxel.rect(bar_x + 50, bar_y, fill_w, bar_h, fill_color)
        # Center marker
        pyxel.line(bar_x + 50, bar_y - 2, bar_x + 50, bar_y + bar_h + 2, WHITE)

        # HEAT meter (right side)
        heat_x = 310
        heat_y_top = 20
        heat_h = 200
        pyxel.rect(heat_x, heat_y_top, 6, heat_h, GRAY)
        heat_fill = int(self.heat / MAX_HEAT * heat_h)
        if heat_fill > 0:
            heat_color = GREEN if self.heat < 50 else ORANGE if self.heat < 80 else RED
            pyxel.rect(heat_x, heat_y_top + heat_h - heat_fill, 6, heat_fill, heat_color)
        pyxel.text(heat_x - 10, heat_y_top + heat_h + 4, "HEAT", WHITE)

        # Score (top-left)
        pyxel.text(4, 4, f"SCORE:{self.score:06d}", YELLOW)

        # COMBO (center-top)
        combo_text = f"COMBO x{self.combo}"
        combo_color = WHITE
        if self.combo >= SUPER_COMBO_THRESHOLD:
            combo_color = PINK
        elif self.combo >= 2:
            combo_color = YELLOW
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 16, combo_text, combo_color)

        # SUPER timer
        if self.super_timer > 0:
            super_text = f"SUPER {self.super_timer // 60 + 1}s"
            pyxel.text(SCREEN_W // 2 - len(super_text) * 2, 26, super_text, CYAN if self.frame % 10 < 5 else YELLOW)

        # Distance
        dist_text = f"DIST:{int(self.distance // 10)}m"
        pyxel.text(4, 14, dist_text, CYAN)

        pyxel.camera(0, 0)

    def _draw_game_over(self) -> None:
        self._draw_starfield()

        # Background darken
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)

        # Falling particles
        for p in self.particles:
            alpha = min(p.life, 15)
            if alpha > 0:
                pyxel.pset(int(p.x), int(p.y), p.color)

        if self.game_over_flash % 4 < 2:
            pyxel.text(SCREEN_W // 2 - len("GAME OVER") * 2, 60, "GAME OVER", RED)

        pyxel.text(SCREEN_W // 2 - len(f"Score: {self.score}") * 2, 90, f"Score: {self.score}", WHITE)
        pyxel.text(
            SCREEN_W // 2 - len(f"Max Combo: {self.max_combo}") * 2,
            110,
            f"Max Combo: {self.max_combo}",
            YELLOW,
        )
        pyxel.text(
            SCREEN_W // 2 - len(f"Distance: {int(self.distance // 10)}m") * 2,
            130,
            f"Distance: {int(self.distance // 10)}m",
            CYAN,
        )

        retry_text = "Press ENTER to retry"
        if self.game_over_flash <= 0 and (self.frame // 20) % 2:
            pyxel.text(SCREEN_W // 2 - len(retry_text) * 2, 170, retry_text, WHITE)

        self.frame += 1


if __name__ == "__main__":
    Game()
