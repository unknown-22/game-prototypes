"""Fork Bomb — Dice-splitting circuit battler.

Core mechanic: Split dice values across 3 circuit lanes;
matching adjacent values RECOMBINE for multiplied burst damage.

Most fun moment: All 3 lanes converge with the same value
for a TRIPLE RECOMBINE, dealing massive multiplied damage.

Based on: game_idea_factory idea #1 (Score 31.6)
Theme: Hacking (circuit/log)
Hook: Numbers split into multiple paths and recombine for explosion.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
import pyxel

# ── Constants ──

SCREEN_W = 400
SCREEN_H = 300
MAX_RISK = 10
MAX_TURN = 12
DICE_PER_TURN = 4
LANE_COUNT = 3
SPLIT_RISK_COST = 2
RISK_DECAY = 1
ENEMY_BASE_HP = 150
PLAYER_BASE_HP = 100
ENEMY_BASE_DMG = 6

# ── Data classes ──


@dataclass
class Die:
    """A signal die with a numeric value, optionally placed on a lane."""

    value: int
    lane: int = -1  # -1 = unplaced, 0/1/2 = lanes
    split_from: int = -1  # index of parent die if this is a split offspring


@dataclass
class Particle:
    """Lightweight visual particle for damage numbers and effects."""

    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    text: str = ""


# ── Phase enum ──


class Phase(Enum):
    ROLL = auto()
    ROUTE = auto()
    FIRE = auto()
    RESOLVE = auto()
    VICTORY = auto()
    DEFEAT = auto()


# ── Main game class ──


class ForkBomb:
    """Fork Bomb — dice-splitting circuit battler.

    Each turn, roll dice and route them through 3 circuit lanes.
    Split dice to fill more lanes at the cost of RISK.
    Matching adjacent values RECOMBINE for multiplied damage.
    """

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Fork Bomb", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State management ──

    def reset(self) -> None:
        """Initialize or reset all game state."""
        self.phase: Phase = Phase.ROLL
        self.turn: int = 0
        self.hp: int = PLAYER_BASE_HP
        self.max_hp: int = PLAYER_BASE_HP
        self.enemy_hp: int = ENEMY_BASE_HP
        self.enemy_max_hp: int = ENEMY_BASE_HP
        self.risk: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.dice: list[Die] = []
        self.lanes: list[Die | None] = [None, None, None]
        self.selected_die: int = -1
        self.fire_timer: int = 0
        self.fire_step: int = 0
        self.fire_damage: int = 0
        self.fire_msg: str = ""
        self.recombine_flash: int = 0
        self.particles: list[Particle] = []
        self.result_msg: str = ""
        self.result_timer: int = 0
        self._start_turn()

    def _start_turn(self) -> None:
        """Begin a new turn: roll dice, clear lanes, advance turn counter."""
        self.turn += 1
        self.dice = [Die(value=random.randint(1, 8)) for _ in range(DICE_PER_TURN)]
        self.lanes = [None, None, None]
        self.selected_die = -1
        self.fire_timer = 0
        self.fire_step = 0
        self.fire_damage = 0
        self.fire_msg = ""
        self.recombine_flash = 0
        self.phase = Phase.ROLL

    # ── Core mechanics ──

    def _split_die(self, lane_idx: int) -> None:
        """Split a placed die on the given lane into halves on adjacent lanes.

        Costs RISK. Only works if at least one adjacent lane is empty.
        The original die is consumed; two new half-value dice are created.
        """
        placed = self.lanes[lane_idx]
        if placed is None or placed.value <= 1:
            return  # nothing to split or value too small

        # Find empty adjacent lanes
        targets: list[int] = []
        if lane_idx > 0 and self.lanes[lane_idx - 1] is None:
            targets.append(lane_idx - 1)
        if lane_idx < LANE_COUNT - 1 and self.lanes[lane_idx + 1] is None:
            targets.append(lane_idx + 1)

        if len(targets) == 0:
            return  # nowhere to split to

        # Pay risk cost
        self.risk = min(MAX_RISK, self.risk + SPLIT_RISK_COST)

        # Remove original from lane and mark consumed
        orig_value = placed.value
        placed.value = 0
        placed.lane = -1
        self.lanes[lane_idx] = None

        # Create half-value dice on adjacent lanes
        half = orig_value // 2
        values = [half, orig_value - half]
        for i, tgt in enumerate(targets[:2]):
            if values[i] <= 0:
                continue
            new_die = Die(value=values[i], lane=tgt, split_from=id(placed))
            self.dice.append(new_die)
            self.lanes[tgt] = new_die

        # Spawn split particles
        ly = 80 + lane_idx * 45
        for _ in range(4):
            self.particles.append(
                Particle(
                    x=160,
                    y=ly + 15,
                    vx=random.uniform(-3, 3),
                    vy=random.uniform(-2, 2),
                    life=15,
                    color=12,
                )
            )

    def _calculate_damage(self) -> tuple[int, int, str]:
        """Calculate fire damage with recombine multipliers.

        Returns (base_damage, final_damage, message).
        """
        lane_vals: list[int] = []
        for lane_die in self.lanes:
            lane_vals.append(lane_die.value if lane_die is not None else 0)

        # Check adjacent pairs for recombines
        multiplier = 1
        recombine_count = 0
        for i in range(LANE_COUNT - 1):
            if lane_vals[i] > 0 and lane_vals[i] == lane_vals[i + 1]:
                multiplier *= 2
                recombine_count += 1

        base_dmg = sum(lane_vals)
        final_dmg = base_dmg * multiplier

        if recombine_count >= 2:
            msg = "TRIPLE RECOMBINE x4!"
        elif recombine_count == 1:
            msg = "RECOMBINE x2!"
        else:
            msg = ""

        return base_dmg, final_dmg, msg

    def _begin_fire(self) -> None:
        """Transition from ROUTE to FIRE phase, compute damage."""
        self.phase = Phase.FIRE
        self.fire_step = 0
        self.fire_timer = 18

        base_dmg, final_dmg, msg = self._calculate_damage()
        self.fire_damage = final_dmg
        self.fire_msg = msg

        # Update combo
        if final_dmg > base_dmg:
            self.combo += 1
        else:
            self.combo = 0
        self.max_combo = max(self.max_combo, self.combo)

        # Score: damage scaled by combo streak
        self.score += final_dmg * (1 + self.combo)

        # Recombine flash effect
        if final_dmg > base_dmg:
            self.recombine_flash = 15

    def _resolve(self) -> None:
        """Apply damage, enemy counterattack, risk decay, check win/lose."""
        self.phase = Phase.RESOLVE

        # Apply player damage to enemy
        self.enemy_hp = max(0, self.enemy_hp - self.fire_damage)

        # Enemy counterattack
        enemy_dmg = ENEMY_BASE_DMG + self.turn + self.risk
        self.hp = max(0, self.hp - enemy_dmg)

        # Risk naturally decays
        self.risk = max(0, self.risk - RISK_DECAY)

        # Result message
        self.result_msg = f"DEALT:{self.fire_damage}  TOOK:{enemy_dmg}"
        self.result_timer = 75  # ~2.5 seconds at 30 fps

        # Spawn damage particles on enemy
        if self.fire_damage > 0:
            for _ in range(6):
                self.particles.append(
                    Particle(
                        x=350,
                        y=120,
                        vx=random.uniform(-3, 3),
                        vy=random.uniform(-4, -0.5),
                        life=25,
                        color=10,
                    )
                )
            # Floating damage number
            self.particles.append(
                Particle(
                    x=350,
                    y=110,
                    vx=0.0,
                    vy=-1.5,
                    life=50,
                    color=10,
                    text=str(self.fire_damage),
                )
            )

        # Spawn particles on player for damage taken
        if enemy_dmg > 0:
            for _ in range(4):
                self.particles.append(
                    Particle(
                        x=60,
                        y=275,
                        vx=random.uniform(-2, 2),
                        vy=random.uniform(-3, -0.5),
                        life=20,
                        color=8,
                    )
                )

    # ── Update ──

    def update(self) -> None:
        """Main update loop — input handling and phase transitions."""
        # Global: restart
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            return

        # Update particles
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

        # Recombine flash decay
        if self.recombine_flash > 0:
            self.recombine_flash -= 1

        # Phase-specific updates
        match self.phase:
            case Phase.ROLL:
                if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                    self.phase = Phase.ROUTE

            case Phase.ROUTE:
                self._update_route()

            case Phase.FIRE:
                self._update_fire()

            case Phase.RESOLVE:
                self.result_timer -= 1
                if self.result_timer <= 0:
                    if self.hp <= 0:
                        self.phase = Phase.DEFEAT
                    elif self.enemy_hp <= 0 or self.turn >= MAX_TURN:
                        self.phase = Phase.VICTORY
                    else:
                        self._start_turn()

            case Phase.VICTORY | Phase.DEFEAT:
                pass

    def _update_route(self) -> None:
        """Handle mouse input during the ROUTE phase."""
        if not pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            return

        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        # Check FIRE button (bottom-right)
        if 320 <= mx <= 390 and 258 <= my <= 288:
            self._begin_fire()
            return

        # Check lane click
        lane_h = 30
        lane_y_start = 80
        for lane_idx in range(LANE_COUNT):
            ly = lane_y_start + lane_idx * 45
            if ly <= my <= ly + lane_h and 20 <= mx <= 310:
                if self.selected_die >= 0:
                    # Place selected die on empty lane
                    if self.lanes[lane_idx] is None:
                        self.dice[self.selected_die].lane = lane_idx
                        self.lanes[lane_idx] = self.dice[self.selected_die]
                        self.selected_die = -1
                elif self.lanes[lane_idx] is not None:
                    # Split placed die
                    self._split_die(lane_idx)
                return

        # Check dice pool click (top area)
        dice_y = 15
        dice_h = 30
        if dice_y <= my <= dice_y + dice_h:
            for i, d in enumerate(self.dice):
                if d.lane >= 0 or d.value <= 0:
                    continue
                dx = 20 + i * 55
                if dx <= mx <= dx + 40:
                    self.selected_die = i
                    return

        # Click elsewhere: deselect
        self.selected_die = -1

    def _update_fire(self) -> None:
        """Animate lane firing: step through lanes with visual effects."""
        self.fire_timer -= 1
        if self.fire_timer <= 0:
            self.fire_step += 1
            if self.fire_step >= LANE_COUNT:
                self._resolve()
                return
            self.fire_timer = 18

        # Spawn fire particles
        if self.fire_timer == 12 and self.fire_step < LANE_COUNT:
            if self.lanes[self.fire_step] is not None:
                ly = 80 + self.fire_step * 45
                for _ in range(5):
                    self.particles.append(
                        Particle(
                            x=160,
                            y=ly + 15,
                            vx=random.uniform(3, 8),
                            vy=random.uniform(-2, 2),
                            life=18,
                            color=self.fire_step + 9,
                        )
                    )

    # ── Draw ──

    def draw(self) -> None:
        """Main draw loop — render all game elements."""
        pyxel.cls(0)

        match self.phase:
            case Phase.VICTORY:
                self._draw_victory()
                return
            case Phase.DEFEAT:
                self._draw_defeat()
                return
            case _:
                pass

        # Recombine screen flash
        if self.recombine_flash > 0 and self.recombine_flash % 3 == 0:
            pyxel.cls(1)

        self._draw_circuit_bg()
        self._draw_lanes()
        self._draw_dice_pool()
        self._draw_enemy()
        self._draw_stats()
        self._draw_fire_button()
        self._draw_fire_anim()
        self._draw_particles()
        self._draw_messages()
        self._draw_instructions()

    def _draw_circuit_bg(self) -> None:
        """Draw background circuit traces."""
        for i in range(LANE_COUNT):
            ly = 80 + i * 45
            pyxel.rect(15, ly + 14, 370, 2, 5)

        # Vertical connection lines
        pyxel.rect(320, 95, 2, 70, 5)

    def _draw_lanes(self) -> None:
        """Draw the 3 circuit lanes and any placed dice."""
        lane_colors = [12, 11, 9]  # cyan, green, orange
        for i in range(LANE_COUNT):
            ly = 80 + i * 45
            color = lane_colors[i]

            # Lane border
            pyxel.rectb(20, ly, 290, 30, color)

            # Placed die
            placed = self.lanes[i]
            if placed is not None and placed.value > 0:
                pyxel.rect(22, ly + 2, 44, 26, color)
                pyxel.text(30, ly + 11, str(placed.value), 0)
                # Split indicator
                if placed.split_from >= 0:
                    pyxel.text(50, ly + 18, "/2", 6)

            # Highlight matching adjacent lanes for recombine hint
            if self.phase == Phase.ROUTE and i < LANE_COUNT - 1:
                a = self.lanes[i]
                b = self.lanes[i + 1]
                if (
                    a is not None
                    and b is not None
                    and a.value > 0
                    and b.value > 0
                    and a.value == b.value
                ):
                    py1 = ly + 14
                    py2 = ly + 45 + 14
                    pyxel.rect(310, py1, 8, py2 - py1, 10)

    def _draw_dice_pool(self) -> None:
        """Draw rolled dice available for placement at top of screen."""
        pyxel.text(20, 3, f"TURN {self.turn}/{MAX_TURN}", 7)

        dice_y = 15
        for i, d in enumerate(self.dice):
            if d.lane >= 0 or d.value <= 0:
                continue
            dx = 20 + i * 55
            is_selected = i == self.selected_die
            color = 7 if is_selected else 10
            pyxel.rectb(dx, dice_y, 40, 30, color)
            pyxel.text(dx + 14, dice_y + 11, str(d.value), color)
            if is_selected:
                pyxel.rectb(dx - 1, dice_y - 1, 42, 32, 7)

    def _draw_enemy(self) -> None:
        """Draw enemy unit and HP bar."""
        ex = 325
        ey = 75

        # Enemy body
        pyxel.rect(ex, ey, 55, 75, 8)
        pyxel.text(ex + 5, ey + 5, "NODE", 0)
        pyxel.text(ex + 5, ey + 18, "GUARD", 0)

        # Enemy HP bar
        bar_w = 45
        bar_h = 6
        bar_x = ex + 5
        bar_y = ey + 60
        hp_ratio = max(0.0, self.enemy_hp / self.enemy_max_hp)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, 5)
        pyxel.rect(bar_x, bar_y, int(bar_w * hp_ratio), bar_h, 8)
        pyxel.text(ex, ey + 68, f"HP:{self.enemy_hp}", 7)

        # Enemy attack indicator
        enemy_dmg = ENEMY_BASE_DMG + self.turn + self.risk
        pyxel.text(ex, ey + 78, f"ATK:{enemy_dmg}", 8)

    def _draw_stats(self) -> None:
        """Draw player HP, risk meter, combo, and score."""
        # Player HP bar
        pyxel.text(10, 268, f"HP:{self.hp}", 7)
        pyxel.rect(10, 280, 100, 6, 5)
        hp_ratio = max(0.0, self.hp / self.max_hp)
        hp_color = 8 if hp_ratio < 0.3 else (9 if hp_ratio < 0.6 else 11)
        pyxel.rect(10, 280, int(100 * hp_ratio), 6, hp_color)

        # Risk meter
        risk_color = 11 if self.risk < 4 else (9 if self.risk < 7 else 8)
        pyxel.text(125, 268, f"RISK:{self.risk}", risk_color)
        pyxel.rect(125, 280, 80, 6, 5)
        risk_ratio = self.risk / MAX_RISK
        pyxel.rect(125, 280, int(80 * risk_ratio), 6, risk_color)

        # Combo
        combo_color = 9 if self.combo > 1 else (11 if self.combo > 0 else 6)
        pyxel.text(225, 268, f"COMBO:x{self.combo}", combo_color)

        # Score
        pyxel.text(225, 283, f"SC:{self.score}", 7)

    def _draw_fire_button(self) -> None:
        """Draw the FIRE! action button."""
        bx, by = 320, 258
        fire_active = self.phase == Phase.ROUTE
        fill_color = 11 if fire_active else 5
        text_color = 0 if fire_active else 5

        pyxel.rectb(bx, by, 70, 28, fill_color)
        if fire_active:
            pyxel.rect(bx + 1, by + 1, 68, 26, fill_color)
        pyxel.text(bx + 16, by + 10, "FIRE!", text_color)

    def _draw_fire_anim(self) -> None:
        """Draw fire animation: lane-by-lane bolt traveling right."""
        if self.phase != Phase.FIRE:
            return

        for i in range(self.fire_step):
            ly = 80 + i * 45
            # Lane already fired — draw greyed out
            pyxel.rect(20, ly, 290, 30, 5)

        if self.fire_step < LANE_COUNT:
            ly = 80 + self.fire_step * 45
            progress = (18 - self.fire_timer) / 18
            bolt_x = int(20 + progress * 280)
            bolt_w = max(6, int(50 * (1 - progress)))
            pyxel.rect(bolt_x, ly + 8, bolt_w, 14, 10)

    def _draw_particles(self) -> None:
        """Draw all active particles."""
        for p in self.particles:
            if p.text:
                alpha = min(15, max(1, p.life // 3))
                pyxel.text(int(p.x), int(p.y), p.text, alpha)
            else:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_messages(self) -> None:
        """Draw result and fire messages."""
        if self.phase == Phase.RESOLVE and self.result_msg:
            pyxel.text(130, 245, self.result_msg, 7)

        if self.fire_msg and self.phase in (Phase.FIRE, Phase.RESOLVE):
            msg_color = 10 if self.recombine_flash > 0 else 7
            pyxel.text(130, 228, self.fire_msg, msg_color)

    def _draw_instructions(self) -> None:
        """Draw contextual help text."""
        if self.phase == Phase.ROLL:
            pyxel.text(100, 55, "Click or press SPACE to begin routing", 6)
        elif self.phase == Phase.ROUTE and self.selected_die < 0:
            lanes_filled = sum(1 for lane_die in self.lanes if lane_die is not None)
            if lanes_filled == 0:
                pyxel.text(60, 55, "Click a die, then click a lane to place it", 6)
            else:
                pyxel.text(
                    80, 55, "Click placed die to SPLIT (+2 RISK)", 12,
                )

    def _draw_victory(self) -> None:
        """Draw victory screen."""
        pyxel.cls(1)
        pyxel.text(130, 90, "CIRCUIT BREACHED!", 7)
        pyxel.text(140, 115, f"SCORE: {self.score}", 10)
        pyxel.text(140, 135, f"MAX COMBO: x{self.max_combo}", 9)
        pyxel.text(140, 155, f"TURNS: {self.turn}", 11)
        pyxel.text(120, 185, "Press R to retry", 7)

    def _draw_defeat(self) -> None:
        """Draw defeat screen."""
        pyxel.cls(1)
        pyxel.text(145, 90, "SYSTEM FAILURE", 8)
        pyxel.text(140, 115, f"SCORE: {self.score}", 7)
        pyxel.text(140, 135, f"TURNS: {self.turn}", 6)
        pyxel.text(140, 155, f"MAX COMBO: x{self.max_combo}", 9)
        pyxel.text(120, 185, "Press R to retry", 7)


# ── Entry point ──

if __name__ == "__main__":
    ForkBomb()
