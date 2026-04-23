"""
Customize screen
================
• Pick your snake's body colour from a palette
• Remap all 4 movement keys (click a row, press the new key)
• Click "Ready!" when done — the game starts once both players are ready
"""
import pygame

# ─── Snake colour palette  (name, RGB) ────────────────────────────────────────
# Edit this list freely to add / remove / change colours.
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

# ─── Direction display labels ─────────────────────────────────────────────────
DIR_ICONS = {"up": "↑  Up", "down": "↓  Down",
             "left": "<-  Left", "right": "->  Right"}

# ─── Colours used in this screen ─────────────────────────────────────────────
BG_CARD  = (22, 22, 45)
BORDER   = (55, 55, 85)
WHITE    = (255, 255, 255)
GRAY     = (140, 140, 160)
DIM      = ( 70,  70,  90)
YELLOW   = (255, 210,   0)
GREEN    = ( 50, 200,  80)


def draw(client, events):
    W     = client.screen.get_width()
    H     = client.screen.get_height()
    cx    = W // 2
    mouse = pygame.mouse.get_pos()

    client._title_banner("Customise Your Snake")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — COLOUR PICKER
    # ══════════════════════════════════════════════════════════════════════════
    section_header(client, cx - 200, 100, "1. Body Colour")

    swatch_w = 48
    gap      = 10
    total_sw = len(PALETTE) * (swatch_w + gap) - gap
    start_x  = cx - total_sw // 2

    for i, (name, col) in enumerate(PALETTE):
        sx = start_x + i * (swatch_w + gap)
        r  = pygame.Rect(sx, 128, swatch_w, swatch_w)

        # Draw swatch
        pygame.draw.rect(client.screen, col, r, border_radius=8)

        # Selected ring
        if i == client.color_idx:
            pygame.draw.rect(client.screen, WHITE, r, 3, border_radius=8)
            # colour name below swatch
            lbl = client.f_sm.render(name, True, WHITE)
            client.screen.blit(lbl, lbl.get_rect(centerx=r.centerx, y=r.bottom + 4))

        # Hover ring + tooltip
        elif r.collidepoint(mouse):
            pygame.draw.rect(client.screen, GRAY, r, 2, border_radius=8)
            lbl = client.f_sm.render(name, True, GRAY)
            client.screen.blit(lbl, lbl.get_rect(centerx=r.centerx, y=r.bottom + 4))

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and r.collidepoint(ev.pos):
                client.color_idx = i

    # Live snake preview  — floats up and down using a sine wave ───────────────
    import math, time
    bob   = int(math.sin(time.time() * 3) * 5)   # -5 to +5 px oscillation
    base  = PALETTE[client.color_idx][1]
    head  = tuple(min(255, c + 60) for c in base)
    dark  = tuple(max(0,   c - 50) for c in base)
    py    = 205 + bob
    for i in range(6):
        pr = pygame.Rect(cx - 65 + i * 23, py, 21, 21)
        pygame.draw.rect(client.screen, head if i == 0 else dark, pr, border_radius=5)
        if i == 0:
            pygame.draw.circle(client.screen, WHITE, (pr.x + 5,  pr.y + 5), 3)
            pygame.draw.circle(client.screen, WHITE, (pr.right-5, pr.y + 5), 3)
    preview_lbl = client.f_sm.render("preview", True, DIM)
    client.screen.blit(preview_lbl, preview_lbl.get_rect(centerx=cx, y=py + 26))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — KEY BINDINGS
    # ══════════════════════════════════════════════════════════════════════════
    section_header(client, cx - 200, 252, "2. Movement Keys   (click a row -> press new key)")

    directions = ["up", "down", "left", "right"]
    cols       = 2
    box_w, box_h = 220, 38
    x_gap, y_gap =  16,  10

    for i, d in enumerate(directions):
        col_idx = i % cols
        row_idx = i // cols
        bx = cx - (cols * box_w + (cols - 1) * x_gap) // 2 + col_idx * (box_w + x_gap)
        by = 278 + row_idx * (box_h + y_gap)
        box = pygame.Rect(bx, by, box_w, box_h)

        is_rebinding = (client.rebinding == d)

        # Background
        pygame.draw.rect(client.screen, BG_CARD, box, border_radius=6)
        border_col = YELLOW if is_rebinding else (BORDER if not box.collidepoint(mouse) else GRAY)
        pygame.draw.rect(client.screen, border_col, box, 2, border_radius=6)

        # Label
        if is_rebinding:
            label = f"{DIR_ICONS[d]}  ->  Press any key..."
            lbl_col = YELLOW
        else:
            key_name = pygame.key.name(client.keys[d]).upper()
            label    = f"{DIR_ICONS[d]}  :  {key_name}"
            lbl_col  = WHITE

        lbl_surf = client.f_sm.render(label, True, lbl_col)
        client.screen.blit(lbl_surf, (box.x + 10, box.y + 11))

        # Click to start rebinding
        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and box.collidepoint(ev.pos):
                client.rebinding = d
            if ev.type == pygame.KEYDOWN and client.rebinding == d:
                client.keys[d]   = ev.key
                client.rebinding = None

    # ══════════════════════════════════════════════════════════════════════════
    # READY BUTTON
    # ══════════════════════════════════════════════════════════════════════════
    r_ready = pygame.Rect(cx - 100, H - 110, 200, 48)
    client._button("Ready!", r_ready, r_ready.collidepoint(mouse),
                   (30, 110, 40), (40, 155, 55))

    if client.is_challenger:
        hint = f"Ready to challenge  {client.challenge_target}?"
    else:
        hint = f"Ready to accept  {client.incoming_chal}'s challenge?"
    waiting = client.f_sm.render(hint, True, DIM)
    client.screen.blit(waiting, waiting.get_rect(centerx=cx, y=H - 58))

    for ev in events:
        if ev.type == pygame.MOUSEBUTTONDOWN and r_ready.collidepoint(ev.pos):
            if client.is_challenger:
                # Send challenge now (after customising)
                client.net.send({"type": "challenge",
                                 "target": client.challenge_target})
                client.state = "awaiting"
            else:
                # Send accept now (after customising)
                client.net.send({"type": "accept_challenge",
                                 "from": client.incoming_chal})
                client.incoming_chal = ""
                # Stay on customize — game_start will move us to "game"


# ─── Helper ───────────────────────────────────────────────────────────────────

def section_header(client, x, y, text):
    """Draws a left-aligned section title with an underline."""
    surf = client.f_md.render(text, True, (180, 180, 220))
    client.screen.blit(surf, (x, y))
    pygame.draw.line(client.screen, (55, 55, 85),
                     (x, y + surf.get_height() + 2),
                     (x + surf.get_width(), y + surf.get_height() + 2), 1)
