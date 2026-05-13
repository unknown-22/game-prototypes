"""CALAMITY SIEGE — Space-invaders style gallery shooter.

Reinterpreted from deckbuilder idea #1 "Calamity Sealing (Runaway Control)"
(score 32.05, hooks: effect fusion/compression, cost=future hand).

Core mechanic: Contain enemies before they escape.
Same-color consecutive kills build COMBO → PIERCE shot at 5+ combo.
Enemies that reach the bottom ESCAPE and return as stronger elites.

Prototype 022 — first fixed-shooter in the collection.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ═══════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════

SCREEN_W = 256
SCREEN_H = 256
PLAYER_W = 16
PLAYER_H = 12
PLAYER_SPEED = 2
BULLET_SPEED = 5
ENEMY_COLS = 8
ENEMY_ROWS = 4
ENEMY_W = 12
ENEMY_H = 10
GRID_LEFT = 24
GRID_TOP = 28
CELL_W = 26
CELL_H = 20
MAX_HEAT = 12
HEAT_PER_SHOT = 1
HEAT_COOL_RATE = 0.12
MAX_HP = 5
COMBO_FOR_PIERCE = 5
FIRE_COOLDOWN = 10
GRID_MOVE_X = 4
GRID_DROP_Y = 8
ESCAPE_Y = SCREEN_H - 30  # y threshold for escape
DIVE_SPEED = 3

COLORS: list[int] = [
    pyxel.COLOR_RED,
    pyxel.COLOR_CYAN,
    pyxel.COLOR_YELLOW,
    pyxel.COLOR_LIME,
]
COLOR_NAMES: list[str] = ["RED", "CYAN", "YELLOW", "LIME"]
N_COLORS: int = len(COLORS)

# ═══════════════════════════════════════════════════════════════════════
# Enums & Data classes
# ═══════════════════════════════════════════════════════════════════════


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    WAVE_CLEAR = auto()
    GAME_OVER = auto()


@dataclass
class Bullet:
    x: float
    y: float
    pierce: bool = False
    alive: bool = True


@dataclass
class Enemy:
    x: float
    y: float
    color: int
    hp: int = 1
    escaped: bool = False
    alive: bool = True
    dive_timer: int = 0
    diving: bool = False
    dive_dx: float = 0.0
    dive_dy: float = 0.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int


# ═══════════════════════════════════════════════════════════════════════
# Starfield helper (deterministic)
# ═══════════════════════════════════════════════════════════════════════

def _make_stars(count: int = 40) -> list[tuple[int, int]]:
    rng = random.Random(42)
    return [(rng.randrange(SCREEN_W), rng.randrange(SCREEN_H)) for _ in range(count)]


STARS: list[tuple[int, int]] = _make_stars()

# ═══════════════════════════════════════════════════════════════════════
# Game
# ═══════════════════════════════════════════════════════════════════════


class Game:
    """CALAMITY SIEGE — Contain the breach."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CALAMITY SIEGE")
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State init ──────────────────────────────────────────────────

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.hp: int = MAX_HP
        self.heat: float = 0.0
        self.combo: int = 0
        self.combo_color: int = -1
        self.max_combo: int = 0
        self.wave: int = 1
        self.player_x: float = SCREEN_W / 2
        self.bullets: list[Bullet] = []
        self.enemies: list[Enemy] = []
        self.particles: list[Particle] = []
        self.float_texts: list[FloatText] = []
        self.fire_timer: int = 0
        self.grid_dir: int = 1
        self.grid_move_timer: float = 0.0
        self.grid_speed: float = 0.025  # moves per frame
        self.pierce_ready: bool = False
        self.shake_timer: int = 0
        self.shake_amount: int = 0
        self._spawn_formation()

    # ── Spawning ────────────────────────────────────────────────────

    def _spawn_formation(self) -> None:
        """Create the enemy grid formation for the current wave."""
        self.enemies.clear()
        n_colors_wave = min(N_COLORS, 2 + self.wave // 2)
        for row in range(ENEMY_ROWS):
            for col in range(ENEMY_COLS):
                color = random.randrange(n_colors_wave)
                self.enemies.append(Enemy(
                    x=GRID_LEFT + col * CELL_W,
                    y=GRID_TOP + row * CELL_H,
                    color=color,
                    dive_timer=random.randint(60, 300),
                ))
        self.grid_move_timer = 0.0
        self.grid_speed = max(0.008, 0.025 - (self.wave - 1) * 0.0025)

    def _spawn_escaped(self, color: int) -> None:
        """An enemy escaped — return as elite at the top."""
        self.enemies.append(Enemy(
            x=random.uniform(ENEMY_W, SCREEN_W - ENEMY_W),
            y=GRID_TOP,
            color=color,
            hp=2,
            escaped=True,
            dive_timer=random.randint(30, 120),
        ))
        self._add_float_text(SCREEN_W / 2, SCREEN_H / 2, "BREACH!", 40, pyxel.COLOR_RED)

    # ── Update ──────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
            return
        if self.phase == Phase.GAME_OVER:
            self._update_game_over()
            return
        if self.phase == Phase.WAVE_CLEAR:
            self._update_wave_clear()
            return
        # PLAYING
        self._update_player()
        self._update_bullets()
        self._update_formation()
        self._update_escaped_enemies()
        self._update_dives()
        self._update_collisions()
        self._update_heat()
        self._update_particles()
        self._update_float_texts()
        self._update_shake()
        self._check_wave_clear()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_wave_clear(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.wave += 1
            self._spawn_formation()
            self.phase = Phase.PLAYING
            self.combo = 0
            self.combo_color = -1
            self.pierce_ready = False

    def _update_player(self) -> None:
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.player_x = max(PLAYER_W / 2, self.player_x - PLAYER_SPEED)
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.player_x = min(SCREEN_W - PLAYER_W / 2, self.player_x + PLAYER_SPEED)
        self.fire_timer = max(0, self.fire_timer - 1)
        if (pyxel.btn(pyxel.KEY_SPACE) or pyxel.btn(pyxel.KEY_Z)) \
                and self.fire_timer == 0 and self.heat < MAX_HEAT:
            self._fire()

    def _fire(self) -> None:
        pierce = self.pierce_ready
        self.bullets.append(Bullet(x=self.player_x, y=SCREEN_H - 20, pierce=pierce))
        self.heat += HEAT_PER_SHOT
        self.fire_timer = FIRE_COOLDOWN
        if pierce:
            self.pierce_ready = False

    def _update_bullets(self) -> None:
        for b in self.bullets:
            b.y -= BULLET_SPEED
            if b.y < -6:
                b.alive = False
        self.bullets = [b for b in self.bullets if b.alive]

    def _update_formation(self) -> None:
        """Move the enemy formation side-to-side + step down."""
        formation = [e for e in self.enemies if not e.escaped and e.alive]
        if not formation:
            return
        self.grid_move_timer += self.grid_speed
        if self.grid_move_timer < 1.0:
            return
        self.grid_move_timer -= 1.0

        hit_edge = False
        for e in formation:
            nx = e.x + self.grid_dir * GRID_MOVE_X
            if nx < ENEMY_W or nx > SCREEN_W - ENEMY_W:
                hit_edge = True
                break

        if hit_edge:
            self.grid_dir *= -1
            for e in formation:
                e.y += GRID_DROP_Y
        else:
            for e in formation:
                e.x += self.grid_dir * GRID_MOVE_X

        # Check for enemies reaching escape threshold
        for e in formation:
            if e.y >= ESCAPE_Y and not e.escaped:
                e.alive = False
                self._spawn_escaped(e.color)

    def _update_escaped_enemies(self) -> None:
        """Escaped enemies move independently, drifting down slowly."""
        for e in self.enemies:
            if not e.alive or not e.escaped:
                continue
            e.y += 0.3  # slow drift down
            # Wrap around if off bottom
            if e.y > SCREEN_H + ENEMY_H:
                e.y = GRID_TOP
                e.x = random.uniform(ENEMY_W, SCREEN_W - ENEMY_W)

    def _update_dives(self) -> None:
        """Some enemies perform dive attacks toward the player."""
        for e in self.enemies:
            if not e.alive or e.diving:
                continue
            e.dive_timer -= 1
            if e.dive_timer <= 0:
                e.diving = True
                dx = self.player_x - e.x
                dy = (SCREEN_H - 20) - e.y
                dist = math.hypot(dx, dy) or 1.0
                e.dive_dx = (dx / dist) * DIVE_SPEED
                e.dive_dy = (dy / dist) * DIVE_SPEED
        for e in self.enemies:
            if not e.alive or not e.diving:
                continue
            e.x += e.dive_dx
            e.y += e.dive_dy
            if e.y > SCREEN_H + ENEMY_H or e.y < -ENEMY_H \
                    or e.x < -ENEMY_W or e.x > SCREEN_W + ENEMY_W:
                e.alive = False
                if e.escaped:
                    self._spawn_escaped(e.color)

    def _update_collisions(self) -> None:
        player_y = SCREEN_H - 20
        for b in self.bullets:
            if not b.alive:
                continue
            for e in self.enemies:
                if not e.alive:
                    continue
                if abs(b.x - e.x) < (ENEMY_W / 2 + 3) \
                        and abs(b.y - e.y) < (ENEMY_H / 2 + 4):
                    self._hit_enemy(e, b)
                    if not b.pierce:
                        b.alive = False
                        break

        # Player–enemy collision
        for e in self.enemies:
            if not e.alive:
                continue
            if abs(self.player_x - e.x) < (PLAYER_W + ENEMY_W) / 2 \
                    and abs(player_y - e.y) < (PLAYER_H + ENEMY_H) / 2:
                self._hit_player(e)

    def _hit_enemy(self, e: Enemy, b: Bullet) -> None:
        e.hp -= 1
        if e.hp <= 0:
            e.alive = False
            close_bonus = 1.0 + max(0.0, e.y / SCREEN_H)  # closer to bottom = higher bonus
            base = 200 if e.escaped else 100
            points = int(base * close_bonus)
            if self.combo_color == e.color:
                self.combo += 1
            else:
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
                self.combo_color = e.color
                self.combo = 1
            combo_mult = 1.0 + self.combo * 0.25
            earned = int(points * combo_mult)
            self.score += earned
            if self.combo >= COMBO_FOR_PIERCE:
                self.pierce_ready = True
            count = 12 if e.escaped else 6
            self._spawn_particles(e.x, e.y, e.color, count)
            self._add_float_text(e.x, e.y - 4, str(earned), 20,
                                 COLORS[e.color % len(COLORS)])
            if self.combo >= 3:
                self._add_float_text(
                    e.x, e.y - 12, f"x{self.combo}", 25, pyxel.COLOR_WHITE,
                )

    def _hit_player(self, e: Enemy) -> None:
        self.hp -= 1
        self.shake_timer = 10
        self.shake_amount = 3
        self._spawn_particles(self.player_x, SCREEN_H - 20, pyxel.COLOR_WHITE, 12)
        self._spawn_particles(e.x, e.y, pyxel.COLOR_RED, 8)
        if e.escaped:
            e.alive = False
        else:
            e.alive = False
            self._spawn_escaped(e.color)
        if self.hp <= 0:
            self.phase = Phase.GAME_OVER
            if self.combo > self.max_combo:
                self.max_combo = self.combo

    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_COOL_RATE)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vx *= 0.95
            p.vy *= 0.95
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_float_texts(self) -> None:
        for ft in self.float_texts:
            ft.y -= 0.6
            ft.life -= 1
        self.float_texts = [ft for ft in self.float_texts if ft.life > 0]

    def _update_shake(self) -> None:
        if self.shake_timer > 0:
            self.shake_timer -= 1

    def _check_wave_clear(self) -> None:
        if not any(e.alive for e in self.enemies):
            self.phase = Phase.WAVE_CLEAR
            self.bullets.clear()

    # ── Helper spawners ─────────────────────────────────────────────

    def _spawn_particles(self, x: float, y: float, color: int,
                         count: int) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(0.5, 2.5)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(6, 22),
                color=color,
            ))

    def _add_float_text(self, x: float, y: float, text: str, life: int,
                        color: int) -> None:
        self.float_texts.append(FloatText(x=x, y=y, text=text, life=life,
                                          color=color))

    # ── Draw ────────────────────────────────────────────────────────

    def draw(self) -> None:
        # Screen shake offset
        ox = random.randint(-self.shake_amount, self.shake_amount) \
            if self.shake_timer > 0 else 0
        oy = random.randint(-self.shake_amount, self.shake_amount) \
            if self.shake_timer > 0 else 0

        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title(ox, oy)
            return
        if self.phase == Phase.GAME_OVER:
            self._draw_game_over(ox, oy)
            return
        if self.phase == Phase.WAVE_CLEAR:
            self._draw_wave_clear(ox, oy)
            return

        # Starfield
        for sx, sy in STARS:
            pyxel.pset(sx, sy, pyxel.COLOR_GRAY if (sx + sy) % 3 == 0
                       else pyxel.COLOR_NAVY)

        # Player
        px = self.player_x + ox
        py = SCREEN_H - 20 + oy
        player_color = pyxel.COLOR_YELLOW if self.pierce_ready \
            else pyxel.COLOR_LIME
        pw2 = PLAYER_W // 2
        pyxel.tri(px, py - 12, px - pw2, py, px + pw2, py, player_color)
        pyxel.rect(px - pw2, py, pw2 * 2, 4, pyxel.COLOR_CYAN)

        # Bullets
        for b in self.bullets:
            bx = int(b.x + ox)
            by = int(b.y + oy)
            if b.pierce:
                pyxel.rect(bx - 2, by - 6, 4, 12, pyxel.COLOR_YELLOW)
                pyxel.rect(bx - 1, by - 7, 2, 14, pyxel.COLOR_WHITE)
            else:
                pyxel.rect(bx - 1, by - 4, 2, 8, pyxel.COLOR_WHITE)

        # Enemies
        for e in self.enemies:
            if not e.alive:
                continue
            ex = int(e.x + ox)
            ey = int(e.y + oy)
            col = COLORS[e.color % len(COLORS)]
            ew2 = ENEMY_W // 2
            eh2 = ENEMY_H // 2
            if e.escaped:
                pyxel.rectb(ex - ew2 - 1, ey - eh2 - 1,
                            ENEMY_W + 2, ENEMY_H + 2, col)
                pyxel.rect(ex - ew2, ey - eh2, ENEMY_W, ENEMY_H, col)
                if e.hp >= 2:
                    pyxel.rect(ex - 2, ey - eh2 - 4, 4, 3, pyxel.COLOR_WHITE)
            else:
                pyxel.rect(ex - ew2, ey - eh2, ENEMY_W, ENEMY_H, col)

        # Particles
        for p in self.particles:
            c = p.color if p.color < 16 else pyxel.COLOR_WHITE
            pyxel.pset(int(p.x + ox), int(p.y + oy), c)

        # Float texts
        for ft in self.float_texts:
            c = ft.color if ft.color < 16 else pyxel.COLOR_WHITE
            pyxel.text(int(ft.x + ox), int(ft.y + oy), ft.text, c)

        # HUD
        self._draw_hud(ox, oy)

    def _draw_hud(self, ox: int, oy: int) -> None:
        del ox, oy  # HUD is fixed, no shake
        pyxel.text(4, 2, f"SCORE:{self.score:>7}", pyxel.COLOR_WHITE)
        pyxel.text(4, 10, f"WAVE:{self.wave}", pyxel.COLOR_WHITE)
        pyxel.text(4, 18, f"HP:{'|' * self.hp}", pyxel.COLOR_RED)

        # Combo
        if self.combo >= 2:
            ccol = COLORS[self.combo_color % len(COLORS)]
            pyxel.text(SCREEN_W // 2 - 22, 2, f"COMBO x{self.combo}", ccol)

        # Pierce ready
        if self.pierce_ready:
            t = "PIERCE READY!"
            tw = len(t) * 4
            pyxel.text(SCREEN_W // 2 - tw // 2, SCREEN_H // 2 - 6, t,
                       pyxel.COLOR_YELLOW)

        # Heat bar
        bar_w = 40
        bar_h = 6
        bar_x = SCREEN_W - 46
        bar_y = 4
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, pyxel.COLOR_WHITE)
        fill_w = max(0, min(bar_w - 2, int((bar_w - 2) * self.heat / MAX_HEAT)))
        fill_col = pyxel.COLOR_RED if self.heat + 1 >= MAX_HEAT \
            else pyxel.COLOR_ORANGE
        pyxel.rect(bar_x + 1, bar_y + 1, fill_w, bar_h - 2, fill_col)
        pyxel.text(bar_x + bar_w + 2, bar_y + 1, "HEAT", pyxel.COLOR_WHITE)

    def _draw_title(self, ox: int, oy: int) -> None:
        del ox, oy
        pyxel.text(SCREEN_W // 2 - 48, 60, "CALAMITY SIEGE", pyxel.COLOR_YELLOW)
        pyxel.text(SCREEN_W // 2 - 56, 100,
                   "Contain the breach.", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 60, 120,
                   "Same-color kills build COMBO.", pyxel.COLOR_GRAY)
        pyxel.text(SCREEN_W // 2 - 48, 130,
                   "COMBO 5+ = PIERCE shot.", pyxel.COLOR_CYAN)
        pyxel.text(SCREEN_W // 2 - 52, 150,
                   "Enemies at bottom = ESCAPE!", pyxel.COLOR_RED)
        pyxel.text(SCREEN_W // 2 - 45, 190,
                   "SPACE to start", pyxel.COLOR_WHITE)

    def _draw_game_over(self, ox: int, oy: int) -> None:
        del ox, oy
        pyxel.text(SCREEN_W // 2 - 36, 80, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(SCREEN_W // 2 - 36, 100,
                   f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 40, 112,
                   f"WAVE: {self.wave}", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 44, 124,
                   f"MAX COMBO: {self.max_combo}", pyxel.COLOR_YELLOW)
        pyxel.text(SCREEN_W // 2 - 40, 180,
                   "R to retry", pyxel.COLOR_WHITE)

    def _draw_wave_clear(self, ox: int, oy: int) -> None:
        del ox, oy
        pyxel.text(SCREEN_W // 2 - 36, 80, "WAVE CLEAR!", pyxel.COLOR_LIME)
        pyxel.text(SCREEN_W // 2 - 56, 100,
                   f"Wave {self.wave} complete", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 48, 112,
                   f"Score: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 48, 180,
                   "SPACE to continue", pyxel.COLOR_WHITE)


# ═══════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    Game()
