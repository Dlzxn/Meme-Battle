"""E2E test: full 2-player game flow via HTTP + WebSocket."""
import asyncio
import json
import httpx
import websockets

BASE = "http://localhost:8000/api"
WS_BASE = "ws://localhost:8000"

async def register_login(username, password):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE}/auth/register", json={"username": username, "password": password})
        if r.status_code not in (200, 201, 400):
            print(f"Register {username}: unexpected {r.status_code} {r.text}")
        r = await c.post(f"{BASE}/auth/login", json={"username": username, "password": password})
        assert r.status_code == 200, f"Login failed: {r.text}"
        return r.json()["access_token"]

async def create_room(token):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE}/rooms", json={
            "mode": "no_czar", "timer_play": 60, "timer_vote": 30,
            "cards_count": 5, "penalty_count": 1, "is_public": False,
            "category": "all", "nickname": "Host"
        }, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code in (200, 201), f"Create room failed: {r.text}"
        d = r.json()
        return d["room_code"], d["player_id"]

async def join_room(token, code, nickname="Player2"):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE}/rooms/{code}/join", params={"nickname": nickname},
                         headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"Join failed: {r.text}"
        return r.json()["player_id"]


async def test_2player_game():
    print("\n=== 2-PLAYER GAME TEST ===")

    # Setup
    tok1 = await register_login("host_e2e", "pass123")
    tok2 = await register_login("guest_e2e", "pass123")
    code, pid1 = await create_room(tok1)
    pid2 = await join_room(tok2, code)
    print(f"Room: {code}, Host pid={pid1}, Guest pid={pid2}")

    msgs1 = []
    msgs2 = []

    async def collect(ws, bag, label):
        async for raw in ws:
            msg = json.loads(raw)
            bag.append(msg)
            t = msg.get("type", "?")
            print(f"  [{label}] {t}: {json.dumps(msg.get('payload',{}))[:120]}")

    async with (
        websockets.connect(f"{WS_BASE}/ws/{code}/{pid1}") as ws1,
        websockets.connect(f"{WS_BASE}/ws/{code}/{pid2}") as ws2,
    ):
        # Start collectors
        t1 = asyncio.create_task(collect(ws1, msgs1, "HOST"))
        t2 = asyncio.create_task(collect(ws2, msgs2, "GUEST"))

        await asyncio.sleep(0.5)  # Let room_updated arrive

        # Start game
        await ws1.send(json.dumps({"type": "start_game", "payload": {}}))
        print("-> start_game sent")

        # Wait for situation_dealt on both
        for _ in range(30):  # 3 seconds max
            await asyncio.sleep(0.1)
            host_dealt = any(m["type"] == "situation_dealt" for m in msgs1)
            guest_dealt = any(m["type"] == "situation_dealt" for m in msgs2)
            if host_dealt and guest_dealt:
                break

        assert any(m["type"] == "situation_dealt" for m in msgs1), "Host never got situation_dealt"
        assert any(m["type"] == "situation_dealt" for m in msgs2), "Guest never got situation_dealt"

        host_sit = next(m for m in msgs1 if m["type"] == "situation_dealt")
        guest_sit = next(m for m in msgs2 if m["type"] == "situation_dealt")
        host_cards = host_sit["payload"]["your_cards"]
        guest_cards = guest_sit["payload"]["your_cards"]
        round_id = host_sit["payload"]["round_id"]

        print(f"\nHost cards ({len(host_cards)}): {[c['name'] for c in host_cards]}")
        print(f"Guest cards ({len(guest_cards)}): {[c['name'] for c in guest_cards]}")
        assert len(host_cards) >= 5, f"Host has too few cards: {len(host_cards)}"
        assert len(guest_cards) >= 5, f"Guest has too few cards: {len(guest_cards)}"
        print("[OK] Both players received cards and situation")

        # Play cards
        await ws1.send(json.dumps({"type": "play_card", "payload": {"card_id": host_cards[0]["card_id"]}}))
        await ws2.send(json.dumps({"type": "play_card", "payload": {"card_id": guest_cards[0]["card_id"]}}))
        print("-> Both played cards")

        # Wait for voting_started
        for _ in range(30):
            await asyncio.sleep(0.1)
            if any(m["type"] == "voting_started" for m in msgs1):
                break

        assert any(m["type"] == "voting_started" for m in msgs1), "Voting never started"
        print("[OK] voting_started received")

        vote_msg = next(m for m in msgs1 if m["type"] == "voting_started")
        plays = vote_msg["payload"]["plays"]
        print(f"  Plays in voting: {len(plays)}")

        # Vote (host votes for guest's play, guest votes for host's play)
        host_play = next((p for p in plays if p["player_id"] != pid1), None)
        guest_play = next((p for p in plays if p["player_id"] != pid2), None)

        if host_play:
            await ws1.send(json.dumps({"type": "vote", "payload": {
                "target_player_id": host_play["player_id"],
                "play_id": host_play["play_id"]
            }}))
        if guest_play:
            await ws2.send(json.dumps({"type": "vote", "payload": {
                "target_player_id": guest_play["player_id"],
                "play_id": guest_play["play_id"]
            }}))
        print("-> Both voted")

        # Wait for round_result
        for _ in range(30):
            await asyncio.sleep(0.1)
            if any(m["type"] == "round_result" for m in msgs1):
                break

        assert any(m["type"] == "round_result" for m in msgs1), "round_result never arrived"
        result = next(m for m in msgs1 if m["type"] == "round_result")
        print(f"[OK] round_result: is_tie={result['payload'].get('is_tie')}, winners={result['payload'].get('winners')}")

        # Cancel collectors
        t1.cancel()
        t2.cancel()
        try:
            await t1
        except asyncio.CancelledError:
            pass
        try:
            await t2
        except asyncio.CancelledError:
            pass

    print("\n=== 2-PLAYER GAME TEST PASSED ===\n")


