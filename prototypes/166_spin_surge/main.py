import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240
RINK_MARGIN = 8
RINK_X = RINK_MARGIN
RINK_Y = RINK_MARGIN
RINK_W = SCREEN_W - RINK_MARGIN * 2
RINK_H = SCREEN_H - RINK_MARGIN * 2
PLAYER_SPEED = 2.0
PLAYER_RADIUS = 8
ZONE_RADIUS = 20
MAX_ZONES = 5
ZONE_SPAWN_INTERVAL = 90
ZONE_LIFE_MIN = 180
ZONE_LIFE_MAX = 300
COLOR_CYCLE_INTERVAL = 300
COMBO_FOR_SUPER = 4
SUPER_DURATION = 300
SCORE_BASE = 100
SCORE_COMBO_MULT = 0.5
SUPER_SCORE_MULT = 3
MAX_HEAT = 100
HEAT_PER_MISMATCH = 20
HEAT_PER_OFF_RINK = 5
HEAT_DECAY = 0.05
CRACK_SPAWN_INTERVAL = 60
CRACK_SPREAD_CHANCE = 0.15
MAX_CRACKS = 80
MAX_PARTICLES = 40
MAX_FLOATING_TEXTS = 10
GAME_TIMER = 5400
GRID_COLS = 15
GRID_ROWS = 11
CELL_W = RINK_W // GRID_COLS
CELL_H = RINK_H // GRID_ROWS

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

ZONE_COLORS = [COLOR_RED, COLOR_GREEN, COLOR_DARK_BLUE, COLOR_YELLOW]
NUM_COLORS = len(ZONE_COLORS)
RAINBOW_COLORS = [COLOR_RED, COLOR_ORANGE, COLOR_YELLOW, COLOR_GREEN, COLOR_CYAN, COLOR_DARK_BLUE, COLOR_PURPLE, COLOR_PINK]


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclass
class SpinZone:
    x: float
    y: float
    color: int
    radius: int = ZONE_RADIUS
    life: int = ZONE_LIFE_MIN
    active: bool = True


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


