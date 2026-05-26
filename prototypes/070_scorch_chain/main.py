"""070_scorch_chain — Color-Match Tank Battle.

Core fun moment: aiming carefully to destroy same-color terrain as the
previous shot, building COMBO chains that culminate in a devastating
SUPER SHELL for massive score and damage.
Risk/reward: keep hitting same color for COMBO multiplier vs. switch
to damage the enemy tank directly.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
CELL = 8
COLS = 40
ROWS = 30
FPS = 30
DISPLAY_SCALE = 2

# Colors
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

TERRAIN_COLORS: tuple[int, int, int, int] = (RED, GREEN, DARK_BLUE, YELLOW)

# Tank
TANK_W = 16
TANK_H = 12
TANK_HP = 100
PLAYER_COL = 5
ENEMY_COL = 34
TANK_COLOR_PLAYER = LIGHT_BLUE
TANK_COLOR_ENEMY = ORANGE

# Projectile
GRAVITY = 0.15
POWER_MIN = 20.0
POWER_MAX = 100.0
ANGLE_MIN = -80.0
ANGLE_MAX = -10.0
POWER_SPEED_SCALE = 0.04
SPEED_SCALE = 0.06

# Explosion
BLAST_NORMAL = 3
BLAST_SUPER = 5
DMG_NORMAL = 25
DMG_SUPER = 50

# COMBO
SUPER_COMBO_THRESHOLD = 3
SCORE_PER_CELL = 100
SUPER_BONUS = 500

# UI
TOP_BAR_H = 16

# ── Phase Enum ─────────────────────────────────────────────────────────

class Phase(Enum):
    TITLE = auto()
    PLAYER_AIM = auto()
    PLAYER_FIRE = auto()
    ANIM_PROJECTILE = auto()
    ANIM_EXPLOSION = auto()
    GRAVITY_COLLAPSE = auto()
    ENEMY_AIM = auto()
    ENEMY_FIRE = auto()
    ANIM_ENEMY_PROJECTILE = auto()
    ANIM_ENEMY_EXPLOSION = auto()
    ENEMY_GRAVITY = auto()
    CHECK_WIN = auto()
    GAME_OVER = auto()


# ── Data Classes ───────────────────────────────────────────────────────

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 1


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    alive: bool = True
    color: int = WHITE
    trail_particles: list[Particle] | None = None

    def __post_init__(self) -> None:
        if self.trail_particles is None:
            self.trail_particles = []


# ── Game Class ─────────────────────────────────────────────────────────

class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Scorch Chain", display_scale=DISPLAY_SCALE, fps=FPS)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self._init_state()

    def _init_state(self) -> None:
        """Initialize or reinitialize mutable game state."""
        self.terrain: list[list[int]] = [[-1] * ROWS for _ in range(COLS)]
        self._generate_terrain()

        self.player_hp: int = TANK_HP
        self.enemy_hp: int = TANK_HP
        self.player_x: float = PLAYER_COL * CELL + CELL / 2
        self.player_y: float = self._tank_y_from_terrain(PLAYER_COL)
        self.enemy_x: float = ENEMY_COL * CELL + CELL / 2
        self.enemy_y: float = self._tank_y_from_terrain(ENEMY_COL)
        self.player_angle: float = -45.0
        self.player_power: float = 60.0
        self.current_projectile: Projectile | None = None
        self.particles: list[Particle] = []
        self.float_texts: list[FloatText] = []
        self.combo: int = 0
        self.last_color: int = -1
        self.score: int = 0
        self.turn: str = "player"
        self.super_shell_ready: bool = False
        self._power_charging: bool = False
        self._power_increasing: bool = True
        self._explosion_timer: int = 0
        self._explosion_cx: int = 0
        self._explosion_cy: int = 0
        self._explosion_radius: int = BLAST_NORMAL
        self._explosion_damage: int = DMG_NORMAL
        self._explosion_has_run: bool = False
        self._gravity_done: bool = False
        self._frame: int = 0
        self._game_over_timer: int = 0

    # ── Terrain Generation ──────────────────────────────────────────

    def _generate_terrain(self) -> None:
        """Generate terrain with varying heights per column."""
        for c in range(COLS):
            if c < COLS // 2:
                h = self._rng.randint(14, 22)
            elif c == COLS // 2:
                h = self._rng.randint(12, 18)
            else:
                h = self._rng.randint(14, 22)

            color_idx = self._rng.randint(0, 3)
            for r in range(ROWS - h, ROWS):
                self.terrain[c][r] = color_idx
                if self._rng.random() < 0.3:
                    color_idx = self._rng.randint(0, 3)

        self._clear_tank_position(PLAYER_COL)
        self._clear_tank_position(ENEMY_COL)

    def _clear_tank_position(self, col: int) -> None:
        """Clear a few columns around tank position."""
        for dc in range(-2, 3):
            c = col + dc
            if 0 <= c < COLS:
                h = self._terrain_height(c)
                clear_from = max(0, ROWS - h - 3)
                for r in range(clear_from, ROWS):
                    if self.terrain[c][r] >= 0:
                        self.terrain[c][r] = -1

    def _terrain_height(self, col: int) -> int:
        """Return number of filled cells in a column."""
        count = 0
        for r in range(ROWS):
            if self.terrain[col][r] >= 0:
                count += 1
        return count

    def _surface_row(self, col: int) -> int:
        """Return the row index of the topmost terrain cell in column, or ROWS if none."""
        for r in range(ROWS):
            if self.terrain[col][r] >= 0:
                return r
        return ROWS

    # ── Pure Logic ───────────────────────────────────────────────────

    def _tank_y_from_terrain(self, col: int) -> float:
        """Calculate tank center Y position sitting on terrain at column."""
        surface = self._surface_row(col)
        return surface * CELL - TANK_H / 2

    def _destroy_terrain(self, cx: int, cy: int, radius: int) -> tuple[int, list[int]]:
        """Destroy terrain cells within radius. Returns (count, list of destroyed colors)."""
        destroyed_colors: list[int] = []
        count = 0
        for r in range(max(0, cy - radius), min(ROWS, cy + radius + 1)):
            for c in range(max(0, cx - radius), min(COLS, cx + radius + 1)):
                dr = r - cy
                dc = c - cx
                if math.hypot(dr, dc) <= radius:
                    if self.terrain[c][r] >= 0:
                        destroyed_colors.append(self.terrain[c][r])
                        self.terrain[c][r] = -1
                        count += 1
        return count, destroyed_colors

    def _gravity_collapse(self) -> int:
        """Compact each column downward. Returns number of cells moved."""
        moved = 0
        for c in range(COLS):
            blocks: list[int] = []
            for r in range(ROWS - 1, -1, -1):
                if self.terrain[c][r] >= 0:
                    blocks.append(self.terrain[c][r])
            blocks.reverse()
            new_len = len(blocks)
            old_len = 0
            for r in range(ROWS):
                if self.terrain[c][r] >= 0:
                    old_len += 1
            for r in range(ROWS):
                self.terrain[c][r] = -1
            for i, color_idx in enumerate(blocks):
                self.terrain[c][ROWS - 1 - i] = color_idx
            if new_len != old_len:
                moved += abs(new_len - old_len)
        return moved

    def _tank_fell(self, col: int) -> bool:
        """Check if tank at column fell off the screen (no terrain underneath)."""
        surface = self._surface_row(col)
        return surface >= ROWS

    def _check_combo(self, destroyed_colors: list[int]) -> str | None:
        """Update combo state based on destroyed colors.
        Returns "super" if SUPER SHELL triggered, None otherwise.
        """
        if not destroyed_colors:
            return None

        color_idx = self._most_frequent(destroyed_colors)
        color_pyxel = TERRAIN_COLORS[color_idx]

        if self.last_color == color_pyxel:
            self.combo += 1
        else:
            self.combo = 0

        self.last_color = color_pyxel

        if self.combo >= SUPER_COMBO_THRESHOLD and not self.super_shell_ready:
            self.super_shell_ready = True
            return "super"

        return None

    def _compute_score(self, cells_destroyed: int) -> int:
        """Compute score for destroying cells."""
        multiplier = 1.0 + self.combo * 0.5
        return int(cells_destroyed * SCORE_PER_CELL * multiplier)

    def _ai_angle(self) -> float:
        """Compute AI aiming angle with some randomness."""
        dx = self.player_x - self.enemy_x
        dy = self.player_y - self.enemy_y
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return float(self._rng.uniform(ANGLE_MIN, ANGLE_MAX))

        ideal_angle_rad = math.atan2(dy, dx)
        ideal_angle = math.degrees(ideal_angle_rad)
        ideal_angle = max(ANGLE_MIN, min(ANGLE_MAX, ideal_angle))

        noise = self._rng.uniform(-15.0, 15.0)
        return max(ANGLE_MIN, min(ANGLE_MAX, ideal_angle + noise))

    @staticmethod
    def _most_frequent(items: list[int]) -> int:
        """Return the most frequent item in a list."""
        if not items:
            return -1
        return max(set(items), key=items.count)

    @staticmethod
    def _update_projectile(proj: Projectile) -> None:
        """Update projectile physics."""
        if not proj.alive:
            return
        proj.vy += GRAVITY
        proj.x += proj.vx
        proj.y += proj.vy

    # ── Particle / FloatText Spawning ────────────────────────────────

    def _spawn_smoke(self, x: float, y: float, color: int, count: int = 1) -> None:
        """Spawn smoke trail particles."""
        for _ in range(count):
            self.particles.append(Particle(
                x=x + self._rng.uniform(-2, 2),
                y=y + self._rng.uniform(-2, 2),
                vx=self._rng.uniform(-0.3, 0.3),
                vy=self._rng.uniform(-0.5, 0.5),
                life=10 + self._rng.randint(0, 5),
                color=color,
                size=1,
            ))

    def _spawn_explosion_particles(self, cx: float, cy: float, colors: list[int], super_shell: bool = False) -> None:
        """Spawn explosion burst particles."""
        count = 20 if super_shell else 12
        for _ in range(count):
            angle = self._rng.random() * math.pi * 2
            speed = self._rng.uniform(1.0, 3.5) if super_shell else self._rng.uniform(0.5, 2.0)
            p_color = self._rng.choice(colors) if colors else WHITE
            self.particles.append(Particle(
                x=float(cx),
                y=float(cy),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=15 + self._rng.randint(0, 10),
                color=p_color,
                size=2 if super_shell else 1,
            ))

    def _spawn_float_text(self, x: float, y: float, text: str, color: int, life: int = 30) -> None:
        """Spawn floating score/combo text."""
        self.float_texts.append(FloatText(
            x=float(x),
            y=float(y),
            text=text,
            life=life,
            color=color,
        ))

    # ── Update Helpers ───────────────────────────────────────────────

    def _barrel_tip(self, tank_x: float, tank_y: float, angle_deg: float) -> tuple[float, float]:
        """Return barrel tip position for a tank."""
        rad = math.radians(angle_deg)
        barrel_len = 12.0
        bx = tank_x + math.cos(rad) * barrel_len
        by = tank_y + math.sin(rad) * barrel_len
        return bx, by

    def _fire_projectile(self, tank_x: float, tank_y: float, angle_deg: float, power: float, color: int = WHITE) -> Projectile:
        """Create a projectile fired from a tank position."""
        rad = math.radians(angle_deg)
        speed = power * SPEED_SCALE
        bx, by = self._barrel_tip(tank_x, tank_y, angle_deg)
        return Projectile(
            x=bx,
            y=by,
            vx=math.cos(rad) * speed,
            vy=math.sin(rad) * speed,
            alive=True,
            color=color,
        )

    def _explosion_hit_tank(self, tank_x: float, tank_y: float, ex: float, ey: float, radius: float) -> bool:
        """Check if tank is within explosion radius."""
        dist = math.hypot(tank_x - ex, tank_y - ey)
        return dist <= radius * CELL + TANK_W / 2

    def _start_game(self) -> None:
        """Start a new game from title."""
        self._init_state()
        self.phase = Phase.PLAYER_AIM

    def _start_game_over(self, victory: bool) -> None:
        """Transition to game over screen."""
        self.phase = Phase.GAME_OVER
        self._game_over_timer = 60
        if victory:
            self._spawn_float_text(SCREEN_W / 2 - 30, SCREEN_H / 2 - 40, "VICTORY!", YELLOW, 120)

    # ── Update ───────────────────────────────────────────────────────

    def update(self) -> None:
        self._frame += 1
        self._update_particles()
        self._update_float_texts()

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYER_AIM:
            self._update_player_aim()
        elif self.phase == Phase.ANIM_PROJECTILE:
            self._update_anim_projectile()
        elif self.phase == Phase.ANIM_EXPLOSION:
            self._update_anim_explosion()
        elif self.phase == Phase.GRAVITY_COLLAPSE:
            self._update_gravity()
        elif self.phase == Phase.ENEMY_AIM:
            self._update_enemy_aim()
        elif self.phase == Phase.ANIM_ENEMY_PROJECTILE:
            self._update_anim_enemy_projectile()
        elif self.phase == Phase.ANIM_ENEMY_EXPLOSION:
            self._update_anim_enemy_explosion()
        elif self.phase == Phase.ENEMY_GRAVITY:
            self._update_enemy_gravity()
        elif self.phase == Phase.CHECK_WIN:
            self._update_check_win()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self._start_game()

    def _update_player_aim(self) -> None:
        if pyxel.btn(pyxel.KEY_LEFT):
            self.player_angle = max(ANGLE_MIN, self.player_angle - 1.0)
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.player_angle = min(ANGLE_MAX, self.player_angle + 1.0)

        if pyxel.btn(pyxel.KEY_SPACE):
            if not self._power_charging:
                self._power_charging = True
                self._power_increasing = True
                self.player_power = POWER_MIN

            if self._power_increasing:
                self.player_power += 1.5
                if self.player_power >= POWER_MAX:
                    self.player_power = POWER_MAX
                    self._power_increasing = False
            else:
                self.player_power -= 1.5
                if self.player_power <= POWER_MIN:
                    self.player_power = POWER_MIN
                    self._power_increasing = True
        else:
            if self._power_charging:
                self._fire_player()

    def _fire_player(self) -> None:
        """Fire player projectile."""
        proj_color = WHITE
        if self.super_shell_ready:
            proj_color = YELLOW
            self.super_shell_ready = False

        self.current_projectile = self._fire_projectile(
            self.player_x, self.player_y, self.player_angle, self.player_power, proj_color
        )
        self._power_charging = False
        self.phase = Phase.ANIM_PROJECTILE

    def _update_anim_projectile(self) -> None:
        proj = self.current_projectile
        if proj is None or not proj.alive:
            self._start_player_explosion()
            return

        self._update_projectile(proj)
        self._spawn_smoke(proj.x, proj.y, GRAY)

        gx = int(proj.x // CELL)
        gy = int(proj.y // CELL)

        if (proj.x < -20 or proj.x > SCREEN_W + 20
                or proj.y > SCREEN_H + 20 or proj.y < -100):
            proj.alive = False
            self._start_player_explosion()
            return

        if 0 <= gx < COLS and 0 <= gy < ROWS:
            if self.terrain[gx][gy] >= 0:
                proj.alive = False
                self._explosion_cx = gx
                self._explosion_cy = gy
                self._start_player_explosion()
                return

        tank_cx = int(self.enemy_x)
        tank_cy = int(self.enemy_y)
        if abs(proj.x - tank_cx) < TANK_W // 2 + 4 and abs(proj.y - tank_cy) < TANK_H // 2 + 4:
            proj.alive = False
            self._explosion_cx = int(proj.x // CELL)
            self._explosion_cy = int(proj.y // CELL)
            self._start_player_explosion()
            return

    def _start_player_explosion(self) -> None:
        """Set up explosion for player's shot."""
        is_super = self.current_projectile is not None and self.current_projectile.color == YELLOW
        radius = BLAST_SUPER if is_super else BLAST_NORMAL
        damage = DMG_SUPER if is_super else DMG_NORMAL

        self._explosion_radius = radius
        self._explosion_damage = damage
        self._explosion_timer = 0
        self._explosion_has_run = False
        self.particles.clear()
        self.current_projectile = None
        self.phase = Phase.ANIM_EXPLOSION

    def _update_anim_explosion(self) -> None:
        self._explosion_timer += 1

        if self._explosion_timer == 5 and not self._explosion_has_run:
            self._explosion_has_run = True
            cx = max(0, min(COLS - 1, self._explosion_cx))
            cy = max(0, min(ROWS - 1, self._explosion_cy))
            is_super = self._explosion_radius == BLAST_SUPER
            damage = self._explosion_damage
            radius = self._explosion_radius

            count, destroyed_colors = self._destroy_terrain(cx, cy, radius)

            color_indices = set(destroyed_colors)
            pyxel_colors = [TERRAIN_COLORS[c] for c in color_indices]
            if not pyxel_colors:
                pyxel_colors = [ORANGE]

            ex = cx * CELL + CELL / 2
            ey = cy * CELL + CELL / 2

            self._spawn_explosion_particles(ex, ey, pyxel_colors, is_super)

            if is_super:
                for _ in range(5):
                    sx = ex + self._rng.uniform(-20, 20)
                    sy = ey + self._rng.uniform(-20, 20)
                    self.particles.append(Particle(
                        x=sx, y=sy,
                        vx=self._rng.uniform(-3, 3),
                        vy=self._rng.uniform(-3, 3),
                        life=20,
                        color=WHITE,
                        size=2,
                    ))

            super_triggered = self._check_combo(destroyed_colors)
            base_score = self._compute_score(count)
            if is_super:
                base_score += SUPER_BONUS
                self._spawn_float_text(ex, ey - 10, "SUPER SHELL!", YELLOW, 40)
            self.score += base_score
            self._spawn_float_text(ex, ey + 10, f"+{base_score}", WHITE, 25)

            if super_triggered:
                self._spawn_float_text(
                    self.player_x, self.player_y - 20,
                    "SUPER READY!", YELLOW, 60,
                )

            if self._explosion_hit_tank(self.enemy_x, self.enemy_y, ex, ey, radius):
                self.enemy_hp -= damage
                real_dmg = damage
                self._spawn_float_text(self.enemy_x, self.enemy_y - 20, f"-{real_dmg}", RED, 30)

        if self._explosion_timer >= 20:
            self._gravity_done = False
            self.phase = Phase.GRAVITY_COLLAPSE

    def _update_gravity(self) -> None:
        if not self._gravity_done:
            self._gravity_collapse()
            self._gravity_done = True

            if self._tank_fell(PLAYER_COL):
                self.player_hp = 0
            if self._tank_fell(ENEMY_COL):
                self.enemy_hp = 0

            self.player_y = self._tank_y_from_terrain(PLAYER_COL)
            self.enemy_y = self._tank_y_from_terrain(ENEMY_COL)

        self.phase = Phase.CHECK_WIN

    def _update_enemy_aim(self) -> None:
        self.enemy_y = self._tank_y_from_terrain(ENEMY_COL)

        ai_angle = self._ai_angle()
        ai_power = self._rng.uniform(POWER_MIN + 10, POWER_MAX - 20)

        self.current_projectile = self._fire_projectile(
            self.enemy_x, self.enemy_y, ai_angle, ai_power, ORANGE
        )
        self.phase = Phase.ANIM_ENEMY_PROJECTILE

    def _update_anim_enemy_projectile(self) -> None:
        proj = self.current_projectile
        if proj is None or not proj.alive:
            self._start_enemy_explosion()
            return

        self._update_projectile(proj)
        self._spawn_smoke(proj.x, proj.y, ORANGE)

        gx = int(proj.x // CELL)
        gy = int(proj.y // CELL)

        if (proj.x < -20 or proj.x > SCREEN_W + 20
                or proj.y > SCREEN_H + 20 or proj.y < -100):
            proj.alive = False
            self._start_enemy_explosion()
            return

        if 0 <= gx < COLS and 0 <= gy < ROWS:
            if self.terrain[gx][gy] >= 0:
                proj.alive = False
                self._explosion_cx = gx
                self._explosion_cy = gy
                self._start_enemy_explosion()
                return

        tank_cx = int(self.player_x)
        tank_cy = int(self.player_y)
        if abs(proj.x - tank_cx) < TANK_W // 2 + 4 and abs(proj.y - tank_cy) < TANK_H // 2 + 4:
            proj.alive = False
            self._explosion_cx = int(proj.x // CELL)
            self._explosion_cy = int(proj.y // CELL)
            self._start_enemy_explosion()
            return

    def _start_enemy_explosion(self) -> None:
        """Set up explosion for enemy's shot."""
        self._explosion_radius = BLAST_NORMAL
        self._explosion_damage = DMG_NORMAL
        self._explosion_timer = 0
        self._explosion_has_run = False
        self.particles.clear()
        self.current_projectile = None
        self.phase = Phase.ANIM_ENEMY_EXPLOSION

    def _update_anim_enemy_explosion(self) -> None:
        self._explosion_timer += 1

        if self._explosion_timer == 5 and not self._explosion_has_run:
            self._explosion_has_run = True
            cx = max(0, min(COLS - 1, self._explosion_cx))
            cy = max(0, min(ROWS - 1, self._explosion_cy))
            radius = self._explosion_radius
            damage = self._explosion_damage

            count, destroyed_colors = self._destroy_terrain(cx, cy, radius)

            color_indices = set(destroyed_colors)
            pyxel_colors = [TERRAIN_COLORS[c] for c in color_indices]
            if not pyxel_colors:
                pyxel_colors = [ORANGE]

            ex = cx * CELL + CELL / 2
            ey = cy * CELL + CELL / 2

            self._spawn_explosion_particles(ex, ey, pyxel_colors, False)

            if self._explosion_hit_tank(self.player_x, self.player_y, ex, ey, radius):
                self.player_hp -= damage
                self._spawn_float_text(self.player_x, self.player_y - 20, f"-{damage}", RED, 30)

        if self._explosion_timer >= 20:
            self._gravity_done = False
            self.phase = Phase.ENEMY_GRAVITY

    def _update_enemy_gravity(self) -> None:
        if not self._gravity_done:
            self._gravity_collapse()
            self._gravity_done = True

            if self._tank_fell(PLAYER_COL):
                self.player_hp = 0
            if self._tank_fell(ENEMY_COL):
                self.enemy_hp = 0

            self.player_y = self._tank_y_from_terrain(PLAYER_COL)
            self.enemy_y = self._tank_y_from_terrain(ENEMY_COL)

        self.phase = Phase.CHECK_WIN

    def _update_check_win(self) -> None:
        if self.player_hp <= 0:
            self._start_game_over(False)
            return
        if self.enemy_hp <= 0:
            self._start_game_over(True)
            return

        self.phase = Phase.ENEMY_AIM

    def _update_game_over(self) -> None:
        if self._game_over_timer > 0:
            self._game_over_timer -= 1
        else:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_float_texts(self) -> None:
        for ft in self.float_texts[:]:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self.float_texts.remove(ft)

    # ── Draw ──────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        self._draw_terrain()
        self._draw_tank(self.enemy_x, self.enemy_y, TANK_COLOR_ENEMY, self.player_angle if self.phase == Phase.ENEMY_AIM else 0)
        self._draw_tank(self.player_x, self.player_y, TANK_COLOR_PLAYER, self.player_angle)
        self._draw_projectile()
        self._draw_particles()
        self._draw_float_texts()
        self._draw_hud()

        if self.phase == Phase.ANIM_EXPLOSION or self.phase == Phase.ANIM_ENEMY_EXPLOSION:
            self._draw_explosion_effect()

        if self.phase == Phase.PLAYER_AIM:
            self._draw_power_bar()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "SCORCH CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * 4 // 2, 60, title, WHITE)

        instructions = [
            "ARROWS: Adjust angle",
            "SPACE: Charge & fire",
            "Same-color hits = COMBO",
            "COMBO x3 = SUPER SHELL!",
            "",
            "ENTER to Start",
        ]
        for i, line in enumerate(instructions):
            if line:
                pyxel.text(SCREEN_W // 2 - len(line) * 4 // 2, 90 + i * 14, line, GRAY)

    def _draw_terrain(self) -> None:
        for r in range(ROWS):
            py = r * CELL
            for c in range(COLS):
                color_idx = self.terrain[c][r]
                if color_idx >= 0:
                    px = c * CELL
                    actual_color = TERRAIN_COLORS[color_idx]
                    pyxel.rect(px, py, CELL, CELL, actual_color)
                    if color_idx == 0:
                        pyxel.rectb(px, py, CELL, CELL, RED)
                    elif color_idx == 1:
                        pyxel.rectb(px, py, CELL, CELL, GREEN)
                    elif color_idx == 2:
                        pyxel.rectb(px, py, CELL, CELL, DARK_BLUE)
                    else:
                        pyxel.rectb(px, py, CELL, CELL, YELLOW)

    def _draw_power_bar(self) -> None:
        if self._power_charging:
            bar_x = int(self.player_x - 20)
            bar_y = int(self.player_y + 12)
            bar_w = 40
            bar_h = 4
            pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
            fill = int(bar_w * (self.player_power - POWER_MIN) / (POWER_MAX - POWER_MIN))
            pyxel.rect(bar_x, bar_y, fill, bar_h, LIME)

    def _draw_tank(self, cx: float, cy: float, body_color: int, angle: float) -> None:
        tx = int(cx - TANK_W // 2)
        ty = int(cy - TANK_H // 2)
        pyxel.rect(tx, ty, TANK_W, TANK_H, body_color)
        pyxel.rectb(tx, ty, TANK_W, TANK_H, WHITE)

        rad = math.radians(angle)
        barrel_len = 12.0
        bx = cx + math.cos(rad) * barrel_len
        by = cy + math.sin(rad) * barrel_len
        pyxel.line(int(cx), int(cy), int(bx), int(by), WHITE)

    def _draw_projectile(self) -> None:
        proj = self.current_projectile
        if proj is not None and proj.alive:
            px = int(proj.x)
            py = int(proj.y)
            color = proj.color
            if color == YELLOW:
                rainbow = [RED, ORANGE, YELLOW, LIME, CYAN]
                idx = (self._frame // 3) % len(rainbow)
                color = rainbow[idx]
            pyxel.circ(px, py, 3, color)
            pyxel.circb(px, py, 3, WHITE)

    def _draw_explosion_effect(self) -> None:
        t = self._explosion_timer
        cx = self._explosion_cx * CELL + CELL // 2
        cy = self._explosion_cy * CELL + CELL // 2
        r = min(t * 2, self._explosion_radius * CELL)
        color = YELLOW if t < 5 else ORANGE
        if t < 15:
            pyxel.circb(int(cx), int(cy), int(r), color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.size > 1:
                pyxel.rect(int(p.x), int(p.y), p.size, p.size, p.color)
            else:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_float_texts(self) -> None:
        for ft in self.float_texts:
            pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 14, NAVY)
        pyxel.text(2, 3, "HP:", WHITE)
        pyxel.rect(22, 3, 50, 6, DARK_BLUE)
        hp_w = max(0, int(50 * self.player_hp / TANK_HP))
        pyxel.rect(22, 3, hp_w, 6, GREEN if self.player_hp > 30 else RED)

        enemy_label_x = SCREEN_W - 75
        pyxel.text(enemy_label_x, 3, "HP:", WHITE)
        pyxel.rect(enemy_label_x + 18, 3, 50, 6, DARK_BLUE)
        e_hp_w = max(0, int(50 * self.enemy_hp / TANK_HP))
        pyxel.rect(enemy_label_x + 18, 3, e_hp_w, 6, ORANGE if self.enemy_hp > 30 else RED)

        combo_text = f"COMBO: x{self.combo}" if self.combo > 0 else ""
        combo_color = YELLOW if self.combo >= SUPER_COMBO_THRESHOLD else WHITE
        if combo_text:
            pyxel.text(SCREEN_W // 2 - len(combo_text) * 4 // 2, 3, combo_text, combo_color)

        if self.super_shell_ready:
            pyxel.text(SCREEN_W // 2 - 40, 12, "SUPER READY!", YELLOW)

        score_text = f"SCORE: {self.score}"
        pyxel.text(2, SCREEN_H - 8, score_text, WHITE)

        turn_text = "YOUR TURN" if self.phase in (Phase.PLAYER_AIM, Phase.ANIM_PROJECTILE, Phase.ANIM_EXPLOSION, Phase.GRAVITY_COLLAPSE) else ""
        pyxel.text(SCREEN_W // 2 - len(turn_text) * 4 // 2, SCREEN_H - 8, turn_text, LIME)

    def _draw_game_over(self) -> None:
        victory = self.enemy_hp <= 0
        pyxel.rect(SCREEN_W // 2 - 80, 60, 160, 120, NAVY)
        pyxel.rectb(SCREEN_W // 2 - 80, 60, 160, 120, WHITE)

        msg = "VICTORY!" if victory else "DEFEAT"
        color = YELLOW if victory else RED
        pyxel.text(SCREEN_W // 2 - len(msg) * 4 // 2, 75, msg, color)

        pyxel.text(SCREEN_W // 2 - 50, 100, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 60, 120, f"MAX COMBO: {self.combo}", YELLOW)

        retry = "ENTER to Retry"
        pyxel.text(SCREEN_W // 2 - len(retry) * 4 // 2, 155, retry, WHITE)


# ── Entry Point ────────────────────────────────────────────────────────

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
