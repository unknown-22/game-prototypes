"""Mining Front — Lane-based Tower Defense Prototype.

Reinterpreted from game_idea_factory idea #1 (31.8):
  "Same card consecutively → effect changes" → Chain Reactors amplify
  "Chain reaction UI" → cascade effects, floating numbers
  "Space mining / resource conversion" → ore economy, tower placement
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from random import Random

import pyxel

# ── Config ──
SCREEN_W = 400
SCREEN_H = 300
FPS = 60

GRID_COLS = 8
GRID_ROWS = 5
CELL_SIZE = 38
GRID_X = 36
GRID_Y = 36

MAX_HP = 10
START_ORE = 50
INTEREST_RATE = 0.05
PREP_TIME = 5 * FPS
WAVE_PREP_TIME = 3 * FPS
TOTAL_WAVES = 10

# ── Enums ──


class TowerKind(Enum):
    LASER = auto()
    CHAIN = auto()
    SIPHON = auto()


class EnemyKind(Enum):
    SCOUT = auto()
    DRONE = auto()
    TANK = auto()


class Phase(Enum):
    PREP = auto()
    COMBAT = auto()
    VICTORY = auto()
    DEFEAT = auto()


# ── Data Classes ──


@dataclass
class TowerDef:
    name: str
    cost: int
    damage: float
    cooldown: float
    color: int
    desc: str
    range_cols: int = 3


TOWER_DEFS: dict[TowerKind, TowerDef] = {
    TowerKind.LASER: TowerDef("LASER", 10, 15.0, 0.8, pyxel.COLOR_RED, "Basic dmg"),
    TowerKind.CHAIN: TowerDef(
        "CHAIN", 25, 12.0, 0.55, pyxel.COLOR_ORANGE, "+50%/adj chain"
    ),
    TowerKind.SIPHON: TowerDef(
        "SIPHON", 15, 8.0, 1.0, pyxel.COLOR_CYAN, "+10 ore/kill"
    ),
}


@dataclass
class EnemyDef:
    name: str
    hp: float
    speed: float
    reward: int
    color: int
    size: int


ENEMY_DEFS: dict[EnemyKind, EnemyDef] = {
    EnemyKind.SCOUT: EnemyDef("SCOUT", 20.0, 60.0, 5, pyxel.COLOR_GREEN, 6),
    EnemyKind.DRONE: EnemyDef("DRONE", 45.0, 38.0, 12, pyxel.COLOR_YELLOW, 8),
    EnemyKind.TANK: EnemyDef("TANK", 120.0, 22.0, 30, pyxel.COLOR_PURPLE, 10),
}


@dataclass
class Tower:
    kind: TowerKind
    col: int
    row: int
    cooldown: float = 0.0


@dataclass
class Enemy:
    kind: EnemyKind
    x: float
    row: int
    hp: float
    reward: int = 0

    @property
    def defn(self) -> EnemyDef:
        return ENEMY_DEFS[self.kind]


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: float
    color: int


# ── Game ──


class Game:
    """Lane-based tower defense: place mining towers, survive waves."""

    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H, title="Mining Front", fps=FPS, display_scale=2
        )
        self.rng = Random(42)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.hp: int = MAX_HP
        self.ore: int = START_ORE
        self.wave: int = 0
        self.phase: Phase = Phase.PREP
        self.prep_timer: int = PREP_TIME
        self.wave_timer: float = 0.0
        self.wave_queue: list[tuple[EnemyKind, float]] = []
        self.enemies: list[Enemy] = []
        self.towers: list[Tower] = []
        self.particles: list[Particle] = []
        self.floaters: list[FloatingText] = []
        self.selected_tower: TowerKind = TowerKind.LASER
        self.score: int = 0
        self.shake_frames: int = 0
        self._gen_wave()

    # ── Wave Generation ──

    def _gen_wave(self) -> None:
        self.wave_queue.clear()
        base_count = 3 + self.wave * 2
        for i in range(base_count):
            delay = i * max(0.2, 0.7 - self.wave * 0.03)
            delay += self.rng.random() * 0.3
            if self.wave < 3:
                kind = EnemyKind.SCOUT
            elif self.wave < 6:
                kind = self.rng.choice([EnemyKind.SCOUT, EnemyKind.DRONE])
            else:
                kind = self.rng.choices(
                    [EnemyKind.SCOUT, EnemyKind.DRONE, EnemyKind.TANK],
                    weights=[2, 3, 2],
                )[0]
            self.wave_queue.append((kind, delay))
        self.wave_timer = 0.0

    # ── Grid Helpers ──

    @staticmethod
    def _cell_center(col: int, row: int) -> tuple[int, int]:
        x = GRID_X + col * CELL_SIZE + CELL_SIZE // 2
        y = GRID_Y + row * CELL_SIZE + CELL_SIZE // 2
        return x, y

    @staticmethod
    def _cell_rect(col: int, row: int) -> tuple[int, int, int, int]:
        x = GRID_X + col * CELL_SIZE
        y = GRID_Y + row * CELL_SIZE
        return x, y, CELL_SIZE, CELL_SIZE

    @staticmethod
    def _grid_pos(px: int, py: int) -> tuple[int, int] | None:
        col = (px - GRID_X) // CELL_SIZE
        row = (py - GRID_Y) // CELL_SIZE
        if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
            return col, row
        return None

    def _tower_at(self, col: int, row: int) -> Tower | None:
        for t in self.towers:
            if t.col == col and t.row == row:
                return t
        return None

    def _chain_bonus(self, tower: Tower) -> float:
        """Damage multiplier from orthogonally adjacent Chain Reactors."""
        if tower.kind != TowerKind.CHAIN:
            return 1.0
        adjacent = 0
        for t in self.towers:
            if t.kind != TowerKind.CHAIN or t is tower:
                continue
            if abs(t.col - tower.col) + abs(t.row - tower.row) == 1:
                adjacent += 1
        return 1.0 + adjacent * 0.5

    # ── Effects ──

    def _float(self, x: float, y: float, text: str, color: int) -> None:
        self.floaters.append(FloatingText(x, y, text, 1.2, color))

    def _burst(self, x: float, y: float, color: int, count: int = 4) -> None:
        import math
        for _ in range(count):
            angle = self.rng.random() * 6.2832
            speed = 20.0 + self.rng.random() * 60.0
            life = 0.25 + self.rng.random() * 0.35
            self.particles.append(
                Particle(
                    x,
                    y,
                    speed * math.cos(angle),
                    speed * math.sin(angle),
                    life,
                    life,
                    color,
                )
            )

    def _shake(self, amount: int = 2) -> None:
        self.shake_frames = max(self.shake_frames, amount)

    # ── Targeting ──

    def _find_target(self, tower: Tower) -> Enemy | None:
        """Find nearest enemy within tower's column range (rightward only)."""
        defn = TOWER_DEFS[tower.kind]
        cx, _cy = self._cell_center(tower.col, tower.row)
        tower_left = GRID_X + tower.col * CELL_SIZE
        max_x = tower_left + defn.range_cols * CELL_SIZE + 20

        best: Enemy | None = None
        best_dist = float("inf")
        for e in self.enemies:
            if e.x < tower_left - 10 or e.x > max_x:
                continue
            dist = abs(e.x - cx) + abs(e.row - tower.row) * CELL_SIZE * 0.3
            if dist < best_dist:
                best_dist = dist
                best = e
        return best

    # ── Tower Selection UI ──

    def _check_select_ui(self, mx: int, my: int) -> None:
        btn_y = SCREEN_H - 30
        btn_w = 110
        btn_h = 24
        for i, kind in enumerate(
            [TowerKind.LASER, TowerKind.CHAIN, TowerKind.SIPHON]
        ):
            bx = 10 + i * (btn_w + 6)
            if bx <= mx <= bx + btn_w and btn_y <= my <= btn_y + btn_h:
                self.selected_tower = kind
                return

    # ── Update ──

    def update(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            return

        if self.phase in (Phase.VICTORY, Phase.DEFEAT):
            return

        if self.phase == Phase.PREP:
            self._update_prep()
        elif self.phase == Phase.COMBAT:
            self._update_combat()

        self._update_particles()
        self._update_floaters()
        if self.shake_frames > 0:
            self.shake_frames -= 1
            offset = self.shake_frames % 3 - 1
            pyxel.camera(offset, 0)
        else:
            pyxel.camera(0, 0)

    def _update_prep(self) -> None:
        self.prep_timer -= 1

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            pos = self._grid_pos(pyxel.mouse_x, pyxel.mouse_y)
            if pos is not None:
                col, row = pos
                if (
                    self._tower_at(col, row) is None
                    and self.ore >= TOWER_DEFS[self.selected_tower].cost
                ):
                    self.ore -= TOWER_DEFS[self.selected_tower].cost
                    self.towers.append(Tower(self.selected_tower, col, row))
            else:
                self._check_select_ui(pyxel.mouse_x, pyxel.mouse_y)

        if pyxel.btnp(pyxel.KEY_1):
            self.selected_tower = TowerKind.LASER
        elif pyxel.btnp(pyxel.KEY_2):
            self.selected_tower = TowerKind.CHAIN
        elif pyxel.btnp(pyxel.KEY_3):
            self.selected_tower = TowerKind.SIPHON
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.prep_timer = 1

        if self.prep_timer <= 0:
            self.phase = Phase.COMBAT
            self.wave_timer = 0.0

    def _update_combat(self) -> None:
        dt = 1.0 / FPS
        self.wave_timer += dt

        # Spawn enemies
        i = 0
        while i < len(self.wave_queue):
            kind, delay = self.wave_queue[i]
            if self.wave_timer >= delay:
                row = self.rng.randint(0, GRID_ROWS - 1)
                edef = ENEMY_DEFS[kind]
                self.enemies.append(
                    Enemy(
                        kind,
                        float(GRID_X + GRID_COLS * CELL_SIZE + 16),
                        row,
                        edef.hp,
                        edef.reward,
                    )
                )
                self.wave_queue.pop(i)
            else:
                i += 1

        # Move enemies
        for e in self.enemies[:]:
            e.x -= e.defn.speed * dt
            if e.x < GRID_X - 12:
                self.hp -= 1
                cy = GRID_Y + e.row * CELL_SIZE + CELL_SIZE // 2
                self._float(float(e.x), float(cy), "-1 HP", pyxel.COLOR_RED)
                self._shake(4)
                self.enemies.remove(e)
                if self.hp <= 0:
                    self.hp = 0
                    self.phase = Phase.DEFEAT
                    return

        # Towers fire
        for t in self.towers:
            t.cooldown -= dt
            if t.cooldown <= 0:
                target = self._find_target(t)
                if target is not None:
                    tdef = TOWER_DEFS[t.kind]
                    bonus = self._chain_bonus(t)
                    dmg = tdef.damage * bonus
                    target.hp -= dmg
                    t.cooldown = tdef.cooldown

                    cy = float(GRID_Y + target.row * CELL_SIZE + CELL_SIZE // 2)
                    self._burst(float(target.x), cy, tdef.color, 2)

                    if target.hp <= 0:
                        gained = target.reward
                        if t.kind == TowerKind.SIPHON:
                            gained += 10
                        self.ore += gained
                        self.score += gained
                        self._float(
                            float(target.x),
                            cy - 4.0,
                            f"+{gained}",
                            pyxel.COLOR_YELLOW,
                        )
                        self._burst(
                            float(target.x), cy, target.defn.color, 5
                        )
                        self.enemies.remove(target)
                    elif bonus > 1.05:
                        self._float(
                            float(target.x),
                            cy - 12.0,
                            f"x{bonus:.1f}",
                            pyxel.COLOR_ORANGE,
                        )
                        self._shake(1)

        # Wave complete check
        if not self.wave_queue and not self.enemies:
            self.wave += 1
            if self.wave >= TOTAL_WAVES:
                self.phase = Phase.VICTORY
            else:
                self.ore += int(self.ore * INTEREST_RATE)
                self.phase = Phase.PREP
                self.prep_timer = WAVE_PREP_TIME
                self._gen_wave()

    def _update_particles(self) -> None:
        dt = 1.0 / FPS
        for p in self.particles[:]:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floaters(self) -> None:
        dt = 1.0 / FPS
        for f in self.floaters[:]:
            f.y -= 28.0 * dt
            f.life -= dt
            if f.life <= 0:
                self.floaters.remove(f)

    # ── Draw ──

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.VICTORY:
            self._draw_victory()
            return
        if self.phase == Phase.DEFEAT:
            self._draw_defeat()
            return

        self._draw_grid()
        self._draw_chain_links()
        self._draw_enemies()
        self._draw_towers()
        self._draw_particles()
        self._draw_floaters()
        self._draw_hud()
        self._draw_tower_select()

    def _draw_grid(self) -> None:
        for col in range(GRID_COLS):
            for row in range(GRID_ROWS):
                x, y, w, h = self._cell_rect(col, row)
                bg = (
                    pyxel.COLOR_NAVY
                    if (col + row) % 2 == 0
                    else pyxel.COLOR_DARK_BLUE
                )
                pyxel.rect(x, y, w, h, bg)
                pyxel.rectb(x, y, w, h, pyxel.COLOR_GRAY)

        if self.phase == Phase.PREP:
            pos = self._grid_pos(pyxel.mouse_x, pyxel.mouse_y)
            if pos is not None:
                col, row = pos
                x, y, w, h = self._cell_rect(col, row)
                occupied = self._tower_at(col, row) is not None
                affordable = self.ore >= TOWER_DEFS[self.selected_tower].cost
                hl = pyxel.COLOR_RED if occupied else (
                    pyxel.COLOR_GREEN if affordable else pyxel.COLOR_YELLOW
                )
                pyxel.rectb(x, y, w, h, hl)

    def _draw_chain_links(self) -> None:
        """Draw lines between adjacent chain reactors."""
        for t in self.towers:
            if t.kind != TowerKind.CHAIN:
                continue
            x1, y1 = self._cell_center(t.col, t.row)
            for other in self.towers:
                if other is t or other.kind != TowerKind.CHAIN:
                    continue
                if (
                    abs(other.col - t.col) + abs(other.row - t.row) == 1
                    and (other.col > t.col or other.row > t.row)
                ):
                    x2, y2 = self._cell_center(other.col, other.row)
                    pyxel.line(x1, y1, x2, y2, pyxel.COLOR_ORANGE)

    def _draw_enemies(self) -> None:
        for e in self.enemies:
            cy = GRID_Y + e.row * CELL_SIZE + CELL_SIZE // 2
            edef = e.defn
            ex = int(e.x)
            pyxel.circ(ex, int(cy), edef.size, edef.color)
            pyxel.circ(ex, int(cy), edef.size - 2, pyxel.COLOR_BLACK)
            # HP bar
            hp_pct = max(0.0, e.hp / edef.hp)
            bar_w = edef.size * 2
            pyxel.rect(
                ex - bar_w // 2, int(cy) - edef.size - 6, bar_w, 3, pyxel.COLOR_RED
            )
            pyxel.rect(
                ex - bar_w // 2,
                int(cy) - edef.size - 6,
                int(bar_w * hp_pct),
                3,
                pyxel.COLOR_GREEN,
            )

    def _draw_towers(self) -> None:
        for t in self.towers:
            x, y = self._cell_center(t.col, t.row)
            tdef = TOWER_DEFS[t.kind]
            size = 10
            if t.kind == TowerKind.CHAIN:
                bonus = self._chain_bonus(t)
                s = int(size * (0.8 + bonus * 0.15))
                pyxel.rect(x - s, y - s, s * 2, s * 2, tdef.color)
            else:
                pyxel.rect(x - size, y - size, size * 2, size * 2, tdef.color)
            abbr = t.kind.name[:3]
            pyxel.text(x - 6, y - 3, abbr, pyxel.COLOR_WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / p.max_life
            c = p.color if alpha > 0.5 else pyxel.COLOR_GRAY
            pyxel.pset(int(p.x), int(p.y), c)

    def _draw_floaters(self) -> None:
        for f in self.floaters:
            alpha = f.life
            c = f.color if alpha > 0.5 else pyxel.COLOR_GRAY
            pyxel.text(int(f.x) - len(f.text) * 2, int(f.y), f.text, c)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 22, pyxel.COLOR_DARK_BLUE)
        hp_bar = "|" * self.hp + "." * (MAX_HP - self.hp)
        pyxel.text(4, 4, f"HP:{hp_bar}", pyxel.COLOR_RED if self.hp <= 3 else pyxel.COLOR_GREEN)
        pyxel.text(120, 4, f"ORE:{self.ore}", pyxel.COLOR_YELLOW)
        pyxel.text(210, 4, f"W:{self.wave + 1}/{TOTAL_WAVES}", pyxel.COLOR_CYAN)
        pyxel.text(290, 4, f"SC:{self.score}", pyxel.COLOR_WHITE)

        if self.phase == Phase.PREP:
            secs = max(0, self.prep_timer // FPS + 1)
            msg = f"PREP {secs}s  [SPACE=start]"
            pyxel.text(SCREEN_W // 2 - 45, SCREEN_H - 10, msg, pyxel.COLOR_YELLOW)
        elif self.phase == Phase.COMBAT:
            remaining = len(self.wave_queue) + len(self.enemies)
            pyxel.text(
                SCREEN_W // 2 - 30,
                SCREEN_H - 10,
                f"COMBAT! x{remaining}",
                pyxel.COLOR_RED,
            )

    def _draw_tower_select(self) -> None:
        btn_y = SCREEN_H - 30
        btn_w = 110
        btn_h = 24
        kinds = [TowerKind.LASER, TowerKind.CHAIN, TowerKind.SIPHON]
        for i, kind in enumerate(kinds):
            bx = 10 + i * (btn_w + 6)
            tdef = TOWER_DEFS[kind]
            bg = tdef.color if self.selected_tower == kind else pyxel.COLOR_DARK_BLUE
            pyxel.rect(bx, btn_y, btn_w, btn_h, bg)
            pyxel.rectb(bx, btn_y, btn_w, btn_h, pyxel.COLOR_WHITE)
            label = f"{i + 1}:{tdef.name} ${tdef.cost}"
            pyxel.text(bx + 3, btn_y + 3, label, pyxel.COLOR_WHITE)
            pyxel.text(bx + 3, btn_y + 13, tdef.desc, pyxel.COLOR_GRAY)

    def _draw_victory(self) -> None:
        pyxel.cls(pyxel.COLOR_DARK_BLUE)
        pyxel.text(SCREEN_W // 2 - 28, SCREEN_H // 2 - 15, "VICTORY!", pyxel.COLOR_GREEN)
        pyxel.text(
            SCREEN_W // 2 - 50, SCREEN_H // 2 + 10, f"Score: {self.score}", pyxel.COLOR_WHITE
        )
        pyxel.text(
            SCREEN_W // 2 - 28, SCREEN_H // 2 + 30, "R: Retry", pyxel.COLOR_GRAY
        )

    def _draw_defeat(self) -> None:
        pyxel.cls(pyxel.COLOR_DARK_BLUE)
        pyxel.text(SCREEN_W // 2 - 25, SCREEN_H // 2 - 15, "DEFEAT!", pyxel.COLOR_RED)
        pyxel.text(
            SCREEN_W // 2 - 50,
            SCREEN_H // 2 + 10,
            f"Wave: {self.wave + 1}/{TOTAL_WAVES}",
            pyxel.COLOR_WHITE,
        )
        pyxel.text(
            SCREEN_W // 2 - 50, SCREEN_H // 2 + 25, f"Score: {self.score}", pyxel.COLOR_WHITE
        )
        pyxel.text(
            SCREEN_W // 2 - 28, SCREEN_H // 2 + 45, "R: Retry", pyxel.COLOR_GRAY
        )


if __name__ == "__main__":
    Game()