@dataclass
class IceCrack:
    x: int
    y: int
    life: int


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self) -> None:
        self._init_state()
        self.phase = Phase.TITLE
        self.best_path: list[tuple[float, float]] = []

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.player_x: float = float(RINK_X + RINK_W // 2)
        self.player_y: float = float(RINK_Y + RINK_H // 2)
        self.player_color_idx: int = 0
        self.player_color_timer: int = COLOR_CYCLE_INTERVAL
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = GAME_TIMER
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.zones: list[SpinZone] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.cracks: list[IceCrack] = []
        self.zone_spawn_timer: int = 0
        self.crack_spawn_timer: int = 0
        self.frame: int = 0
        self.rng: random.Random = random.Random()
        self.current_path: list[tuple[float, float]] = []

    def reset(self) -> None:
        self._init_state()
        self.phase = Phase.PLAYING
        self.rng = random.Random()
        self._spawn_initial_zones()

    # -- spawning -----------------------------------------------------------

    def _spawn_initial_zones(self) -> None:
        for _ in range(3):
            self.zones.append(self._spawn_zone())

    def _spawn_zone(self) -> SpinZone:
        x = float(self.rng.randint(RINK_X + ZONE_RADIUS, RINK_X + RINK_W - ZONE_RADIUS))
        y = float(self.rng.randint(RINK_Y + ZONE_RADIUS, RINK_Y + RINK_H - ZONE_RADIUS))
        color = self.rng.randint(0, NUM_COLORS - 1)
        life = self.rng.randint(ZONE_LIFE_MIN, ZONE_LIFE_MAX)
        return SpinZone(x=x, y=y, color=color, life=life)

    # -- collision ----------------------------------------------------------

    def _check_zone_collision(
        self, px: float, py: float, p_color: int, zone: SpinZone
    ) -> tuple[bool, bool]:
        """Returns (collided, is_match)."""
        if not zone.active:
            return False, False
        dist = math.hypot(px - zone.x, py - zone.y)
        if dist < PLAYER_RADIUS + zone.radius:
            is_match = (p_color == zone.color)
            return True, is_match
        return False, False

    # -- color cycling ------------------------------------------------------

    def _cycle_color(self) -> None:
        self.player_color_timer -= 1
        if self.player_color_timer <= 0:
            self.player_color_idx = (self.player_color_idx + 1) % NUM_COLORS
            self.player_color_timer = COLOR_CYCLE_INTERVAL

    # -- combo / super ------------------------------------------------------

    def _update_combo(self, matched: bool) -> int:
        if matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            if self.combo >= COMBO_FOR_SUPER and not self.super_mode:
                self._start_super()
        else:
            self.combo = 0
        return self.combo

    def _start_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        for _ in range(20):
            vx = self.rng.uniform(-3.0, 3.0)
            vy = self.rng.uniform(-3.0, 3.0)
            c = ZONE_COLORS[self.rng.randint(0, NUM_COLORS - 1)]
            self.particles.append(
                Particle(
                    x=self.player_x, y=self.player_y,
                    vx=float(vx), vy=float(vy), color=c,
                    life=self.rng.randint(20, 40),
                )
            )
        self._add_floating_text(self.player_x, self.player_y - 20, "SUPER SPIN!", COLOR_WHITE)

    def _end_super(self) -> None:
        self.super_mode = False
        self.super_timer = 0
        self.combo = 0

    # -- heat ---------------------------------------------------------------

    def _add_heat(self, amount: float) -> None:
        self.heat = min(float(MAX_HEAT), self.heat + amount)

    def _update_heat_decay(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    # -- scoring (pure logic, no pyxel) ------------------------------------

    def _score_for_match(self) -> int:
        base = SCORE_BASE
        multiplier = 1.0 + self.combo * SCORE_COMBO_MULT
        score = int(base * multiplier)
        if self.super_mode:
            score *= SUPER_SCORE_MULT
        return max(1, score)

    # -- CA cracks ----------------------------------------------------------

    def _spread_cracks(self) -> None:
        new_cracks: list[IceCrack] = []
        for crack in self.cracks:
            if self.rng.random() < CRACK_SPREAD_CHANCE:
                direction = self.rng.randint(0, 3)
                nx, ny = crack.x, crack.y
                if direction == 0:
                    nx -= 1
                elif direction == 1:
                    nx += 1
                elif direction == 2:
                    ny -= 1
                else:
                    ny += 1
                if 0 <= nx < GRID_COLS and 0 <= ny < GRID_ROWS:
                    exists = any(
                        c.x == nx and c.y == ny for c in self.cracks
                    ) or any(c.x == nx and c.y == ny for c in new_cracks)
                    if not exists and len(self.cracks) + len(new_cracks) < MAX_CRACKS:
                        new_cracks.append(
                            IceCrack(x=nx, y=ny, life=self.rng.randint(60, 180))
                        )
        self.cracks.extend(new_cracks)

    def _spawn_crack(self) -> None:
        if len(self.cracks) >= MAX_CRACKS:
            return
        x = self.rng.randint(0, GRID_COLS - 1)
        y = self.rng.randint(0, GRID_ROWS - 1)
        exists = any(c.x == x and c.y == y for c in self.cracks)
        if not exists:
            self.cracks.append(
                IceCrack(x=x, y=y, life=self.rng.randint(60, 180))
            )

    def _update_cracks(self) -> None:
        for c in self.cracks:
            c.life -= 1
        self.cracks = [c for c in self.cracks if c.life > 0]

    # -- particles / texts --------------------------------------------------

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0.0, math.pi * 2)
            speed = self.rng.uniform(1.0, 3.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self.rng.randint(15, 30)
            self.particles.append(
                Particle(x=x, y=y, vx=float(vx), vy=float(vy), color=color, life=life)
            )

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        if len(self.floating_texts) >= MAX_FLOATING_TEXTS:
            return
        self.floating_texts.append(
            FloatingText(x=x - len(text) * 2, y=y, text=text, color=color, life=45)
        )

    # -- update / draw ------------------------------------------------------

    def update(self) -> None:
        self.frame += 1
        if self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floating_texts()

    def _update_playing(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self._on_game_over()
            return

        # --- movement ---
        dx = 0.0
        dy = 0.0
        if pyxel.btn(pyxel.KEY_LEFT):
            dx -= PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT):
            dx += PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_UP):
            dy -= PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_DOWN):
            dy += PLAYER_SPEED

        if dx != 0.0 and dy != 0.0:
            inv_sqrt2 = 1.0 / math.sqrt(2)
            dx *= inv_sqrt2
            dy *= inv_sqrt2

        self.player_x += dx
        self.player_y += dy

        # --- clamp to rink & check off-rink ---
        in_rink_x = RINK_X <= self.player_x <= RINK_X + RINK_W
        in_rink_y = RINK_Y <= self.player_y <= RINK_Y + RINK_H
        if not in_rink_x or not in_rink_y:
            self.player_x = max(float(RINK_X), min(float(RINK_X + RINK_W), self.player_x))
            self.player_y = max(float(RINK_Y), min(float(RINK_Y + RINK_H), self.player_y))
            self._add_heat(HEAT_PER_OFF_RINK)

        # --- record path ---
        self.current_path.append((self.player_x, self.player_y))
        if len(self.current_path) > 600:
            self.current_path = self.current_path[-600:]

        # --- color cycle ---
        if not self.super_mode:
            self._cycle_color()

        # --- zone collisions (only first one per frame) ---
        collided = False
        for zone in self.zones:
            if not zone.active:
                continue
            hit, is_match = self._check_zone_collision(
                self.player_x, self.player_y, self.player_color_idx, zone
            )
            if hit:
                zone.active = False
                collided = True
                zone_color = ZONE_COLORS[zone.color]

                if self.super_mode or is_match:
                    self.combo += 1
                    self.max_combo = max(self.max_combo, self.combo)
                    gained = self._score_for_match()
                    self.score += gained
                    self._spawn_particles(zone.x, zone.y, zone_color, 8)
                    self._add_floating_text(
                        zone.x, zone.y - 8,
                        f"COMBO x{self.combo}",
                        ZONE_COLORS[zone.color],
                    )
                    if not self.super_mode:
                        self._update_combo(True)
                else:
                    self._add_heat(HEAT_PER_MISMATCH)
                    self._spawn_particles(zone.x, zone.y, COLOR_GRAY, 4)
                    self._add_floating_text(zone.x, zone.y - 8, "MISS!", COLOR_RED)
                    self.combo = 0
                break

        if not collided:
            if self.super_mode:
                self._update_combo(True)

        # --- update zones ---
        for zone in self.zones:
            if zone.active:
                zone.life -= 1
                if zone.life <= 0:
                    zone.active = False
        self.zones = [z for z in self.zones if z.active]

        # --- spawn zones ---
        self.zone_spawn_timer += 1
        if self.zone_spawn_timer >= ZONE_SPAWN_INTERVAL:
            self.zone_spawn_timer = 0
            if len(self.zones) < MAX_ZONES:
                self.zones.append(self._spawn_zone())

        # --- super timer ---
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self._end_super()

        # --- heat decay ---
        self._update_heat_decay()

        # --- cracks ---
        if self.heat >= 50:
            self.crack_spawn_timer += 1
            if self.crack_spawn_timer >= CRACK_SPAWN_INTERVAL:
                self.crack_spawn_timer = 0
                self._spawn_crack()
            self._spread_cracks()
        else:
            self.crack_spawn_timer = 0
        self._update_cracks()

        # --- check heat game over ---
        if self.heat >= MAX_HEAT:
            self._on_game_over()

        # --- update visual effects ---
        self._update_particles()
        self._update_floating_texts()

    def _on_game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        for _ in range(30):
            vx = self.rng.uniform(-4.0, 4.0)
            vy = self.rng.uniform(-4.0, 4.0)
            c = ZONE_COLORS[self.rng.randint(0, NUM_COLORS - 1)]
            self.particles.append(
                Particle(
                    x=self.player_x, y=self.player_y,
                    vx=float(vx), vy=float(vy), color=c,
                    life=self.rng.randint(20, 40),
                )
            )
        if self.score > 0 and (not self.best_path or self.score >= self._best_score()):
            self.best_path = list(self.current_path)

    def _best_score(self) -> int:
        return self.score

    def draw(self) -> None:
        pyxel.cls(COLOR_BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # -- drawing helpers ----------------------------------------------------

    def _draw_title(self) -> None:
        # ice rink background
        pyxel.rect(RINK_X, RINK_Y, RINK_W, RINK_H, COLOR_LIGHT_BLUE)
        pyxel.rectb(RINK_X, RINK_Y, RINK_W, RINK_H, COLOR_WHITE)

        title = "SPIN SURGE"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 50, title, COLOR_WHITE)

        subtitle = "Figure Skating Color-Match"
        pyxel.text(SCREEN_W // 2 - len(subtitle) * 2, 66, subtitle, COLOR_CYAN)

        instructions = [
            "ARROW KEYS to skate on ice",
            "Enter colored SPIN ZONES",
            "MATCH player color = COMBO",
            "MISMATCH = HEAT +20",
            "",
            "COMBO x4 = SUPER SPIN (5s)",
            "SUPER matches ALL colors (3x score)",
            "",
            "HEAT 100 = Ice breaks!",
            "Survive 90 seconds!",
        ]
        for i, line in enumerate(instructions):
            c = COLOR_WHITE if i != 4 and i != 7 else COLOR_GRAY
            pyxel.text(SCREEN_W // 2 - len(line) * 2, 86 + i * 12, line, c)

        prompt = "PRESS SPACE TO START"
        if (self.frame // 30) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - len(prompt) * 2, 220, prompt, COLOR_YELLOW)

    def _draw_playing(self) -> None:
        # ice rink
        pyxel.rect(RINK_X, RINK_Y, RINK_W, RINK_H, COLOR_LIGHT_BLUE)
        pyxel.rectb(RINK_X, RINK_Y, RINK_W, RINK_H, COLOR_WHITE)

        # ghost trail (best path)
        if self.best_path:
            for i, (bx, by) in enumerate(self.best_path):
                if i % 4 == 0:
                    pyxel.pset(int(bx), int(by), COLOR_NAVY)

        # ice cracks
        for crack in self.cracks:
            cx = RINK_X + crack.x * CELL_W + CELL_W // 2
            cy = RINK_Y + crack.y * CELL_H + CELL_H // 2
            alpha = min(1.0, crack.life / 60.0)
            c = COLOR_DARK_BLUE if alpha > 0.5 else COLOR_GRAY
            pyxel.line(
                int(cx - 3), int(cy), int(cx + 3), int(cy), c
            )
            pyxel.line(
                int(cx), int(cy - 3), int(cx), int(cy + 3), c
            )
            if self.rng.random() < 0.3:
                pyxel.line(
                    int(cx - 2), int(cy - 2), int(cx + 2), int(cy + 2), c
                )

        # spin zones
        for zone in self.zones:
            if not zone.active:
                continue
            zone_color = ZONE_COLORS[zone.color]
            pulse = int(math.sin(self.frame * 0.1 + zone.x * 0.05 + zone.y * 0.05) * 3)
            r = zone.radius + pulse
            pyxel.circb(int(zone.x), int(zone.y), int(r), zone_color)
            pyxel.circ(int(zone.x), int(zone.y), int(r - 6), 0 if self.super_mode else zone_color)
            # concentric ring for visibility
            if r > 14:
                pyxel.circb(int(zone.x), int(zone.y), int(r - 8), zone_color)
            # life indicator (shrink ring)
            life_ratio = zone.life / ZONE_LIFE_MAX
            if life_ratio < 0.33:
                blink = (self.frame // 15) % 2 == 0
                if blink:
                    pyxel.circb(int(zone.x), int(zone.y), int(r + 2), COLOR_WHITE)

        # player
        self._draw_player()

        # super trail particles
        if self.super_mode:
            trail_color = RAINBOW_COLORS[(self.frame // 4) % len(RAINBOW_COLORS)]
            for i in range(3):
                ox = self.rng.uniform(-6, 6)
                oy = self.rng.uniform(-6, 6)
                pyxel.pset(
                    int(self.player_x + ox), int(self.player_y + oy),
                    trail_color,
                )

        # particles
        self._draw_particles()

        # floating texts
        self._draw_floating_texts()

        # HUD
        self._draw_hud()

    def _draw_player(self) -> None:
        px = int(self.player_x)
        py = int(self.player_y)

        if self.super_mode:
            # rainbow player
            color = RAINBOW_COLORS[(self.frame // 4) % len(RAINBOW_COLORS)]
            pyxel.circ(px, py, PLAYER_RADIUS + 2, color)
            pyxel.circ(px, py, PLAYER_RADIUS - 2, COLOR_WHITE)
            # sparkle
            pyxel.circ(px, py, 3, COLOR_YELLOW if (self.frame // 8) % 2 == 0 else COLOR_WHITE)
        else:
            player_color = ZONE_COLORS[self.player_color_idx]
            # shadow
            pyxel.circ(px + 1, py + 1, PLAYER_RADIUS, COLOR_BLACK)
            # body
            pyxel.circ(px, py, PLAYER_RADIUS, player_color)
            # inner highlight
            pyxel.circ(px, py, PLAYER_RADIUS - 3, COLOR_WHITE)
            # color indicator ring
            pyxel.circb(px, py, PLAYER_RADIUS + 1, player_color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 0:
                size = 2 if p.life > 10 else 1
                pyxel.rect(int(p.x), int(p.y), size, size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                alpha = ft.life / 45.0
                c = ft.color if alpha > 0.5 else COLOR_GRAY
                pyxel.text(int(ft.x), int(ft.y), ft.text, c)

    def _draw_hud(self) -> None:
        # SCORE (top-left)
        pyxel.text(4, 2, f"SCORE {self.score}", COLOR_WHITE)

        # COMBO
        combo_color = COLOR_WHITE
        if self.combo >= 2:
            combo_color = COLOR_YELLOW
        if self.combo >= COMBO_FOR_SUPER:
            combo_color = COLOR_RED
        pyxel.text(4, 12, f"COMBO x{self.combo}", combo_color)

        # TIMER (top-center)
        secs = max(0, self.timer // 60)
        time_text = f"TIME {secs}"
        timer_color = COLOR_WHITE if secs > 30 else (COLOR_YELLOW if secs > 10 else COLOR_RED)
        pyxel.text(SCREEN_W // 2 - len(time_text) * 2, 2, time_text, timer_color)

        # SUPER timer
        if self.super_mode:
            sup_secs = self.super_timer // 60 + 1
            sup_text = f"SUPER {sup_secs}s"
            rainbow_c = RAINBOW_COLORS[(self.frame // 6) % len(RAINBOW_COLORS)]
            pyxel.text(SCREEN_W // 2 - len(sup_text) * 2, 12, sup_text, rainbow_c)

        # HEAT bar (top-right)
        bar_x = SCREEN_W - 66
        bar_y = 2
        bar_w = 60
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, COLOR_GRAY)
        fill = int(self.heat / MAX_HEAT * bar_w)
        heat_color = COLOR_ORANGE if self.heat < 50 else (COLOR_YELLOW if self.heat < 80 else COLOR_RED)
        if fill > 0:
            pyxel.rect(bar_x, bar_y, fill, bar_h, heat_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, COLOR_WHITE)

        heat_label = "HEAT"
        pyxel.text(bar_x - 20, bar_y - 1, heat_label, COLOR_WHITE)

        # Danger indicator when heat >= 80
        if self.heat >= 80 and (self.frame // 15) % 2 == 0:
            danger_text = "DANGER!"
            pyxel.text(SCREEN_W // 2 - len(danger_text) * 2, 22, danger_text, COLOR_RED)

    def _draw_game_over(self) -> None:
        # dark background
        for i in range(SCREEN_H):
            c = COLOR_DARK_BLUE if i % 3 == 0 else COLOR_NAVY
            pyxel.line(0, i, SCREEN_W, i, c)

        self._draw_particles()
        self._draw_floating_texts()

        go = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(go) * 2, 40, go, COLOR_RED)

        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 2, 70, score_text, COLOR_WHITE)

        combo_text = f"MAX COMBO: x{self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 90, combo_text, COLOR_YELLOW)

        if self.heat >= MAX_HEAT:
            reason = "Ice shattered beneath you!"
        else:
            reason = "Time is up!"
        pyxel.text(SCREEN_W // 2 - len(reason) * 2, 115, reason, COLOR_WHITE)

        retry = "PRESS R TO RETRY"
        if (self.frame // 30) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - len(retry) * 2, 160, retry, COLOR_YELLOW)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SPIN SURGE", display_scale=2)
        font_path = Path(__file__).with_name("k8x12.bdf")
        if font_path.exists():
            pyxel.load(str(font_path))
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game
        if g.phase == Phase.TITLE:
            g.update()
            if pyxel.btnp(pyxel.KEY_SPACE):
                g.reset()
        elif g.phase == Phase.GAME_OVER:
            g.update()
            if pyxel.btnp(pyxel.KEY_R):
                g.reset()
        elif g.phase == Phase.PLAYING:
            g.update()

    def draw(self) -> None:
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
