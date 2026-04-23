"""
Game screen
===========
Renders the live game board: grid, obstacles, pies, shields, snakes.
Also draws the right-side panel: HP bars, timer, legend, chat.
Handles keyboard input for movement and chat.
"""
import pygame

# ─── Rendering constants ──────────────────────────────────────────────────────
CELL      = 20
PANEL_W   = 260

GRID_LINE = (22,  22,  38)
PANEL_BG  = (18,  18,  35)
WHITE     = (255, 255, 255)
GRAY      = (120, 120, 140)
DIM       = ( 70,  70,  90)
RED       = (220,  50,  50)
GREEN     = ( 50, 205,  80)
ORANGE    = (255, 165,   0)
CYAN      = (  0, 210, 210)

# Keep in sync with customize.py
PALETTE = [
    ("Lime",     ( 50, 220,  80)),
    ("Sky",      ( 40, 140, 255)),
    ("Crimson",  (220,  50,  50)),
    ("Gold",     (220, 190,   0)),
    ("Cyan",     (  0, 210, 210)),
    ("Tangerine",(255, 130,   0)),
    ("Orchid",   (200,  80, 210)),
    ("White",    (230, 230, 230)),
]
OPPONENT_COLOR = (80, 80, 200)


def draw(client, events):
    gs = client.gs
    gw = client.gw
    gh = client.gh

    # ── Grid background ───────────────────────────────────────────────────────
    for x in range(gw):
        for y in range(gh):
            pygame.draw.rect(client.screen, GRID_LINE,
                             pygame.Rect(x * CELL, y * CELL, CELL, CELL))

    if not gs:
        client._text(client.f_md, "Connecting to game…", GRAY,
                     cx=gw * CELL // 2, y=gh * CELL // 2)
        _draw_panel(client, {})
        return

    _draw_obstacles(client, gs)
    _draw_pies(client, gs)
    _draw_shields(client, gs)
    _draw_snakes(client, gs)
    _draw_panel(client, gs)
    _handle_input(client, events)


# ─── Board elements ───────────────────────────────────────────────────────────

def _draw_obstacles(client, gs):
    for obs in gs.get("obstacles", []):
        r = pygame.Rect(obs["x"] * CELL, obs["y"] * CELL, CELL, CELL)
        pygame.draw.rect(client.screen, tuple(obs.get("color", [105, 105, 105])), r)
        pygame.draw.rect(client.screen, (190, 190, 190), r, 1)


def _draw_pies(client, gs):
    for pie in gs.get("pies", []):
        cx = pie["x"] * CELL + CELL // 2
        cy = pie["y"] * CELL + CELL // 2
        col = tuple(pie.get("color", [255, 165, 0]))
        pygame.draw.circle(client.screen, col, (cx, cy), CELL // 2 - 1)
        pygame.draw.circle(client.screen, WHITE, (cx, cy), CELL // 2 - 1, 1)


def _draw_shields(client, gs):
    """Creative feature: shield power-up items (blue glowing orbs)."""
    for sh in gs.get("shields", []):
        sx = sh["x"] * CELL + CELL // 2
        sy = sh["y"] * CELL + CELL // 2
        pygame.draw.circle(client.screen, (60, 180, 255), (sx, sy), CELL // 2 - 1)
        pygame.draw.circle(client.screen, WHITE,           (sx, sy), CELL // 2 - 1, 2)
        s = client.f_sm.render("S", True, WHITE)
        client.screen.blit(s, s.get_rect(center=(sx, sy)))


def _draw_snakes(client, gs):
    snakes = gs.get("snakes", {})
    for pid_str, sdata in snakes.items():
        is_me    = str(client.my_id) == pid_str
        base     = PALETTE[client.color_idx][1] if is_me else OPPONENT_COLOR
        head_col = tuple(min(255, c + 60) for c in base)
        dark     = tuple(max(0,   c - 50) for c in base)

        for i, seg in enumerate(sdata.get("body", [])):
            r = pygame.Rect(seg[0] * CELL + 1, seg[1] * CELL + 1, CELL - 2, CELL - 2)
            if i == 0:
                pygame.draw.rect(client.screen, head_col, r, border_radius=5)
                # Eyes
                ec = WHITE if sdata.get("alive") else RED
                pygame.draw.circle(client.screen, ec,           (r.x + 5,   r.y + 5), 3)
                pygame.draw.circle(client.screen, ec,           (r.right-5, r.y + 5), 3)
                pygame.draw.circle(client.screen, (0, 0, 0),    (r.x + 5,   r.y + 5), 2)
                pygame.draw.circle(client.screen, (0, 0, 0),    (r.right-5, r.y + 5), 2)
                # Shield glow
                if sdata.get("shielded"):
                    pygame.draw.rect(client.screen, CYAN, r, 3, border_radius=5)
            else:
                pygame.draw.rect(client.screen, dark, r, border_radius=3)


# ─── Right panel ──────────────────────────────────────────────────────────────

def _draw_panel(client, gs):
    px = client.gw * CELL
    pygame.draw.rect(client.screen, PANEL_BG, pygame.Rect(px, 0, PANEL_W, client.screen.get_height()))

    y      = 8
    snakes = gs.get("snakes", {})

    # Player cards
    for pid_str in ["1", "2"]:
        sdata    = snakes.get(pid_str, {})
        uname    = client.usernames.get(pid_str, f"P{pid_str}")
        is_me    = str(client.my_id) == pid_str
        hp       = sdata.get("health", 0)
        alive    = sdata.get("alive", True)
        shielded = sdata.get("shielded", False)
        col      = PALETTE[client.color_idx][1] if is_me else OPPONENT_COLOR

        card = pygame.Rect(px + 6, y, PANEL_W - 12, 72)
        pygame.draw.rect(client.screen, (22, 22, 45), card, border_radius=7)
        pygame.draw.rect(client.screen, col if alive else DIM, card, 2, border_radius=7)

        tag = "  YOU" if is_me else ""
        client._text(client.f_sm, f"{'>' if is_me else '  '} {uname}{tag}",
                     col, x=card.x + 10, y=card.y + 7)

        # HP bar
        bar = pygame.Rect(card.x + 8, card.y + 28, card.width - 16, 14)
        pygame.draw.rect(client.screen, (40, 0, 0), bar, border_radius=3)
        hw = int(bar.width * max(0, hp) / 100)
        bar_col = GREEN if hp > 50 else (ORANGE if hp > 25 else RED)
        if hw > 0:
            pygame.draw.rect(client.screen, bar_col,
                             pygame.Rect(bar.x, bar.y, hw, bar.height), border_radius=3)
        pygame.draw.rect(client.screen, WHITE, bar, 1, border_radius=3)
        client._text(client.f_sm, f"HP {hp}", WHITE, x=bar.x + 4, y=bar.y + 1)

        # Status
        if shielded:
            client._text(client.f_sm, "[SHIELD]", CYAN, x=card.x + 10, y=card.y + 48)
        elif not alive:
            client._text(client.f_sm, "[OUT]", RED, x=card.x + 10, y=card.y + 48)

        y += 80

    # Timer
    time_left = gs.get("time_left", 0)
    mm, ss    = divmod(time_left, 60)
    t_col     = RED if time_left < 30 else WHITE
    client._text(client.f_lg, f"{mm:02d}:{ss:02d}", t_col,
                 cx=px + PANEL_W // 2, y=y + 4)
    y += 42

    # Legend
    pygame.draw.line(client.screen, DIM, (px + 8, y), (px + PANEL_W - 8, y))
    y += 8
    client._text(client.f_sm, "Items", GRAY, x=px + 8, y=y)
    y += 18
    legend = [
        ([255, 165,   0], "+10 HP Pie"),
        ([255, 215,   0], "+25 HP Pie"),
        ([180,   0, 180], "−15 HP Pie"),
        ([105, 105, 105], "Rock  −20 HP"),
        ([139,   0,   0], "Spike −35 HP"),
        ([ 60, 180, 255], "Shield  [S]  (1-hit block)"),
    ]
    for col, lbl in legend:
        pygame.draw.circle(client.screen, tuple(col), (px + 15, y + 7), 6)
        client._text(client.f_sm, lbl, (200, 200, 220), x=px + 28, y=y)
        y += 18

    # Chat area
    y += 6
    pygame.draw.line(client.screen, DIM, (px + 8, y), (px + PANEL_W - 8, y))
    y += 6
    client._text(client.f_sm, "Chat  (Enter to open, Esc to close)", GRAY, x=px + 8, y=y)
    y += 18

    chat_area = pygame.Rect(px + 5, y, PANEL_W - 10, 120)
    pygame.draw.rect(client.screen, (12, 12, 28), chat_area, border_radius=4)
    pygame.draw.rect(client.screen, DIM, chat_area, 1, border_radius=4)

    msg_y = chat_area.y + 5
    for msg in client.chat_log[-6:]:
        s = client.f_sm.render(msg[:34], True, (200, 200, 220))
        client.screen.blit(s, (chat_area.x + 5, msg_y))
        msg_y += 18
    y += 125

    # Chat input
    ci = pygame.Rect(px + 5, y, PANEL_W - 10, 28)
    pygame.draw.rect(client.screen, (20, 20, 45), ci, border_radius=4)
    border = (90, 140, 255) if client.chat_active else DIM
    pygame.draw.rect(client.screen, border, ci, 1, border_radius=4)
    display = (client.chat_input + "|") if client.chat_active else client.chat_input
    s = client.f_sm.render(display[:40], True, WHITE)
    client.screen.blit(s, (ci.x + 5, ci.y + 6))

    # Store chat input rect position for click detection
    client._chat_ci_rect = ci


# ─── Input handling ───────────────────────────────────────────────────────────

def _handle_input(client, events):
    for ev in events:
        if ev.type == pygame.MOUSEBUTTONDOWN:
            ci = getattr(client, "_chat_ci_rect", None)
            if ci:
                client.chat_active = ci.collidepoint(ev.pos)

        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RETURN and not client.chat_active:
                client.chat_active = True
                continue
            if ev.key == pygame.K_ESCAPE:
                client.chat_active = False
                continue

            if client.chat_active:
                if ev.key == pygame.K_RETURN:
                    msg = client.chat_input.strip()
                    if msg:
                        client.net.send({"type": "chat", "message": msg})
                        client.chat_log.append(f"You: {msg}")
                        client.chat_input = ""
                    client.chat_active = False
                elif ev.key == pygame.K_BACKSPACE:
                    client.chat_input = client.chat_input[:-1]
                else:
                    if len(client.chat_input) < 60:
                        client.chat_input += ev.unicode
            else:
                # Movement — only send if not spectating
                if client.state == "game":
                    for d, k in client.keys.items():
                        if ev.key == k:
                            client.net.send({"type": "move", "direction": d})
                            break
