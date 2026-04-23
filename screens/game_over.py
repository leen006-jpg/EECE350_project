"""Game-over screen — shows winner and final HP, then back to lobby."""
import pygame

WHITE  = (255, 255, 255)
YELLOW = (255, 210,   0)
GREEN  = ( 50, 200,  80)
DIM    = ( 70,  70,  90)

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
    # Render last game board as backdrop (import here to avoid circular import)
    from screens import game as game_screen
    if client.gs:
        game_screen.draw(client, [])

    # Dark overlay
    ov = pygame.Surface(client.screen.get_size(), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 170))
    client.screen.blit(ov, (0, 0))

    cx  = client.screen.get_width()  // 2
    cy  = client.screen.get_height() // 2
    box = pygame.Rect(cx - 230, cy - 160, 460, 320)
    pygame.draw.rect(client.screen, (18, 18, 38), box, border_radius=14)
    pygame.draw.rect(client.screen, GREEN, box, 3, border_radius=14)

    client._text(client.f_xl, "Game Over!", YELLOW, cx=cx, y=cy - 148)

    god       = client.go_data
    winner    = god.get("winner", "?")
    scores    = god.get("scores", {})
    usernames = god.get("usernames", client.usernames)

    if winner == "Draw":
        client._text(client.f_lg, "It's a Draw!", YELLOW, cx=cx, y=cy - 105)
    else:
        client._text(client.f_lg, f"{winner}  wins!", GREEN, cx=cx, y=cy - 105)

    for i, pid_str in enumerate(["1", "2"]):
        uname = usernames.get(pid_str, f"P{pid_str}")
        hp    = scores.get(pid_str, 0)
        col   = PALETTE[client.color_idx][1] if str(client.my_id) == pid_str else OPPONENT_COLOR
        client._text(client.f_md, f"{uname}  —  {hp} HP", col,
                     cx=cx, y=cy - 52 + i * 38)

    r_menu = pygame.Rect(cx - 80, cy + 65, 160, 42)
    mouse  = pygame.mouse.get_pos()
    client._button("Main Menu", r_menu, r_menu.collidepoint(mouse))

    for ev in events:
        if ev.type == pygame.MOUSEBUTTONDOWN and r_menu.collidepoint(ev.pos):
            client.state      = "lobby"
            client.gs         = {}
            client.go_data    = {}
            client.chat_log   = []
            client.chat_input = ""
