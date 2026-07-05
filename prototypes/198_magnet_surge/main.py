"""MAGNET SURGE — Top-down magnet collector with color-match synthesis and CA chain.

Most Fun Moment: Switching magnet color at the last moment to pull a cluster of
same-color scraps together, triggering SYNTHESIS + CA color spread that cascades
through nearby scraps, building COMBO into SUPER MAGNET rainbow mode for a
massive score explosion.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# === Constants ===
SCREEN_W = 320
SCREEN_H = 240
SCRAP_RADIUS = 3
NUGGET_MIN_RADIUS = 5
NUGGET_MAX_RADIUS = 10
MAGNET_RADIUS = 8
MAGNET_SPEED = 2.0
ATTRACTION_FORCE = 0.15
SYNTHESIS_THRESHOLD = 3
SYNTHESIS_PROXIMITY = 8
CA_SPREAD_RADIUS = 30
MAX_SCRAPS = 30
SPAWN_INTERVAL = 30
SUPER_DURATION = 300
SUPER_COMBO_THRESHOLD = 4
HEAT_MAX = 100
HEAT_DECAY = 0.05
HEAT_SYNTH_REDUCTION = 5
GAME_DURATION = 3600

COLORS = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
BLACK = 0
NAVY = 1
GREEN = 3
DARK_BLUE = 5
WHITE = 7
RED = 8
ORANGE = 9
YELLOW = 10
GRAY = 13
PINK = 14


# === Phase ===
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# === Data Classes ===
@dataclass
class Scrap:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    radius: float = SCRAP_RADIUS


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


# === Main Game Class ===
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="MAGNET SURGE", display_scale=2)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.game_timer: int = GAME_DURATION
        self.magnet_x: float = SCREEN_W / 2
        self.magnet_y: float = SCREEN_H / 2
        self.magnet_color: int = 0
        self._spawn_timer: int = 0
        self._last_syn_color: int | None = None
        self._frame_without_syn: int = 0
        self.scraps: list[Scrap] = []
        self.nuggets: list[Scrap] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

    @staticmethod
    def _make_game() -> Game:
        g = Game.__new__(Game)
        g._rng = random.Random()
        g.phase = Phase.TITLE
        g.score = 0
        g.combo = 0
        g.max_combo = 0
        g.heat = 0.0
        g.super_timer = 0
        g.game_timer = GAME_DURATION
        g.magnet_x = SCREEN_W / 2
        g.magnet_y = SCREEN_H / 2
        g.magnet_color = 0
        g._spawn_timer = 0
        g._last_syn_color = None
        g._frame_without_syn = 0
        g.scraps = []
        g.nuggets = []
        g.particles = []
        g.floating_texts = []
        return g

    # --- Helpers ---
    def _magnet_col(self) -> int:
        return COLORS[self.magnet_color]

    def _is_super_active(self) -> bool:
        return self.super_timer > 0

    def _heat_percent(self) -> float:
        return self.heat / HEAT_MAX

    # --- Spawning ---
    def _spawn_scrap(self) -> None:
        if len(self.scraps) + len(self.nuggets) >= MAX_SCRAPS:
            return

        color = self._rng.randint(0, 3)
        edge = self._rng.randint(0, 3)
        if edge == 0:
            x = self._rng.uniform(0, SCREEN_W)
            y = -SCRAP_RADIUS
        elif edge == 1:
            x = SCREEN_W + SCRAP_RADIUS
            y = self._rng.uniform(0, SCREEN_H)
        elif edge == 2:
            x = self._rng.uniform(0, SCREEN_W)
            y = SCREEN_H + SCRAP_RADIUS
        else:
            x = -SCRAP_RADIUS
            y = self._rng.uniform(0, SCREEN_H)

        scrap = Scrap(
            x=x,
            y=y,
            vx=self._rng.uniform(-0.5, 0.5),
            vy=self._rng.uniform(-0.5, 0.5),
            color=color,
        )
        self.scraps.append(scrap)

    # --- Attraction ---
    def _attract_scraps(self) -> None:
        for s in self.scraps:
            dx = self.magnet_x - s.x
            dy = self.magnet_y - s.y
            dist = math.hypot(dx, dy)
            if dist < 1:
                continue
            if self._is_super_active() or s.color == self.magnet_color:
                force = ATTRACTION_FORCE
                if dist < 80:
                    force *= 1.5
                s.vx += (dx / dist) * force
                s.vy += (dy / dist) * force
            s.vx *= 0.99
            s.vy *= 0.99

    def _move_scraps(self) -> None:
        for s in self.scraps:
            s.x += s.vx
            s.y += s.vy
            margin = s.radius
            if s.x < margin:
                s.x = margin
                s.vx *= -0.6
            elif s.x > SCREEN_W - margin:
                s.x = SCREEN_W - margin
                s.vx *= -0.6
            if s.y < margin:
                s.y = margin
                s.vy *= -0.6
            elif s.y > SCREEN_H - margin:
                s.y = SCREEN_H - margin
                s.vy *= -0.6

        for n in self.nuggets:
            n.x += n.vx
            n.y += n.vy
            n.vx *= 0.95
            n.vy *= 0.95

    # --- Synthesis ---
    def _check_synthesis(self) -> None:
        while True:
            indices = list(range(len(self.scraps)))
            visited: set[int] = set()
            synthesized = False

            for i in indices:
                if i in visited:
                    continue
                cluster: list[int] = []
                queue: list[int] = [i]
                while queue:
                    cur = queue.pop()
                    if cur in visited:
                        continue
                    visited.add(cur)
                    cluster.append(cur)
                    cs = self.scraps[cur]
                    for j in indices:
                        if j in visited:
                            continue
                        js = self.scraps[j]
                        if js.color != cs.color:
                            continue
                        if math.hypot(cs.x - js.x, cs.y - js.y) < SYNTHESIS_PROXIMITY:
                            queue.append(j)

                if len(cluster) < SYNTHESIS_THRESHOLD:
                    continue

                near_magnet = any(
                    math.hypot(
                        self.scraps[c].x - self.magnet_x,
                        self.scraps[c].y - self.magnet_y,
                    )
                    < 20
                    for c in cluster
                )
                if not near_magnet:
                    continue

                syn_color = self.scraps[i].color
                self._do_synthesis(cluster, syn_color)
                synthesized = True
                break

            if not synthesized:
                break

    def _do_synthesis(self, cluster: list[int], syn_color: int) -> None:
        cx = sum(self.scraps[i].x for i in cluster) / len(cluster)
        cy = sum(self.scraps[i].y for i in cluster) / len(cluster)

        if self._last_syn_color is not None and self._last_syn_color == syn_color:
            self.combo += 1
        else:
            self.combo = 1
        self._last_syn_color = syn_color
        self.max_combo = max(self.max_combo, self.combo)

        combo_mult = min(self.combo, 10)
        if self._is_super_active():
            combo_mult *= 3
        points = 100 * combo_mult
        self.score += points

        self.heat = max(0, self.heat - HEAT_SYNTH_REDUCTION)
        self._frame_without_syn = 0

        # CA spread first (before removing scraps)
        for s in self.scraps:
            if math.hypot(s.x - cx, s.y - cy) < CA_SPREAD_RADIUS:
                s.color = syn_color

        nugget_size = min(NUGGET_MAX_RADIUS, NUGGET_MIN_RADIUS + len(cluster) * 0.8)
        for idx in sorted(cluster, reverse=True):
            del self.scraps[idx]
        nugget = Scrap(
            x=cx,
            y=cy,
            vx=self._rng.uniform(-0.3, 0.3),
            vy=self._rng.uniform(-0.3, 0.3),
            color=syn_color,
            radius=nugget_size,
        )
        self.nuggets.append(nugget)

        self._add_particles(cx, cy, 10, COLORS[syn_color])

        combo_text = f"+{points}"
        if self.combo >= 4:
            combo_text += f" x{self.combo}!"
        self._add_floating_text(cx, cy - 10, combo_text, YELLOW)
        if self.combo >= SUPER_COMBO_THRESHOLD and not self._is_super_active():
            self._activate_super(cx, cy)

    def _activate_super(self, x: float, y: float) -> None:
        self.super_timer = SUPER_DURATION
        self._add_particles(x, y, 20, -1)
        self._add_floating_text(x, y - 22, "SUPER!", PINK)

    # --- Update ---
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

        self._update_particles()
        self._update_floating_texts()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.PLAYING

    def _tick(self) -> None:
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.game_timer = 0
            self.phase = Phase.GAME_OVER
            return

        self._frame_without_syn += 1
        if self._frame_without_syn >= 20:
            self.heat = min(HEAT_MAX, self.heat + HEAT_DECAY * self._frame_without_syn / 20)
            self._frame_without_syn = 0

        if self.heat >= HEAT_MAX:
            self.heat = HEAT_MAX
            self.phase = Phase.GAME_OVER
            return

        if self.super_timer > 0:
            self.super_timer -= 1

        self._spawn_timer += 1
        if self._spawn_timer >= SPAWN_INTERVAL:
            self._spawn_timer = 0
            self._spawn_scrap()

        self._attract_scraps()
        self._move_scraps()
        self._check_synthesis()

    def _update_playing(self) -> None:
        if pyxel.btn(pyxel.KEY_UP):
            self.magnet_y = max(MAGNET_RADIUS, self.magnet_y - MAGNET_SPEED)
        if pyxel.btn(pyxel.KEY_DOWN):
            self.magnet_y = min(SCREEN_H - MAGNET_RADIUS, self.magnet_y + MAGNET_SPEED)
        if pyxel.btn(pyxel.KEY_LEFT):
            self.magnet_x = max(MAGNET_RADIUS, self.magnet_x - MAGNET_SPEED)
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.magnet_x = min(SCREEN_W - MAGNET_RADIUS, self.magnet_x + MAGNET_SPEED)

        if pyxel.btnp(pyxel.KEY_SPACE):
            self._cycle_color()

        self._tick()

    def _cycle_color(self) -> None:
        self.magnet_color = (self.magnet_color + 1) % 4

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            self.phase = Phase.TITLE

    # --- Particles ---
    def _add_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            angle = self._rng.random() * 2 * math.pi
            speed = self._rng.uniform(1.0, 3.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            if color == -1:
                pc = self._rng.choice(list(COLORS))
            else:
                pc = color
            life = self._rng.randint(15, 25)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, color=pc, life=life)
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # --- Floating text ---
    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, color=color, life=35)
        )

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.7
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # --- Draw ---
    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(80, 60, "MAGNET SURGE", YELLOW)
        pyxel.text(60, 90, "Press SPACE to start", WHITE)
        pyxel.text(30, 120, "Arrow keys: move", GRAY)
        pyxel.text(30, 132, "SPACE: change color", GRAY)
        pyxel.text(20, 160, "Attract same-color scraps.", GRAY)
        pyxel.text(20, 172, "Cluster 3+ near you to SYNTHESIZE!", GRAY)
        pyxel.text(20, 184, "Combo x4 = SUPER MAGNET (rainbow!)", PINK)

    def _draw_playing(self) -> None:
        for s in self.scraps:
            pyxel.circ(int(s.x), int(s.y), int(s.radius), COLORS[s.color])
            pyxel.circb(int(s.x), int(s.y), int(s.radius) + 1, GRAY)

        for n in self.nuggets:
            r = int(n.radius)
            col = COLORS[n.color]
            if self._is_super_active():
                pulse = (pyxel.frame_count // 4) % 4
                col = COLORS[pulse]
            pyxel.circ(int(n.x), int(n.y), r, col)
            pyxel.circb(int(n.x), int(n.y), r + 1, WHITE)

        for p in self.particles:
            if p.life <= 0:
                continue
            sz = 1
            pyxel.rect(int(p.x) - sz, int(p.y) - sz, sz * 2, sz * 2, p.color)

        for ft in self.floating_texts:
            if ft.life > 0:
                text_x = int(ft.x) - len(ft.text) * 2
                pyxel.text(text_x, int(ft.y), ft.text, ft.color)

        mx, my = int(self.magnet_x), int(self.magnet_y)
        magnet_draw_color = COLORS[self.magnet_color]
        if self._is_super_active():
            pulse_idx = (pyxel.frame_count // 6) % 4
            magnet_draw_color = COLORS[pulse_idx]
            pyxel.circb(mx, my, MAGNET_RADIUS + 4, YELLOW)
        pyxel.circ(mx, my, MAGNET_RADIUS, magnet_draw_color)
        pyxel.circb(mx, my, MAGNET_RADIUS, WHITE)

        self._draw_hud()

    def _draw_hud(self) -> None:
        secs = self.game_timer // 60
        timer_color = RED if secs <= 10 else WHITE
        pyxel.text(SCREEN_W // 2 - 12, 4, f"{secs}s", timer_color)

        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)

        combo_col = YELLOW if self._is_super_active() else WHITE
        pyxel.text(SCREEN_W - 60, 4, f"COMBO: {self.combo}", combo_col)

        color_ind_x = 4
        color_ind_y = 16
        pyxel.circ(color_ind_x + 4, color_ind_y + 4, 4, COLORS[self.magnet_color])
        pyxel.circb(color_ind_x + 4, color_ind_y + 4, 4, WHITE)

        if self._is_super_active():
            super_secs = self.super_timer // 60
            pyxel.text(SCREEN_W // 2 - 30, 16, f"SUPER {super_secs}s", PINK)

        bar_x, bar_y, bar_w, bar_h = 10, SCREEN_H - 18, SCREEN_W - 20, 10
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        heat_fill = int(self._heat_percent() * bar_w)
        if self.heat < 30:
            heat_color = GREEN
        elif self.heat < 60:
            heat_color = YELLOW
        elif self.heat < 80:
            heat_color = ORANGE
        else:
            heat_color = RED
        pyxel.rect(bar_x, bar_y, heat_fill, bar_h, heat_color)
        pyxel.text(bar_x + 2, bar_y - 8, "HEAT", GRAY)

    def _draw_game_over(self) -> None:
        pyxel.text(100, 50, "GAME OVER", RED)

        death_reason = "Time Up!" if self.game_timer <= 0 else "Overheated!"
        pyxel.text(110, 70, death_reason, WHITE)

        pyxel.text(90, 100, f"FINAL SCORE: {self.score}", YELLOW)
        pyxel.text(90, 115, f"MAX COMBO:  {self.max_combo}", WHITE)
        pyxel.text(90, 130, f"NUGGETS:    {len(self.nuggets)}", GRAY)

        pyxel.text(70, 170, "Press R to restart", GRAY)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
