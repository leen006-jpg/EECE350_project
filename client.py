"""
Πthon Arena - Client Engine
============================
This file is the CORE ENGINE. You should not need to edit it.

To customise appearance:  edit files in  screens/
To add a new screen:      add            screens/myscreen.py  with draw(client, events)
To change a screen:       edit the matching file in screens/

All screen modules are loaded automatically from the screens/ folder.
"""

import socket
import threading
import json
import time
import importlib
import os
import pygame

CELL    = 20
GRID_W  = 30
GRID_H  = 30
PANEL_W = 260
WIN_W   = GRID_W * CELL + PANEL_W
WIN_H   = GRID_H * CELL

BG    = (15, 15, 25)
WHITE = (255, 255, 255)
GRAY  = (120, 120, 140)
DIM   = ( 70,  70,  90)


class NetClient:
    def __init__(self):
        self.sock  = None
        self.alive = False
        self._buf  = ""
        self._cbs  = {}

    def connect(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        self.sock.connect((host, port))
        self.sock.settimeout(None)
        self.alive = True
        threading.Thread(target=self._recv, daemon=True).start()

    def send(self, data):
        if self.sock and self.alive:
            try:
                self.sock.sendall((json.dumps(data) + "\n").encode())
            except Exception:
                self.alive = False

    def on(self, msg_type, cb):
        self._cbs[msg_type] = cb

    def _recv(self):
        while self.alive:
            try:
                chunk = self.sock.recv(8192).decode()
                if not chunk:
                    self.alive = False
                    break
                self._buf += chunk
                while "\n" in self._buf:
                    line, self._buf = self._buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    cb = self._cbs.get(msg.get("type"))
                    if cb:
                        cb(msg)
            except Exception:
                self.alive = False
                break


class PithonArena:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Πthon Arena")
        self.clock  = pygame.time.Clock()

        self.f_xl = pygame.font.SysFont("Arial", 32, bold=True)
        self.f_lg = pygame.font.SysFont("Arial", 24, bold=True)
        self.f_md = pygame.font.SysFont("Arial", 19)
        self.f_sm = pygame.font.SysFont("Arial", 15)

        self.state = "connect"

        self.inp_host   = "127.0.0.1"
        self.inp_port   = "5000"
        self.inp_user   = ""
        self.active_inp = "host"
        self.err_msg    = ""
        self.err_timer  = 0.0

        self.lobby_players    = []
        self.game_active      = False
        self.incoming_chal    = ""   # username of player challenging us
        self.challenge_target = ""   # username we are challenging
        self.is_challenger    = False  # True if WE sent the challenge

        # Snake customisation — edit screens/customize.py to change the palette
        self.color_idx = 0
        self.keys = {
            "up":    pygame.K_UP,
            "down":  pygame.K_DOWN,
            "left":  pygame.K_LEFT,
            "right": pygame.K_RIGHT,
        }
        self.rebinding = None

        self.my_id     = 1
        self.gs        = {}
        self.usernames = {}
        self.gw        = GRID_W
        self.gh        = GRID_H

        self.chat_log    = []
        self.chat_input  = ""
        self.chat_active = False
        self.go_data     = {}

        self.net = NetClient()
        self._register_callbacks()
        self._screens = {}
        self._load_screens()

    def _load_screens(self):
        screens_dir = os.path.join(os.path.dirname(__file__), "screens")
        for fname in sorted(os.listdir(screens_dir)):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            name   = fname[:-3]
            module = importlib.import_module(f"screens.{name}")
            if hasattr(module, "draw"):
                self._screens[name] = module.draw
                print(f"[Client] Loaded screen: {name}")

    def _register_callbacks(self):
        n = self.net
        n.on("username_ok",        self._cb_username_ok)
        n.on("username_taken",     lambda _: self._set_err("Username already taken!"))
        n.on("lobby_update",       lambda m: setattr(self, "lobby_players",
                                       [p for p in m.get("players",[]) if p != self.inp_user]))
        n.on("server_status",      lambda m: setattr(self, "game_active", m.get("game_active", False)))
        n.on("challenged",         lambda m: setattr(self, "incoming_chal", m.get("from","")))
        n.on("challenge_declined", lambda m: (self._set_err(f"{m.get('by','?')} declined."),
                                              setattr(self, "state", "lobby")))
        n.on("game_start",         self._cb_game_start)
        n.on("game_state",         self._cb_game_state)
        n.on("game_over",          self._cb_game_over)
        n.on("watch_ok",           lambda _: None)
        n.on("chat",               self._cb_chat)
        n.on("error",              lambda m: self._set_err(m.get("message","Error")))

    def _cb_username_ok(self, msg):
        self.inp_user = msg["username"]
        self.state    = "lobby"

    def _cb_game_start(self, msg):
        self.my_id     = msg.get("player_id", 1)
        self.usernames = msg.get("usernames", {})
        self.gw        = msg.get("grid_width",  GRID_W)
        self.gh        = msg.get("grid_height", GRID_H)
        self.go_data   = {}
        self.chat_log  = []
        self.state     = "game"

    def _cb_game_state(self, msg):
        self.gs        = msg
        self.usernames = msg.get("usernames", self.usernames)

    def _cb_game_over(self, msg):
        self.go_data = msg
        self.state   = "game_over"

    def _cb_chat(self, msg):
        self.chat_log.append(f"{msg.get('from','?')}: {msg.get('message','')}")
        if len(self.chat_log) > 30:
            self.chat_log = self.chat_log[-30:]

    # ── Shared helpers (called by screen modules as client.xxx) ────────────────

    def _set_err(self, msg):
        self.err_msg   = msg
        self.err_timer = time.time()

    def _text(self, font, text, color, cx=None, x=None, y=0):
        surf = font.render(text, True, color)
        r    = surf.get_rect()
        r.x  = x if x is not None else (cx - r.width // 2)
        r.y  = y
        self.screen.blit(surf, r)
        return r

    def _button(self, text, rect, hover=False,
                col_normal=(55,80,170), col_hover=(80,110,220)):
        col = col_hover if hover else col_normal
        pygame.draw.rect(self.screen, col,           rect, border_radius=7)
        pygame.draw.rect(self.screen, (120,150,255), rect, 2, border_radius=7)
        surf = self.f_md.render(text, True, WHITE)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def _input_box(self, rect, text, active, label=""):
        if label:
            s = self.f_sm.render(label, True, GRAY)
            self.screen.blit(s, (rect.x, rect.y - 20))
        pygame.draw.rect(self.screen, (25,25,50), rect)
        border = (90,140,255) if active else (55,55,80)
        pygame.draw.rect(self.screen, border, rect, 2)
        surf = self.f_md.render(text + ("|" if active else ""), True, WHITE)
        self.screen.blit(surf, (rect.x + 8, rect.y + 6))

    def _handle_text_input(self, events, active, current, max_len=64):
        if not active:
            return current
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_BACKSPACE:
                    current = current[:-1]
                elif ev.key not in (pygame.K_RETURN, pygame.K_TAB, pygame.K_ESCAPE):
                    if len(current) < max_len:
                        current += ev.unicode
        return current

    def _error_label(self, y):
        if self.err_msg and (time.time() - self.err_timer < 5):
            self._text(self.f_sm, self.err_msg, (255,80,80), cx=WIN_W//2, y=y)
        elif time.time() - self.err_timer >= 5:
            self.err_msg = ""

    def _title_banner(self, subtitle=""):
        self._text(self.f_xl, "Πthon Arena", (80,220,100), cx=WIN_W//2, y=40)
        if subtitle:
            self._text(self.f_md, subtitle, GRAY, cx=WIN_W//2, y=82)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        running = True
        while running:
            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    running = False
            self.screen.fill(BG)
            draw_fn = self._screens.get(self.state)
            if draw_fn:
                draw_fn(self, events)
            else:
                self._text(self.f_md, f"Unknown state: '{self.state}'",
                           (255,80,80), cx=WIN_W//2, y=WIN_H//2)
            pygame.display.flip()
            self.clock.tick(30)
        pygame.quit()


if __name__ == "__main__":
    PithonArena().run()
