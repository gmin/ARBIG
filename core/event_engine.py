import queue
import threading
import json
import time

class Event:
    """
    事件对象，包含事件类型和数据内容。
    """
    def __init__(self, type: str, data: dict):
        self.type = type      # 事件类型，如 'TICK_EVENT'
        self.data = data      # 事件数据，字典结构

class EventEngine:
    """
    单线程事件引擎，负责事件的注册、推送、分发和持久化。
    """
    def __init__(self, persist_path: str = None):
        self._queue = queue.Queue()         # 事件队列
        self._handlers = dict()             # 事件类型 -> 处理函数列表
        self._active = False                # 事件循环开关
        self._persist_path = persist_path   # 持久化文件路径
        self._thread = None                 # 事件循环线程

    def register(self, event_type: str, handler):
        """
        注册事件处理函数。
        :param event_type: 事件类型字符串
        :param handler: 处理函数，参数为 Event 对象
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def unregister(self, event_type: str, handler):
        """
        注销事件处理函数。
        """
        if event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
            if not self._handlers[event_type]:
                del self._handlers[event_type]

    def put(self, event: Event):
        """
        推送事件到队列，并持久化。
        """
        self._queue.put(event)
        if self._persist_path:
            self.persist(event)

    def start(self):
        """
        启动事件循环，处理队列中的事件。
        """
        self._active = True
        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def stop(self):
        """
        停止事件循环。
        """
        self._active = False
        if self._thread:
            self._thread.join()

    def _run(self):
        """
        事件主循环。
        """
        while self._active:
            try:
                event = self._queue.get(timeout=1)
                self._process(event)
            except queue.Empty:
                continue

    def _process(self, event: Event):
        """
        分发事件到已注册的处理函数。
        """
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"[EventEngine] 处理事件 {event.type} 出错: {e}")

    def persist(self, event: Event):
        """
        持久化事件到本地文件（jsonl，每行一个事件）。
        """
        try:
            with open(self._persist_path, 'a', encoding='utf-8') as f:
                json.dump({'type': event.type, 'data': event.data}, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            print(f"[EventEngine] 持久化事件出错: {e}")

    def replay(self, file_path: str):
        """
        从本地文件回放事件，依次推送到队列。
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    obj = json.loads(line.strip())
                    event = Event(obj['type'], obj['data'])
                    self.put(event)
        except Exception as e:
            print(f"[EventEngine] 回放事件出错: {e}") 