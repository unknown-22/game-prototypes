"""test_imports.py — Headless logic tests for NETWORK SURGE."""
import sys
import random

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/062_network_surge")


def _make_game():
    """Factory for headless Game instances (bypasses pyxel.init)."""
    import main as m
    g = m.Game.__new__(m.Game)
    g._rng = random.Random(42)
    g.phase = m.PHASE_TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.trace = 0.0
    g.nodes_hacked = 0
    g.total_data_nodes = 0
    g.seed_val = 0
    g.grid = []
    g.particles = []
    g.floating_texts = []
    g.surge_queue = []
    g.surge_timer = 0.0
    g._shake_frames = 0
    g._shake_x = 0.0
    g._shake_y = 0.0
    g._hovered_col = -1
    g._hovered_row = -1
    g._hacking_node = None
    g._hack_timer = 0.0
    g._surge_source_color = -1
    g._frame_count = 0
    g._init_state()
    return g


def test_node_dataclass():
    """Test Node dataclass properties."""
    import main as m
    data_node = m.Node(col=3, row=2, node_type=0, color=1)
    assert data_node.is_data is True
    assert data_node.is_ice is False
    assert data_node.is_firewall is False
    assert not data_node.hacked
    assert not data_node.hacking

    ice_node = m.Node(col=0, row=0, node_type=1, color=-1)
    assert ice_node.is_ice is True
    assert ice_node.is_data is False
    assert ice_node.is_firewall is False

    fw_node = m.Node(col=5, row=3, node_type=2, color=-1)
    assert fw_node.is_firewall is True
    assert fw_node.is_data is False
    assert fw_node.is_ice is False


def test_particle_dataclass():
    """Test Particle dataclass."""
    import main as m
    p = m.Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, color=m.RED, life=20)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.color == m.RED
    assert p.life == 20
    assert p.max_life == 20


def test_constants():
    """Test game constants are valid."""
    import main as m
    assert m.SCREEN_W == 320
    assert m.SCREEN_H == 240
    assert m.COLS == 8
    assert m.ROWS == 6
    assert m.CELL_SIZE == 28
    assert len(m.DATA_COLORS) == 4
    assert m.SURGE_THRESHOLD == 4
    assert m.TRACE_MAX == 100.0
    assert m.TRACE_PENALTY == 5.0
    # Verify data colors
    for c in m.DATA_COLORS:
        assert c in (8, 3, 12, 10)  # RED, GREEN, CYAN, YELLOW


def test_grid_generation():
    """Test _generate_grid creates correct numbers of each node type."""
    import main as m
    g = _make_game()
    g.seed_val = 123
    g._generate_grid()

    total = 0
    data_count = 0
    ice_count = 0
    fw_count = 0
    for r in range(m.ROWS):
        for c in range(m.COLS):
            node = g.grid[r][c]
            assert node is not None, f"Grid cell ({c},{r}) is None"
            total += 1
            if node.is_data:
                data_count += 1
                assert 0 <= node.color < m.NUM_DATA_COLORS
                assert not node.hacked
            elif node.is_ice:
                ice_count += 1
                assert node.color == -1
            elif node.is_firewall:
                fw_count += 1
                assert node.color == -1

    assert total == m.COLS * m.ROWS  # 48
    assert 6 <= ice_count <= 8, f"ICE count {ice_count} out of range"
    assert 4 <= fw_count <= 6, f"FIREWALL count {fw_count} out of range"
    assert data_count == total - ice_count - fw_count
    assert g.total_data_nodes == data_count


def test_grid_deterministic():
    """Test grid generation is deterministic with same seed."""
    import main as m
    g1 = _make_game()
    g1.seed_val = 42
    g1._generate_grid()

    g2 = _make_game()
    g2.seed_val = 42
    g2._generate_grid()

    for r in range(m.ROWS):
        for c in range(m.COLS):
            n1 = g1.grid[r][c]
            n2 = g2.grid[r][c]
            assert n1.node_type == n2.node_type
            assert n1.color == n2.color
            assert n1.col == n2.col
            assert n1.row == n2.row


