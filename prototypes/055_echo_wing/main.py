"""ECHO WING — Side-scrolling shoot-em-up with color-match COMBO chains.

Reinterpreted from game_idea_factory #1 (Score 32.15):
  "log/replay as asset" → echo orbital follows ship, repeats movement
  "CA grid spread" → CHAIN BURST: BFS propagation through same-color enemies
  "one-color-per-turn" → weapon cycles through 4 colors

Core fun moment: building a 5+ COMBO chain and watching the BFS chain burst
cascade through an entire enemy formation in one explosive moment.
"""
from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import NamedTuple

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 256
SCREEN_H = 224
DISPLAY_SCALE = 2
FPS = 30
GAME_DURATION = 90  # seconds

# Player
PLAYER_X = 50
PLAYER_SPEED = 3
PLAYER_RADIUS = 8
FIRE_INTERVAL = 6  # frames
BULLET_SPEED = 6.0
BULLET_W = 8
BULLET_H = 4
INVINCIBLE_FRAMES = 40  # after taking damage

# Echo orbital
ECHO_DELAY = 15  # frames behind player
ECHO_FIRE_INTERVAL = 12

# Colors (Pyxel palette indices)
NUM_COLORS = 4
COLOR_IDS: tuple[int, int, int, int] = (
    pyxel.COLOR_RED,     # 0
    pyxel.COLOR_GREEN,   # 1
    pyxel.COLOR_CYAN,    # 2
    pyxel.COLOR_YELLOW,  # 3
)
COLOR_NAMES: tuple[str, str, str, str] = ("RED", "GREEN", "CYAN", "YELLOW")

# Enemy
ENEMY_RADIUS = 10
ENEMY_SPEED_BASE = 1.2
ENEMY_SPEED_MAX = 3.5
ENEMY_SPAWN_INTERVAL_INIT = 90
ENEMY_SPAWN_INTERVAL_MIN = 30

# COMBO
CHAIN_BURST_COMBO = 3
CHAIN_BURST_RADIUS = 45.0

# HEAT
MAX_HEAT = 100.0
HEAT_PER_BURST = 20.0
HEAT_PER_KILL = 2.0
HEAT_COOL_RATE = 0.3

# Scoring
BASE_SCORE = 100
COMBO_MULTIPLIER = 0.5  # score = BASE * (1 + combo * this)
BURST_BONUS = 50

# ── Data Classes ────────────────────────────────────────────────────────


class Phase(Enum):
    PLAYING = auto()
    GAME_OVER = auto()


class EnemyType(Enum):
    NORMAL = auto()    # 1 HP, straight line
    FAST = auto()      # 1 HP, faster, smaller
    TANK = auto()      # 3 HP, slower, bigger


@dataclass
class EnemyDef:
    hp: int
    radius: int
    speed_mult: float
    score_mult: float
    color_id: int


ENEMY_DEFS: dict[EnemyType, EnemyDef] = {
    EnemyType.NORMAL: EnemyDef(hp=1, radius=10, speed_mult=1.0, score_mult=1.0, color_id=0),
    EnemyType.FAST:   EnemyDef(hp=1, radius=7,  speed_mult=1.8, score_mult=1.5, color_id=1),
    EnemyType.TANK:   EnemyDef(hp=3, radius=12, speed_mult=0.6, score_mult=2.0, color_id=2),
}


@dataclass
class Enemy:
    x: float
    y: float
    color: int
    etype: EnemyType = EnemyType.NORMAL
    hp: int = 1
    radius: int = ENEMY_RADIUS
    speed: float = ENEMY_SPEED_BASE
    alive: bool = True
    flash_frames: int = 0  # hit flash

    @property
    def defn(self) -> EnemyDef:
        return ENEMY_DEFS[self.etype]


@dataclass
class Bullet:
    x: float
    y: float
    color: int
    speed: float = BULLET_SPEED
    hit: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    max_life: int = 0

    def __post_init__(self) -> None:
        if self.max_life == 0:
            self.max_life = self.life


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int
    vy: float = -1.5


class Pos(NamedTuple):
    x: float
    y: float


# ── Formation templates ─────────────────────────────────────────────────


class Formation(NamedTuple):
    name: str
    offsets: tuple[tuple[float, float], ...]  # relative to spawn position


