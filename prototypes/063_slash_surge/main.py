"""SLASH SURGE -- Color-Match Slashing Game (Prototype 063)

Experience Hypothesis:
  Slashing an orb and watching it split into fragments creates a moment of panic;
  chaining same-color slashes for a SURGE explosion creates cathartic relief.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pyxel

# --- Constants ---
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
MAX_ORBS = 25
COMBO_SURGE_THRESHOLD = 5
ORB_RADIUS = 10.0
FRAGMENT_RADIUS = 5.0
HP_MAX = 10
SPAWN_INTERVAL = 60
GRAVITY = 0.05
SURGE_RADIUS = 30.0
OVERLOAD_WARN_THRESHOLD = 20
OVERLOAD_DAMAGE_INTERVAL = 30
FRAGMENT_LIFETIME = 300

COLOR_RED = 8
COLOR_GREEN = 3
COLOR_BLUE = 5
COLOR_YELLOW = 10
ORB_COLORS = (COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW)

PHASE_TITLE = 0
PHASE_PLAYING = 1
PHASE_GAME_OVER = 2


# --- Data Classes ---
@dataclass
class Orb:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    radius: float
    is_fragment: bool
    life: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


# --- Game ---
class Game:
    def __init__(self) -> None:
        self._init_state()

    def _init_state(self) -> None:
        self.phase = PHASE_TITLE
        self.orbs: list[Orb] = []
        self.particles: list[Particle] = []
        self.score = 0
        self.hp = HP_MAX
        self.combo = 0
        self.last_slashed_color: int | None = None
        self.max_combo = 0
        self.spawn_timer = SPAWN_INTERVAL
        self.slash_line: list[tuple[float, float]] = []
        self.is_slashing = False
        self.surge_queue: list[tuple[float, float, int]] = []
        self.surge_anim_timer = 0
        self.overload_damage_timer = 0

    # ------------------------------------------------------------------
    # Phase switching
    # ------------------------------------------------------------------
    def update(self) -> None:
        if self.phase == PHASE_TITLE:
            self._update_title()
        elif self.phase == PHASE_PLAYING:
            self._update_playing()
        elif self.phase == PHASE_GAME_OVER:
            self._update_game_over()

    def draw(self) -> None:
        pyxel.cls(0)
        if self.phase == PHASE_TITLE:
            self._draw_title()
        elif self.phase == PHASE_PLAYING:
            self._draw_playing()
        elif self.phase == PHASE_GAME_OVER:
            self._draw_game_over()

    # ------------------------------------------------------------------
    # Title screen
    # ------------------------------------------------------------------
    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._init_state()
            self.phase = PHASE_PLAYING

    def _draw_title(self) -> None:
        tx = SCREEN_W // 2
        pyxel.text(tx - len("SLASH SURGE") * 2, 80, "SLASH SURGE", 7)
        pyxel.text(tx - 40, 120, "Click to Start", 7)
        pyxel.text(tx - 80, 160, "Click + Drag : slash orbs", 13)
        pyxel.text(tx - 90, 180, "Chain same color -> SURGE!", 10)

    # ------------------------------------------------------------------
    # Game Over screen
    # ------------------------------------------------------------------
    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._init_state()
            self.phase = PHASE_PLAYING

    def _draw_game_over(self) -> None:
        tx = SCREEN_W // 2
        pyxel.text(tx - 25, 70, "GAME OVER", 8)
        pyxel.text(tx - 40, 110, f"Score: {self.score}", 7)
        pyxel.text(tx - 50, 130, f"Max Combo: {self.max_combo}", 7)
        pyxel.text(tx - 45, 170, "Click to Retry", 7)

    # ------------------------------------------------------------------
    # Playing -- update (pyxel input allowed here)
    # ------------------------------------------------------------------
    def _update_playing(self) -> None:
        self._update_particles()

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_orb()
            self.spawn_timer = SPAWN_INTERVAL

        self._update_orbs()

        if self.surge_queue:
            self._update_surge_anim()

        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            self.is_slashing = True
            self.slash_line.append((pyxel.mouse_x, pyxel.mouse_y))
        elif self.is_slashing:
            self._check_slash_collisions()
            self.slash_line.clear()
            self.is_slashing = False

        self._check_overload()

        if self.hp <= 0:
            self.hp = 0
            self.phase = PHASE_GAME_OVER

    def _update_surge_anim(self) -> None:
        self.surge_anim_timer -= 1
        if self.surge_anim_timer <= 0:
            x, y, color = self.surge_queue.pop(0)
            self._spawn_explosion_particles(x, y, color)
            self.surge_anim_timer = 2

    # ------------------------------------------------------------------
    # Testable methods  (no pyxel input calls)
    # ------------------------------------------------------------------

    def _spawn_orb(self) -> None:
        edge = random.randint(0, 3)
        color = random.choice(ORB_COLORS)
        speed = random.uniform(0.25, 0.75)

        pad = ORB_RADIUS * 2
        if edge == 0:  # top
            x = random.uniform(pad, SCREEN_W - pad)
            y = -ORB_RADIUS
            vx = random.uniform(-speed, speed)
            vy = abs(speed)
        elif edge == 1:  # bottom
            x = random.uniform(pad, SCREEN_W - pad)
            y = SCREEN_H + ORB_RADIUS
            vx = random.uniform(-speed, speed)
            vy = -abs(speed)
        elif edge == 2:  # left
            x = -ORB_RADIUS
            y = random.uniform(pad, SCREEN_H - pad)
            vx = abs(speed)
            vy = random.uniform(-speed, speed)
        else:  # right
            x = SCREEN_W + ORB_RADIUS
            y = random.uniform(pad, SCREEN_H - pad)
            vx = -abs(speed)
            vy = random.uniform(-speed, speed)

        self.orbs.append(Orb(x, y, vx, vy, color, ORB_RADIUS, False, -1))

    def _update_orbs(self) -> None:
        dead: list[int] = []
        for i, orb in enumerate(self.orbs):
            orb.x += orb.vx
            orb.y += orb.vy

            if orb.is_fragment:
                orb.vy += GRAVITY
                orb.life -= 1
                if orb.life <= 0:
                    dead.append(i)
                    continue

            if orb.x < orb.radius:
                orb.x = orb.radius
                orb.vx = abs(orb.vx)
            elif orb.x > SCREEN_W - orb.radius:
                orb.x = SCREEN_W - orb.radius
                orb.vx = -abs(orb.vx)
            if orb.y < orb.radius:
                orb.y = orb.radius
                orb.vy = abs(orb.vy) * 0.8
            elif orb.y > SCREEN_H - orb.radius:
                orb.y = SCREEN_H - orb.radius
                orb.vy = -abs(orb.vy) * 0.8

        for idx in sorted(dead, reverse=True):
            self.orbs.pop(idx)

    def _check_slash_collisions(self) -> None:
        if len(self.slash_line) < 2:
            return

        hit: set[int] = set()
        for i in range(len(self.slash_line) - 1):
            p1 = self.slash_line[i]
            p2 = self.slash_line[i + 1]
            for j, orb in enumerate(self.orbs):
                if j in hit:
                    continue
                if self._segment_circle_hit(p1[0], p1[1], p2[0], p2[1], orb.x, orb.y, orb.radius):
                    hit.add(j)

        for idx in sorted(hit, reverse=True):
            self._slash_orb(idx)

    @staticmethod
    def _segment_circle_hit(
        ax: float, ay: float, bx: float, by: float,
        cx: float, cy: float, r: float,
    ) -> bool:
        dx = bx - ax
        dy = by - ay
        if dx == 0.0 and dy == 0.0:
            return math.hypot(ax - cx, ay - cy) <= r
        t = max(0.0, min(1.0, ((cx - ax) * dx + (cy - ay) * dy) / (dx * dx + dy * dy)))
        px = ax + t * dx
        py = ay + t * dy
        return math.hypot(px - cx, py - cy) <= r

    def _slash_orb(self, idx: int) -> None:
        orb = self.orbs[idx]

        self._update_combo(orb.color)

        multiplier = self._combo_multiplier()
        self.score += int(100 * multiplier)

        self._spawn_slash_particles(orb.x, orb.y, orb.color)

        if not orb.is_fragment:
            self._split_orb(idx)
        else:
            self.orbs.pop(idx)

        if self.combo >= COMBO_SURGE_THRESHOLD:
            self._trigger_surge(orb.color)

    def _update_combo(self, color: int) -> None:
        if self.last_slashed_color is not None and color == self.last_slashed_color:
            self.combo += 1
        else:
            self.combo = 1
        self.last_slashed_color = color
        if self.combo > self.max_combo:
            self.max_combo = self.combo

    def _combo_multiplier(self) -> int:
        if self.combo <= 1:
            return 1
        if self.combo <= 3:
            return 2
        if self.combo <= 5:
            return 3
        return 5

    def _split_orb(self, idx: int) -> None:
        orb = self.orbs[idx]
        for _ in range(2):
            c = random.choice(ORB_COLORS)
            angle = random.uniform(0.0, math.pi * 2)
            speed = random.uniform(0.5, 2.0)
            fx = orb.x + math.cos(angle) * 5.0
            fy = orb.y + math.sin(angle) * 5.0
            self.orbs.append(Orb(
                fx, fy,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                c, FRAGMENT_RADIUS, True, FRAGMENT_LIFETIME,
            ))
        self.orbs.pop(idx)

    def _trigger_surge(self, color: int) -> None:
        to_destroy = self._bfs_surge(color)
        if not to_destroy:
            return

        bonus = 50 * len(to_destroy) * self._combo_multiplier()
        self.score += bonus

        for idx in sorted(to_destroy, reverse=True):
            orb = self.orbs[idx]
            self.surge_queue.append((orb.x, orb.y, orb.color))
            self.orbs.pop(idx)

        self.surge_anim_timer = 2
        self.combo = 0
        self.last_slashed_color = None

    def _bfs_surge(self, seed_color: int) -> list[int]:
        """Return indices of all same-color fragments, in BFS propagation order."""
        indices = [i for i, o in enumerate(self.orbs) if o.is_fragment and o.color == seed_color]
        if len(indices) < 2:
            return indices

        adj: dict[int, list[int]] = {i: [] for i in indices}
        for a in range(len(indices)):
            for b in range(a + 1, len(indices)):
                ia, ib = indices[a], indices[b]
                dx = self.orbs[ia].x - self.orbs[ib].x
                dy = self.orbs[ia].y - self.orbs[ib].y
                if dx * dx + dy * dy < SURGE_RADIUS * SURGE_RADIUS:
                    adj[ia].append(ib)
                    adj[ib].append(ia)

        visited: set[int] = set()
        order: list[int] = []
        for start in indices:
            if start in visited:
                continue
            queue: list[int] = [start]
            while queue:
                idx = queue.pop(0)
                if idx in visited:
                    continue
                visited.add(idx)
                order.append(idx)
                for nb in adj[idx]:
                    if nb not in visited:
                        queue.append(nb)
        return order

    def _check_overload(self) -> None:
        if len(self.orbs) > MAX_ORBS:
            self.overload_damage_timer += 1
            if self.overload_damage_timer >= OVERLOAD_DAMAGE_INTERVAL:
                self._update_hp(-1)
                self.overload_damage_timer = 0
        else:
            if self.overload_damage_timer > 0:
                self.overload_damage_timer = max(0, self.overload_damage_timer - 1)

    def _update_hp(self, amount: int) -> None:
        self.hp = max(0, self.hp + amount)

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _spawn_slash_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(6):
            a = random.uniform(0.0, math.pi * 2)
            s = random.uniform(0.5, 2.0)
            self.particles.append(Particle(
                x, y,
                math.cos(a) * s,
                math.sin(a) * s,
                color,
                random.randint(6, 16),
            ))

    def _spawn_explosion_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(10):
            a = random.uniform(0.0, math.pi * 2)
            s = random.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x, y,
                math.cos(a) * s,
                math.sin(a) * s,
                color,
                random.randint(10, 22),
            ))

    # ------------------------------------------------------------------
    # Playing -- draw
    # ------------------------------------------------------------------
    def _draw_playing(self) -> None:
        # --- Orbs ---
        for orb in self.orbs:
            ox, oy = int(orb.x), int(orb.y)
            r = int(orb.radius)
            if orb.is_fragment:
                pyxel.circb(ox, oy, r, orb.color)
            else:
                pyxel.circ(ox, oy, r, orb.color)
                pyxel.circb(ox, oy, r, orb.color)

        # --- Slash trail ---
        if self.is_slashing and len(self.slash_line) >= 2:
            for i in range(len(self.slash_line) - 1):
                x1 = int(self.slash_line[i][0])
                y1 = int(self.slash_line[i][1])
                x2 = int(self.slash_line[i + 1][0])
                y2 = int(self.slash_line[i + 1][1])
                pyxel.line(x1, y1, x2, y2, 7)

        # --- Particles ---
        for p in self.particles:
            px, py = int(p.x), int(p.y)
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                pyxel.pset(px, py, p.color)

        # --- HUD ---
        self._draw_hud()

    def _draw_hud(self) -> None:
        # Score (top-left)
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)

        # HP bar (top-center)
        bar_x = SCREEN_W // 2 - 40
        bar_y = 4
        bar_w = 80
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, 7)
        if self.hp > 0:
            fill = max(1, int((bar_w - 2) * self.hp / HP_MAX))
            if self.hp <= 2:
                hp_col = 8
            elif self.hp <= 5:
                hp_col = 9
            else:
                hp_col = 11
            pyxel.rect(bar_x + 1, bar_y + 1, fill, bar_h - 2, hp_col)

        # Combo (top-right)
        if self.combo > 0:
            text = f"COMBO: {self.combo}"
            col = 10 if self.combo >= COMBO_SURGE_THRESHOLD - 1 else 7
            pyxel.text(SCREEN_W - len(text) * 4 - 4, 4, text, col)

        # SURGE indicator
        if self.combo >= COMBO_SURGE_THRESHOLD:
            blink = (pyxel.frame_count // 6) % 2 == 0
            if blink:
                pyxel.text(SCREEN_W // 2 - 18, 15, "SURGE!", 8)
        elif self.combo == COMBO_SURGE_THRESHOLD - 1:
            pyxel.text(SCREEN_W // 2 - 30, 15, "ALMOST SURGE!", 10)

        # Overload warning
        count = len(self.orbs)
        if count >= OVERLOAD_WARN_THRESHOLD:
            if count > MAX_ORBS:
                text = f"OVERLOAD! {count}/{MAX_ORBS}"
                col = 8
            else:
                text = f"WARNING: {count}/{MAX_ORBS}"
                col = 10
            pyxel.text(SCREEN_W // 2 - len(text) * 2, 26, text, col)

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def run(self) -> None:
        pyxel.run(self.update, self.draw)


def main() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="SLASH SURGE", display_scale=DISPLAY_SCALE)
    Game().run()


if __name__ == "__main__":
    main()
