"""Lobby screen — see online players, send/receive challenges, watch game."""
import pygame

# ── Colours ───────────────────────────────────────────────────────────────────
ORANGE  = (255, 165,   0)
WHITE   = (255, 255, 255)
DIM     = ( 70,  70,  90)
GRAY    = (120, 120, 140)


def draw(client, events):
    cx    = client.screen.get_width()  // 2
    cy    = client.screen.get_height() // 2
    mouse = pygame.mouse.get_pos()

    client._title_banner(f"Lobby  •  {client.inp_user}")
    y = 110

    # ── Incoming challenge banner ──────────────────────────────────────────────
    if client.incoming_chal:
        bx = pygame.Rect(cx - 220, y, 440, 75)
        pygame.draw.rect(client.screen, (50, 35, 10), bx, border_radius=8)
        pygame.draw.rect(client.screen, ORANGE, bx, 2, border_radius=8)
        client._text(client.f_md,
                     f"{client.incoming_chal}  challenges you!",
                     ORANGE, cx=cx, y=y + 8)

        r_acc = pygame.Rect(cx - 115, y + 38, 105, 28)
        r_dec = pygame.Rect(cx +  10, y + 38, 105, 28)
        client._button("Accept",  r_acc, r_acc.collidepoint(mouse), (30,120,30),(40,160,40))
        client._button("Decline", r_dec, r_dec.collidepoint(mouse), (120,30,30),(160,40,40))

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if r_acc.collidepoint(ev.pos):
                    # Customise FIRST — Ready button will send accept_challenge
                    client.is_challenger = False
                    client.state         = "customize"
                elif r_dec.collidepoint(ev.pos):
                    client.net.send({"type": "decline_challenge",
                                     "from": client.incoming_chal})
                    client.incoming_chal = ""
        y += 90

    # ── Player list ───────────────────────────────────────────────────────────
    client._text(client.f_md, "Online Players", GRAY, cx=cx, y=y)
    y += 30

    if not client.lobby_players:
        client._text(client.f_sm,
                     "Waiting for other players to join…", DIM, cx=cx, y=y + 5)

    for player in client.lobby_players:
        row    = pygame.Rect(cx - 200, y, 400, 42)
        pygame.draw.rect(client.screen, (25, 25, 50), row, border_radius=6)
        pygame.draw.rect(client.screen, DIM, row, 1, border_radius=6)
        client._text(client.f_md, player, WHITE, x=row.x + 14, y=row.y + 11)

        # Only show Challenge button if no game is currently running
        if not client.game_active:
            r_chal = pygame.Rect(row.right - 115, row.y + 7, 108, 28)
            client._button("Challenge", r_chal, r_chal.collidepoint(mouse))
            for ev in events:
                if ev.type == pygame.MOUSEBUTTONDOWN and r_chal.collidepoint(ev.pos):
                    client.challenge_target = player
                    client.is_challenger    = True
                    client.state            = "customize"
        y += 50

    # ── Watch / spectate section ──────────────────────────────────────────────
    if client.game_active:
        # Friendly notice explaining why Challenge is hidden
        notice = client.f_sm.render(
            "A game is in progress — you can only watch until it ends.", True, ORANGE)
        client.screen.blit(notice, notice.get_rect(centerx=cx, y=y + 5))
        y += 30

        r_watch = pygame.Rect(cx - 90, y + 5, 180, 40)
        client._button("Watch Game", r_watch, r_watch.collidepoint(mouse),
                       (40, 60, 100), (60, 90, 150))
        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and r_watch.collidepoint(ev.pos):
                client.net.send({"type": "watch"})
                client.state = "watch"

    client._error_label(client.screen.get_height() - 30)