FORMATIONS: tuple[Formation, ...] = (
    Formation("column", ((0, -30), (0, -15), (0, 0), (0, 15), (0, 30))),
    Formation("vshape", ((-10, -25), (-5, -12), (0, 0), (-5, 12), (-10, 25))),
    Formation("diagonal", ((-25, -25), (-15, -15), (-5, -5), (5, 5), (15, 15))),
    Formation("diamond", ((0, -20), (-15, 0), (0, 0), (15, 0), (0, 20))),
    Formation("wave", ((-20, -15), (-10, 10), (0, -10), (10, 15), (20, -5))),
)


# ── Game ────────────────────────────────────────────────────────────────


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="ECHO WING", fps=FPS, display_scale=DISPLAY_SCALE)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.frame = 0
        self.game_timer = GAME_DURATION * FPS
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.hp = 5
        self.max_hp = 5
        self.player_y = SCREEN_H / 2
        self.player_color = 0  # RED
        self.invincible = 0

        # Echo orbital state
        self.echo_positions: deque[float] = deque(maxlen=ECHO_DELAY)
        self.echo_fire_cooldown = 0
        for _ in range(ECHO_DELAY):
            self.echo_positions.append(self.player_y)

        # Firing
        self.fire_cooldown = 0

        # Entities
        self.enemies: list[Enemy] = []
        self.bullets: list[Bullet] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

        # Spawning
        self.spawn_timer = ENEMY_SPAWN_INTERVAL_INIT
        self.enemies_killed = 0
        self.burst_count = 0

        # Starfield background
        self.stars: list[list[float]] = []  # [x, y, speed]
        self._init_stars()

    def _init_stars(self) -> None:
        self.stars.clear()
        for _ in range(50):
            self.stars.append([
                self._rng.uniform(0, SCREEN_W),
                self._rng.uniform(0, SCREEN_H),
                self._rng.uniform(0.5, 2.5),
            ])

    # ── Update ─────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        self.frame += 1
        self.game_timer -= 1
        if self.game_timer <= 0 or self.hp <= 0:
            self.phase = Phase.GAME_OVER
            return

        self._update_player()
        self._update_weapon_cycle()
        self._update_echo_orbital()
        self._update_shooting()
        self._update_bullets()
        self._update_enemies()
        self._update_spawns()
        self._update_collisions()
        self._update_particles()
        self._update_floating_texts()
        self._update_heat()
        self._update_stars()

    def _update_player(self) -> None:
        dy = 0
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = PLAYER_SPEED
        self.player_y += dy
        self.player_y = max(16.0, min(float(SCREEN_H - 16), self.player_y))

        if self.invincible > 0:
            self.invincible -= 1

        # Record position for echo orbital
        self.echo_positions.append(self.player_y)

    def _update_weapon_cycle(self) -> None:
        if pyxel.btnp(pyxel.KEY_Q):
            self.player_color = (self.player_color - 1) % NUM_COLORS
        if pyxel.btnp(pyxel.KEY_E) or pyxel.btnp(pyxel.KEY_SPACE):
            self.player_color = (self.player_color + 1) % NUM_COLORS

    def _update_echo_orbital(self) -> None:
        if self.echo_fire_cooldown > 0:
            self.echo_fire_cooldown -= 1

    def _update_shooting(self) -> None:
        if self.heat >= MAX_HEAT:
            return
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
            return
        self.bullets.append(Bullet(PLAYER_X + 12, self.player_y - 1, self.player_color))
        self.fire_cooldown = FIRE_INTERVAL

        # Echo orbital fire
        if self.echo_fire_cooldown <= 0 and len(self.echo_positions) >= ECHO_DELAY:
            echo_y = self.echo_positions[0]
            self.bullets.append(Bullet(PLAYER_X + 12, echo_y - 1, self.player_color))
            self.echo_fire_cooldown = ECHO_FIRE_INTERVAL

    def _update_bullets(self) -> None:
        survivors: list[Bullet] = []
        for b in self.bullets:
            b.x += b.speed
            if b.x > SCREEN_W + 10 or b.hit:
                continue
            survivors.append(b)
        self.bullets = survivors

    def _update_enemies(self) -> None:
        speed_mult = 1.0 + self.enemies_killed * 0.003
        survivors: list[Enemy] = []
        for e in self.enemies:
            e.x -= e.speed * speed_mult
            if e.flash_frames > 0:
                e.flash_frames -= 1
            if e.x < -30 or (e.hp <= 0 and not e.alive):
                continue
            survivors.append(e)
        self.enemies = survivors

    def _update_spawns(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_formation()
            interval = max(ENEMY_SPAWN_INTERVAL_MIN,
                           ENEMY_SPAWN_INTERVAL_INIT - self.enemies_killed // 10)
            self.spawn_timer = interval

    def _spawn_formation(self) -> None:
        formation = self._rng.choice(FORMATIONS)
        base_y = self._rng.uniform(50, SCREEN_H - 50)
        spawn_x = SCREEN_W + 20

        for ox, oy in formation.offsets:
            etype = self._rng.choices(
                [EnemyType.NORMAL, EnemyType.FAST, EnemyType.TANK],
                weights=[60, 25, 15],
                k=1,
            )[0]
            defn = ENEMY_DEFS[etype]
            color = self._rng.randrange(NUM_COLORS)
            self.enemies.append(Enemy(
                x=spawn_x + ox,
                y=base_y + oy,
                color=color,
                etype=etype,
                hp=defn.hp,
                radius=defn.radius,
                speed=ENEMY_SPEED_BASE * defn.speed_mult,
            ))

    def _update_collisions(self) -> None:
        # Bullet-enemy collisions
        for b in self.bullets:
            if b.hit:
                continue
            for e in self.enemies:
                if not e.alive:
                    continue
                dist = math.hypot(b.x - e.x, b.y - e.y)
                if dist < e.radius + 4:
                    b.hit = True
                    self._hit_enemy(e, b.color)
                    break

        # Enemy-player collisions
        if self.invincible <= 0:
            for e in self.enemies:
                if not e.alive:
                    continue
                dist = math.hypot(PLAYER_X - e.x, self.player_y - e.y)
                if dist < e.radius + PLAYER_RADIUS:
                    self._hit_player()
                    e.alive = False
                    e.hp = 0
                    self._spawn_explosion(e.x, e.y, e.color, 8)
                    break

    def _hit_enemy(self, e: Enemy, bullet_color: int) -> None:
        e.hp -= 1
        e.flash_frames = 4
        if e.hp <= 0:
            self._kill_enemy(e, bullet_color)
        else:
            # Non-lethal hit
            self.particles.append(Particle(e.x, e.y, 0, 0, pyxel.COLOR_WHITE, 12))

    def _kill_enemy(self, e: Enemy, bullet_color: int) -> None:
        e.alive = False
        self.enemies_killed += 1

        # COMBO logic
        if bullet_color == e.color:
            self.combo += 1
        else:
            self.combo = 1  # reset on wrong-color kill

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        # Score
        kill_score = int(BASE_SCORE * (1 + (self.combo - 1) * COMBO_MULTIPLIER) * e.defn.score_mult)
        self.score += kill_score
        self.heat = min(MAX_HEAT, self.heat + HEAT_PER_KILL)

        # CHAIN BURST at combo >= threshold
        if self.combo >= CHAIN_BURST_COMBO and bullet_color == e.color:
            burst_kills = self._chain_burst(e.x, e.y, e.color)
            if burst_kills > 0:
                self.burst_count += 1
                burst_score = burst_kills * BURST_BONUS * self.combo
                self.score += burst_score
                self.heat = min(MAX_HEAT, self.heat + HEAT_PER_BURST)
                self.floating_texts.append(FloatingText(
                    e.x, e.y, f"BURST x{burst_kills}", pyxel.COLOR_YELLOW, 40,
                ))
                # Bigger explosion for burst
                self._spawn_explosion(e.x, e.y, e.color, 16)

        # Floating score text
        self.floating_texts.append(FloatingText(
            e.x, e.y, str(kill_score), COLOR_IDS[bullet_color], 25,
        ))

        if self.combo >= CHAIN_BURST_COMBO:
            self.floating_texts.append(FloatingText(
                e.x + 10, e.y - 8, f"x{self.combo}", pyxel.COLOR_ORANGE, 30, vy=-2.0,
            ))

        # Explosion
        self._spawn_explosion(e.x, e.y, COLOR_IDS[e.color], 10)

    def _chain_burst(self, cx: float, cy: float, color: int) -> int:
        """BFS through same-color enemies within radius."""
        visited: set[int] = set()
        queue: deque[int] = deque()
        alive_indices = [i for i, e in enumerate(self.enemies) if e.alive]

        # Find seed
        for i in alive_indices:
            e = self.enemies[i]
            if e.color == color and math.hypot(cx - e.x, cy - e.y) < CHAIN_BURST_RADIUS:
                queue.append(i)
                visited.add(i)

        kill_count = 0
        while queue:
            idx = queue.popleft()
            e = self.enemies[idx]
            if not e.alive:
                continue
            e.alive = False
            e.hp = 0
            kill_count += 1
            self.enemies_killed += 1
            self._spawn_explosion(e.x, e.y, COLOR_IDS[e.color], 6)

            # BFS: find adjacent same-color enemies
            for j in alive_indices:
                if j in visited:
                    continue
                other = self.enemies[j]
                if other.color == color and math.hypot(e.x - other.x, e.y - other.y) < CHAIN_BURST_RADIUS:
                    visited.add(j)
                    queue.append(j)

        return kill_count

    def _hit_player(self) -> None:
        self.hp -= 1
        self.invincible = INVINCIBLE_FRAMES
        self.combo = 0  # reset combo on hit
        # Screen shake equivalent: spawn particles
        for _ in range(15):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1, 3)
            self.particles.append(Particle(
                PLAYER_X, self.player_y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                pyxel.COLOR_WHITE, 20,
            ))

    def _spawn_explosion(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                color, 15,
            ))

    def _update_particles(self) -> None:
        survivors: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                survivors.append(p)
        self.particles = survivors

    def _update_floating_texts(self) -> None:
        survivors: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                survivors.append(ft)
        self.floating_texts = survivors

    def _update_heat(self) -> None:
        self.heat = max(0.0, min(MAX_HEAT, self.heat - HEAT_COOL_RATE))

    def _update_stars(self) -> None:
        for s in self.stars:
            s[0] -= s[2]
            if s[0] < -5:
                s[0] = SCREEN_W + 5
                s[1] = self._rng.uniform(0, SCREEN_H)

    # ── Draw ───────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        self._draw_stars()
        self._draw_enemies()
        self._draw_bullets()
        self._draw_player()
        self._draw_echo_orbital()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_stars(self) -> None:
        for s in self.stars:
            brightness = int(3 + s[2] * 2)
            col = brightness if brightness < 16 else 7
            pyxel.pset(int(s[0]), int(s[1]), col)

    def _draw_enemies(self) -> None:
        for e in self.enemies:
            if not e.alive:
                continue
            col = COLOR_IDS[e.color]
            # Flash white when hit
            draw_col = pyxel.COLOR_WHITE if e.flash_frames > 0 and e.flash_frames % 2 == 0 else col
            r = e.radius
            if e.etype == EnemyType.TANK:
                pyxel.circb(int(e.x), int(e.y), r, draw_col)
                pyxel.circb(int(e.x), int(e.y), r - 2, draw_col)
                # HP indicator for tanks
                if e.hp > 1:
                    pyxel.text(int(e.x) - 2, int(e.y) - 2, str(e.hp), pyxel.COLOR_WHITE)
            elif e.etype == EnemyType.FAST:
                pyxel.tri(
                    int(e.x - r), int(e.y),
                    int(e.x + r), int(e.y),
                    int(e.x), int(e.y - r),
                    draw_col,
                )
            else:
                pyxel.circ(int(e.x), int(e.y), r, draw_col)
                # Inner circle
                pyxel.circ(int(e.x), int(e.y), r - 3, pyxel.COLOR_BLACK)

    def _draw_bullets(self) -> None:
        for b in self.bullets:
            if b.hit:
                continue
            col = COLOR_IDS[b.color]
            pyxel.rect(int(b.x - BULLET_W / 2), int(b.y - BULLET_H / 2), BULLET_W, BULLET_H, col)

    def _draw_player(self) -> None:
        if self.invincible > 0 and self.invincible % 6 < 3:
            return  # blink when invincible
        px, py = PLAYER_X, int(self.player_y)
        col = COLOR_IDS[self.player_color]
        # Ship body
        pyxel.tri(px + 10, py, px - 4, py - 8, px - 4, py + 8, col)
        pyxel.tri(px + 6, py, px - 2, py - 5, px - 2, py + 5, col)
        # Engine glow
        glow_col = pyxel.COLOR_ORANGE if self.frame % 10 < 5 else pyxel.COLOR_YELLOW
        engine_size = 3 if self.heat < MAX_HEAT / 2 else 5
        pyxel.circ(px - 6, py, engine_size, glow_col)

    def _draw_echo_orbital(self) -> None:
        if len(self.echo_positions) < ECHO_DELAY:
            return
        echo_y = self.echo_positions[0]
        alpha_col = pyxel.COLOR_GRAY  # dim echo
        px = PLAYER_X
        py = int(echo_y)
        # Smaller, dimmer version of player
        pyxel.tri(px + 8, py, px - 3, py - 6, px - 3, py + 6, alpha_col)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / p.max_life
            col = p.color if alpha > 0.5 else pyxel.COLOR_GRAY
            size = max(1, int(alpha * 3))
            pyxel.pset(int(p.x), int(p.y), col)
            if size > 1:
                pyxel.pset(int(p.x) + 1, int(p.y), col)
                pyxel.pset(int(p.x), int(p.y) + 1, col)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 40 if ft.life < 40 else 1.0
            col = ft.color if alpha > 0.4 else pyxel.COLOR_GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, col)

    def _draw_hud(self) -> None:
        # Score
        pyxel.text(4, 4, f"SCORE:{self.score}", pyxel.COLOR_WHITE)
        # Combo
        if self.combo >= 2:
            combo_text = f"COMBO x{self.combo}"
            combo_col = pyxel.COLOR_ORANGE if self.combo >= CHAIN_BURST_COMBO else pyxel.COLOR_WHITE
            pyxel.text(4, 14, combo_text, combo_col)
        # HP bar
        hp_text = "|" * self.hp + "." * (self.max_hp - self.hp)
        pyxel.text(4, 24, f"HP:{hp_text}", pyxel.COLOR_RED if self.hp <= 2 else pyxel.COLOR_GREEN)
        # Heat bar
        bar_w = 60
        bar_x = SCREEN_W - bar_w - 8
        bar_y = 8
        pyxel.rectb(bar_x, bar_y, bar_w, 6, pyxel.COLOR_WHITE)
        heat_w = int(bar_w * self.heat / MAX_HEAT)
        heat_col = pyxel.COLOR_RED if self.heat > 70 else pyxel.COLOR_ORANGE if self.heat > 30 else pyxel.COLOR_GREEN
        if heat_w > 0:
            pyxel.rect(bar_x + 1, bar_y + 1, heat_w - 1, 4, heat_col)
        pyxel.text(bar_x - 30, bar_y - 1, "HEAT", pyxel.COLOR_WHITE)
        if self.heat >= MAX_HEAT:
            pyxel.text(bar_x + 10, bar_y + 1, "OVR", pyxel.COLOR_RED)
        # Timer
        time_left = max(0, self.game_timer // FPS)
        pyxel.text(SCREEN_W - 40, SCREEN_H - 12, f"T:{time_left}", pyxel.COLOR_WHITE)
        # Weapon color indicator
        color_name = COLOR_NAMES[self.player_color]
        pyxel.text(SCREEN_W // 2 - len(color_name) * 2, 4, color_name, COLOR_IDS[self.player_color])

    def _draw_game_over(self) -> None:
        # Title
        title = "ECHO WING"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 60, title, pyxel.COLOR_CYAN)
        # Score
        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 2, 80, score_text, pyxel.COLOR_WHITE)
        # Stats
        combo_text = f"MAX COMBO: {self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 95, combo_text, pyxel.COLOR_YELLOW)
        burst_text = f"BURSTS: {self.burst_count}"
        pyxel.text(SCREEN_W // 2 - len(burst_text) * 2, 108, burst_text, pyxel.COLOR_ORANGE)
        kills_text = f"KILLS: {self.enemies_killed}"
        pyxel.text(SCREEN_W // 2 - len(kills_text) * 2, 121, kills_text, pyxel.COLOR_GREEN)
        # Restart
        msg = "PRESS ENTER TO RETRY"
        col = pyxel.COLOR_WHITE if self.frame % 40 < 20 else pyxel.COLOR_GRAY
        pyxel.text(SCREEN_W // 2 - len(msg) * 2, 160, msg, col)


if __name__ == "__main__":
    Game()
