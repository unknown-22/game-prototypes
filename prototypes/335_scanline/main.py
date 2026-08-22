"""SCANLINE: Baggage X-Ray Contraband Scanner.

A 90-second shift as an airport X-ray operator. Bags scroll along the belt;
spot the contraband silhouettes (gun, knife, bottle) among safe clutter and
FLAG them before they exit the scanner. Flag aggressively to build combo, or
conservatively to protect your security rating.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Color constants (raw ints) ---
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

# --- Screen / world constants ---
WIDTH = 320
HEIGHT = 240
BAG_W = 64
BAG_H = 40
BAG_Y = 120
RESOLVE_X = 320
SHIFT_FRAMES = 5400
SECURITY_START = 100
ITEM_CELL = 14


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass(frozen=True)
class ItemDef:
    kind: str
    contraband: bool
    subtle: bool
    color: int


@dataclass
class Bag:
    x: float
    y: float
    items: list[ItemDef]
    flagged: bool = False
    resolved: bool = False

    def has_contraband(self) -> bool:
        return any(it.contraband for it in self.items)


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


ITEMS: dict[str, ItemDef] = {
    "BOOK": ItemDef("BOOK", False, False, GREEN),
    "SHOE": ItemDef("SHOE", False, False, BROWN),
    "BOTTLE": ItemDef("BOTTLE", True, True, LIGHT_BLUE),
    "GUN": ItemDef("GUN", True, False, DARK_BLUE),
    "KNIFE": ItemDef("KNIFE", True, True, WHITE),
}
SAFE_ITEMS = ["BOOK", "SHOE"]
CONTRABAND_ITEMS = ["BOTTLE", "GUN", "KNIFE"]


# --- Module-level pure functions (testable, no pyxel) ---
def combo_multiplier(combo: int) -> float:
    return min(1.0 + combo * 0.5, 4.0)


def resolve_outcome(has_contraband: bool, flagged: bool) -> str:
    if flagged and has_contraband:
        return "CAUGHT"
    if flagged:
        return "FALSE_ALARM"
    if has_contraband:
        return "MISS"
    return "PASS"


def spawn_interval(frame: int) -> int:
    return max(28, 90 - frame // 45)


def bag_speed(frame: int) -> float:
    return 1.0 + frame * (2.2 / SHIFT_FRAMES)


def max_items(frame: int) -> int:
    return min(5, 2 + frame // 1800)


def contraband_chance(frame: int) -> float:
    return min(0.55, 0.30 + frame * (0.25 / SHIFT_FRAMES))


class Game:
    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="SCANLINE", display_scale=2, fps=60)
        self.best_score = 0
        self.reset()
        pyxel.run(self.update, self.draw)

    # --- State init ---
    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.rng = getattr(self, "rng", None) or random.Random()
        self.bags: list[Bag] = []
        self.frame: int = 0
        self.spawn_timer: int = spawn_interval(0)
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.security: int = SECURITY_START
        self.caught: int = 0
        self.missed: int = 0
        self.false_alarms: int = 0
        self.passed: int = 0
        self.end_reason: str = ""
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake: int = 0
        self.best_score = getattr(self, "best_score", 0)

    def start_game(self) -> None:
        self.reset()
        self.phase = Phase.PLAYING

    # --- Spawning ---
    def _spawn_bag(self) -> None:
        item_count = self.rng.randint(2, max_items(self.frame))
        if self.rng.random() < contraband_chance(self.frame):
            n_contraband = self.rng.randint(1, min(2, item_count))
            contraband_kinds = self.rng.choices(
                CONTRABAND_ITEMS,
                weights=[2 if ITEMS[k].subtle else 1 for k in CONTRABAND_ITEMS],
                k=n_contraband,
            )
            items = [ITEMS[k] for k in contraband_kinds]
        else:
            items = []
        while len(items) < item_count:
            items.append(ITEMS[self.rng.choice(SAFE_ITEMS)])
        self.rng.shuffle(items)
        x = -BAG_W - self.rng.uniform(0.0, 40.0)
        self.bags.append(Bag(x=x, y=float(BAG_Y), items=items))

    # --- Update helpers ---
    def _update_bags(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_bag()
            self.spawn_timer = spawn_interval(self.frame)

        for bag in self.bags:
            bag.x += bag_speed(self.frame)

        resolved: list[Bag] = []
        for bag in self.bags:
            if bag.x + BAG_W >= RESOLVE_X:
                self._resolve_bag(bag)
                resolved.append(bag)
        for bag in resolved:
            self.bags.remove(bag)

    def _resolve_bag(self, bag: Bag) -> str:
        outcome = resolve_outcome(bag.has_contraband(), bag.flagged)
        self._apply_outcome(outcome, bag)
        bag.resolved = True
        return outcome

    def _spawn_particles(
        self, x: float, y: float, count: int, color: int, speed: float, life: int
    ) -> None:
        for _ in range(count):
            ang = self.rng.uniform(0.0, math.tau)
            sp = self.rng.uniform(0.3, speed)
            vx = math.cos(ang) * sp
            vy = math.sin(ang) * sp
            self.particles.append(
                Particle(x, y, vx, vy, self.rng.randint(life // 2, life), color)
            )

    def _apply_outcome(self, outcome: str, bag: Bag) -> None:
        px = bag.x + BAG_W
        py = bag.y - BAG_H / 2
        if outcome == "CAUGHT":
            mult = combo_multiplier(self.combo)
            gain = int(100 * mult)
            self.score += gain
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.security = min(100, self.security + 5)
            self.caught += 1
            self._spawn_particles(px, bag.y, 10, YELLOW, 1.5, 20)
            self.floating_texts.append(FloatingText(px, py, f"+{gain}", 40, YELLOW))
        elif outcome == "PASS":
            self.score += 20
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.passed += 1
            self._spawn_particles(px, bag.y, 4, LIME, 0.8, 15)
            self.floating_texts.append(FloatingText(px, py, "+20", 40, LIME))
        elif outcome == "FALSE_ALARM":
            self.combo = 0
            self.security -= 10
            self.false_alarms += 1
            self.shake = 5
            self._spawn_particles(px, bag.y, 8, GRAY, 1.0, 20)
            self.floating_texts.append(FloatingText(px, py, "FALSE ALARM!", 40, ORANGE))
        elif outcome == "MISS":
            self.combo = 0
            self.security -= 15
            self.missed += 1
            self.shake = 5
            self._spawn_particles(px, bag.y, 8, RED, 1.2, 25)
            self.floating_texts.append(FloatingText(px, py, "MISSED!", 40, RED))

    def _flag_at(self, x: float, y: float) -> bool:
        for bag in reversed(self.bags):
            if bag.resolved:
                continue
            if bag.x <= x <= bag.x + BAG_W and bag.y - BAG_H / 2 <= y <= bag.y + BAG_H / 2:
                bag.flagged = not bag.flagged
                return True
        return False

    def _check_game_over(self) -> None:
        if self.security <= 0:
            self.phase = Phase.GAME_OVER
            self.end_reason = "SECURITY BREACH"
        elif self.frame >= SHIFT_FRAMES:
            self.phase = Phase.GAME_OVER
            self.end_reason = "SHIFT COMPLETE"
        if self.phase == Phase.GAME_OVER:
            self.best_score = max(self.best_score, self.score)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.03
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # --- Update ---
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.start_game()
        elif self.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._flag_at(pyxel.mouse_x, pyxel.mouse_y)
            self.frame += 1
            if self.shake > 0:
                self.shake -= 1
            self._update_bags()
            self._update_particles()
            self._update_floating_texts()
            self._check_game_over()
        elif self.phase == Phase.GAME_OVER:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.phase = Phase.TITLE

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
        pyxel.text(118, 80, "SCANLINE", YELLOW)
        pyxel.text(124, 100, "Baggage X-Ray", WHITE)
        pyxel.text(72, 140, "CLICK: flag / unflag a bag", WHITE)
        pyxel.text(72, 150, "SPACE: start shift", WHITE)
        pyxel.text(72, 168, "Catch contraband. Don't false-alarm.", GRAY)
        if self.best_score > 0:
            pyxel.text(72, 186, f"BEST SCORE {self.best_score}", YELLOW)

    def _draw_playing(self) -> None:
        try:
            if self.shake > 0:
                jx = (self.shake * 7) % 5 - 2
                jy = (self.shake * 11) % 5 - 2
                pyxel.camera(jx, jy)
            else:
                pyxel.camera(0, 0)
        except BaseException:
            pass

        # Belt
        pyxel.rect(0, BAG_Y - 30, WIDTH, 60, NAVY)
        pyxel.rect(0, BAG_Y - 30, WIDTH, 2, GRAY)
        pyxel.rect(0, BAG_Y + 28, WIDTH, 2, GRAY)
        spacing = 24
        offset = (self.frame // 4) % spacing
        for x in range(-spacing + offset, WIDTH, spacing):
            pyxel.rect(x, BAG_Y - 1, 10, 2, GRAY)

        # Bags
        for bag in self.bags:
            self._draw_bag(bag)

        # Particles
        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), 1, p.color)

        # Floating text
        for ft in self.floating_texts:
            pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

        self._draw_hud()

    def _draw_bag(self, bag: Bag) -> None:
        bx = int(bag.x)
        by = int(bag.y - BAG_H / 2)
        pyxel.rect(bx, by, BAG_W, BAG_H, DARK_BLUE)
        if bag.flagged:
            pyxel.rectb(bx, by, BAG_W, BAG_H, RED)
            pyxel.rectb(bx - 1, by - 1, BAG_W + 2, BAG_H + 2, RED)
        else:
            pyxel.rectb(bx, by, BAG_W, BAG_H, GRAY)
        n = len(bag.items)
        total_w = n * ITEM_CELL
        start_x = bx + (BAG_W - total_w) // 2
        for i, it in enumerate(bag.items):
            self._draw_item(it, start_x + i * ITEM_CELL + ITEM_CELL // 2, bag.y)

    def _draw_item(self, it: ItemDef, cx: float, cy: float) -> None:
        x = int(cx)
        y = int(cy)
        col = it.color
        if it.kind == "BOOK":
            pyxel.rect(x - 4, y - 6, 8, 12, col)
        elif it.kind == "SHOE":
            pyxel.rect(x - 5, y - 4, 10, 8, col)
            pyxel.rect(x - 5, y + 3, 6, 2, col)
        elif it.kind == "BOTTLE":
            pyxel.rect(x - 3, y - 5, 6, 10, col)
            pyxel.rect(x - 2, y - 7, 4, 3, col)
        elif it.kind == "GUN":
            pyxel.rect(x - 6, y - 2, 12, 4, col)
            pyxel.rect(x + 2, y - 2, 4, 8, col)
        elif it.kind == "KNIFE":
            pyxel.line(x - 5, y + 4, x + 5, y - 4, col)
            pyxel.rect(x - 5, y + 1, 4, 3, col)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE {self.score}", WHITE)
        sec_col = LIME if self.security > 60 else YELLOW if self.security > 30 else RED
        pyxel.text(4, 14, "SEC", WHITE)
        pyxel.rect(28, 14, 100, 6, BLACK)
        pyxel.rect(28, 14, int(100 * max(0, self.security) / 100), 6, sec_col)
        pyxel.rectb(28, 14, 100, 6, GRAY)
        if self.combo > 1:
            pyxel.text(140, 4, f"COMBO x{self.combo}", YELLOW)
        pyxel.text(220, 4, f"C {self.caught}", LIME)
        pyxel.text(220, 14, f"M {self.missed}", RED)
        pyxel.text(270, 4, f"F {self.false_alarms}", ORANGE)
        pyxel.text(270, 14, f"P {self.passed}", LIME)
        remain = max(0, SHIFT_FRAMES - self.frame)
        pyxel.rect(4, HEIGHT - 8, WIDTH - 8, 4, BLACK)
        pyxel.rect(4, HEIGHT - 8, int((WIDTH - 8) * remain / SHIFT_FRAMES), 4, CYAN)
        pyxel.rectb(4, HEIGHT - 8, WIDTH - 8, 4, GRAY)

    def _draw_game_over(self) -> None:
        color = RED if self.end_reason == "SECURITY BREACH" else LIME
        pyxel.text(92, 80, self.end_reason, color)
        pyxel.text(92, 100, f"SCORE {self.score}", WHITE)
        pyxel.text(92, 110, f"BEST  {self.best_score}", YELLOW)
        pyxel.text(92, 120, f"MAX COMBO x{self.max_combo}", WHITE)
        pyxel.text(92, 132, f"CAUGHT {self.caught}  MISS {self.missed}", WHITE)
        pyxel.text(92, 142, f"FALSE {self.false_alarms}  PASS {self.passed}", WHITE)
        pyxel.text(92, 164, "SPACE to retry", WHITE)


if __name__ == "__main__":
    Game()
