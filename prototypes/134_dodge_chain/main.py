"""DODGE CHAIN — Top-down dodgeball arena game.

Core mechanic: dodge enemy throws, collect echo trails for power-ups,
build combo chains with same-color hits, and unleash SUPER THROW.

Most fun moment: barely dodging an enemy ball, collecting the echo trail,
and unleashing a powered-up SUPER THROW to wipe out all opponents.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
import math
import random

import pyxel


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCREEN_W = 320
SCREEN_H = 240
ARENA_LEFT = 16
ARENA_TOP = 40
ARENA_RIGHT = 304
ARENA_BOTTOM = 224
NUM_COLORS = 4
GAME_TIME = 90 * 60
SUPER_DURATION = 5 * 60
MAX_HEAT = 100
MAX_STAMINA = 100
THROW_STAMINA_COST = 15
ECHO_DURATION = 120
COMBO_THRESHOLD = 5
INITIAL_OPPONENTS = 3
MAX_OPPONENTS = 8
NEAR_MISS_RADIUS = 20.0
STAMINA_REGEN_RATE = 0.15
ECHO_STAMINA_BONUS = 30
ECHO_DAMAGE_MULTIPLIER = 2
PLAYER_RADIUS = 6.0
PLAYER_SPEED = 1.8
OPPONENT_RADIUS = 7.0
OPPONENT_SPEED = 1.2
BALL_RADIUS = 3.0
BALL_SPEED = 3.5
BALL_LIFE = 300
OPPONENT_BALL_SPEED = 2.5
PARTICLE_COUNT_HIT = 8
PARTICLE_COUNT_COMBO = 4
PARTICLE_COUNT_SUPER = 20
PARTICLE_COUNT_ECHO = 5
FLOATING_TEXT_LIFE = 30

BALL_COLORS = [8, 3, 6, 10]  # RED, GREEN, LIGHT_BLUE, YELLOW
COLOR_NAMES = ["RED", "GRN", "BLU", "YEL"]


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Player:
    x: float
    y: float
    radius: float = PLAYER_RADIUS
    speed: float = PLAYER_SPEED
    color: int = 0
    color_timer: int = 120
    hit_flash: int = 0


@dataclass
class Opponent:
    x: float
    y: float
    radius: float = OPPONENT_RADIUS
    color: int = 0
    hp: int = 1
    throw_cooldown: int = 0
    score_value: int = 100
    alive: bool = True
    speed: float = OPPONENT_SPEED


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    owner_is_player: bool = True
    damage: int = 1
    life: int = BALL_LIFE
    radius: float = BALL_RADIUS
    echo_spawned: bool = False


@dataclass
class EchoTrail:
    x: float
    y: float
    life: int
    color: int


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
    vy: float = -1.0


# ---------------------------------------------------------------------------
# Game class
# ---------------------------------------------------------------------------

class Game:
    """Main game class for DODGE CHAIN."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="DODGE CHAIN", display_scale=2)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ---- State reset ----

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.stamina: float = float(MAX_STAMINA)
        self.game_timer: int = GAME_TIME
        self.super_timer: int = 0
        self.super_active: bool = False
        self.player: Player = Player(
            x=SCREEN_W / 2.0,
            y=(ARENA_TOP + ARENA_BOTTOM) / 2.0,
        )
        self.opponents: list[Opponent] = []
        self.balls: list[Ball] = []
        self.echoes: list[EchoTrail] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.next_opponent_spawn: int = 0
        self.shake_frames: int = 0
        self.echo_bonus: bool = False
        self._rng = random.Random()

    # ---- Update dispatch ----

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()
        self._update_particles()
        self._update_floating_texts()

    # ---- Draw dispatch ----

    def draw(self) -> None:
        pyxel.cls(0)
        if self.shake_frames > 0:
            ox = self._rng.randint(-2, 2)
            oy = self._rng.randint(-2, 2)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        pyxel.camera(0, 0)

    # ---- Title screen ----

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _start_game(self) -> None:
        self.reset()
        self.phase = Phase.PLAYING
        for _ in range(INITIAL_OPPONENTS):
            self.opponents.append(self._spawn_opponent())
        self.next_opponent_spawn = 15 * 60

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 42, 50, "DODGE CHAIN", 7)
        pyxel.text(SCREEN_W // 2 - 55, 75, "Click or ENTER to start", 7)
        pyxel.text(SCREEN_W // 2 - 58, 105, "WASD: Move", 13)
        pyxel.text(SCREEN_W // 2 - 58, 117, "Mouse: Aim / Click: Throw", 13)
        pyxel.text(SCREEN_W // 2 - 58, 129, "Wheel: Change Color", 13)
        pyxel.text(SCREEN_W // 2 - 48, 150, "Dodge -> Echo -> POWER!", 15)
        bx = SCREEN_W // 2 + 60
        by = 120 + int(math.sin(pyxel.frame_count * 0.1) * 8)
        for i in range(4):
            pyxel.circ(bx - 12 + i * 8, by, 3, BALL_COLORS[i])

    # ---- Playing phase ----

    def _update_playing(self) -> None:
        # --- Input handling (pyxel-dependent) ---
        dx = 0.0
        dy = 0.0
        if pyxel.btn(pyxel.KEY_W) or pyxel.btn(pyxel.KEY_UP):
            dy = -1.0
        if pyxel.btn(pyxel.KEY_S) or pyxel.btn(pyxel.KEY_DOWN):
            dy = 1.0
        if pyxel.btn(pyxel.KEY_A) or pyxel.btn(pyxel.KEY_LEFT):
            dx = -1.0
        if pyxel.btn(pyxel.KEY_D) or pyxel.btn(pyxel.KEY_RIGHT):
            dx = 1.0
        self._move_player(dx, dy)

        if pyxel.mouse_wheel != 0:
            self._cycle_player_color(pyxel.mouse_wheel > 0)

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            tx, ty = float(pyxel.mouse_x), float(pyxel.mouse_y)
            if self.super_active:
                nearest = self._nearest_opponent()
                if nearest is not None:
                    tx, ty = nearest.x, nearest.y
            ball = self._throw_ball(tx, ty)
            if ball is not None:
                self.balls.append(ball)

        # --- Core logic (pyxel-free) ---
        self._update_balls()
        self._update_opponents()
        self._update_echoes()
        self._check_echo_collect()

        damage = self._check_player_hit()
        if damage > 0:
            self.heat = min(float(MAX_HEAT), self.heat + 15.0)
            self._spawn_particles(self.player.x, self.player.y, 8, 10)
            self._spawn_floating_text(self.player.x, self.player.y - 15, "OUCH!", 8)
            self.shake_frames = 10
            self.player.hit_flash = 8

        hit_opponents = self._check_opponent_hits()
        for opp, ball in hit_opponents:
            self._resolve_hit(opp, ball)

        for ball in self.balls:
            if not ball.owner_is_player and not ball.echo_spawned:
                dist = math.hypot(ball.x - self.player.x, ball.y - self.player.y)
                if dist < NEAR_MISS_RADIUS:
                    self._spawn_echo(self.player.x, self.player.y, ball.color)
                    ball.echo_spawned = True

        self._update_timers()

        if self.game_timer > 0:
            self.next_opponent_spawn -= 1
            alive_count = sum(1 for o in self.opponents if o.alive)
            if self.next_opponent_spawn <= 0 and alive_count < MAX_OPPONENTS:
                self.opponents.append(self._spawn_opponent())
                self.next_opponent_spawn = 15 * 60

            if alive_count == 0:
                for _ in range(min(INITIAL_OPPONENTS, MAX_OPPONENTS)):
                    self.opponents.append(self._spawn_opponent())
                self.next_opponent_spawn = 15 * 60

        if self.stamina < MAX_STAMINA:
            self.stamina = min(float(MAX_STAMINA), self.stamina + STAMINA_REGEN_RATE)

        if self.shake_frames > 0:
            self.shake_frames -= 1
        if self.player.hit_flash > 0:
            self.player.hit_flash -= 1

        if self._check_game_over():
            self.phase = Phase.GAME_OVER

    # ---- Game over screen ----

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 32, 80, "GAME OVER", 7)
        pyxel.text(SCREEN_W // 2 - 40, 100, f"Score: {self.score}", 7)
        pyxel.text(SCREEN_W // 2 - 42, 115, f"Max Combo: {self.max_combo}", 10)
        if self.heat >= MAX_HEAT:
            pyxel.text(SCREEN_W // 2 - 38, 135, "Overheated!", 8)
        else:
            pyxel.text(SCREEN_W // 2 - 42, 135, "Time's up!", 12)
        pyxel.text(SCREEN_W // 2 - 55, 165, "Click or ENTER to retry", 7)

    # ---- Core logic methods (testable, no pyxel) ----

    def _spawn_opponent(self) -> Opponent:
        """Spawn an opponent at a random arena edge, avoiding player position."""
        for _ in range(100):
            side = self._rng.randint(0, 3)
            if side == 0:
                x = self._rng.uniform(ARENA_LEFT + 20, ARENA_RIGHT - 20)
                y = float(ARENA_TOP + 10)
            elif side == 1:
                x = self._rng.uniform(ARENA_LEFT + 20, ARENA_RIGHT - 20)
                y = float(ARENA_BOTTOM - 10)
            elif side == 2:
                x = float(ARENA_LEFT + 10)
                y = self._rng.uniform(ARENA_TOP + 20, ARENA_BOTTOM - 20)
            else:
                x = float(ARENA_RIGHT - 10)
                y = self._rng.uniform(ARENA_TOP + 20, ARENA_BOTTOM - 20)

            if math.hypot(x - self.player.x, y - self.player.y) > 60:
                color = self._rng.randint(0, NUM_COLORS - 1)
                base_cd = max(60, 150 - self._difficulty_bonus())
                cooldown = self._rng.randint(base_cd - 20, base_cd + 20)
                speed = OPPONENT_SPEED + self._difficulty_speed_bonus()
                return Opponent(x=x, y=y, color=color, throw_cooldown=cooldown, speed=speed)

        return Opponent(
            x=float(ARENA_LEFT + 40), y=float(ARENA_TOP + 40),
            color=0, throw_cooldown=120, speed=OPPONENT_SPEED,
        )

    def _difficulty_bonus(self) -> int:
        """Return cooldown reduction based on remaining time."""
        remaining_secs = self.game_timer / 60
        if remaining_secs <= 30:
            return 50
        if remaining_secs <= 60:
            return 20
        return 0

    def _difficulty_speed_bonus(self) -> float:
        """Return speed bonus for opponents based on remaining time."""
        remaining_secs = self.game_timer / 60
        if remaining_secs <= 30:
            return 0.6
        if remaining_secs <= 60:
            return 0.3
        return 0.0

    def _nearest_opponent(self) -> Opponent | None:
        """Return the nearest alive opponent, or None."""
        best: Opponent | None = None
        best_dist = float("inf")
        for opp in self.opponents:
            if not opp.alive:
                continue
            dist = math.hypot(opp.x - self.player.x, opp.y - self.player.y)
            if dist < best_dist:
                best_dist = dist
                best = opp
        return best

    def _throw_ball(self, tx: float, ty: float) -> Ball | None:
        """Player throws a ball toward (tx, ty). Returns None if insufficient stamina."""
        stamina_cost = 0 if self.super_active else THROW_STAMINA_COST
        if self.stamina < stamina_cost:
            return None

        self.stamina -= stamina_cost

        dx = tx - self.player.x
        dy = ty - self.player.y
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            dx, dy = 0.0, -1.0
            dist = 1.0
        speed = BALL_SPEED
        vx = dx / dist * speed
        vy = dy / dist * speed

        color = -1 if self.super_active else self.player.color
        damage = 1
        if self.echo_bonus:
            damage *= ECHO_DAMAGE_MULTIPLIER
            self.echo_bonus = False

        return Ball(
            x=self.player.x, y=self.player.y,
            vx=vx, vy=vy,
            color=color,
            owner_is_player=True,
            damage=damage,
        )

    def _opponent_throw(self, opp: Opponent) -> Ball:
        """Opponent throws a ball toward the player with some inaccuracy."""
        dx = self.player.x - opp.x
        dy = self.player.y - opp.y
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            dx, dy = 0.0, -1.0
            dist = 1.0
        angle_offset = self._rng.uniform(-0.3, 0.3)
        angle = math.atan2(dy, dx) + angle_offset
        speed = OPPONENT_BALL_SPEED + self._difficulty_speed_bonus() * 0.5
        return Ball(
            x=opp.x, y=opp.y,
            vx=math.cos(angle) * speed,
            vy=math.sin(angle) * speed,
            color=opp.color,
            owner_is_player=False,
            damage=1,
        )

    def _move_player(self, dx: float, dy: float) -> None:
        """Move player within arena bounds."""
        if dx != 0.0 and dy != 0.0:
            mag = math.hypot(dx, dy)
            dx /= mag
            dy /= mag
        self.player.x += dx * self.player.speed
        self.player.y += dy * self.player.speed
        self.player.x = max(
            ARENA_LEFT + self.player.radius,
            min(ARENA_RIGHT - self.player.radius, self.player.x),
        )
        self.player.y = max(
            ARENA_TOP + self.player.radius,
            min(ARENA_BOTTOM - self.player.radius, self.player.y),
        )

    def _update_balls(self) -> None:
        """Move all balls, bounce off arena walls, remove expired. Reset combo on miss."""
        alive: list[Ball] = []
        for ball in self.balls:
            ball.x += ball.vx
            ball.y += ball.vy
            ball.life -= 1

            if ball.x - ball.radius < ARENA_LEFT:
                ball.x = ARENA_LEFT + ball.radius
                ball.vx = abs(ball.vx)
            elif ball.x + ball.radius > ARENA_RIGHT:
                ball.x = ARENA_RIGHT - ball.radius
                ball.vx = -abs(ball.vx)

            if ball.y - ball.radius < ARENA_TOP:
                ball.y = ARENA_TOP + ball.radius
                ball.vy = abs(ball.vy)
            elif ball.y + ball.radius > ARENA_BOTTOM:
                ball.y = ARENA_BOTTOM - ball.radius
                ball.vy = -abs(ball.vy)

            if ball.life <= 0:
                if ball.owner_is_player and ball.color != -1:
                    self.combo = 0
                continue

            alive.append(ball)
        self.balls = alive

    def _check_player_hit(self) -> int:
        """Check if any opponent ball hits the player. Return total damage."""
        total_damage = 0
        surviving: list[Ball] = []
        for ball in self.balls:
            if ball.owner_is_player:
                surviving.append(ball)
                continue
            dist = math.hypot(ball.x - self.player.x, ball.y - self.player.y)
            if dist < self.player.radius + ball.radius:
                total_damage += ball.damage
            else:
                surviving.append(ball)
        self.balls = surviving
        return total_damage

    def _check_opponent_hits(self) -> list[tuple[Opponent, Ball]]:
        """Check if player balls hit opponents. Return list of (opponent, ball) pairs."""
        hits: list[tuple[Opponent, Ball]] = []
        surviving_balls: list[Ball] = []
        for ball in self.balls:
            if not ball.owner_is_player:
                surviving_balls.append(ball)
                continue
            hit = False
            for opp in self.opponents:
                if not opp.alive:
                    continue
                dist = math.hypot(ball.x - opp.x, ball.y - opp.y)
                if dist < opp.radius + ball.radius:
                    hits.append((opp, ball))
                    hit = True
                    break
            if not hit:
                surviving_balls.append(ball)
        self.balls = surviving_balls
        return hits

    def _resolve_hit(self, opp: Opponent, ball: Ball) -> None:
        """Process a player ball hitting an opponent: update score/combo/spawn effects."""
        is_match = self.super_active or ball.color == -1 or ball.color == opp.color

        if is_match:
            opp.hp -= ball.damage
            self.combo += 1
            score_mult = 3 if self.super_active else 1
            score_gain = opp.score_value * score_mult * self.combo
            self.score += score_gain
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            particle_color = opp.color if ball.color >= 0 else self._rng.randint(0, 3)
            self._spawn_particles(opp.x, opp.y, particle_color, PARTICLE_COUNT_HIT)
            self._spawn_floating_text(opp.x, opp.y - 10, f"+{score_gain}", 14)
            if self.combo >= 3:
                self._spawn_floating_text(opp.x, opp.y - 22, f"{self.combo} COMBO!", 10)
        else:
            opp.hp -= ball.damage
            self.combo = 0
            score_gain = opp.score_value // 2
            self.score += score_gain
            self._spawn_particles(opp.x, opp.y, ball.color, 4)
            self._spawn_floating_text(opp.x, opp.y - 10, f"+{score_gain}", 13)

        if opp.hp <= 0:
            opp.alive = False
            self._spawn_particles(opp.x, opp.y, 14, 12)
            self._spawn_floating_text(opp.x, opp.y - 30, "DOWN!", 8)

        if self.combo >= COMBO_THRESHOLD and not self.super_active:
            self._activate_super()

    def _activate_super(self) -> None:
        """Activate SUPER THROW mode."""
        self.super_active = True
        self.super_timer = SUPER_DURATION
        self._spawn_particles(self.player.x, self.player.y, 10, PARTICLE_COUNT_SUPER)
        self._spawn_floating_text(self.player.x, self.player.y - 20, "SUPER!", 2)
        self._spawn_floating_text(self.player.x, self.player.y - 35, "3x SCORE!", 2)

    def _spawn_echo(self, x: float, y: float, color: int) -> None:
        """Spawn an echo trail at the given position."""
        self.echoes.append(EchoTrail(x=x, y=y, life=ECHO_DURATION, color=color))

    def _update_echoes(self) -> None:
        """Age echo trails and remove expired ones."""
        surviving: list[EchoTrail] = []
        for echo in self.echoes:
            echo.life -= 1
            if echo.life > 0:
                surviving.append(echo)
        self.echoes = surviving

    def _check_echo_collect(self) -> None:
        """Check if player touches any echo trail. Grant stamina and echo bonus."""
        surviving: list[EchoTrail] = []
        for echo in self.echoes:
            dist = math.hypot(echo.x - self.player.x, echo.y - self.player.y)
            if dist < self.player.radius + 8.0:
                self.stamina = min(float(MAX_STAMINA), self.stamina + ECHO_STAMINA_BONUS)
                self.echo_bonus = True
                self._spawn_particles(self.player.x, self.player.y, 7, PARTICLE_COUNT_ECHO)
                self._spawn_floating_text(self.player.x, self.player.y - 15, "ECHO x2!", 7)
            else:
                surviving.append(echo)
        self.echoes = surviving

    def _update_opponents(self) -> None:
        """Opponent AI: move toward player, throw when cooldown ready, remove dead."""
        for opp in self.opponents:
            if not opp.alive:
                continue

            dx = self.player.x - opp.x
            dy = self.player.y - opp.y
            dist = math.hypot(dx, dy)
            if dist > 50.0:
                if dist > 0:
                    opp.x += dx / dist * opp.speed
                    opp.y += dy / dist * opp.speed
            elif dist < 40.0:
                if dist > 0:
                    opp.x -= dx / dist * opp.speed * 0.5
                    opp.y -= dy / dist * opp.speed * 0.5

            opp.x = max(ARENA_LEFT + opp.radius, min(ARENA_RIGHT - opp.radius, opp.x))
            opp.y = max(ARENA_TOP + opp.radius, min(ARENA_BOTTOM - opp.radius, opp.y))

            opp.throw_cooldown -= 1
            if opp.throw_cooldown <= 0:
                ball = self._opponent_throw(opp)
                self.balls.append(ball)
                base_cd = max(60, 150 - self._difficulty_bonus())
                opp.throw_cooldown = self._rng.randint(base_cd - 20, base_cd + 20)

        self.opponents = [o for o in self.opponents if o.alive]

    def _update_timers(self) -> None:
        """Tick down game timer, super timer, and player color timer."""
        self.game_timer -= 1

        if self.super_active:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_active = False
                self.combo = 0

        self.player.color_timer -= 1
        if self.player.color_timer <= 0:
            self._cycle_player_color(True)
            self.player.color_timer = 120

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        """Spawn burst of particles at position."""
        for _ in range(count):
            vx = self._rng.uniform(-2.5, 2.5)
            vy = self._rng.uniform(-2.5, 2.5)
            life = self._rng.randint(15, 30)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        """Spawn floating text."""
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=FLOATING_TEXT_LIFE, color=color)
        )

    def _cycle_player_color(self, forward: bool = True) -> None:
        """Cycle player ball color forward or backward."""
        if forward:
            self.player.color = (self.player.color + 1) % NUM_COLORS
        else:
            self.player.color = (self.player.color - 1) % NUM_COLORS

    def _check_game_over(self) -> bool:
        """Return True if game over conditions are met."""
        return self.heat >= MAX_HEAT or self.game_timer <= 0

    # ---- Particle and floating text updates ----

    def _update_particles(self) -> None:
        surviving: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                surviving.append(p)
        self.particles = surviving

    def _update_floating_texts(self) -> None:
        surviving: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                surviving.append(ft)
        self.floating_texts = surviving

    # ---- Drawing methods ----

    def _draw_playing(self) -> None:
        self._draw_arena()
        self._draw_echoes()
        self._draw_opponents()
        self._draw_balls()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_arena(self) -> None:
        pyxel.rectb(ARENA_LEFT, ARENA_TOP, ARENA_RIGHT - ARENA_LEFT, ARENA_BOTTOM - ARENA_TOP, 7)

    def _draw_player(self) -> None:
        p = self.player
        if p.hit_flash > 0 and p.hit_flash % 2 == 0:
            body_color = 8
        else:
            body_color = 7

        if self.super_active:
            ring_color = BALL_COLORS[(pyxel.frame_count // 4) % 4]
        else:
            ring_color = BALL_COLORS[p.color]
        pyxel.circb(int(p.x), int(p.y), int(p.radius) + 2, ring_color)

        pyxel.circ(int(p.x), int(p.y), int(p.radius), body_color)

        if self.echo_bonus:
            pyxel.circb(int(p.x), int(p.y), int(p.radius) + 4, 7)

    def _draw_opponents(self) -> None:
        for opp in self.opponents:
            if not opp.alive:
                continue
            color = BALL_COLORS[opp.color]
            pyxel.circ(int(opp.x), int(opp.y), int(opp.radius), color)
            pyxel.circb(int(opp.x), int(opp.y), int(opp.radius), 7)

    def _draw_balls(self) -> None:
        for ball in self.balls:
            if ball.color == -1:
                color = BALL_COLORS[(pyxel.frame_count // 3) % 4]
            else:
                color = BALL_COLORS[ball.color]
            pyxel.circ(int(ball.x), int(ball.y), int(ball.radius), color)

    def _draw_echoes(self) -> None:
        for echo in self.echoes:
            alpha = max(0.0, echo.life / ECHO_DURATION)
            radius = int(4.0 + 4.0 * alpha)
            color = BALL_COLORS[echo.color % 4]
            if alpha < 0.3:
                continue
            pyxel.circb(int(echo.x), int(echo.y), radius, color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha_scale = p.life / 30.0
            r = max(0.5, 1.5 * alpha_scale)
            pyxel.circ(int(p.x), int(p.y), int(r), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / FLOATING_TEXT_LIFE
            if alpha < 0.2:
                continue
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        y_top = 2

        pyxel.text(4, y_top, f"SCORE:{self.score}", 7)
        pyxel.text(4, y_top + 10, f"COMBO:{self.combo}", 10)
        if self.max_combo > 0:
            pyxel.text(4, y_top + 20, f"MAX:{self.max_combo}", 10)

        pyxel.text(100, y_top, "HEAT", 9)
        pyxel.rect(100, y_top + 9, 60, 6, 0)
        heat_w = int(60.0 * self.heat / MAX_HEAT)
        pyxel.rect(100, y_top + 9, heat_w, 6, 9)

        pyxel.text(100, y_top + 18, "STM", 12)
        pyxel.rect(100, y_top + 27, 60, 6, 0)
        stm_w = int(60.0 * self.stamina / MAX_STAMINA)
        pyxel.rect(100, y_top + 27, stm_w, 6, 12)

        if self.super_active:
            secs = self.super_timer // 60 + 1
            pyxel.text(170, y_top + 6, f"SUPER {secs}s", 2)

        secs = max(0, self.game_timer // 60)
        if secs > 10:
            timer_color = 7
        elif secs > 5:
            timer_color = 10
        else:
            timer_color = 8 if (pyxel.frame_count // 15) % 2 == 0 else 10
        pyxel.text(SCREEN_W - 42, y_top, f"TIME:{secs:2d}", timer_color)

        pyxel.text(
            SCREEN_W - 42, y_top + 20,
            f"C:{COLOR_NAMES[self.player.color]}",
            BALL_COLORS[self.player.color],
        )

        if self.echo_bonus:
            pyxel.text(170, y_top + 20, "ECHO x2!", 7)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
