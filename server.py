"""
Πthon Arena - Server
EECE 350 - Computing Networks
Handles all game logic, client connections, and state broadcasting.
Protocol: Newline-delimited JSON over TCP
"""

import socket
import threading
import json
import random
import time
import sys

# ─── Grid & Game Constants ────────────────────────────────────────────────────
GRID_W        = 30
GRID_H        = 30
INITIAL_HP    = 100
GAME_DURATION = 180        # seconds
PIE_COUNT     = 6
OBSTACLE_COUNT = 8
TICK_RATE     = 8          # game ticks per second

# Pie definitions: points > 0 = health gain, < 0 = poison
PIE_TYPES = [
    {"pie_type": "regular", "points":  10, "color": [255, 165,   0]},
    {"pie_type": "golden",  "points":  25, "color": [255, 215,   0]},
    {"pie_type": "poison",  "points": -15, "color": [180,   0, 180]},
]

# Obstacle definitions
OBSTACLE_TYPES = [
    {"obs_type": "rock",  "damage": 20, "color": [105, 105, 105]},
    {"obs_type": "spike", "damage": 35, "color": [139,   0,   0]},
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def send_msg(sock: socket.socket, data: dict) -> bool:
    """Send a JSON message terminated with newline. Returns False on error."""
    try:
        sock.sendall((json.dumps(data) + "\n").encode())
        return True
    except Exception:
        return False


# ─── Snake ────────────────────────────────────────────────────────────────────

class Snake:
    """Represents one player's snake."""

    def __init__(self, player_id: int, head: tuple, direction: tuple):
        self.player_id = player_id
        dx, dy = direction
        # Build 3-cell initial body
        self.body = [
            head,
            (head[0] - dx, head[1] - dy),
            (head[0] - 2 * dx, head[1] - 2 * dy),
        ]
        self.direction = direction
        self.health    = INITIAL_HP
        self.alive     = True
        self.shielded  = False   # Creative feature: shield power-up

    # ── Movement ──────────────────────────────────────────────────────────────

    def set_direction(self, new_dir: tuple):
        """Change direction, preventing 180° reversal."""
        dx, dy = new_dir
        if dx + self.direction[0] != 0 or dy + self.direction[1] != 0:
            self.direction = new_dir

    def step(self):
        """Advance the snake by one cell (does NOT grow)."""
        hx, hy = self.body[0]
        dx, dy = self.direction
        self.body.insert(0, (hx + dx, hy + dy))
        self.body.pop()

    def grow(self):
        """Append one segment at the tail."""
        self.body.append(self.body[-1])

    def head(self) -> tuple:
        return self.body[0]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "body":     self.body,
            "direction": list(self.direction),
            "health":   self.health,
            "alive":    self.alive,
            "shielded": self.shielded,
        }


# ─── Game Session ─────────────────────────────────────────────────────────────

