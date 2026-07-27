"""248_ping_chain -- Table Tennis Color-Match COMBO Chain Game

Top-down table tennis where hitting the ball with a matching-color paddle
builds a COMBO chain. COMBO >= 4 triggers SUPER SPIN -- rainbow mode,
3x score, rainbow paddle. HEAT risk system. 60s match timer.
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass, field

import pyxel

# -- Constants ------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240

TABLE_LEFT = 20
TABLE_RIGHT = 300
TABLE_TOP = 30
TABLE_BOTTOM = 210
NET_Y = 120
NET_HEIGHT = 4

PADDLE_W = 40
PADDLE_H = 10
PADDLE_SPEED = 3.0
BALL_R = 4

PLAYER_Y = 215
AI_Y = 25

COLORS = (8, 11, 5, 10)
COLOR_NAMES = ("RED", "LIME", "D. BLUE", "YELLOW")
NUM_COLORS = 4

COMBO_THRESHOLD = 4
SUPER_DURATION = 300
SUPER_SCORE_MULT = 3

HEAT_MISMATCH = 15.0
HEAT_MISS = 25.0
HEAT_DECAY = 0.02
HEAT_MAX = 100.0

GAME_TIME = 60 * 60
BALL_SPEED_BASE = 2.0
BALL_SPEED_MAX = 5.0
BALL_SPEED_ESCALATION = 0.02

AI_SPEED = 2.5
AI_REACTION_BASE = 45
AI_REACTION_MIN = 8
AI_COLOR_CYCLE_BASE = 90
AI_COLOR_CYCLE_MIN = 30

COLOR_COOLDOWN = 8

# -----------------------------------------------------------------------


class Phase(enum.Enum):
    TITLE = enum.auto()
    PLAYING = enum.auto()
    GAME_OVER = enum.auto()


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    trail: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class Particle:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    life: int = 20
    color: int = 7


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int = 30
    color: int = 7


# -----------------------------------------------------------------------


class Game:
    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.timer: int = GAME_TIME
        self.heat: float = 0.0
        self.player_x: float = 160.0
        self.player_color_idx: int = 0
        self.ai_x: float = 160.0
        self.ai_color_idx: int = 0
        self.super_timer: int = 0
        self._color_cooldown: int = 0
        self._ai_reaction_timer: int = 0
        self._ai_color_timer: int = 0
        self.ball: Ball = Ball(160.0, 120.0, 0.0, 0.0, COLORS[0])
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self._ghost_trail: list[tuple[float, float]] = []
        self._best_rally: int = 0
        self._rally_count: int = 0
        self._screen_shake: int = 0
        self._rng = random.Random(42)

    # -- Public API -------------------------------------------------------

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.timer = GAME_TIME
        self.heat = 0.0
        self.player_x = 160.0
        self.player_color_idx = self._rng.randint(0, NUM_COLORS - 1)
        self.ai_x = 160.0
        self.ai_color_idx = self._rng.randint(0, NUM_COLORS - 1)
        self.super_timer = 0
        self._color_cooldown = 0
        self._ai_reaction_timer = 0
        self._ai_color_timer = 0
        self._ghost_trail.clear()
        self._best_rally = 0
        self._rally_count = 0
        self._screen_shake = 0
        self.particles.clear()
        self.floats.clear()
        self._spawn_ball()

    def _spawn_ball(self) -> None:
        vx = self._rng.uniform(1.5, 2.5) * self._rng.choice([-1, 1])
        vy = self._rng.uniform(1.5, 2.5)
        if vy > 0:
            vy *= -1
        color = self._rng.choice(COLORS)
        self.ball = Ball(x=160.0, y=120.0, vx=vx, vy=vy, color=color, trail=[])
        self._rally_count = 0

    def _ball_speed(self) -> float:
        elapsed_sec = (GAME_TIME - self.timer) / 60.0
        speed = BALL_SPEED_BASE + BALL_SPEED_ESCALATION * elapsed_sec
        return min(speed, BALL_SPEED_MAX)

    def _super_active(self) -> bool:
        return self.super_timer > 0

    # -- Testable logic methods -------------------------------------------

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER

    def _update_ball(self) -> None:
        b = self.ball
        b.trail.append((b.x, b.y))
        if len(b.trail) > 12:
            b.trail = b.trail[-12:]

        b.x += b.vx
        b.y += b.vy

        if b.x < TABLE_LEFT + BALL_R:
            b.x = TABLE_LEFT + BALL_R
            b.vx = abs(b.vx)
        elif b.x > TABLE_RIGHT - BALL_R:
            b.x = TABLE_RIGHT - BALL_R
            b.vx = -abs(b.vx)

        if b.y <= AI_Y + PADDLE_H:
            self._resolve_ai_hit()
        elif b.y >= PLAYER_Y - PADDLE_H:
            self._resolve_player_hit()

        if b.y < -20:
            self._on_miss()
        elif b.y > SCREEN_H + 20:
            self._on_miss()

    def _resolve_player_hit(self) -> None:
        b = self.ball
        if not (PLAYER_Y - PADDLE_H - BALL_R <= b.y <= PLAYER_Y + BALL_R):
            return

        if abs(b.x - self.player_x) < PADDLE_W / 2 + BALL_R:
            self._on_paddle_hit(is_player=True)
        else:
            self._on_miss()

    def _resolve_ai_hit(self) -> None:
        b = self.ball
        if not (AI_Y - BALL_R <= b.y <= AI_Y + PADDLE_H + BALL_R):
            return

        if abs(b.x - self.ai_x) < PADDLE_W / 2 + BALL_R:
            self._on_paddle_hit(is_player=False)
        else:
            self._on_miss()

    def _on_paddle_hit(self, is_player: bool) -> None:
        b = self.ball
        paddle_x = self.player_x if is_player else self.ai_x
        paddle_color_idx = self.player_color_idx if is_player else self.ai_color_idx
        hit_x = b.x
        hit_y = b.y

        spread = (b.x - paddle_x) * 0.15
        speed = self._ball_speed()

        if is_player:
            b.vy = -abs(b.vy) if b.vy > -0.5 else -speed * 0.7
            b.vx = spread
        else:
            b.vy = abs(b.vy) if b.vy < 0.5 else speed * 0.7
            b.vx = spread

        mag = (b.vx**2 + b.vy**2) ** 0.5
        if mag > 0:
            b.vx = b.vx / mag * speed
            b.vy = b.vy / mag * speed

        matched = COLORS[paddle_color_idx] == b.color or self._super_active()

        if matched:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            mult = SUPER_SCORE_MULT if self._super_active() else 1
            score_gain = 10 * self.combo * mult
            self.score += score_gain

            if self.combo >= COMBO_THRESHOLD and not self._super_active():
                self._activate_super()

            b.color = COLORS[(self.combo + paddle_color_idx) % NUM_COLORS]

            self._rally_count += 1
            if self._rally_count > self._best_rally:
                self._best_rally = self._rally_count
                self._ghost_trail = list(b.trail)

            if is_player:
                if self._super_active():
                    self._spawn_particles(hit_x, hit_y, b.color, 15)
                else:
                    self._spawn_particles(hit_x, hit_y, b.color, 8)
                self._spawn_float(hit_x, hit_y - 10, f"+{score_gain}", 10)
                if self.combo >= 2:
                    self._spawn_float(hit_x, hit_y - 22, f"COMBO x{self.combo}", 9)
        else:
            self.combo = 0
            self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
            self._rally_count = 0
            if is_player:
                self._spawn_particles(hit_x, hit_y, 13, 4)
                self._spawn_float(hit_x, hit_y - 10, "MISS!", 8)

        if is_player:
            self.player_color_idx = (self.player_color_idx + 1) % NUM_COLORS

    def _on_miss(self) -> None:
        self.heat = min(HEAT_MAX, self.heat + HEAT_MISS)
        self._rally_count = 0
        self._spawn_float(self.player_x, PLAYER_Y - 20, "MISS!", 8)
        self._spawn_shake()
        self._spawn_ball()

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self._spawn_float(SCREEN_W // 2 - 40, 80, "SUPER SPIN!", 11, 50)

    def _update_ai(self) -> None:
        b = self.ball
        progress = 1.0 - (self.timer / GAME_TIME)

        reaction_delay = int(AI_REACTION_BASE - (AI_REACTION_BASE - AI_REACTION_MIN) * progress)
        if self._ai_reaction_timer > 0:
            self._ai_reaction_timer -= 1
        else:
            self._ai_reaction_timer = reaction_delay
            miss_chance = 0.1 * (1.0 - min(self.timer / GAME_TIME, 1.0))
            if self._rng.random() > miss_chance:
                if self.ai_x < b.x:
                    self.ai_x = min(TABLE_RIGHT - PADDLE_W / 2, self.ai_x + AI_SPEED)
                elif self.ai_x > b.x:
                    self.ai_x = max(TABLE_LEFT + PADDLE_W / 2, self.ai_x - AI_SPEED)

        cycle_interval = int(AI_COLOR_CYCLE_BASE - (AI_COLOR_CYCLE_BASE - AI_COLOR_CYCLE_MIN) * progress)
        self._ai_color_timer += 1
        if self._ai_color_timer >= cycle_interval:
            self._ai_color_timer = 0
            self.ai_color_idx = (self.ai_color_idx + 1) % NUM_COLORS

    def _update_heat(self) -> None:
        # Check BEFORE decay to avoid the "decay-before-threshold-check" pitfall
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_super_mode(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _check_game_over(self) -> None:
        if self.timer <= 0 or self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER

    def _update_particles(self) -> None:
        remaining: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                remaining.append(p)
        self.particles = remaining

    def _update_floats(self) -> None:
        remaining: list[FloatingText] = []
        for ft in self.floats:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                remaining.append(ft)
        self.floats = remaining

    def _spawn_shake(self) -> None:
        self._screen_shake = 8

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            pc = color if not self._super_active() else self._rng.choice(COLORS)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-1.5, 1.5),
                    vy=self._rng.uniform(-1.5, 1.5),
                    life=self._rng.randint(15, 25),
                    color=pc,
                )
            )

    def _spawn_float(self, x: float, y: float, text: str, color: int, life: int = 30) -> None:
        self.floats.append(
            FloatingText(x=x, y=y, text=text, life=life, color=color)
        )

    # -- Update dispatch --------------------------------------------------

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()

    def _update_playing(self) -> None:
        if self._screen_shake > 0:
            self._screen_shake -= 1

        self._update_timer()
        if self.phase == Phase.GAME_OVER:
            return

        self._update_ball()
        self._update_heat()
        self._update_super_mode()
        self._update_ai()
        self._update_particles()
        self._update_floats()

        if pyxel.btn(pyxel.KEY_LEFT):
            self.player_x = max(TABLE_LEFT + PADDLE_W / 2, self.player_x - PADDLE_SPEED)
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.player_x = min(TABLE_RIGHT - PADDLE_W / 2, self.player_x + PADDLE_SPEED)

        if self._color_cooldown > 0:
            self._color_cooldown -= 1

        if pyxel.btnp(pyxel.KEY_UP) and self._color_cooldown == 0:
            self.player_color_idx = (self.player_color_idx + 1) % NUM_COLORS
            self._color_cooldown = COLOR_COOLDOWN
        if pyxel.btnp(pyxel.KEY_DOWN) and self._color_cooldown == 0:
            self.player_color_idx = (self.player_color_idx - 1) % NUM_COLORS
            self._color_cooldown = COLOR_COOLDOWN

        self._check_game_over()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.phase = Phase.TITLE

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    # -- Draw -------------------------------------------------------------

    def _draw_title(self) -> None:
        pyxel.cls(0)
        pyxel.text(SCREEN_W // 2 - 30, 50, "PING CHAIN", 7)
        pyxel.text(SCREEN_W // 2 - 58, 72, "Color-Match Table Tennis", 13)

        pyxel.text(90, 100, "Controls:", 7)
        pyxel.text(95, 115, "LEFT / RIGHT: Move paddle", 13)
        pyxel.text(95, 130, "UP / DOWN: Cycle color", 13)
        pyxel.text(70, 150, "Match paddle color = COMBO!", 10)
        pyxel.text(65, 165, "COMBO x4 = SUPER SPIN!", 11)
        pyxel.text(60, 185, "Mismatch raises HEAT = danger", 8)
        pyxel.text(100, 220, "Press ENTER to Start", 7)

    def _draw_playing(self) -> None:
        shake_x = 0
        shake_y = 0
        if self._screen_shake > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)

        pyxel.cls(0)

        # Table surface
        pyxel.rect(TABLE_LEFT + shake_x, TABLE_TOP + shake_y,
                   TABLE_RIGHT - TABLE_LEFT, TABLE_BOTTOM - TABLE_TOP, 3)

        # Table border
        pyxel.rectb(TABLE_LEFT + shake_x, TABLE_TOP + shake_y,
                    TABLE_RIGHT - TABLE_LEFT, TABLE_BOTTOM - TABLE_TOP, 7)

        # SUPER mode rainbow borders
        if self._super_active():
            super_color = COLORS[(pyxel.frame_count // 6) % NUM_COLORS]
            pyxel.rectb(TABLE_LEFT + shake_x - 1, TABLE_TOP + shake_y - 1,
                        TABLE_RIGHT - TABLE_LEFT + 2, TABLE_BOTTOM - TABLE_TOP + 2, super_color)
            pyxel.rectb(TABLE_LEFT + shake_x - 2, TABLE_TOP + shake_y - 2,
                        TABLE_RIGHT - TABLE_LEFT + 4, TABLE_BOTTOM - TABLE_TOP + 4, super_color)

        # Net
        net_y = NET_Y + shake_y
        net_x = TABLE_LEFT + shake_x
        net_w = TABLE_RIGHT - TABLE_LEFT
        pyxel.rect(net_x, net_y - NET_HEIGHT // 2, net_w, NET_HEIGHT, 7)

        # Ghost trail
        for i, (gx, gy) in enumerate(self._ghost_trail):
            if i % 2 == 0:
                pyxel.pset(int(gx) + shake_x, int(gy) + shake_y, 12)

        # Ball trail
        b = self.ball
        for i, (tx, ty) in enumerate(b.trail):
            alpha = i / len(b.trail) if b.trail else 0
            tc = 13 if alpha < 0.5 else b.color
            pyxel.pset(int(tx) + shake_x, int(ty) + shake_y, tc)

        # Ball
        bx = int(b.x) + shake_x
        by = int(b.y) + shake_y
        if self._super_active():
            bc = COLORS[(pyxel.frame_count // 3) % NUM_COLORS]
        else:
            bc = b.color
        pyxel.circ(bx, by, BALL_R, bc)

        # AI paddle
        ac = COLORS[self.ai_color_idx]
        ai_px = int(self.ai_x - PADDLE_W // 2) + shake_x
        ai_py = AI_Y + shake_y
        pyxel.rect(ai_px, ai_py, PADDLE_W, PADDLE_H, ac)

        # Player paddle
        if self._super_active():
            pc = COLORS[(pyxel.frame_count // 4) % NUM_COLORS]
        else:
            pc = COLORS[self.player_color_idx]
        pl_px = int(self.player_x - PADDLE_W // 2) + shake_x
        pl_py = PLAYER_Y - PADDLE_H + shake_y
        pyxel.rect(pl_px, pl_py, PADDLE_W, PADDLE_H, pc)

        # Particles
        for p in self.particles:
            alpha = p.life / 25.0
            if alpha > 0.2:
                pyxel.pset(int(p.x) + shake_x, int(p.y) + shake_y, p.color if alpha > 0.5 else 13)

        # Floating texts
        for ft in self.floats:
            alpha = ft.life / 50.0
            if alpha > 0.1:
                tw = len(ft.text) * 4
                pyxel.text(int(ft.x) - tw // 2 + shake_x,
                           int(ft.y) + shake_y,
                           ft.text, ft.color)

        # HUD
        self._draw_hud()

    def _draw_hud(self) -> None:
        seconds = max(0, self.timer // 60)

        pyxel.text(4, 4, f"SCORE: {self.score}", 7)
        pyxel.text(120, 4, f"COMBO: {self.combo}", 7 if self.combo < 4 else 10)
        pyxel.text(240, 4, f"TIME: {seconds}s", 7)

        cname = COLOR_NAMES[self.player_color_idx]
        pyxel.text(4, 14, f"COLOR: {cname}", COLORS[self.player_color_idx])

        if self._super_active():
            st = self.super_timer // 60 + 1
            pyxel.text(120, 14, f"SUPER SPIN {st}s", 11)

        # HEAT bar at bottom
        bar_x = 10
        bar_y = SCREEN_H - 12
        bar_w = 300
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, 7)
        fill = int(self.heat / HEAT_MAX * (bar_w - 2))
        if fill > 0:
            if self.heat < 40:
                hc = 11
            elif self.heat < 70:
                hc = 9
            else:
                hc = 8
            pyxel.rect(bar_x + 1, bar_y + 1, fill, bar_h - 2, hc)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, "HEAT", 7)

    def _draw_game_over(self) -> None:
        pyxel.cls(0)
        reason = "TIME UP!" if self.timer <= 0 else "OVERHEAT!"
        pyxel.text(120, 50, "GAME OVER", 8)
        pyxel.text(130, 70, reason, 7)
        pyxel.text(100, 100, f"SCORE: {self.score}", 7)
        pyxel.text(80, 115, f"MAX COMBO: {self.max_combo}", 10)
        pyxel.text(80, 130, f"BEST RALLY: {self._best_rally}", 11)
        pyxel.text(80, 200, "Press ENTER to Retry", 7)

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()


def main() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="Ping Chain")
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
