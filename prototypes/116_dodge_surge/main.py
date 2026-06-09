from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

import pyxel

RED = 8
GREEN = 3
BLUE = 6
YELLOW = 10
COLORS = [RED, GREEN, BLUE, YELLOW]
WHITE = 7
BLACK = 0
GRAY = 13
NAVY = 1
ORANGE = 9
PINK = 14


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Opponent:
    x: float
    y: float
    color: int
    vx: float
    throw_timer: int
    alive: bool
    respawn_timer: int


@dataclass
class Ball:
    x: float
    y: float
    color: int
    vx: float
    vy: float
    owner: str


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.0


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    PLAYER_SPEED = 2
    BALL_SPEED = 4
    OPPONENT_SPEED = 1
    OPPONENT_BALL_SPEED = 3
    MAX_HEAT = 10
    MAX_HP = 5
    COMBO_THRESHOLD = 4
    GAME_DURATION = 60 * 60
    SUPER_DURATION = 5 * 60
    MAX_INVENTORY = 3
    MAX_FIELD_BALLS = 8
    SPAWN_INTERVAL = 120
    PICKUP_RADIUS = 12
    HIT_RADIUS = 10
    PLAYER_RADIUS = 8
    OPPONENT_RADIUS = 7
    FIELD_BALL_RADIUS = 4
    THROWN_BALL_RADIUS = 3
    HEAT_DECAY_INTERVAL = 180

    def __init__(self) -> None:
        self._rng = random.Random()
        self.phase: Phase = Phase.TITLE
        self.opponents: list[Opponent] = []
        self.field_balls: list[Ball] = []
        self.thrown_balls: list[Ball] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.player_x = 160.0
        self.player_y = 200.0
        self.player_color = RED
        self.player_inventory = 3
        self.hp = self.MAX_HP
        self.heat = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_mode = False
        self.super_timer = 0
        self.game_timer = self.GAME_DURATION
        self.shake_frames = 0
        self.opponents.clear()
        self.field_balls.clear()
        self.thrown_balls.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self._heat_decay_timer = 0
        self._spawn_timer = 0
        self._last_hit_color = -1
        self._init_opponents()

    def _init_opponents(self) -> None:
        colors = [RED, RED, GREEN, GREEN, BLUE, YELLOW]
        positions = [(40, 30), (120, 30), (200, 30), (40, 70), (120, 70), (200, 70)]
        self.opponents.clear()
        for (x, y), c in zip(positions, colors):
            self.opponents.append(
                Opponent(
                    x=float(x),
                    y=float(y),
                    color=c,
                    vx=1.0 if self._rng.random() > 0.5 else -1.0,
                    throw_timer=self._rng.randint(60, 180),
                    alive=True,
                    respawn_timer=0,
                )
            )

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.phase = Phase.PLAYING
                self.game_timer = self.GAME_DURATION
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
                self.phase = Phase.PLAYING
                self.game_timer = self.GAME_DURATION
        elif self.phase == Phase.PLAYING:
            self._update_playing(1)

    def _update_playing(self, dt: int = 1, headless: bool = False) -> None:
        self.game_timer -= dt
        if not headless:
            self._update_player_input()
        self._update_spawning(dt)
        self._update_field_balls()
        self._update_thrown_balls()
        self._update_opponents(dt)
        self._update_particles()
        self._update_floating_texts()
        self._update_heat_decay(dt)
        self._update_super_mode(dt)
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if self.hp <= 0 or self.heat >= self.MAX_HEAT or self.game_timer <= 0:
            self.phase = Phase.GAME_OVER

    def _update_player_input(self) -> None:
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_LEFT):
            self.player_x -= self.PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT):
            self.player_x += self.PLAYER_SPEED
        self.player_x = max(16.0, min(float(self.SCREEN_W - 16), self.player_x))

        if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_DPAD_UP):
            idx = COLORS.index(self.player_color)
            self.player_color = COLORS[(idx - 1) % 4]
        if pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_DPAD_DOWN):
            idx = COLORS.index(self.player_color)
            self.player_color = COLORS[(idx + 1) % 4]

        if pyxel.btnp(pyxel.KEY_SPACE) and self.player_inventory > 0:
            self._player_throw()

    def _player_throw(self) -> None:
        if self.player_inventory <= 0:
            return
        self.player_inventory -= 1
        target_x = self.player_x
        target_y = 0.0
        nearest_dist = float("inf")
        for opp in self.opponents:
            if not opp.alive:
                continue
            d = math.hypot(opp.x - self.player_x, opp.y - self.player_y)
            if d < nearest_dist:
                nearest_dist = d
                target_x = opp.x
                target_y = opp.y
        dx = target_x - self.player_x
        dy = target_y - self.player_y
        length = math.hypot(dx, dy) or 1.0
        self.thrown_balls.append(
            Ball(
                self.player_x,
                self.player_y - 10,
                self.player_color,
                dx / length * self.BALL_SPEED,
                dy / length * self.BALL_SPEED,
                "player",
            )
        )

    def _update_spawning(self, dt: int) -> None:
        self._spawn_timer += dt
        if self._spawn_timer >= self.SPAWN_INTERVAL:
            self._spawn_timer = 0
            if len(self.field_balls) < self.MAX_FIELD_BALLS:
                color = self._rng.choice(COLORS)
                x = float(self._rng.randint(20, 300))
                self.field_balls.append(Ball(x, 120.0, color, 0.0, 0.0, "field"))

    def _update_field_balls(self) -> None:
        for ball in self.field_balls[:]:
            d = math.hypot(ball.x - self.player_x, ball.y - self.player_y)
            if d < self.PICKUP_RADIUS and self.player_inventory < self.MAX_INVENTORY:
                self.player_inventory += 1
                self.field_balls.remove(ball)

    def _update_thrown_balls(self) -> None:
        for ball in self.thrown_balls[:]:
            ball.x += ball.vx
            ball.y += ball.vy

            if ball.owner == "player":
                hit_any = False
                for i, opp in enumerate(self.opponents):
                    if not opp.alive:
                        continue
                    d = math.hypot(ball.x - opp.x, ball.y - opp.y)
                    if d < self.HIT_RADIUS:
                        self._handle_hit(i, ball.color)
                        hit_any = True
                        if not self.super_mode:
                            break
                if hit_any:
                    self.thrown_balls.remove(ball)
                elif (
                    ball.x < -30
                    or ball.x > self.SCREEN_W + 30
                    or ball.y < -30
                    or ball.y > self.SCREEN_H + 30
                ):
                    self.thrown_balls.remove(ball)
            else:
                d = math.hypot(ball.x - self.player_x, ball.y - self.player_y)
                if d < self.PLAYER_RADIUS + self.THROWN_BALL_RADIUS + 2:
                    self._handle_player_hit()
                    self.thrown_balls.remove(ball)
                elif (
                    ball.x < -30
                    or ball.x > self.SCREEN_W + 30
                    or ball.y < -30
                    or ball.y > self.SCREEN_H + 30
                ):
                    self.thrown_balls.remove(ball)

    def _handle_hit(self, opponent_idx: int, ball_color: int) -> None:
        opp = self.opponents[opponent_idx]
        if not opp.alive:
            return

        is_match = self.super_mode or ball_color == opp.color

        if is_match:
            if ball_color == self._last_hit_color:
                self.combo += 1
            else:
                self.combo = 1
            self._last_hit_color = ball_color
            self.max_combo = max(self.max_combo, self.combo)

            if self.super_mode:
                score_gain = 300 + self.combo * 75
                self._spawn_super_particles(opp.x, opp.y)
                self._add_floating_text(opp.x, opp.y - 8, f"+{score_gain}", YELLOW, 45)
                if self.combo == 1:
                    self._add_floating_text(opp.x, opp.y - 20, "SUPER!", PINK, 60)
                opp.respawn_timer = 5 * 60
            else:
                score_gain = 100 + self.combo * 25
                self._spawn_hit_particles(opp.x, opp.y, opp.color)
                self._add_floating_text(opp.x, opp.y - 8, f"+{score_gain}", WHITE, 30)
                if self.combo > 1:
                    self._add_floating_text(
                        opp.x, opp.y - 20, f"x{self.combo}", YELLOW, 45
                    )
                opp.respawn_timer = 3 * 60

            self.score += score_gain
            opp.alive = False

            if self.combo >= self.COMBO_THRESHOLD and not self.super_mode:
                self.super_mode = True
                self.super_timer = self.SUPER_DURATION
                self._add_floating_text(
                    self.SCREEN_W // 2, self.SCREEN_H // 2, "SUPER THROW!", PINK, 60
                )
        else:
            self.heat = min(self.heat + 2, self.MAX_HEAT)
            self.combo = 0
            self._last_hit_color = -1
            self._add_floating_text(opp.x, opp.y - 8, "MISS", GRAY, 30)

    def _handle_player_hit(self) -> None:
        self.hp -= 1
        self.heat = min(self.heat + 1, self.MAX_HEAT)
        self.combo = 0
        self._last_hit_color = -1
        self.shake_frames = 10
        for _ in range(10):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    self.player_x,
                    self.player_y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    20,
                    RED,
                    3,
                )
            )

    def _update_opponents(self, dt: int) -> None:
        for opp in self.opponents:
            if opp.alive:
                opp.x += opp.vx * dt
                if opp.x < 16 or opp.x > self.SCREEN_W - 16:
                    opp.vx *= -1
                opp.x += self._rng.uniform(-0.5, 0.5) * dt
                opp.x = max(16.0, min(float(self.SCREEN_W - 16), opp.x))

                opp.throw_timer -= dt
                if opp.throw_timer <= 0:
                    self._opponent_throw(opp)
                    opp.throw_timer = self._rng.randint(60, 180)
            else:
                opp.respawn_timer -= dt
                if opp.respawn_timer <= 0:
                    opp.alive = True
                    opp.color = self._rng.choice(COLORS)
                    opp.throw_timer = self._rng.randint(60, 180)
                    opp.vx = 1.0 if self._rng.random() > 0.5 else -1.0

    def _opponent_throw(self, opp: Opponent) -> None:
        dx = self.player_x - opp.x
        dy = self.player_y - opp.y
        length = math.hypot(dx, dy) or 1.0
        self.thrown_balls.append(
            Ball(
                opp.x,
                opp.y + 10,
                opp.color,
                dx / length * self.OPPONENT_BALL_SPEED,
                dy / length * self.OPPONENT_BALL_SPEED,
                "opponent",
            )
        )

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life % 3 == 0:
                p.size = max(1, p.size - 1)
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _update_heat_decay(self, dt: int) -> None:
        self._heat_decay_timer += dt
        if self._heat_decay_timer >= self.HEAT_DECAY_INTERVAL:
            self._heat_decay_timer = 0
            self.heat = max(0, self.heat - 1)

    def _update_super_mode(self, dt: int) -> None:
        if self.super_mode:
            self.super_timer -= dt
            if self.super_timer <= 0:
                self.super_mode = False
                self.combo = 0
                self._last_hit_color = -1

    def _spawn_hit_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(8):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    15,
                    color,
                    3,
                )
            )

    def _spawn_super_particles(self, x: float, y: float) -> None:
        for _ in range(20):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(2.0, 5.0)
            pc = self._rng.choice(COLORS)
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    20,
                    pc,
                    3,
                )
            )

    def _add_floating_text(
        self, x: float, y: float, text: str, color: int, life: int
    ) -> None:
        self.floating_texts.append(FloatingText(x, y, text, life, color))

    def draw(self) -> None:
        pyxel.cls(NAVY)
        if self.shake_frames > 0:
            ox = self._rng.randint(-3, 3)
            oy = self._rng.randint(-3, 3)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 35, 60, "DODGE SURGE", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 60, 90, "LEFT/RIGHT: Move", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 60, 100, "UP/DOWN: Change Color", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 60, 110, "SPACE: Throw Ball", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 60, 130, "Match colors -> COMBO!", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 60, 140, "COMBO x4 -> SUPER THROW!", PINK)
        if pyxel.frame_count % 30 < 15:
            pyxel.text(
                self.SCREEN_W // 2 - 55, 170, "Press SPACE to Start", WHITE
            )

    def _draw_playing(self) -> None:
        self._draw_field_balls()
        self._draw_opponents()
        self._draw_thrown_balls()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_game_over(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 30, 70, "GAME OVER", RED)
        pyxel.text(self.SCREEN_W // 2 - 40, 90, f"SCORE: {self.score}", WHITE)
        pyxel.text(
            self.SCREEN_W // 2 - 50, 100, f"MAX COMBO: x{self.max_combo}", YELLOW
        )
        if self.hp <= 0:
            pyxel.text(self.SCREEN_W // 2 - 40, 120, "HP depleted!", RED)
        elif self.heat >= self.MAX_HEAT:
            pyxel.text(self.SCREEN_W // 2 - 40, 120, "Overheated!", ORANGE)
        elif self.game_timer <= 0:
            pyxel.text(self.SCREEN_W // 2 - 40, 120, "Time up!", WHITE)
        if pyxel.frame_count % 30 < 15:
            pyxel.text(
                self.SCREEN_W // 2 - 55, 150, "Press SPACE to Retry", WHITE
            )

    def _draw_field_balls(self) -> None:
        for ball in self.field_balls:
            pyxel.circ(int(ball.x), int(ball.y), self.FIELD_BALL_RADIUS, ball.color)

    def _draw_opponents(self) -> None:
        for opp in self.opponents:
            if opp.alive:
                pyxel.circ(int(opp.x), int(opp.y), self.OPPONENT_RADIUS, opp.color)
                pyxel.circb(
                    int(opp.x), int(opp.y), self.OPPONENT_RADIUS + 1, WHITE
                )
            else:
                pyxel.circb(
                    int(opp.x), int(opp.y), self.OPPONENT_RADIUS, GRAY
                )
                pyxel.text(int(opp.x) - 3, int(opp.y) - 3, "X", GRAY)

    def _draw_thrown_balls(self) -> None:
        for ball in self.thrown_balls:
            if ball.owner == "player" and self.super_mode:
                c = COLORS[(pyxel.frame_count // 4) % 4]
                pyxel.circ(
                    int(ball.x), int(ball.y), self.THROWN_BALL_RADIUS + 1, c
                )
            elif ball.owner == "player":
                pyxel.circ(
                    int(ball.x), int(ball.y), self.THROWN_BALL_RADIUS, ball.color
                )
            else:
                pyxel.circ(
                    int(ball.x), int(ball.y), self.THROWN_BALL_RADIUS + 1, ball.color
                )
                pyxel.circb(
                    int(ball.x),
                    int(ball.y),
                    self.THROWN_BALL_RADIUS + 2,
                    WHITE,
                )

    def _draw_player(self) -> None:
        px = int(self.player_x)
        py = int(self.player_y)
        if self.super_mode:
            c = COLORS[(pyxel.frame_count // 4) % 4]
            pyxel.circb(px, py, self.PLAYER_RADIUS + 3, c)
        pyxel.circ(px, py, self.PLAYER_RADIUS, self.player_color)
        pyxel.circb(px, py, self.PLAYER_RADIUS + 1, WHITE)
        for i in range(self.player_inventory):
            bx = px - 10 + i * 10
            by = py + 14
            pyxel.circ(bx, by, 3, self.player_color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.size > 0:
                pyxel.circ(int(p.x), int(p.y), p.size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, self.SCREEN_W, 14, BLACK)
        pyxel.text(4, 2, f"SCORE:{self.score}", WHITE)
        secs = max(0, self.game_timer // 60)
        t = f"TIME:{secs}"
        pyxel.text(self.SCREEN_W // 2 - len(t) * 2, 2, t, WHITE)
        ct = f"COMBO:x{self.combo}"
        pyxel.text(
            self.SCREEN_W - len(ct) * 4 - 4, 2, ct, YELLOW if self.combo > 0 else WHITE
        )

        hx = 4
        for i in range(self.MAX_HP):
            pyxel.text(hx, self.SCREEN_H - 14, "H", RED if i < self.hp else GRAY)
            hx += 10

        inv_x = self.SCREEN_W // 2 - 15
        for i in range(self.MAX_INVENTORY):
            if i < self.player_inventory:
                pyxel.circ(inv_x + i * 12, self.SCREEN_H - 8, 4, self.player_color)
            else:
                pyxel.circb(inv_x + i * 12, self.SCREEN_H - 8, 4, GRAY)

        bar_x = self.SCREEN_W - 120
        bar_y = self.SCREEN_H - 14
        bar_w = 110
        bar_h = 8
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        seg_w = max(1, (bar_w - 2) // self.MAX_HEAT)
        for i in range(self.MAX_HEAT):
            sx = bar_x + 1 + i * seg_w
            if i < self.heat:
                if i < 4:
                    sc = GREEN
                elif i < 7:
                    sc = YELLOW
                else:
                    sc = RED
                pyxel.rect(sx, bar_y + 1, seg_w, bar_h - 2, sc)
        pyxel.text(bar_x - 14, bar_y, "H", ORANGE)

        if self.super_mode:
            c = COLORS[(pyxel.frame_count // 4) % 4]
            sl = self.super_timer // 60 + 1
            pyxel.text(
                self.SCREEN_W // 2 - 25, self.SCREEN_H - 28, f"SUPER {sl}s", c
            )


def main() -> None:
    game = Game()
    pyxel.init(Game.SCREEN_W, Game.SCREEN_H, title="DODGE SURGE", display_scale=2, fps=60)
    game.reset()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
