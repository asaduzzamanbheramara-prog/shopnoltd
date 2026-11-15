import asyncio

MAX_EVENTS = 2000


class TaskSink:
    """Looks like a WebSocket (send_json/receive_json) but survives client disconnects."""
    def __init__(self, user: str):
        self.user = user
        self.events: list[dict] = []
        self.watchers: set = set()
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.status = "running"          # running | done
        self.task: asyncio.Task | None = None
        self.finished_at: float | None = None

    async def send_json(self, data: dict):
        data = dict(data)
        if data.get("type") == "screenshot":      # keep only the latest image in memory
            for e in self.events:
                if e.get("type") == "screenshot":
                    e["image"] = None
        self.events.append(data)
        if len(self.events) > MAX_EVENTS:
            del self.events[: len(self.events) - MAX_EVENTS]
        for w in list(self.watchers):
            try:
                await w.send_json(data)
            except Exception:
                self.watchers.discard(w)

    async def receive_json(self):
        return await self.inbox.get()

    async def attach(self, ws):
        for e in list(self.events):
            if e.get("type") == "screenshot" and e.get("image") is None:
                continue
            await ws.send_json(e)
        self.watchers.add(ws)

    def detach(self, ws):
        self.watchers.discard(ws)
