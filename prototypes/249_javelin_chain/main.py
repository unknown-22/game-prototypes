"""249_javelin_chain -- Javelin Throw Color-Match COMBO Chain Game

Olympic javelin throw meets color-matching COMBO chain.
Player throws javelins at colored landing zones.
Same-color consecutive hits build COMBO -> SUPER THROW.
STAMINA as "future hand as cost" resource. HEAT as risk system.
"""

from __future__ import annotations

import enum
import math
import random
from dataclasses import dataclass
from pathlib import Path

import pyxel

SCREEN_W = 320
SCREEN_H = 240
COLORS = (8, 11, 5, 10)
COLOR_NAMES = ("RED", "LIME", "D BLUE", "YELLOW")
NUM_COLORS = 4

THROWER_X = 40
THROWER_Y = 180
GROUND_Y = 200
GRAVITY = 0.2
POWER_MAX = 12.0
POWER_MIN = 3.0
VELOCITY_SCALE = 0.5
POWER_CHARGE_FRAMES = 60
CHARGE_RATE = 100.0 / POWER_CHARGE_FRAMES
NUM_ZONES = 6
ZONE_RADIUS = 18
ZONE_MIN_X = 120
ZONE_MAX_X = 300
COMBO_THRESHOLD = 4
SUPER_DURATION = 300
GAME_DURATION = 60 * 60
STAMINA_MAX = 100.0
STAMINA_COST = 25.0
STAMINA_RECHARGE = 0.15
HEAT_MAX = 100.0
HEAT_MISMATCH = 15.0
HEAT_FAULT = 20.0
HEAT_DECAY = 0.02
WIND_CHANGE_INTERVAL = 3
WIND_FORCE = 0.03
SCORING_FRAMES = 30


class Phase(enum.Enum):
    TITLE = enum.auto()
    AIMING = enum.auto()
    FLYING = enum.auto()
    SCORING = enum.auto()
    GAME_OVER = enum.auto()


@dataclass
class LandingZone:
    x: float
    y: float
    radius: float
    color: int
    active: bool = True


@dataclass
class Javelin:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    angle: float = 0.0
    landed: bool = False
    hit_zone_idx: int = -1


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