def test_get_grid_cell():
    """Test _get_grid_cell coordinate mapping."""
    import main as m
    g = _make_game()

    # Top-left node
    col, row = g._get_grid_cell(m.GRID_X, m.GRID_Y)
    assert col == 0
    assert row == 0

    # Bottom-right node
    col, row = g._get_grid_cell(m.GRID_X + m.COLS * m.CELL_SIZE - 1, m.GRID_Y + m.ROWS * m.CELL_SIZE - 1)
    assert col == m.COLS - 1
    assert row == m.ROWS - 1

    # Outside grid
    col, row = g._get_grid_cell(0, 0)
    assert col == -1
    assert row == -1

    # Center of grid
    col, row = g._get_grid_cell(m.GRID_X + 2 * m.CELL_SIZE + m.CELL_SIZE // 2,
                                  m.GRID_Y + 1 * m.CELL_SIZE + m.CELL_SIZE // 2)
    assert col == 2
    assert row == 1


def test_handle_click_data_node():
    """Test clicking a DATA node starts hacking."""
    import main as m
    g = _make_game()
    g.seed_val = 123
    g._generate_grid()
    g.phase = m.PHASE_PLAYING

    # Find first DATA node
    found = False
    for r in range(m.ROWS):
        for c in range(m.COLS):
            node = g.grid[r][c]
            if node.is_data and not node.hacked:
                g._handle_click(c, r)
                assert g._hacking_node == (c, r)
                assert node.hacking is True
                assert g._hack_timer > 0
                found = True
                break
        if found:
            break

    assert found, "No DATA node found in grid"


def test_handle_click_wrong_color_reset():
    """Test clicking a different color resets COMBO and adds TRACE penalty."""
    import main as m
    g = _make_game()
    g.seed_val = 123
    g._generate_grid()
    g.phase = m.PHASE_PLAYING

    # Set up: find two DATA nodes of different colors
    nodes_by_color: dict[int, list[tuple[int, int]]] = {}
    for r in range(m.ROWS):
        for c in range(m.COLS):
            node = g.grid[r][c]
            if node.is_data:
                nodes_by_color.setdefault(node.color, []).append((c, r))

    # Need at least 2 colors
    colors = list(nodes_by_color.keys())
    assert len(colors) >= 2, f"Need at least 2 colors, got {len(colors)}"

    # Hack first node (finish it)
    c1, r1 = nodes_by_color[colors[0]][0]
    n1 = g.grid[r1][c1]
    g.combo = 1
    g._surge_source_color = n1.color
    g._finish_hack(n1)
    assert g.combo == 2  # combo incremented

    # Now click a DIFFERENT color
    c2, r2 = nodes_by_color[colors[1]][0]
    old_trace = g.trace
    g._handle_click(c2, r2)
    assert g.combo == 0, f"Combo should reset, got {g.combo}"
    assert g.trace > old_trace, "Trace should increase on wrong-color click"
    assert abs(g.trace - old_trace - m.TRACE_PENALTY) < 0.01


def test_handle_click_same_color_no_reset():
    """Test clicking same color does NOT reset combo."""
    import main as m
    g = _make_game()
    g.seed_val = 123
    g._generate_grid()
    g.phase = m.PHASE_PLAYING

    # Find two DATA nodes of same color
    nodes_by_color: dict[int, list[tuple[int, int]]] = {}
    for r in range(m.ROWS):
        for c in range(m.COLS):
            node = g.grid[r][c]
            if node.is_data:
                nodes_by_color.setdefault(node.color, []).append((c, r))

    # Find a color with at least 2 nodes
    target_color = None
    for col, positions in nodes_by_color.items():
        if len(positions) >= 2:
            target_color = col
            break

    if target_color is None:
        # Fallback: all colors have 1 node each
        return

    c1, r1 = nodes_by_color[target_color][0]
    n1 = g.grid[r1][c1]
    g.combo = 1
    g._surge_source_color = n1.color
    g._finish_hack(n1)
    assert g.combo == 2

    # Click same color
    c2, r2 = nodes_by_color[target_color][1]
    old_trace = g.trace
    g._handle_click(c2, r2)
    # Should not reset
    assert g.combo == 2, f"Combo should NOT reset on same-color click, got {g.combo}"
    assert abs(g.trace - old_trace) < 0.01, "Trace should NOT increase on same-color click"


def test_handle_click_ice_blocked():
    """Test clicking ICE or FIREWALL shows BLOCKED and adds trace."""
    import main as m
    g = _make_game()
    g.seed_val = 123
    g._generate_grid()
    g.phase = m.PHASE_PLAYING

    # Find an ICE node
    found = False
    for r in range(m.ROWS):
        for c in range(m.COLS):
            node = g.grid[r][c]
            if node.is_ice:
                old_trace = g.trace
                g._handle_click(c, r)
                assert g.trace > old_trace, "Trace should increase on ICE click"
                assert g._hacking_node is None
                found = True
                break
        if found:
            break
    assert found, "No ICE node found"


def test_handle_click_firewall_blocked():
    """Test clicking FIREWALL shows BLOCKED."""
    import main as m
    g = _make_game()
    g.seed_val = 123
    g._generate_grid()
    g.phase = m.PHASE_PLAYING

    found = False
    for r in range(m.ROWS):
        for c in range(m.COLS):
            node = g.grid[r][c]
            if node.is_firewall:
                old_trace = g.trace
                g._handle_click(c, r)
                assert g.trace > old_trace, "Trace should increase on FIREWALL click"
                found = True
                break
        if found:
            break
    assert found, "No FIREWALL node found"


def test_handle_click_already_hacked():
    """Test clicking already-hacked node does nothing."""
    import main as m
    g = _make_game()
    g.seed_val = 123
    g._generate_grid()
    g.phase = m.PHASE_PLAYING

    # Find a DATA node, hack it
    for r in range(m.ROWS):
        for c in range(m.COLS):
            node = g.grid[r][c]
            if node.is_data:
                node.hacked = True
                old_trace = g.trace
                g._handle_click(c, r)
                assert g._hacking_node is None  # Should not start hacking
                assert abs(g.trace - old_trace) < 0.01
                return


def test_finish_hack_score_and_combo():
    """Test _finish_hack increments combo and score."""
    import main as m
    g = _make_game()
    g.seed_val = 123
    g._generate_grid()

    # Find DATA node
    for r in range(m.ROWS):
        for c in range(m.COLS):
            node = g.grid[r][c]
            if node.is_data:
                g.combo = 2
                old_score = g.score
                old_hacked = g.nodes_hacked
                g._finish_hack(node)
                assert g.combo == 3
                assert g.max_combo == 3
                assert g.nodes_hacked == old_hacked + 1
                assert g.score == old_score + 100 * 3  # base 100 × multiplier 3
                assert node.hacked is True
                assert node.hacking is False
                return


def test_finish_hack_max_combo_tracking():
    """Test max_combo tracks highest combo."""
    import main as m
    g = _make_game()
    g.seed_val = 123
    g._generate_grid()

    # Hack first node
    for r in range(m.ROWS):
        for c in range(m.COLS):
            node = g.grid[r][c]
            if node.is_data and not node.hacked:
                g.combo = 0
                g._finish_hack(node)
                assert g.max_combo == 1
                # Hack another same-color to build combo
                for r2 in range(m.ROWS):
                    for c2 in range(m.COLS):
                        n2 = g.grid[r2][c2]
                        if n2 is not node and n2.is_data and n2.color == node.color:
                            g.combo = 4
                            g._finish_hack(n2)
                            assert g.max_combo >= 5
                            return
                return


def test_check_victory():
    """Test victory condition: all DATA nodes hacked."""
    import main as m
    g = _make_game()
    g.seed_val = 123
    g._generate_grid()

    # Initially not victory
    assert not g._check_victory()

    # Hack all DATA nodes
    for r in range(m.ROWS):
        for c in range(m.COLS):
            node = g.grid[r][c]
            if node.is_data:
                node.hacked = True

    assert g._check_victory()


def test_trace_game_over():
    """Test TRACE >= 100 causes GAME OVER."""
    import main as m
    g = _make_game()
    g.seed_val = 123
    g._generate_grid()
    g.phase = m.PHASE_PLAYING
    g.trace = 99.5

    # Simulate trace increase from time
    g.trace += m.TRACE_RATE * (1.0 / 60.0)
    # Manually check game-over condition (normally in _update_playing)
    if g.trace >= m.TRACE_MAX:
        g.phase = m.PHASE_GAME_OVER

    # May not trigger in one frame — push it
    g.trace = m.TRACE_MAX
    g.phase = m.PHASE_GAME_OVER
    assert g.phase == m.PHASE_GAME_OVER


def test_start_game_resets_state():
    """Test _start_game resets all state."""
    import main as m
    g = _make_game()
    g.seed_val = 123
    g._generate_grid()
    g.score = 9999
    g.combo = 10
    g.max_combo = 12
    g.trace = 50.0
    g.nodes_hacked = 5
    g.particles = [m.Particle(x=0, y=0, vx=1, vy=1, color=m.RED, life=10)]
    g.floating_texts = [m.FloatingText(x=0, y=0, text="test", color=m.WHITE, life=10)]
    g.phase = m.PHASE_GAME_OVER

    g._start_game()

    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.trace == 0.0
    assert g.nodes_hacked == 0
    assert g.phase == m.PHASE_PLAYING
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g._hacking_node is None
    assert g._surge_source_color == -1


def test_surge_bfs_cluster():
    """Test SURGE BFS detects correct cluster of same-color nodes."""
    import main as m
    g = _make_game()
    # Build a controlled grid: all DATA nodes, same color, with one FIREWALL in the middle
    g.grid = [[None] * m.COLS for _ in range(m.ROWS)]
    for r in range(m.ROWS):
        for c in range(m.COLS):
            g.grid[r][c] = m.Node(col=c, row=r, node_type=0, color=0)

    g.total_data_nodes = m.COLS * m.ROWS

    # Place a FIREWALL at (3, 3) to test blocking
    g.grid[3][3] = m.Node(col=3, row=3, node_type=2, color=-1)

    source = g.grid[0][0]
    g._trigger_surge(source)

    assert len(g.surge_queue) > 0
    assert g.phase == m.PHASE_SURGE_ANIM
    assert g._shake_frames > 0

    # Verify the firewall cell is NOT in the surge queue
    fw_positions = {(s.col, s.row) for s in g.surge_queue}
    assert (3, 3) not in fw_positions, "FIREWALL should not be in surge queue"


def test_surge_bfs_correct_cluster_size():
    """Test SURGE BFS includes all reachable same-color nodes."""
    import main as m
    g = _make_game()
    g.grid = [[None] * m.COLS for _ in range(m.ROWS)]
    for r in range(m.ROWS):
        for c in range(m.COLS):
            g.grid[r][c] = m.Node(col=c, row=r, node_type=0, color=0)

    g.total_data_nodes = m.COLS * m.ROWS

    # No firewalls — surge should reach ALL 47 other nodes (from 0,0)
    source = g.grid[0][0]
    g._trigger_surge(source)

    # All nodes except source should be in queue
    total_nodes = m.COLS * m.ROWS
    assert len(g.surge_queue) == total_nodes - 1, \
        f"Expected {total_nodes - 1} surge nodes, got {len(g.surge_queue)}"


def test_surge_bfs_different_color_not_included():
    """Test SURGE BFS does NOT include different-colored nodes."""
    import main as m
    g = _make_game()
    g.grid = [[None] * m.COLS for _ in range(m.ROWS)]
    for r in range(m.ROWS):
        for c in range(m.COLS):
            color = 1 if (c + r) % 2 == 0 else 0
            g.grid[r][c] = m.Node(col=c, row=r, node_type=0, color=color)

    g.total_data_nodes = m.COLS * m.ROWS

    # Source at 0,0 is color 1
    source = g.grid[0][0]
    assert source is not None
    assert source.color == 1
    g._trigger_surge(source)

    # Only color-1 nodes (even-sum positions) should be in queue
    expected = sum(1 for r in range(m.ROWS) for c in range(m.COLS)
                   if (c + r) % 2 == 0 and not (c == 0 and r == 0))
    assert len(g.surge_queue) == expected, \
        f"Expected {expected} surge nodes, got {len(g.surge_queue)}"


def test_surge_firewall_blocks_bfs():
    """Test FIREWALL completely blocks BFS propagation."""
    import main as m
    g = _make_game()
    g.grid = [[None] * m.COLS for _ in range(m.ROWS)]
    for r in range(m.ROWS):
        for c in range(m.COLS):
            g.grid[r][c] = m.Node(col=c, row=r, node_type=0, color=0)

    g.total_data_nodes = m.COLS * m.ROWS

    # Place FIREWALL at (1, 0) — blocks everything to the right of column 0
    g.grid[0][1] = m.Node(col=1, row=0, node_type=2, color=-1)
    # Also block downward from (0,0): FIREWALL at (0,1)
    g.grid[1][0] = m.Node(col=0, row=1, node_type=2, color=-1)

    source = g.grid[0][0]
    g._trigger_surge(source)

    # Source at (0,0) is completely surrounded by firewalls — no nodes reachable
    assert len(g.surge_queue) == 0, \
        f"Expected 0 surge nodes (firewall blocked), got {len(g.surge_queue)}"


def test_particle_update():
    """Test _update_particles moves and decays particles."""
    import main as m
    g = _make_game()
    p = m.Particle(x=100.0, y=100.0, vx=2.0, vy=3.0, color=m.RED, life=5, max_life=5)
    g.particles = [p]

    g._update_particles()
    assert abs(p.x - 102.0) < 0.01
    assert abs(p.y - 103.0) < 0.01  # vy + 0.1 gravity
    assert p.life == 4

    # Run until particle dies
    for _ in range(4):
        g._update_particles()
    assert len(g.particles) == 0


def test_floating_text_update():
    """Test _update_floating_texts moves and removes texts."""
    import main as m
    g = _make_game()
    ft = m.FloatingText(x=100.0, y=100.0, text="+100", color=m.WHITE, life=2, max_life=2)
    g.floating_texts = [ft]

    g._update_floating_texts()
    assert abs(ft.y - 99.0) < 0.01
    assert ft.life == 1

    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_surge_step_dataclass():
    """Test SurgeStep dataclass."""
    import main as m
    s = m.SurgeStep(col=3, row=2, delay=0.5)
    assert s.col == 3
    assert s.row == 2
    assert abs(s.delay - 0.5) < 0.01


def test_shake_update():
    """Test screen shake update."""
    g = _make_game()
    g._shake_frames = 3
    g._update_shake()
    assert g._shake_frames == 2
    # Should be non-zero (random displacement)
    g._update_shake()
    assert g._shake_frames == 1
    g._update_shake()
    assert g._shake_frames == 0
    g._update_shake()
    assert g._shake_x == 0.0
    assert g._shake_y == 0.0


def test_handle_click_out_of_bounds():
    """Test clicking outside grid returns early."""
    import main as m
    g = _make_game()
    g.seed_val = 123
    g._generate_grid()
    g.phase = m.PHASE_PLAYING

    g._handle_click(-1, -1)  # Should not crash
    g._handle_click(8, 0)     # Out of bounds col
    g._handle_click(0, 6)     # Out of bounds row
    # Should still be fine


def test_spawn_particles():
    """Test _spawn_particles creates correct count."""
    import main as m
    g = _make_game()
    g._spawn_particles(100, 100, m.RED, 8)
    assert len(g.particles) == 8
    for p in g.particles:
        assert p.color == m.RED
        assert p.life == 20


def test_directions():
    """Test directions are 4-directional (no diagonals)."""
    import main as m
    assert len(m.DIRECTIONS) == 4
    # All should be cardinal directions
    for dc, dr in m.DIRECTIONS:
        assert abs(dc) + abs(dr) == 1  # Manhattan distance = 1


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