async def test_reconnect():
    print("\n=== RECONNECT TEST ===")
    tok1 = await register_login("host_rc", "pass123")
    tok2 = await register_login("guest_rc", "pass123")
    code, pid1 = await create_room(tok1)
    pid2 = await join_room(tok2, code)
    print(f"Room: {code}")

    # Connect both, start game
    msgs1 = []
    msgs2 = []
    reconnect_msgs = []

    async def drain(ws, bag, label, stop_event):
        try:
            while not stop_event.is_set():
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.2)
                    msg = json.loads(raw)
                    bag.append(msg)
                    print(f"  [{label}] {msg['type']}")
                except asyncio.TimeoutError:
                    pass
        except Exception:
            pass

    stop = asyncio.Event()
    async with (
        websockets.connect(f"{WS_BASE}/ws/{code}/{pid1}") as ws1,
        websockets.connect(f"{WS_BASE}/ws/{code}/{pid2}") as ws2,
    ):
        t1 = asyncio.create_task(drain(ws1, msgs1, "HOST", stop))
        t2 = asyncio.create_task(drain(ws2, msgs2, "GUEST", stop))
        await asyncio.sleep(0.3)
        await ws1.send(json.dumps({"type": "start_game", "payload": {}}))

        # Wait for situation_dealt
        for _ in range(40):
            await asyncio.sleep(0.1)
            if any(m["type"] == "situation_dealt" for m in msgs1):
                break

        assert any(m["type"] == "situation_dealt" for m in msgs1), "situation_dealt not received before disconnect"
        print("[OK] situation_dealt received on original connection")

        stop.set()
        t1.cancel()
        t2.cancel()

    # Simulate host reconnecting (game page loads, new WS)
    print("-> Host reconnecting (simulating GamePage mount)...")
    await asyncio.sleep(0.5)

    async with websockets.connect(f"{WS_BASE}/ws/{code}/{pid1}") as ws_reconnect:
        stop2 = asyncio.Event()
        t = asyncio.create_task(drain(ws_reconnect, reconnect_msgs, "RECONNECT", stop2))

        for _ in range(30):
            await asyncio.sleep(0.1)
            if any(m["type"] == "situation_dealt" for m in reconnect_msgs):
                break

        stop2.set()
        t.cancel()

    assert any(m["type"] == "situation_dealt" for m in reconnect_msgs), \
        f"Reconnect didn't get situation_dealt. Got: {[m['type'] for m in reconnect_msgs]}"
    print("[OK] situation_dealt resent on reconnect")
    print("\n=== RECONNECT TEST PASSED ===\n")


async def main():
    try:
        await test_2player_game()
    except Exception as e:
        print(f"FAILED 2-player: {e}")
        import traceback; traceback.print_exc()

    try:
        await test_reconnect()
    except Exception as e:
        print(f"FAILED reconnect: {e}")
        import traceback; traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