class GameSession:
    """
    Manages one complete match between two players.
    Runs its own game-loop thread at TICK_RATE ticks/sec.
    on_end(usernames: list[str]) is called by the server after the game finishes
    so it can reset player states and refresh the lobby.
    """

    def __init__(self, p1_info: dict, p2_info: dict, on_end=None):
        # p*_info = {"socket": sock, "username": str}
        self.players = {1: p1_info, 2: p2_info}
        self.viewers: list = []
        self.lock    = threading.Lock()

        self.pies:      list = []
        self.obstacles: list = []
        self.shields:   list = []   # creative: shield items on board
        self.pending    = {1: None, 2: None}

        self.running    = False
        self.game_over  = False
        self.start_time = 0.0
        self.winner     = ""
        self._on_end    = on_end  # callback(usernames) invoked when game finishes

        # Build snakes
        p1_info["snake"] = Snake(1, (5,  GRID_H // 2),  ( 1,  0))
        p2_info["snake"] = Snake(2, (GRID_W - 6, GRID_H // 2), (-1, 0))

        self._gen_obstacles()
        self._gen_pies(PIE_COUNT)
        self._gen_shields(2)

    # ── Board generation ──────────────────────────────────────────────────────

    def _occupied(self) -> set:
        cells = set()
        for p in self.players.values():
            if "snake" in p:
                for seg in p["snake"].body:
                    cells.add(tuple(seg))
        for o in self.obstacles:
            cells.add((o["x"], o["y"]))
        for pie in self.pies:
            cells.add((pie["x"], pie["y"]))
        for sh in self.shields:
            cells.add((sh["x"], sh["y"]))
        return cells

    def _rand_cell(self) -> tuple:
        occupied = self._occupied()
        while True:
            x = random.randint(2, GRID_W - 3)
            y = random.randint(2, GRID_H - 3)
            if (x, y) not in occupied:
                return x, y

    def _gen_obstacles(self):
        for _ in range(OBSTACLE_COUNT):
            x, y = self._rand_cell()
            ot = random.choice(OBSTACLE_TYPES)
            self.obstacles.append({"x": x, "y": y, **ot})

    def _gen_pies(self, count: int):
        for _ in range(count):
            x, y = self._rand_cell()
            pt = random.choice(PIE_TYPES)
            self.pies.append({"x": x, "y": y, **pt, "id": random.randint(0, 999999)})

    def _gen_shields(self, count: int):
        for _ in range(count):
            x, y = self._rand_cell()
            self.shields.append({"x": x, "y": y, "id": random.randint(0, 999999)})

    # ── Network helpers ───────────────────────────────────────────────────────

    def broadcast(self, data: dict):
        """Send a message to all players and viewers."""
        for p in self.players.values():
            send_msg(p["socket"], data)
        for vsock in self.viewers[:]:
            if not send_msg(vsock, data):
                self.viewers.remove(vsock)

    def add_viewer(self, sock: socket.socket):
        self.viewers.append(sock)

    # ── Game state snapshot ───────────────────────────────────────────────────

    def snapshot(self) -> dict:
        elapsed   = time.time() - self.start_time if self.start_time else 0
        time_left = max(0, int(GAME_DURATION - elapsed))
        return {
            "type":      "game_state",
            "snakes":    {str(pid): p["snake"].to_dict() for pid, p in self.players.items()},
            "pies":      self.pies,
            "obstacles": self.obstacles,
            "shields":   self.shields,
            "time_left": time_left,
            "usernames": {str(pid): p["username"] for pid, p in self.players.items()},
        }

    # ── External input ────────────────────────────────────────────────────────

    def set_move(self, player_id: int, direction: str):
        dir_map = {
            "up":    ( 0, -1),
            "down":  ( 0,  1),
            "left":  (-1,  0),
            "right": ( 1,  0),
        }
        if direction in dir_map:
            with self.lock:
                self.pending[player_id] = dir_map[direction]

    # ── Game loop ─────────────────────────────────────────────────────────────

    def start(self):
        self.running    = True
        self.start_time = time.time()
        # Notify both players
        for pid, p in self.players.items():
            send_msg(p["socket"], {
                "type":       "game_start",
                "player_id":  pid,
                "usernames":  {str(k): v["username"] for k, v in self.players.items()},
                "grid_width": GRID_W,
                "grid_height": GRID_H,
            })
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        interval = 1.0 / TICK_RATE
        while self.running:
            t0 = time.time()
            self._tick()
            self.broadcast(self.snapshot())
            if self.game_over:
                self._announce_result()
                self.running = False
                break
            sleep = interval - (time.time() - t0)
            if sleep > 0:
                time.sleep(sleep)

    def _tick(self):
        with self.lock:
            s1 = self.players[1]["snake"]
            s2 = self.players[2]["snake"]

            # Apply pending direction changes
            if self.pending[1] and s1.alive:
                s1.set_direction(self.pending[1])
            if self.pending[2] and s2.alive:
                s2.set_direction(self.pending[2])
            self.pending = {1: None, 2: None}

            # Move snakes
            if s1.alive: s1.step()
            if s2.alive: s2.step()

            # Resolve collisions for each snake
            for snake, other in [(s1, s2), (s2, s1)]:
                if snake.alive:
                    self._resolve_collisions(snake, other)

            # Collect pies / shields
            for snake in [s1, s2]:
                if snake.alive:
                    self._collect_pies(snake)
                    self._collect_shields(snake)

            # Check game-over conditions
            time_up = (time.time() - self.start_time) >= GAME_DURATION
            if not s1.alive or not s2.alive or time_up:
                self.game_over = True
                h1, h2 = s1.health, s2.health
                u1 = self.players[1]["username"]
                u2 = self.players[2]["username"]
                if   h1 > h2:  self.winner = u1
                elif h2 > h1:  self.winner = u2
                else:          self.winner = "Draw"

    def _hit(self, snake: Snake, damage: int):
        """Apply damage, respecting shield."""
        if snake.shielded:
            snake.shielded = False   # shield absorbs one hit
            return
        snake.health -= damage
        if snake.health <= 0:
            snake.health = 0
            snake.alive  = False

    def _resolve_collisions(self, snake: Snake, other: Snake):
        head = snake.head()

        # Wall
        if not (0 <= head[0] < GRID_W and 0 <= head[1] < GRID_H):
            self._hit(snake, 30)
            # Clamp so the snake stays on screen visually
            hx = max(0, min(GRID_W - 1, head[0]))
            hy = max(0, min(GRID_H - 1, head[1]))
            snake.body[0] = (hx, hy)
            return

        # Obstacle
        for obs in self.obstacles:
            if head == (obs["x"], obs["y"]):
                self._hit(snake, obs["damage"])
                return

        # Own body (skip head)
        if head in snake.body[1:]:
            self._hit(snake, 15)
            return

        # Other snake's body
        if head in other.body:
            self._hit(snake, 25)

    def _collect_pies(self, snake: Snake):
        head = snake.head()
        for pie in self.pies[:]:
            if head == (pie["x"], pie["y"]):
                pts = pie["points"]
                if pts > 0:
                    snake.health = min(INITIAL_HP, snake.health + pts)
                    snake.grow()
                else:
                    snake.health = max(0, snake.health + pts)
                    if snake.health == 0:
                        snake.alive = False
                self.pies.remove(pie)
                # Respawn
                x, y = self._rand_cell()
                pt = random.choice(PIE_TYPES)
                self.pies.append({"x": x, "y": y, **pt, "id": random.randint(0, 999999)})
                break

    def _collect_shields(self, snake: Snake):
        """Creative feature: collecting a shield item grants one-hit immunity."""
        head = snake.head()
        for sh in self.shields[:]:
            if head == (sh["x"], sh["y"]):
                snake.shielded = True
                self.shields.remove(sh)
                # Respawn after a delay (spawn immediately for simplicity)
                x, y = self._rand_cell()
                self.shields.append({"x": x, "y": y, "id": random.randint(0, 999999)})
                break

    def _announce_result(self):
        scores = {
            str(pid): p["snake"].health
            for pid, p in self.players.items()
        }
        self.broadcast({
            "type":      "game_over",
            "winner":    self.winner,
            "scores":    scores,
            "usernames": {str(k): v["username"] for k, v in self.players.items()},
        })
        # Notify the server so it can reset player states and refresh the lobby
        if self._on_end:
            usernames = [p["username"] for p in self.players.values()]
            self._on_end(usernames)


# ─── Server ───────────────────────────────────────────────────────────────────

class Server:
    def __init__(self, port: int):
        self.port    = port
        self.clients: dict = {}        # username -> {"socket": sock, "state": str}
        self.c_lock  = threading.Lock()
        self.session: GameSession | None = None
        self.s_lock  = threading.Lock()

    def run(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("", self.port))
        srv.listen(20)
        print(f"[Server] Πthon Arena listening on port {self.port}")
        while True:
            conn, addr = srv.accept()
            print(f"[Server] Connection from {addr}")
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    # ── Per-client thread ─────────────────────────────────────────────────────

    def _handle(self, sock: socket.socket):
        buf      = ""
        username = None
        try:
            # ── Phase 1: authenticate username ────────────────────────────────
            while True:
                chunk = sock.recv(1024).decode()
                if not chunk:
                    return
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    msg = json.loads(line)
                    if msg.get("type") == "join":
                        name = msg.get("username", "").strip()
                        with self.c_lock:
                            if name and name not in self.clients:
                                username = name
                                self.clients[username] = {"socket": sock, "state": "lobby"}
                                send_msg(sock, {"type": "username_ok", "username": username})
                            else:
                                send_msg(sock, {"type": "username_taken"})
                if username:
                    break

            self._broadcast_lobby()

            # ── Phase 2: message loop ─────────────────────────────────────────
            while True:
                chunk = sock.recv(4096).decode()
                if not chunk:
                    break
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        self._dispatch(username, sock, json.loads(line))
                    except json.JSONDecodeError:
                        pass

        except Exception as e:
            print(f"[Server] Client error ({username}): {e}")
        finally:
            if username:
                with self.c_lock:
                    self.clients.pop(username, None)
                self._broadcast_lobby()
                print(f"[Server] {username} disconnected")
            sock.close()

    # ── Message dispatcher ────────────────────────────────────────────────────

    def _dispatch(self, username: str, sock: socket.socket, msg: dict):
        t = msg.get("type")

        # ── Challenge ─────────────────────────────────────────────────────────
        if t == "challenge":
            target = msg.get("target")
            with self.c_lock:
                available = (target in self.clients and
                             self.clients[target]["state"] == "lobby" and
                             self.clients[username]["state"] == "lobby")
                if available:
                    tsock = self.clients[target]["socket"]
                else:
                    tsock = None
            if tsock:
                send_msg(tsock, {"type": "challenged", "from": username})
            else:
                send_msg(sock, {"type": "error", "message": "Player not available."})

        # ── Accept challenge ──────────────────────────────────────────────────
        elif t == "accept_challenge":
            challenger = msg.get("from")
            p1_sock = p2_sock = None
            with self.c_lock:
                if (challenger in self.clients and
                        self.clients[challenger]["state"] == "lobby" and
                        self.clients[username]["state"] == "lobby"):
                    self.clients[challenger]["state"] = "game"
                    self.clients[username]["state"]    = "game"
                    p1_sock = self.clients[challenger]["socket"]
                    p2_sock = self.clients[username]["socket"]
            if p1_sock and p2_sock:
                with self.s_lock:
                    self.session = GameSession(
                        {"socket": p1_sock, "username": challenger},
                        {"socket": p2_sock, "username": username},
                        on_end=self._on_game_end,
                    )
                    self.session.start()
                self._broadcast_lobby()

        # ── Decline challenge ─────────────────────────────────────────────────
        elif t == "decline_challenge":
            challenger = msg.get("from")
            with self.c_lock:
                if challenger in self.clients:
                    send_msg(self.clients[challenger]["socket"],
                             {"type": "challenge_declined", "by": username})

        # ── Player move ───────────────────────────────────────────────────────
        elif t == "move":
            with self.s_lock:
                gs = self.session
            if gs and gs.running:
                for pid, p in gs.players.items():
                    if p["username"] == username:
                        gs.set_move(pid, msg.get("direction", ""))
                        break

        # ── Chat (P2P via server relay) ───────────────────────────────────────
        elif t == "chat":
            text = msg.get("message", "").strip()
            if not text:
                return
            with self.s_lock:
                gs = self.session
            relay = {"type": "chat", "from": username, "message": text}
            if gs:
                for p in gs.players.values():
                    if p["username"] != username:
                        send_msg(p["socket"], relay)
                for vsock in gs.viewers:
                    send_msg(vsock, relay)
            # Also relay to lobby members
            with self.c_lock:
                for uname, c in self.clients.items():
                    if uname != username and c["state"] == "lobby":
                        send_msg(c["socket"], relay)

        # ── Watch (spectator mode) ────────────────────────────────────────────
        elif t == "watch":
            with self.s_lock:
                gs = self.session
            if gs and gs.running:
                gs.add_viewer(sock)
                with self.c_lock:
                    if username in self.clients:
                        self.clients[username]["state"] = "watching"
                send_msg(sock, {"type": "watch_ok"})
                send_msg(sock, gs.snapshot())
            else:
                send_msg(sock, {"type": "error", "message": "No active game to watch."})

    # ── Lobby broadcast ───────────────────────────────────────────────────────

    def _broadcast_lobby(self):
        with self.c_lock:
            lobby = [u for u, c in self.clients.items() if c["state"] == "lobby"]
            msg   = {"type": "lobby_update", "players": lobby}
            for c in self.clients.values():
                if c["state"] in ("lobby", "watching"):
                    send_msg(c["socket"], msg)
            # Also inform about current game status
            with self.s_lock:
                game_active = self.session is not None and self.session.running
            status_msg = {"type": "server_status", "game_active": game_active}
            for c in self.clients.values():
                send_msg(c["socket"], status_msg)

    # ── Post-game cleanup ─────────────────────────────────────────────────────

    def _on_game_end(self, usernames: list):
        """
        Called by GameSession after the game finishes.
        Resets both players back to 'lobby' state and refreshes
        the lobby list for everyone — this is what was missing before.
        """
        print(f"[Server] Game ended. Returning {usernames} to lobby.")
        with self.c_lock:
            for uname in usernames:
                if uname in self.clients:
                    self.clients[uname]["state"] = "lobby"
            # Also reset any spectators back to lobby
            for uname, c in self.clients.items():
                if c["state"] == "watching":
                    c["state"] = "lobby"
        self._broadcast_lobby()


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python server.py <port>")
        sys.exit(1)
    Server(int(sys.argv[1])).run()
