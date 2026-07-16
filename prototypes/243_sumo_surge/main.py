"""100_sumo_surge -- Top-Down Sumo Wrestling Color-Match Combo Prototype

The most fun moment:
    相手を土俵際ギリギリまで押し込み、同色連続突きでSUPER SUMOを発動させて
    圧倒的なパワーで吹き飛ばす瞬間が面白い
    (Push opponent to the edge, chain same-color shoves into SUPER SUMO,
    then blast them out with 3x power for massive score.)

Core loop: Move wrestler with arrow keys, SPACE to shove. Same-color consecutive
shoves build COMBO. COMBO >= 4 triggers SUPER SUMO (rainbow mode, any-color match,
3x power, stamina cost halved). Push opponent out of the ring to score.
60-second timer and HEAT system create urgency.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240

DOHYO_CX = 160
DOHYO_CY = 120
DOHYO_RADIUS = 100
WRESTLER_RADIUS = 18

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

COLORS = (RED, LIME, DARK_BLUE, YELLOW)
COLOR_NAMES = ("RED", "LIME", "DARK_BLUE", "YELLOW")

SUPER_COMBO_THRESHOLD = 4
SUPER_DURATION = 300
GAME_TIMER = 3600  # 60 seconds at 60fps
HEAT_CAP = 100
HEAT_DECAY = 0.02

COLOR_CYCLE_BASE = 90
STAMINA_MAX = 100.0
STAMINA_COST = 20.0
STAMINA_COST_SUPER = 10.0
STAMINA_REGEN_PLAYER = 0.08
STAMINA_REGEN_OPPONENT = 0.05

PLAYER_SPEED = 1.0
PLAYER_SPEED_PUSHING = 1.5
PLAYER_POWER = 3.0
PLAYER_POWER_SUPER = 5.0
OPPONENT_SPEED = 0.6
OPPONENT_POWER = 2.0
OPPONENT_AI_DISTANCE = 80
PUSH_COOLDOWN = 15

RING_OUT_BONUS = 500
RING_OUT_PENALTY_HEAT = 25
MISS_HEAT = 15
SHAVE_HEAT = 5

RAINBOW_COLORS = (RED, ORANGE, YELLOW, LIME, CYAN, PINK)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = "TITLE"
    PLAYING = "PLAYING"
    SUPER_ANIM = "SUPER_ANIM"
    GAME_OVER = "GAME_OVER"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Wrestler:
    x: float
    y: float
    radius: float = 18
    power: float = 0
    direction: float = 0
    color_idx: int = 0
    stamina: float = 100.0
    stunned: int = 0
    pushing: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SUMO SURGE")
        self._rng: random.Random = random.Random()
        self._init_state()
        pyxel.run(self._update, self._draw)

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.max_score: int = 0
        self.heat: float = 0.0
        self.timer: int = GAME_TIMER
        self.super_timer: int = 0
        self.color_timer: int = COLOR_CYCLE_BASE
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self.opponent_defeated: int = 0
        self._push_cooldown: int = 0
        self._opponent_ai_timer: int = 0
        self._opponent_color_idx: int = 0
        self.player = Wrestler(x=160.0, y=160.0, stamina=STAMINA_MAX)
        self.opponent = Wrestler(x=160.0, y=80.0, stamina=STAMINA_MAX)

    def reset(self) -> None:
        self._init_state()
        self._spawn_opponent()

    def _spawn_opponent(self) -> None:
        angle = self._rng.uniform(-0.8, 0.8) - 1.57
        dist = self._rng.uniform(30, 70)
        self.opponent.x = DOHYO_CX + math.cos(angle) * dist
        self.opponent.y = DOHYO_CY + math.sin(angle) * dist
        self.opponent.stamina = STAMINA_MAX
        self.opponent.power = 0
        self.opponent.stunned = 0
        self.opponent.color_idx = self._rng.randint(0, 3)
        self._opponent_ai_timer = self._rng.randint(20, 60)
        self._opponent_color_idx = self.opponent.color_idx

    # ------------------------------------------------------------------
    # Testable logic (no pyxel input calls)
    # ------------------------------------------------------------------

    def _clamp_to_dohyo(self, w: Wrestler) -> None:
        dist = math.hypot(w.x - DOHYO_CX, w.y - DOHYO_CY)
        if dist > DOHYO_RADIUS - w.radius:
            angle = math.atan2(w.y - DOHYO_CY, w.x - DOHYO_CX)
            w.x = DOHYO_CX + math.cos(angle) * (DOHYO_RADIUS - w.radius)
            w.y = DOHYO_CY + math.sin(angle) * (DOHYO_RADIUS - w.radius)

    def _resolve_hit(self, player_is_attacker: bool) -> None:
        if player_is_attacker:
            color_match = self.player.color_idx == self.opponent.color_idx
        else:
            color_match = self.opponent.color_idx == self.player.color_idx

        if color_match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            mult = 3 if self.super_timer > 0 else 1
            points = 100 * self.combo * mult
            self.score += points
            self.max_score = max(self.max_score, self.score)
            # Check SUPER activation
            if self.combo >= SUPER_COMBO_THRESHOLD and self.super_timer <= 0:
                self.super_timer = SUPER_DURATION
        else:
            self.combo = 0
            self.heat += MISS_HEAT

    def _check_ring_out(self) -> None:
        p_dist = math.hypot(self.player.x - DOHYO_CX, self.player.y - DOHYO_CY)
        o_dist = math.hypot(self.opponent.x - DOHYO_CX, self.opponent.y - DOHYO_CY)

        if o_dist > DOHYO_RADIUS:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            mult = 3 if self.super_timer > 0 else 1
            bonus = RING_OUT_BONUS * mult + 100 * self.combo * mult
            self.score += bonus
            self.max_score = max(self.max_score, self.score)
            self.opponent_defeated += 1
            self.shake_frames = 10
            self._spawn_opponent()
            self.player.pushing = False
            self.player.power = 0
            self.opponent.pushing = False
            self.opponent.power = 0

        if p_dist > DOHYO_RADIUS:
            self.combo = 0
            self.heat += RING_OUT_PENALTY_HEAT
            self.shake_frames = 8
            self.player.x = DOHYO_CX
            self.player.y = DOHYO_CY + 40
            self.player.stunned = 0
            self.player.pushing = False
            self.player.power = 0
            self.opponent.pushing = False
            self.opponent.power = 0

    def _get_push_direction(self, from_x: float, from_y: float, to_x: float, to_y: float) -> float:
        dx = to_x - from_x
        dy = to_y - from_y
        dist = math.hypot(dx, dy)
        if dist > 0:
            return math.atan2(dy, dx)
        return 0.0

    # ------------------------------------------------------------------
    # Particles & floating text
    # ------------------------------------------------------------------

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 3.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=self._rng.randint(10, 30),
                color=color,
                size=self._rng.randint(1, 3),
            ))

    def _add_floating_text(self, x: float, y: float, text: str, life: int, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=life, color=color))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 1.0
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _update(self) -> None:
        if self.shake_frames > 0:
            self.shake_frames -= 1
            try:
                shx = self._rng.randint(-3, 3) if self.shake_frames > 0 else 0
                shy = self._rng.randint(-2, 2) if self.shake_frames > 0 else 0
                pyxel.camera(shx, shy)
            except BaseException:
                pass
        else:
            try:
                pyxel.camera(0, 0)
            except BaseException:
                pass

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.SUPER_ANIM:
            self._update_super_anim()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.phase = Phase.PLAYING

    def _update_super_anim(self) -> None:
        self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self._end_game()
            return

        self.heat = max(0.0, self.heat - HEAT_DECAY)

        if self.heat >= HEAT_CAP:
            self._end_game()
            return

        if self.super_timer > 0:
            self.super_timer -= 1

        self.color_timer -= 1
        if self.color_timer <= 0:
            self.color_timer = max(40, COLOR_CYCLE_BASE - self.opponent_defeated * 5)
            self.player.color_idx = (self.player.color_idx + 1) % 4

        if self._push_cooldown > 0:
            self._push_cooldown -= 1

        self._update_player_movement()
        self._update_player_shove()
        self._update_opponent_ai()

        # Physics / collision resolution
        self._update_physics()
        self._check_ring_out()

        self._update_particles()
        self._update_floating_texts()

        self.player.stamina = min(STAMINA_MAX, self.player.stamina + STAMINA_REGEN_PLAYER)
        self.opponent.stamina = min(STAMINA_MAX, self.opponent.stamina + STAMINA_REGEN_OPPONENT)

        if self.player.stunned > 0:
            self.player.stunned -= 1
        if self.opponent.stunned > 0:
            self.opponent.stunned -= 1

    def _update_player_movement(self) -> None:
        if self.player.stunned > 0:
            return
        speed = PLAYER_SPEED_PUSHING if self.player.pushing else PLAYER_SPEED
        dx: float = 0.0
        dy: float = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -speed
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = speed
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -speed
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = speed

        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707

        self.player.x += dx
        self.player.y += dy
        self._clamp_to_dohyo(self.player)

    def _update_player_shove(self) -> None:
        if not (pyxel.btnp(pyxel.KEY_SPACE) and self._push_cooldown <= 0 and self.player.stunned <= 0):
            return

        is_super = self.super_timer > 0
        cost = STAMINA_COST_SUPER if is_super else STAMINA_COST
        if self.player.stamina >= cost:
            self.player.stamina = max(0.0, self.player.stamina - cost)
            self.player.pushing = True
            self.player.power = PLAYER_POWER_SUPER if is_super else PLAYER_POWER
            self.player.direction = self._get_push_direction(
                self.player.x, self.player.y, self.opponent.x, self.opponent.y,
            )
            self._push_cooldown = PUSH_COOLDOWN
            self._spawn_particles(self.player.x, self.player.y, 5, COLORS[self.player.color_idx])

    def _update_opponent_ai(self) -> None:
        if self.opponent.stunned > 0:
            return

        dx = self.player.x - self.opponent.x
        dy = self.player.y - self.opponent.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            speed = OPPONENT_SPEED + self.opponent_defeated * 0.05
            self.opponent.x += (dx / dist) * speed
            self.opponent.y += (dy / dist) * speed

        self._clamp_to_dohyo(self.opponent)

        self._opponent_ai_timer -= 1
        if self._opponent_ai_timer <= 0 and dist < OPPONENT_AI_DISTANCE:
            self.opponent.pushing = True
            self.opponent.power = OPPONENT_POWER + self.opponent_defeated * 0.3
            self.opponent.direction = math.atan2(dy, dx)
            self._opponent_ai_timer = max(15, 50 - self.opponent_defeated * 3)
            self._spawn_particles(self.opponent.x, self.opponent.y, 3, COLORS[self.opponent.color_idx])

    def _update_physics(self) -> None:
        dx = self.opponent.x - self.player.x
        dy = self.opponent.y - self.player.y
        dist = math.hypot(dx, dy)
        min_dist = WRESTLER_RADIUS * 2

        if dist < min_dist and dist > 0:
            overlap = min_dist - dist

            player_push = self.player.power if self.player.pushing else 0.0
            opponent_push = self.opponent.power if self.opponent.pushing else 0.0

            if player_push > opponent_push:
                push_x = (dx / dist) * (overlap + player_push * 2)
                push_y = (dy / dist) * (overlap + player_push * 2)
                self.opponent.x += push_x
                self.opponent.y += push_y
                self.opponent.stunned = max(self.opponent.stunned, 10)
                self._resolve_hit(player_is_attacker=True)
                self.player.pushing = False
                self.player.power = 0
            elif opponent_push > player_push:
                push_x = (-dx / dist) * (overlap + opponent_push * 2)
                push_y = (-dy / dist) * (overlap + opponent_push * 2)
                self.player.x += push_x
                self.player.y += push_y
                self.player.stunned = max(self.player.stunned, 8)
                self._resolve_hit(player_is_attacker=False)
                self.opponent.pushing = False
                self.opponent.power = 0
            else:
                sep_x = (dx / dist) * overlap * 0.5
                sep_y = (dy / dist) * overlap * 0.5
                self.player.x -= sep_x
                self.player.y -= sep_y
                self.opponent.x += sep_x
                self.opponent.y += sep_y

            self._clamp_to_dohyo(self.player)
            self._clamp_to_dohyo(self.opponent)

        if self.player.pushing:
            self.player.pushing = False
        if self.opponent.pushing:
            self.opponent.pushing = False

    def _end_game(self) -> None:
        self.max_score = max(self.max_score, self.score)
        self.phase = Phase.GAME_OVER
        self.shake_frames = 15
        self._spawn_particles(DOHYO_CX, DOHYO_CY, 30, RED)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_dohyo(self) -> None:
        pyxel.circb(DOHYO_CX, DOHYO_CY, DOHYO_RADIUS, DARK_BLUE)
        pyxel.circ(DOHYO_CX, DOHYO_CY, DOHYO_RADIUS, BROWN)
        # Outer ring highlight
        pyxel.circb(DOHYO_CX, DOHYO_CY, DOHYO_RADIUS - 1, LIGHT_BLUE)
        # Inner circle (center marking)
        pyxel.circb(DOHYO_CX, DOHYO_CY, 10, WHITE)

        # SUPER mode: rainbow border
        if self.super_timer > 0:
            segments = len(RAINBOW_COLORS)
            for i in range(segments):
                angle_start = (pyxel.frame_count * 2 + i * (360 // segments)) % 360
                angle_end = angle_start + (360 // segments)
                c = RAINBOW_COLORS[i]
                for a in range(angle_start, angle_end, 2):
                    rad = math.radians(a)
                    px = int(DOHYO_CX + math.cos(rad) * DOHYO_RADIUS)
                    py2 = int(DOHYO_CY + math.sin(rad) * DOHYO_RADIUS)
                    pyxel.pset(px, py2, c)

    def _draw_wrestler(self, w: Wrestler, facing_up: bool) -> None:
        cx = int(w.x)
        cy = int(w.y)
        r = WRESTLER_RADIUS

        # Stun flash
        stunned = w.stunned > 0 and (pyxel.frame_count // 4) % 2 == 0

        # Body color
        body_color = COLORS[w.color_idx]
        if self.super_timer > 0:
            # Rainbow body flash
            idx = (pyxel.frame_count // 6) % len(RAINBOW_COLORS)
            body_color = RAINBOW_COLORS[idx]

        # Body circle (filled)
        pyxel.circ(cx, cy, r, body_color)
        if stunned:
            pyxel.circb(cx, cy, r + 1, WHITE)

        # Mawashi (belt band) — triangle
        if facing_up:
            # Belt at bottom, triangle pointing down
            pyxel.tri(cx - 6, cy + r - 6, cx + 6, cy + r - 6, cx, cy + r - 2, WHITE)
        else:
            # Belt at top, triangle pointing up
            pyxel.tri(cx - 6, cy - r + 6, cx + 6, cy - r + 6, cx, cy - r + 2, WHITE)

        # Face: simple eyes
        eye_y = cy - 4 if facing_up else cy + 4
        pyxel.pset(cx - 3, eye_y - 1, WHITE)
        pyxel.pset(cx + 3, eye_y - 1, WHITE)

        # STAMINA bar (below wrestler)
        bar_w = 30
        bar_h = 3
        bar_x = cx - bar_w // 2
        bar_y = cy + r + 3
        ratio = w.stamina / STAMINA_MAX
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        pyxel.rect(bar_x, bar_y, int(bar_w * ratio), bar_h, GREEN)

        # Stunned indicator
        if w.stunned > 0:
            pyxel.text(cx - 4, cy - r - 10, "X", RED)

    def _draw_hud(self) -> None:
        # Score (top-left)
        pyxel.text(4, 2, f"SCORE:{self.score}", WHITE)

        # COMBO (below score)
        combo_text = f"COMBO:{self.combo}"
        combo_color = YELLOW if self.combo >= SUPER_COMBO_THRESHOLD else (ORANGE if self.combo >= 2 else WHITE)
        pyxel.text(4, 10, combo_text, combo_color)

        # Timer (top-center)
        secs = max(0, self.timer // 60)
        timer_text = f"TIME:{secs:02d}"
        tw = len(timer_text) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 2, timer_text, WHITE if secs > 10 else RED)

        # HEAT bar (top-right)
        bar_w = 60
        bar_h = 6
        bar_x = SCREEN_W - bar_w - 4
        bar_y = 4
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        fill = int(bar_w * (self.heat / HEAT_CAP))
        heat_color = RED if self.heat > 70 else (ORANGE if self.heat > 40 else YELLOW)
        pyxel.rect(bar_x, bar_y, fill, bar_h, heat_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.text(bar_x - 22, bar_y - 1, "HEAT", RED)

        # SUPER timer
        if self.super_timer > 0:
            super_text = f"SUPER:{self.super_timer // 60 + 1}s"
            sw = len(super_text) * 4
            pyxel.text(SCREEN_W // 2 - sw // 2, 12, super_text, YELLOW)

        # Current color indicator (bottom-left)
        pyxel.text(4, SCREEN_H - 20, "COLOR:", WHITE)
        pyxel.rect(40, SCREEN_H - 19, 10, 10, COLORS[self.player.color_idx])
        pyxel.rectb(40, SCREEN_H - 19, 10, 10, WHITE)

        # Stamina percent
        pct = int(self.player.stamina)
        pyxel.text(4, SCREEN_H - 10, f"STA:{pct}%", GREEN)

        # Opponents defeated
        def_text = f"WINS:{self.opponent_defeated}"
        pyxel.text(SCREEN_W - len(def_text) * 4 - 4, SCREEN_H - 10, def_text, CYAN)

    def _draw_particles_visual(self) -> None:
        for p in self.particles:
            alpha = p.life / 30.0
            c = p.color if alpha > 0.3 else GRAY
            pyxel.rect(int(p.x), int(p.y), p.size, p.size, c)

    def _draw_floating_texts_visual(self) -> None:
        for ft in self.floating_texts:
            alpha = min(1.0, ft.life / 40.0)
            c = ft.color if alpha > 0.4 else GRAY
            tw = len(ft.text) * 4
            pyxel.text(int(ft.x) - tw // 2, int(ft.y), ft.text, c)

    def _draw_title(self) -> None:
        title = "SUMO SURGE"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 30, title, WHITE)

        subtitle = "Color-Match Sumo Wrestling"
        sw = len(subtitle) * 4
        pyxel.text(SCREEN_W // 2 - sw // 2, 44, subtitle, GRAY)

        # Color legend
        for i, (col, name) in enumerate(zip(COLORS, COLOR_NAMES)):
            bx = 40 + i * 63
            pyxel.rect(bx, 60, 12, 12, col)
            pyxel.rectb(bx, 60, 12, 12, WHITE)
            nw = len(name) * 4
            pyxel.text(bx + 6 - nw // 2, 75, name, WHITE)

        lines = [
            "ARROW / WASD: Move",
            "SPACE: Shove (costs STAMINA)",
            "",
            "Push opponent out of the ring!",
            "",
            "Same-color shove = COMBO UP!",
            "Wrong color shove = MISS + HEAT",
            f"COMBO>={SUPER_COMBO_THRESHOLD} = SUPER SUMO!",
            "  (rainbow, 3x score, half cost)",
            "",
            "HEAT>=100 or TIME=0 = GAME OVER",
            "",
            "SPACE to START",
        ]
        for i, ln in enumerate(lines):
            pyxel.text(50, 90 + i * 11, ln, GRAY if i < len(lines) - 2 else WHITE)

    def _draw_playing(self) -> None:
        self._draw_dohyo()
        # Player (bottom area, facing up)
        self._draw_wrestler(self.player, facing_up=True)
        # Opponent (top area, facing down)
        self._draw_wrestler(self.opponent, facing_up=False)
        self._draw_particles_visual()
        self._draw_floating_texts_visual()
        self._draw_hud()

    def _draw_game_over(self) -> None:
        # Dim the dohyo
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)

        go_text = "GAME OVER"
        gw = len(go_text) * 4
        pyxel.text(SCREEN_W // 2 - gw // 2, 40, go_text, RED)

        def _ctr(y: int, text: str, color: int) -> None:
            pyxel.text(SCREEN_W // 2 - len(text) * 2, y, text, color)

        _ctr(70, f"SCORE: {self.score}", WHITE)
        _ctr(90, f"BEST SCORE: {self.max_score}", YELLOW)
        _ctr(110, f"MAX COMBO: {self.max_combo}", ORANGE)
        _ctr(130, f"OPPONENTS DEFEATED: {self.opponent_defeated}", CYAN)
        super_yes = "YES" if self.max_combo >= SUPER_COMBO_THRESHOLD else "NO"
        _ctr(150, f"SUPER REACHED: {super_yes}", LIME)

        secs = max(0, self.timer // 60)
        _ctr(170, f"TIME LEFT: {secs}s", GRAY)

        _ctr(200, "SPACE to RETRY", WHITE)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    Game()


if __name__ == "__main__":
    main()
