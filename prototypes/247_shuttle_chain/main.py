"""247_shuttle_chain -- Badminton Color-Match COMBO Chain Game

Same-color consecutive returns build a COMBO chain.
COMBO >= 4 triggers SUPER SMASH -- rainbow mode, 3x score, super-speed shots.
HEAT risk system punishes mismatches. 60s match timer.
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass

import pyxel

# -- Constants ------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240
FPS = 60

GROUND_Y = 210
NET_X = 160
NET_HEIGHT = 60
NET_TOP_Y = GROUND_Y - NET_HEIGHT

PLAYER_X = 40
AI_X = 280
RACKET_LENGTH = 20
HIT_ZONE_MIN_Y = 60

GRAVITY = 0.15
DRAG = 0.995
MIN_VX = 0.5
TERMINAL_VY = 5.0
SHUTTLE_RADIUS = 4

COLORS = [8, 11, 5, 10]
COLOR_NAMES = ["RED", "LIME", "D. BLUE", "YELLOW"]
NUM_COLORS = 4

COMBO_THRESHOLD = 4
SUPER_DURATION = 300
SUPER_SCORE_MULT = 3

HEAT_MISMATCH = 15.0
HEAT_GROUND_PLAYER = 10.0
HEAT_DECAY = 0.02
HEAT_MAX = 100.0

MATCH_DURATION = 60 * FPS

AI_SPEED = 2.0
AI_BASE_CYCLE = 60
AI_MIN_CYCLE = 30

# -----------------------------------------------------------------------


class Phase(enum.Enum):
    TITLE = enum.auto()
    PLAYING = enum.auto()
    GAME_OVER = enum.auto()


@dataclass
class Shuttle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    active: bool = True


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
        self.timer: int = MATCH_DURATION
        self.heat: float = 0.0
        self.player_color: int = 0
        self.ai_color: int = 0
        self.ai_y: float = 170.0
        self.ai_color_timer: int = 0
        self.ai_reaction_timer: int = -1
        self.shuttle: Shuttle = Shuttle(0, 0, 0, 0, 0)
        self._last_hitter: str | None = None
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.rally_count: int = 0
        self.longest_rally: int = 0
        self.current_trail: list[tuple[float, float]] = []
        self.ghost_trail: list[tuple[float, float]] = []
        self._prev_shuttle_x: float = 0.0
        self._prev_shuttle_y: float = 0.0
        self._screen_shake: int = 0
        self._rng = random.Random(42)

    # -- Public API -------------------------------------------------------

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.timer = MATCH_DURATION
        self.heat = 0.0
        self.player_color = self._rng.randint(0, NUM_COLORS - 1)
        self.ai_color = self._rng.randint(0, NUM_COLORS - 1)
        self.ai_y = 170.0
        self.ai_color_timer = 0
        self.ai_reaction_timer = -1
        self.super_mode = False
        self.super_timer = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.rally_count = 0
        self.longest_rally = 0
        self.current_trail.clear()
        self.ghost_trail.clear()
        self._screen_shake = 0
        self._spawn_shuttle()

    def _spawn_shuttle(self) -> None:
        color = self._rng.choice(COLORS)
        self.shuttle = Shuttle(
            x=float(AI_X),
            y=self._rng.uniform(120, 180),
            vx=-3.0,
            vy=self._rng.uniform(-3.0, -1.0),
            color=color,
            active=True,
        )
        self._last_hitter = "ai"
        self._prev_shuttle_x = self.shuttle.x
        self._prev_shuttle_y = self.shuttle.y
        self.current_trail.clear()

    # -- Testable logic methods -------------------------------------------

    def _update_physics(self) -> None:
        s = self.shuttle
        if not s.active:
            return

        self._prev_shuttle_x = s.x
        self._prev_shuttle_y = s.y

        s.vx *= DRAG
        s.vy *= DRAG

        if abs(s.vx) < MIN_VX:
            s.vx = 0.0

        s.vy += GRAVITY
        if s.vy > TERMINAL_VY:
            s.vy = TERMINAL_VY
        if s.vy < -TERMINAL_VY:
            s.vy = -TERMINAL_VY

        s.x += s.vx
        s.y += s.vy

        if s.y >= GROUND_Y:
            s.y = float(GROUND_Y)
            s.vy = -abs(s.vy) * 0.5
            s.vx *= 0.8
            if s.x < NET_X:
                self.heat = min(HEAT_MAX, self.heat + HEAT_GROUND_PLAYER)

        if s.y < 0:
            s.y = 0.0
            s.vy = abs(s.vy) * 0.5

        prev_x = self._prev_shuttle_x
        curr_x = s.x
        crossed_right = prev_x < NET_X and curr_x >= NET_X
        crossed_left = prev_x > NET_X and curr_x <= NET_X

        if (crossed_right or crossed_left) and s.y >= NET_TOP_Y:
            s.vx = -s.vx * 0.6
            if crossed_right:
                s.x = float(NET_X) - 3.0
            else:
                s.x = float(NET_X) + 3.0

    def _check_player_hit(self) -> None:
        s = self.shuttle
        if not s.active:
            return
        if self._last_hitter != "ai":
            return

        in_zone = (
            PLAYER_X - 10 <= s.x <= PLAYER_X + 20
            and HIT_ZONE_MIN_Y <= s.y <= GROUND_Y
            and s.vx < 0
        )
        if not in_zone:
            return

        matched = s.color == COLORS[self.player_color] or self.super_mode
        if matched:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            mult = SUPER_SCORE_MULT if self.super_mode else 1
            points = int(10 * self.combo * mult)
            self.score += points

            speed = 4.0 + self.combo * 0.3
            if self.super_mode:
                speed = 6.0

            s.vx = speed
            s.vy = self._rng.uniform(-4.0, -2.0)
            s.color = COLORS[self.player_color]

            self._last_hitter = "player"
            self.rally_count += 1

            self._spawn_particles(s.x, s.y, s.color, 5)
            self._spawn_floating_text(s.x, s.y - 8, f"+{points}", 7, 30)

            if self.combo >= 2:
                self._spawn_floating_text(s.x, s.y - 18, f"C x{self.combo}", 10, 25)

            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self._activate_super()
        else:
            self.combo = 0
            self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
            self._screen_shake = 8
            s.vx = 1.5
            s.vy = self._rng.uniform(-2.0, -1.0)
            self._last_hitter = "player"
            self._spawn_floating_text(s.x, s.y - 8, "MISS!", 8, 20)

    def _check_ai_hit(self) -> None:
        s = self.shuttle
        if not s.active:
            return
        if self._last_hitter != "player":
            return

        in_zone = (
            AI_X - 20 <= s.x <= AI_X + 10
            and HIT_ZONE_MIN_Y <= s.y <= GROUND_Y
            and s.vx > 0
        )
        if not in_zone:
            if self.ai_reaction_timer >= 0:
                self.ai_reaction_timer = -1
            return

        if self.ai_reaction_timer == -1:
            progress = 1.0 - (self.timer / MATCH_DURATION)
            rmin = int(15 + (45 - 15) * (1.0 - progress))
            rmax = int(25 + (60 - 25) * (1.0 - progress))
            self.ai_reaction_timer = self._rng.randint(rmin, rmax)

    def _do_ai_hit(self) -> None:
        s = self.shuttle
        if not s.active:
            self.ai_reaction_timer = -1
            return

        matched = s.color == COLORS[self.ai_color]
        if matched:
            s.vx = -3.0
            s.vy = self._rng.uniform(-3.0, -1.5)
        else:
            s.vx = -1.5
            s.vy = self._rng.uniform(-1.5, -0.5)

        s.color = self._rng.choice(COLORS)
        self._last_hitter = "ai"
        self.rally_count += 1
        self._spawn_particles(s.x, s.y, s.color, 3)
        self.ai_reaction_timer = -1

    def _update_ai(self) -> None:
        progress = 1.0 - (self.timer / MATCH_DURATION)
        s = self.shuttle

        if self.ai_y < s.y:
            self.ai_y = min(s.y, self.ai_y + AI_SPEED)
        elif self.ai_y > s.y:
            self.ai_y = max(s.y, self.ai_y - AI_SPEED)

        cycle_interval = int(AI_BASE_CYCLE - (AI_BASE_CYCLE - AI_MIN_CYCLE) * progress)
        self.ai_color_timer += 1
        if self.ai_color_timer >= cycle_interval:
            self.ai_color_timer = 0
            self.ai_color = (self.ai_color + 1) % NUM_COLORS

        if self.ai_reaction_timer > 0:
            self.ai_reaction_timer -= 1
        elif self.ai_reaction_timer == 0:
            self._do_ai_hit()

    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_super_mode(self) -> None:
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self._spawn_floating_text(
            SCREEN_W // 2 - 40, 80, "SUPER SMASH!", 10, 40
        )

    def _update_particles(self) -> None:
        remaining: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                remaining.append(p)
        self.particles = remaining

    def _update_floating_texts(self) -> None:
        remaining: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                remaining.append(ft)
        self.floating_texts = remaining

    def _end_rally(self) -> None:
        if self.rally_count > self.longest_rally:
            self.longest_rally = self.rally_count
            self.ghost_trail = list(self.current_trail)
        self.rally_count = 0

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-1.5, 1.5),
                    vy=self._rng.uniform(-1.5, 1.5),
                    life=self._rng.randint(15, 25),
                    color=color,
                )
            )

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int, life: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=life, color=color)
        )

    # -- Update dispatch --------------------------------------------------

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()

    def _update_playing(self) -> None:
        if self._screen_shake > 0:
            self._screen_shake -= 1

        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return

        self._update_heat()
        self._update_super_mode()
        self._update_ai()
        self._update_physics()
        self._update_particles()
        self._update_floating_texts()

        self._check_player_hit()
        self._check_ai_hit()

        if self.shuttle.active:
            self.current_trail.append((self.shuttle.x, self.shuttle.y))

        s = self.shuttle
        dead = (
            s.x < -30
            or s.x > SCREEN_W + 30
            or (abs(s.vx) < 0.1 and abs(s.vy) < 0.1 and s.y > GROUND_Y - 8)
        )
        if dead:
            self._end_rally()
            self._spawn_shuttle()

        if pyxel.btnp(pyxel.KEY_UP):
            self.player_color = (self.player_color + 1) % NUM_COLORS
        if pyxel.btnp(pyxel.KEY_DOWN):
            self.player_color = (self.player_color - 1) % NUM_COLORS

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()

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
        pyxel.text(100, 50, "SHUTTLE CHAIN", 7)
        pyxel.text(80, 75, "Color-Match Badminton", 13)
        pyxel.text(70, 110, "Cycle racket color with", 7)
        pyxel.text(75, 122, "UP / DOWN to match shuttle", 7)
        pyxel.text(60, 140, "Same-color returns = COMBO!", 10)
        pyxel.text(55, 155, "COMBO x4 = SUPER SMASH!", 11)
        pyxel.text(95, 180, "Controls:", 7)
        pyxel.text(100, 195, "UP/DOWN: Cycle color", 13)
        pyxel.text(85, 220, "Press ENTER to Start", 11)

    def _draw_playing(self) -> None:
        shake_x = 0
        shake_y = 0
        if self._screen_shake > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)

        pyxel.cls(0)

        # Court floor
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, 4)

        # Net
        pyxel.rect(NET_X - 1, NET_TOP_Y, 3, GROUND_Y - NET_TOP_Y, 7)
        pyxel.rect(NET_X - 4, NET_TOP_Y, 9, 4, 7)

        # Ghost trail
        for i, (gx, gy) in enumerate(self.ghost_trail):
            if i % 3 == 0:
                pyxel.pset(int(gx) + shake_x, int(gy) + shake_y, 12)

        # Player (triangle pointing right)
        pc = COLORS[self.player_color]
        px = PLAYER_X + shake_x
        py = 180 + shake_y
        pyxel.tri(px - 8, py - 10, px - 8, py + 10, px + 12, py, pc)

        # AI (triangle pointing left)
        ac = COLORS[self.ai_color]
        ax = AI_X + shake_x
        ay = int(self.ai_y) + shake_y
        pyxel.tri(ax + 8, ay - 10, ax + 8, ay + 10, ax - 12, ay, ac)

        # Shuttle
        if self.shuttle.active:
            sx = int(self.shuttle.x) + shake_x
            sy = int(self.shuttle.y) + shake_y
            sc = self.shuttle.color
            if self.super_mode:
                sc = (pyxel.frame_count // 4) % len(COLORS)
                sc = COLORS[sc]
            pyxel.tri(sx, sy - 4, sx + 3, sy, sx, sy + 4, sc)
            pyxel.tri(sx, sy - 4, sx - 3, sy, sx, sy + 4, sc)

        # Particles
        for p in self.particles:
            if p.life >= 5:
                c = p.color if p.life > 12 else 13
                pyxel.rect(int(p.x) + shake_x, int(p.y) + shake_y, 2, 2, c)

        # Floating texts
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            if alpha > 0.2:
                pyxel.text(
                    int(ft.x) + shake_x - len(ft.text) * 2,
                    int(ft.y) + shake_y,
                    ft.text,
                    ft.color,
                )

        # HUD
        self._draw_hud()

    def _draw_hud(self) -> None:
        seconds = max(0, self.timer // FPS)
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)
        pyxel.text(130, 4, f"TIME: {seconds}", 7)
        if self.combo > 0:
            pyxel.text(250, 4, f"C: {self.combo}", 10)
        else:
            pyxel.text(250, 4, f"C: {self.combo}", 13)

        cname = COLOR_NAMES[self.player_color]
        pyxel.text(4, 14, f"RACKET: {cname}", COLORS[self.player_color])

        if self.super_mode:
            st = self.super_timer // FPS
            pyxel.text(130, 24, f"SUPER {st}s", 11)

        # HEAT bar
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
                hc = 10
            else:
                hc = 8
            pyxel.rect(bar_x + 1, bar_y + 1, fill, bar_h - 2, hc)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, "HEAT", 7)

    def _draw_game_over(self) -> None:
        pyxel.cls(0)
        reason = "TIME UP!" if self.timer <= 0 else "OVERHEAT!"
        pyxel.text(110, 50, "GAME OVER", 8)
        pyxel.text(125, 70, reason, 7)
        pyxel.text(100, 100, f"SCORE: {self.score}", 7)
        pyxel.text(80, 115, f"MAX COMBO: {self.max_combo}", 10)
        pyxel.text(80, 130, f"LONGEST RALLY: {self.longest_rally}", 11)
        pyxel.text(80, 200, "Press ENTER to Retry", 7)

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()


def main() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="Shuttle Chain")
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