class Game:
    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.timer: int = GAME_DURATION
        self.heat: float = 0.0
        self.stamina: float = STAMINA_MAX
        self.zones: list[LandingZone] = []
        self.javelin: Javelin | None = None
        self.javelin_color_idx: int = 0
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self._charging: bool = False
        self._charge_power: float = 0.0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.wind_dir: float = 0.0
        self.wind_speed: float = 0.0
        self._throw_count: int = 0
        self._scoring_timer: int = 0
        self._screen_shake: int = 0
        self._rng: random.Random = random.Random(42)
        self._last_matched: bool = False
        self._last_fault: bool = False

    # -- Public API -------------------------------------------------------

    def reset(self) -> None:
        """Reset game state for a new play session."""
        self.phase = Phase.AIMING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.timer = GAME_DURATION
        self.heat = 0.0
        self.stamina = STAMINA_MAX
        self.javelin = None
        self.javelin_color_idx = self._rng.randint(0, NUM_COLORS - 1)
        self.particles.clear()
        self.floats.clear()
        self._charging = False
        self._charge_power = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.wind_dir = self._rng.uniform(-1.0, 1.0)
        self.wind_speed = self._rng.uniform(0.0, 3.0)
        self._throw_count = 0
        self._scoring_timer = 0
        self._screen_shake = 0
        self._last_matched = False
        self._last_fault = False
        self._spawn_zones()

    # -- Testable logic methods -------------------------------------------

    def _spawn_zones(self) -> None:
        """Generate landing zones with random positions and colors."""
        self.zones.clear()
        r = self._rng
        xs: list[float] = []
        min_gap = ZONE_RADIUS * 3
        for _ in range(NUM_ZONES):
            for _attempt in range(50):
                x = r.uniform(ZONE_MIN_X, ZONE_MAX_X)
                if all(abs(x - ex) >= min_gap for ex in xs):
                    xs.append(x)
                    break
            else:
                xs.append(r.uniform(ZONE_MIN_X, ZONE_MAX_X))
        xs.sort()
        for x in xs:
            color = r.choice(COLORS)
            self.zones.append(
                LandingZone(x=x, y=float(GROUND_Y), radius=float(ZONE_RADIUS), color=color, active=True)
            )

    def _compute_javelin_velocity(self, power: float, angle: float) -> tuple[float, float]:
        """Compute vx, vy from power and angle."""
        actual_power = power
        if self.stamina < STAMINA_COST:
            actual_power = min(actual_power, POWER_MAX * 0.5)
        vx = actual_power * math.cos(angle) * VELOCITY_SCALE
        vy = -actual_power * math.sin(angle) * VELOCITY_SCALE
        return vx, vy

    def _throw_javelin(self, power: float, angle: float) -> Javelin:
        """Create a javelin with computed trajectory."""
        vx, vy = self._compute_javelin_velocity(power, angle)
        color = COLORS[self.javelin_color_idx]
        return Javelin(x=float(THROWER_X), y=float(THROWER_Y), vx=vx, vy=vy, color=color, angle=angle)

    def _update_javelin(self) -> None:
        """Apply gravity + wind, check landing."""
        if self.javelin is None or self.javelin.landed:
            return
        j = self.javelin
        j.x += j.vx
        j.y += j.vy
        j.vy += GRAVITY
        j.vx += self.wind_dir * self.wind_speed * WIND_FORCE
        if j.y >= GROUND_Y:
            j.y = float(GROUND_Y)
            j.landed = True
            self._on_landing()

    def _on_landing(self) -> None:
        """Handle landing logic. Check which zone was hit and compute score."""
        if self.javelin is None:
            return
        j = self.javelin
        land_x = j.x
        land_y = j.y

        matched: bool = False
        fault: bool = True

        for i, zone in enumerate(self.zones):
            if not zone.active:
                continue
            dist = math.hypot(land_x - zone.x, land_y - zone.y)
            if dist <= zone.radius:
                fault = False
                matched = (zone.color == COLORS[self.javelin_color_idx]) or self.super_mode
                zone.active = False
                break

        self._last_matched = matched
        self._last_fault = fault

        if fault:
            self._add_heat(HEAT_FAULT)
            self.combo = 0
            self._spawn_float(land_x, land_y - 20, "FAULT!", 8, 40)
        elif matched:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            mult = 3 if self.super_mode else 1
            points = int(100 * self.combo * mult)
            self.score += points
            self._spawn_float(land_x, land_y - 10, f"+{points}", 10, 35)
            if self.combo >= 2:
                self._spawn_float(land_x, land_y - 24, f"COMBO x{self.combo}!", 9, 35)
            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self._activate_super()
            self._spawn_particles(land_x, land_y, COLORS[self.javelin_color_idx], 10)
        else:
            # Mismatch: hit a zone but wrong color
            self._add_heat(HEAT_MISMATCH)
            self.combo = 0
            self._spawn_float(land_x, land_y - 10, "MISS!", 8, 30)
            self._spawn_particles(land_x, land_y, 13, 5)

        self.javelin_color_idx = (self.javelin_color_idx + 1) % NUM_COLORS
        self._throw_count += 1
        if self._throw_count >= WIND_CHANGE_INTERVAL:
            self._throw_count = 0
            self.wind_dir = self._rng.uniform(-1.0, 1.0)
            self.wind_speed = self._rng.uniform(0.0, 3.0)
        self.stamina = max(0.0, self.stamina - STAMINA_COST)
        self.phase = Phase.SCORING
        self._scoring_timer = SCORING_FRAMES

    def _add_heat(self, amount: float) -> None:
        if not self.super_mode:
            self.heat = min(HEAT_MAX, self.heat + amount)

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self._spawn_float(SCREEN_W // 2 - 45, 60, "SUPER THROW!", 9, 50)

    def _update_stamina(self) -> None:
        self.stamina = min(STAMINA_MAX, self.stamina + STAMINA_RECHARGE)

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER

    def _update_super_mode(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self.super_mode = False

    def _update_particles(self) -> None:
        remaining: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
            if p.life > 0:
                remaining.append(p)
        self.particles = remaining

    def _update_floating_texts(self) -> None:
        remaining: list[FloatingText] = []
        for ft in self.floats:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                remaining.append(ft)
        self.floats = remaining

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-1.5, 1.5),
                    vy=self._rng.uniform(-2.0, -0.5),
                    life=self._rng.randint(12, 25),
                    color=color,
                )
            )

    def _spawn_float(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.floats.append(FloatingText(x=x, y=y, text=text, life=life, color=color))

    def _check_game_over(self) -> bool:
        if self.timer <= 0 or self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return True
        return False

    def _respawn_zones_if_needed(self) -> None:
        active_count = sum(1 for z in self.zones if z.active)
        if active_count < 3:
            self._spawn_zones()

    # -- Update dispatch --------------------------------------------------

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()

    def _update_aiming(self) -> None:
        self.timer -= 1
        if self._check_game_over():
            return
        self._update_heat()
        if self.phase != Phase.AIMING:
            return
        self._update_stamina()
        self._update_super_mode()
        self._update_particles()
        self._update_floating_texts()

        mouse_pressed = pyxel.btn(pyxel.MOUSE_BUTTON_LEFT)

        if mouse_pressed and not self._charging:
            self._charging = True
            self._charge_power = 0.0
        elif mouse_pressed and self._charging:
            self._charge_power = min(100.0, self._charge_power + CHARGE_RATE)
        elif not mouse_pressed and self._charging:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            dx = float(mx - THROWER_X)
            dy = float(THROWER_Y - my)
            if dx < 1.0:
                dx = 1.0
            angle = math.atan2(dy, dx)
            angle = max(0.05, min(angle, 1.2))
            actual_power = POWER_MIN + (POWER_MAX - POWER_MIN) * (self._charge_power / 100.0)
            if self.stamina < STAMINA_COST:
                actual_power = min(actual_power, POWER_MAX * 0.5)
            self.javelin = self._throw_javelin(actual_power, angle)
            self.phase = Phase.FLYING
            self._charging = False
            self._charge_power = 0.0

    def _update_flying(self) -> None:
        self.timer -= 1
        if self._check_game_over():
            return
        self._update_javelin()
        self._update_super_mode()
        self._update_particles()
        self._update_floating_texts()
        self._update_stamina()
        self._update_heat()
        if self.phase != Phase.FLYING:  # landed via _on_landing -> SCORING
            return

    def _update_scoring(self) -> None:
        if self._check_game_over():
            return
        self._update_super_mode()
        self._update_particles()
        self._update_floating_texts()
        self._update_stamina()
        self._update_heat()
        if self.phase != Phase.SCORING:
            return
        self._scoring_timer -= 1
        if self._scoring_timer <= 0:
            if self._check_game_over():
                return
            self._respawn_zones_if_needed()
            self.phase = Phase.AIMING

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.phase = Phase.TITLE

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.AIMING:
            self._update_aiming()
        elif self.phase == Phase.FLYING:
            self._update_flying()
        elif self.phase == Phase.SCORING:
            self._update_scoring()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    # -- Draw -------------------------------------------------------------

    def _draw_sky_ground(self) -> None:
        # Sky gradient: NAVY (top) to LIGHT_BLUE (near ground)
        for y in range(GROUND_Y):
            if y < 70:
                c = 1  # NAVY
            elif y < 120:
                c = 5  # DARK_BLUE
            elif y < 160:
                c = 12  # CYAN
            else:
                c = 6  # LIGHT_BLUE
            pyxel.rect(0, y, SCREEN_W, 1, c)
        # Ground
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, 4)
        pyxel.line(0, GROUND_Y, SCREEN_W, GROUND_Y, 3)

    def _draw_thrower(self) -> None:
        tx = THROWER_X
        ty = THROWER_Y
        pyxel.circ(tx, ty - 18, 4, 7)
        pyxel.line(tx, ty - 14, tx, ty + 4, 7)
        pyxel.line(tx, ty - 8, tx - 8, ty - 4, 7)
        pyxel.line(tx, ty - 8, tx + 8, ty - 10, 7)
        pyxel.line(tx, ty + 4, tx - 5, ty + 16, 7)
        pyxel.line(tx, ty + 4, tx + 5, ty + 16, 7)
        if self.super_mode:
            glow_colors = (8, 9, 10, 11, 12, 14)
            ci = glow_colors[(pyxel.frame_count // 3) % len(glow_colors)]
            pyxel.circb(tx, ty - 18, 7, ci)

    def _draw_landing_zones(self) -> None:
        super_color = COLORS[(pyxel.frame_count // 5) % NUM_COLORS]
        for zone in self.zones:
            zx = int(zone.x)
            zy = int(zone.y)
            zr = int(zone.radius)
            if not zone.active:
                pyxel.circ(zx, zy, zr, 13)
                pyxel.circb(zx, zy, zr, 13)
                continue
            fill_c = 0
            ring_c = super_color if self.super_mode else zone.color
            pyxel.circ(zx, zy, zr, fill_c)
            pyxel.circb(zx, zy, zr, ring_c)
            pyxel.circb(zx, zy, zr - 4, ring_c)

    def _draw_javelin(self) -> None:
        if self.javelin is None:
            return
        j = self.javelin
        if j.landed:
            angle = j.angle
        else:
            angle = math.atan2(-j.vy, max(abs(j.vx), 0.001))
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        length = 16.0
        tip_x = int(j.x + cos_a * length)
        tip_y = int(j.y - sin_a * length)
        tail_x = int(j.x - cos_a * length)
        tail_y = int(j.y + sin_a * length)

        if self.super_mode and not j.landed:
            jc = COLORS[(pyxel.frame_count // 5) % NUM_COLORS]
        else:
            jc = j.color

        pyxel.line(tail_x, tail_y, tip_x, tip_y, jc)
        pyxel.circ(tip_x, tip_y, 1, 7)

        if self.super_mode and not j.landed:
            for i in range(3):
                tc = COLORS[(pyxel.frame_count // 3 + i) % NUM_COLORS]
                ox = int(j.x + cos_a * (length + i * 4))
                oy = int(j.y - sin_a * (length + i * 4))
                pyxel.circ(ox, oy, 2, tc)

    def _draw_aim_line(self) -> None:
        if self.phase != Phase.AIMING:
            return
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        dx = float(mx - THROWER_X)
        dy = float(THROWER_Y - my)
        if dx < 1.0:
            dx = 1.0
        angle = math.atan2(dy, dx)
        angle = max(0.05, min(angle, 1.2))
        aim_len = 30.0
        ax = int(THROWER_X + math.cos(angle) * aim_len)
        ay = int(THROWER_Y - math.sin(angle) * aim_len)
        lc = 10 if self._charging else 13
        pyxel.line(THROWER_X, THROWER_Y, ax, ay, lc)
        if self._charging:
            pc = COLORS[self.javelin_color_idx] if not self.super_mode else 10
            pyxel.circ(ax, ay, 3, pc)

    def _draw_power_bar(self) -> None:
        bar_x = 6
        bar_y = SCREEN_H - 24
        bar_w = 60
        bar_h = 8
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, 7)
        if self._charging:
            pct = self._charge_power / 100.0
            fill = int(pct * (bar_w - 2))
            fc = 10 if pct > 0.7 else (9 if pct > 0.4 else 11)
            pyxel.rect(bar_x + 1, bar_y + 1, fill, bar_h - 2, fc)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, "PWR", 7)

    def _draw_wind_indicator(self) -> None:
        if self.wind_speed < 0.1:
            return
        wx = SCREEN_W - 40
        wy = 15
        pyxel.text(wx - 60, wy - 4, "WIND", 7)
        arrow_len = int(self.wind_speed * 5 + 3)
        arrow_x = wx + int(self.wind_dir * arrow_len * 1.5)
        pyxel.line(wx, wy, arrow_x, wy, 7)
        head_dir = 1 if self.wind_dir >= 0 else -1
        pyxel.tri(arrow_x, wy, arrow_x - head_dir * 4, wy - 2, arrow_x - head_dir * 4, wy + 2, 7)

    def _draw_hud(self) -> None:
        seconds = max(0, self.timer // 60)
        cname = COLOR_NAMES[self.javelin_color_idx]
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)
        pyxel.text(120, 4, f"COMBO: {self.combo}", 10 if self.combo >= COMBO_THRESHOLD else 7)
        pyxel.text(250, 4, f"T: {seconds}s", 7)
        pyxel.text(4, 14, f"CLR: {cname}", COLORS[self.javelin_color_idx])
        if self.super_mode:
            st = self.super_timer // 60 + 1
            pyxel.text(120, 14, f"SUPER {st}s", 11)

        # Stamina bar
        s_bar_x = 170
        s_bar_y = SCREEN_H - 12
        s_bar_w = 80
        s_bar_h = 6
        pyxel.text(130, s_bar_y - 1, "STM", 7)
        pyxel.rectb(s_bar_x, s_bar_y, s_bar_w, s_bar_h, 7)
        s_fill = int(self.stamina / STAMINA_MAX * (s_bar_w - 2))
        if s_fill > 0:
            sc = 11 if self.stamina >= STAMINA_COST else 8
            pyxel.rect(s_bar_x + 1, s_bar_y + 1, s_fill, s_bar_h - 2, sc)

        # Heat bar
        h_bar_x = 6
        h_bar_y = SCREEN_H - 12
        h_bar_w = 110
        h_bar_h = 6
        pyxel.text(h_bar_x + h_bar_w + 4, h_bar_y - 1, "HEAT", 7)
        pyxel.rectb(h_bar_x, h_bar_y, h_bar_w, h_bar_h, 7)
        h_fill = int(self.heat / HEAT_MAX * (h_bar_w - 2))
        if h_fill > 0:
            if self.heat < 40:
                hc = 11
            elif self.heat < 70:
                hc = 9
            else:
                hc = 8
            pyxel.rect(h_bar_x + 1, h_bar_y + 1, h_fill, h_bar_h - 2, hc)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 3:
                alpha = p.life / 25.0
                if alpha > 0.2:
                    c = p.color if alpha > 0.5 else 13
                    pyxel.pset(int(p.x), int(p.y), c)

    def _draw_floating_texts(self) -> None:
        for ft in self.floats:
            if ft.life > 0:
                tw = len(ft.text) * 4
                pyxel.text(int(ft.x) - tw // 2, int(ft.y), ft.text, ft.color)

    def _draw_title(self) -> None:
        pyxel.cls(0)
        pyxel.text(SCREEN_W // 2 - 42, 35, "JAVELIN CHAIN", 7)
        pyxel.text(SCREEN_W // 2 - 60, 55, "Color-Match COMBO Throw", 13)
        pyxel.text(90, 80, "Hold mouse = Charge power", 7)
        pyxel.text(85, 94, "Mouse position = Aim angle", 7)
        pyxel.text(95, 108, "Release = Throw javelin!", 7)
        pyxel.text(85, 126, "Same-color consecutive hit = COMBO!", 10)
        pyxel.text(80, 140, f"COMBO x{COMBO_THRESHOLD} = SUPER THROW!", 11)
        pyxel.text(80, 154, "(rainbow, 3x score, no heat)", 12)
        pyxel.text(90, 172, "Mismatch raises HEAT", 8)
        pyxel.text(85, 186, "Fault (off-field) = heavy HEAT", 8)
        pyxel.text(90, 202, "Stamina governs power (recharges)", 7)
        pyxel.text(85, 218, f"Survive {GAME_DURATION // 60}s, score big!", 7)
        pyxel.text(SCREEN_W // 2 - 40, SCREEN_H - 8, "Click to Start", 7)

    def _draw_playing(self) -> None:
        self._draw_sky_ground()
        self._draw_landing_zones()
        self._draw_thrower()
        self._draw_javelin()
        self._draw_aim_line()
        self._draw_power_bar()
        self._draw_wind_indicator()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

        if self.phase == Phase.SCORING:
            if self._last_fault:
                pyxel.text(SCREEN_W // 2 - 20, 100, "FAULT!", 8)
            elif self._last_matched:
                pyxel.text(SCREEN_W // 2 - 20, 100, "MATCH!", 10)
            else:
                pyxel.text(SCREEN_W // 2 - 20, 100, "MISS!", 8)

    def _draw_game_over(self) -> None:
        pyxel.cls(0)
        reason = "TIME UP!" if self.timer <= 0 else "OVERHEAT!"
        pyxel.text(120, 50, "GAME OVER", 8)
        pyxel.text(125, 70, reason, 7)
        pyxel.text(100, 100, f"FINAL SCORE: {self.score}", 7)
        pyxel.text(85, 115, f"MAX COMBO: {self.max_combo}", 10)
        pyxel.text(85, 130, f"HEAT: {self.heat:.0f}/{HEAT_MAX:.0f}", 8)
        pyxel.text(80, 200, "Click to Retry", 7)

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.AIMING, Phase.FLYING, Phase.SCORING):
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()


def main() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="Javelin Chain")
    font_path = Path(__file__).with_name("k8x12.bdf")
    try:
        pyxel.load(str(font_path))
    except Exception:
        pass
    pyxel.mouse(True)
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
