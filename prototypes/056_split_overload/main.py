"""SPLIT OVERLOAD - split-path power surge arena prototype.

Core fun moment:
Lure enemies close, spend stored charge, and watch three split lightning paths
collapse into a single high-damage convergence blast.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 3
FPS = 30
GAME_SECONDS = 90

PLAYER_RADIUS = 6
PLAYER_SPEED = 2.1
PLAYER_MAX_HP = 6
FIRE_INTERVAL = 13
BULLET_SPEED = 4.2
BULLET_DAMAGE = 8

ENEMY_RADIUS = 7
ENEMY_BASE_HP = 18
ENEMY_BASE_SPEED = 0.62
ENEMY_CONTACT_DAMAGE_COOLDOWN = 26
SPAWN_INTERVAL_START = 38
SPAWN_INTERVAL_MIN = 13

CHARGE_MAX = 100.0
OVERLOAD_COST = 55.0
OVERLOAD_HEAT = 26.0
HEAT_MAX = 100.0
HEAT_COOLING = 0.16
OVERLOAD_TARGETS = 3
SPLIT_PATH_FRAMES = 17
CONVERGE_DELAY = 8
CONVERGE_RADIUS = 42.0
CONVERGE_DAMAGE = 34
CONVERGE_CLOSE_BONUS = 28
CHAIN_RANGE = 34.0


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class EndReason(Enum):
    DEFEAT = auto()
    SURVIVED = auto()


@dataclass
class Player:
    x: float = SCREEN_W / 2
    y: float = SCREEN_H / 2
    hp: int = PLAYER_MAX_HP
    charge: float = 0.0
    heat: float = 0.0
    fire_cooldown: int = 0
    hit_cooldown: int = 0


@dataclass
class Enemy:
    x: float
    y: float
    hp: int
    speed: float
    radius: int = ENEMY_RADIUS
    hot: bool = False


@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    damage: int = BULLET_DAMAGE


@dataclass
class SplitPath:
    sx: float
    sy: float
    tx: float
    ty: float
    age: int = 0
    max_age: int = SPLIT_PATH_FRAMES


@dataclass
class Convergence:
    x: float
    y: float
    radius: float
    damage: int
    delay: int = CONVERGE_DELAY
    life: int = 16
    resolved: bool = False


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
    color: int
    life: int = 24
    vy: float = -0.65


@dataclass(frozen=True)
class OverloadPlan:
    targets: tuple[Enemy, ...]
    center_x: float
    center_y: float
    radius: float
    damage: int


class GameState:
    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.end_reason = EndReason.DEFEAT
        self.player = Player()
        self.enemies: list[Enemy] = []
        self.bullets: list[Bullet] = []
        self.split_paths: list[SplitPath] = []
        self.convergences: list[Convergence] = []
        self.particles: list[Particle] = []
        self.floaters: list[FloatingText] = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.wave = 1
        self.frame = 0
        self.time_left = GAME_SECONDS * FPS
        self.spawn_timer = SPAWN_INTERVAL_START
        self.overload_count = 0
        self.kills = 0
        self.screen_flash = 0

    def start(self) -> None:
        self.reset()
        self.phase = Phase.PLAYING

    def step(self, move_x: float, move_y: float, fire_overload: bool) -> None:
        if self.phase != Phase.PLAYING:
            return

        self.frame += 1
        self.time_left -= 1
        self.wave = 1 + self.frame // (FPS * 18)
        self._move_player(move_x, move_y)
        self._cool_player()
        self._auto_fire()
        self._spawn_enemy()
        self._update_bullets()
        self._update_enemies()
        self._update_overload()
        self._update_effects()
        if fire_overload:
            self.trigger_overload()

        if self.player.hp <= 0:
            self.player.hp = 0
            self.end_reason = EndReason.DEFEAT
            self.phase = Phase.GAME_OVER
        elif self.time_left <= 0:
            self.end_reason = EndReason.SURVIVED
            self.phase = Phase.GAME_OVER

    def _move_player(self, move_x: float, move_y: float) -> None:
        length = math.hypot(move_x, move_y)
        if length > 0:
            move_x /= length
            move_y /= length
        self.player.x = clamp(self.player.x + move_x * PLAYER_SPEED, PLAYER_RADIUS, SCREEN_W - PLAYER_RADIUS)
        self.player.y = clamp(self.player.y + move_y * PLAYER_SPEED, 26 + PLAYER_RADIUS, SCREEN_H - PLAYER_RADIUS)

    def _cool_player(self) -> None:
        self.player.heat = max(0.0, self.player.heat - HEAT_COOLING)
        self.player.fire_cooldown = max(0, self.player.fire_cooldown - 1)
        self.player.hit_cooldown = max(0, self.player.hit_cooldown - 1)
        self.screen_flash = max(0, self.screen_flash - 1)

    def _auto_fire(self) -> None:
        if self.player.fire_cooldown > 0 or self.player.heat >= HEAT_MAX:
            return
        target = self.nearest_enemy()
        if target is None:
            return
        dx = target.x - self.player.x
        dy = target.y - self.player.y
        dist = max(1.0, math.hypot(dx, dy))
        self.bullets.append(Bullet(self.player.x, self.player.y, dx / dist * BULLET_SPEED, dy / dist * BULLET_SPEED))
        heat_factor = self.player.heat / HEAT_MAX
        self.player.fire_cooldown = max(6, int(FIRE_INTERVAL - heat_factor * 5))
        self.player.heat += 0.9

    def _spawn_enemy(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer > 0:
            return

        interval = max(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_START - self.wave * 4)
        self.spawn_timer = interval
        side = self.rng.randrange(4)
        margin = 12
        if side == 0:
            x, y = -margin, self.rng.uniform(32, SCREEN_H - margin)
        elif side == 1:
            x, y = SCREEN_W + margin, self.rng.uniform(32, SCREEN_H - margin)
        elif side == 2:
            x, y = self.rng.uniform(margin, SCREEN_W - margin), 20
        else:
            x, y = self.rng.uniform(margin, SCREEN_W - margin), SCREEN_H + margin

        hp = ENEMY_BASE_HP + self.wave * 3
        speed = ENEMY_BASE_SPEED + self.wave * 0.045 + self.rng.uniform(-0.05, 0.12)
        self.enemies.append(Enemy(x, y, hp, speed))

    def _update_bullets(self) -> None:
        live: list[Bullet] = []
        for bullet in self.bullets:
            bullet.x += bullet.vx
            bullet.y += bullet.vy
            if not (-8 <= bullet.x <= SCREEN_W + 8 and 18 <= bullet.y <= SCREEN_H + 8):
                continue
            hit = self._bullet_hit_enemy(bullet)
            if not hit:
                live.append(bullet)
        self.bullets = live

    def _bullet_hit_enemy(self, bullet: Bullet) -> bool:
        for enemy in self.enemies:
            if distance(enemy.x, enemy.y, bullet.x, bullet.y) <= enemy.radius + 2:
                enemy.hp -= bullet.damage
                enemy.hot = True
                self._spark(bullet.x, bullet.y, pyxel.COLOR_CYAN, 4)
                if enemy.hp <= 0:
                    self._kill_enemy(enemy, 1, "zap")
                return True
        return False

    def _update_enemies(self) -> None:
        for enemy in self.enemies:
            dx = self.player.x - enemy.x
            dy = self.player.y - enemy.y
            dist = max(1.0, math.hypot(dx, dy))
            enemy.x += dx / dist * enemy.speed
            enemy.y += dy / dist * enemy.speed
            if dist <= enemy.radius + PLAYER_RADIUS and self.player.hit_cooldown == 0:
                self.player.hp -= 1
                self.player.hit_cooldown = ENEMY_CONTACT_DAMAGE_COOLDOWN
                self.combo = 0
                self.floaters.append(FloatingText(self.player.x - 10, self.player.y - 12, "HIT", pyxel.COLOR_RED))
                self._spark(self.player.x, self.player.y, pyxel.COLOR_RED, 12)
        self.enemies = [enemy for enemy in self.enemies if enemy.hp > 0]

    def can_overload(self) -> bool:
        return self.player.charge >= OVERLOAD_COST and self.player.heat <= HEAT_MAX - OVERLOAD_HEAT

    def plan_overload(self) -> OverloadPlan | None:
        if not self.enemies:
            return None
        targets = sorted(self.enemies, key=lambda e: distance(self.player.x, self.player.y, e.x, e.y))[:OVERLOAD_TARGETS]
        if len(targets) < 2:
            return None
        center_x = sum(enemy.x for enemy in targets) / len(targets)
        center_y = sum(enemy.y for enemy in targets) / len(targets)
        spread = max(distance(center_x, center_y, enemy.x, enemy.y) for enemy in targets)
        tightness = max(0.0, 1.0 - spread / 90.0)
        radius = CONVERGE_RADIUS + tightness * 18.0
        damage = CONVERGE_DAMAGE + int(tightness * CONVERGE_CLOSE_BONUS)
        return OverloadPlan(tuple(targets), center_x, center_y, radius, damage)

    def trigger_overload(self) -> bool:
        if not self.can_overload():
            return False
        plan = self.plan_overload()
        if plan is None:
            return False

        self.player.charge -= OVERLOAD_COST
        self.player.heat += OVERLOAD_HEAT
        self.overload_count += 1
        for target in plan.targets:
            self.split_paths.append(SplitPath(self.player.x, self.player.y, target.x, target.y))
            target.hp -= 10
            target.hot = True
        self.convergences.append(Convergence(plan.center_x, plan.center_y, plan.radius, plan.damage))
        self.floaters.append(FloatingText(plan.center_x - 25, plan.center_y - 18, "SPLIT", pyxel.COLOR_YELLOW))
        self._spark(self.player.x, self.player.y, pyxel.COLOR_YELLOW, 10)
        return True

    def _update_overload(self) -> None:
        for path in self.split_paths:
            path.age += 1
        self.split_paths = [path for path in self.split_paths if path.age <= path.max_age]

        for convergence in self.convergences:
            if convergence.delay > 0:
                convergence.delay -= 1
                continue
            if not convergence.resolved:
                self._resolve_convergence(convergence)
                convergence.resolved = True
            convergence.life -= 1
        self.convergences = [conv for conv in self.convergences if conv.life > 0]

    def _resolve_convergence(self, convergence: Convergence) -> None:
        primary = [
            enemy
            for enemy in self.enemies
            if distance(convergence.x, convergence.y, enemy.x, enemy.y) <= convergence.radius
        ]
        chain = self._chain_targets(primary)
        if not chain:
            self.floaters.append(FloatingText(convergence.x - 12, convergence.y, "MISS", pyxel.COLOR_GRAY))
            return
        for enemy in chain:
            enemy.hp -= convergence.damage
            enemy.hot = True
            if enemy.hp <= 0:
                self._kill_enemy(enemy, 2 + len(chain) // 2, "boom")
        self.screen_flash = 3
        self.combo += len(chain)
        self.max_combo = max(self.max_combo, self.combo)
        self.score += 40 * len(chain) * max(1, self.combo)
        self.floaters.append(FloatingText(convergence.x - 24, convergence.y - 6, f"x{len(chain)} JOIN", pyxel.COLOR_YELLOW))
        self._spark(convergence.x, convergence.y, pyxel.COLOR_YELLOW, 22)

    def _chain_targets(self, seeds: list[Enemy]) -> list[Enemy]:
        chained: list[Enemy] = []
        frontier = list(seeds)
        while frontier:
            current = frontier.pop()
            if current in chained:
                continue
            chained.append(current)
            for enemy in self.enemies:
                if enemy not in chained and distance(current.x, current.y, enemy.x, enemy.y) <= CHAIN_RANGE:
                    frontier.append(enemy)
        return chained

    def _kill_enemy(self, enemy: Enemy, multiplier: int, label: str) -> None:
        if enemy.hp > 0:
            return
        self.kills += 1
        self.combo = max(1, self.combo + 1)
        self.max_combo = max(self.max_combo, self.combo)
        gained = 35 * multiplier * max(1, self.combo)
        self.score += gained
        self.player.charge = min(CHARGE_MAX, self.player.charge + 8 + multiplier * 2)
        self.floaters.append(FloatingText(enemy.x - 8, enemy.y - 6, f"+{gained}", pyxel.COLOR_WHITE))
        self._spark(enemy.x, enemy.y, pyxel.COLOR_ORANGE if label == "boom" else pyxel.COLOR_CYAN, 9)

    def _update_effects(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]
        for f in self.floaters:
            f.y += f.vy
            f.life -= 1
        self.floaters = [f for f in self.floaters if f.life > 0]

    def _spark(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(0.5, 2.4)
            self.particles.append(Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, self.rng.randint(9, 19), color))

    def nearest_enemy(self) -> Enemy | None:
        if not self.enemies:
            return None
        return min(self.enemies, key=lambda e: distance(self.player.x, self.player.y, e.x, e.y))


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SPLIT OVERLOAD", fps=FPS, display_scale=DISPLAY_SCALE)
        pyxel.mouse(False)
        self.state = GameState()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        if self.state.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.state.start()
            return
        if self.state.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_R):
                self.state.start()
            return

        move_x = float((pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D)) - (pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A)))
        move_y = float((pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S)) - (pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W)))
        self.state.step(move_x, move_y, pyxel.btnp(pyxel.KEY_SPACE))

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_NAVY if self.state.screen_flash == 0 else pyxel.COLOR_DARK_BLUE)
        if self.state.phase == Phase.TITLE:
            self._draw_title()
        elif self.state.phase == Phase.PLAYING:
            self._draw_playing()
        else:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(103, 58, "SPLIT OVERLOAD", pyxel.COLOR_YELLOW)
        pyxel.text(67, 86, "lure enemies, split the surge,", pyxel.COLOR_WHITE)
        pyxel.text(78, 98, "then join paths for a blast", pyxel.COLOR_WHITE)
        pyxel.text(76, 126, "ARROWS / WASD : MOVE", pyxel.COLOR_CYAN)
        pyxel.text(76, 138, "SPACE         : SPLIT OVERLOAD", pyxel.COLOR_CYAN)
        pyxel.text(76, 150, "ENTER         : START", pyxel.COLOR_CYAN)
        pyxel.text(58, 184, "Close enemy clusters make stronger blasts.", pyxel.COLOR_GRAY)

    def _draw_playing(self) -> None:
        self._draw_grid()
        for conv in self.state.convergences:
            color = pyxel.COLOR_YELLOW if conv.delay == 0 else pyxel.COLOR_ORANGE
            pyxel.circb(int(conv.x), int(conv.y), int(conv.radius), color)
            pyxel.circ(int(conv.x), int(conv.y), 3 + max(0, conv.life // 4), color)
        for path in self.state.split_paths:
            t = min(1.0, path.age / path.max_age)
            mx = path.sx + (path.tx - path.sx) * t
            my = path.sy + (path.ty - path.sy) * t
            pyxel.line(int(path.sx), int(path.sy), int(mx), int(my), pyxel.COLOR_YELLOW)
            pyxel.circ(int(mx), int(my), 2, pyxel.COLOR_WHITE)
        for bullet in self.state.bullets:
            pyxel.circ(int(bullet.x), int(bullet.y), 2, pyxel.COLOR_CYAN)
        for enemy in self.state.enemies:
            color = pyxel.COLOR_ORANGE if enemy.hot else pyxel.COLOR_RED
            pyxel.circ(int(enemy.x), int(enemy.y), enemy.radius, pyxel.COLOR_BROWN)
            pyxel.circ(int(enemy.x), int(enemy.y), max(2, int(enemy.radius * enemy.hp / (ENEMY_BASE_HP + self.state.wave * 3))), color)
        for p in self.state.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)
        player_color = pyxel.COLOR_WHITE if self.state.player.hit_cooldown % 6 < 3 else pyxel.COLOR_CYAN
        pyxel.circ(int(self.state.player.x), int(self.state.player.y), PLAYER_RADIUS, player_color)
        pyxel.circb(int(self.state.player.x), int(self.state.player.y), 13, pyxel.COLOR_CYAN if self.state.can_overload() else pyxel.COLOR_GRAY)
        for f in self.state.floaters:
            pyxel.text(int(f.x), int(f.y), f.text, f.color)
        self._draw_hud()

    def _draw_grid(self) -> None:
        for x in range(0, SCREEN_W, 32):
            pyxel.line(x, 24, x, SCREEN_H, pyxel.COLOR_DARK_BLUE)
        for y in range(32, SCREEN_H, 32):
            pyxel.line(0, y, SCREEN_W, y, pyxel.COLOR_DARK_BLUE)

    def _draw_hud(self) -> None:
        s = self.state
        pyxel.rect(0, 0, SCREEN_W, 24, pyxel.COLOR_BLACK)
        pyxel.text(5, 5, f"SCORE {s.score}", pyxel.COLOR_WHITE)
        pyxel.text(86, 5, f"HP {s.player.hp}", pyxel.COLOR_RED)
        pyxel.text(126, 5, f"COMBO {s.combo}", pyxel.COLOR_YELLOW)
        pyxel.text(194, 5, f"TIME {max(0, s.time_left // FPS):02}", pyxel.COLOR_WHITE)
        self._bar(5, 15, 88, 5, s.player.charge / CHARGE_MAX, pyxel.COLOR_CYAN, "CHG")
        self._bar(107, 15, 88, 5, s.player.heat / HEAT_MAX, pyxel.COLOR_ORANGE, "HEAT")
        ready = "READY" if s.can_overload() else "WAIT"
        pyxel.text(238, 15, f"SPACE {ready}", pyxel.COLOR_YELLOW if s.can_overload() else pyxel.COLOR_GRAY)

    def _bar(self, x: int, y: int, w: int, h: int, ratio: float, color: int, label: str) -> None:
        pyxel.rectb(x, y, w, h, pyxel.COLOR_GRAY)
        pyxel.rect(x + 1, y + 1, int((w - 2) * clamp(ratio, 0.0, 1.0)), h - 2, color)
        pyxel.text(x + w + 3, y - 1, label, color)

    def _draw_game_over(self) -> None:
        title = "SURVIVED" if self.state.end_reason == EndReason.SURVIVED else "CORE LOST"
        color = pyxel.COLOR_YELLOW if self.state.end_reason == EndReason.SURVIVED else pyxel.COLOR_RED
        pyxel.text(134, 56, title, color)
        pyxel.text(108, 88, f"SCORE      {self.state.score}", pyxel.COLOR_WHITE)
        pyxel.text(108, 102, f"KILLS      {self.state.kills}", pyxel.COLOR_WHITE)
        pyxel.text(108, 116, f"MAX COMBO  {self.state.max_combo}", pyxel.COLOR_WHITE)
        pyxel.text(108, 130, f"OVERLOADS  {self.state.overload_count}", pyxel.COLOR_WHITE)
        pyxel.text(92, 166, "ENTER / R : RETRY", pyxel.COLOR_CYAN)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def distance(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


if __name__ == "__main__":
    Game()
