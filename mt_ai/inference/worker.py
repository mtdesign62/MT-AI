from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event
from typing import Callable

from .qwen import QwenEngine
from .types import RenderRequest, RenderResult


class RenderWorker:
    """Single-GPU serialized worker independent of any UI toolkit."""

    def __init__(self, engine: QwenEngine) -> None:
        self.engine = engine
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mt-ai-render")
        self.cancel_event = Event()

    def submit(
        self,
        request: RenderRequest,
        callback: Callable[[RenderResult], None] | None = None,
        error_callback: Callable[[BaseException], None] | None = None,
    ) -> Future:
        self.cancel_event.clear()

        def job() -> RenderResult:
            if self.cancel_event.is_set():
                raise RuntimeError("Render cancelled")
            return self.engine.render(request)

        future = self.executor.submit(job)
        if callback or error_callback:
            def done(f: Future) -> None:
                try:
                    result = f.result()
                except BaseException as exc:
                    if error_callback:
                        error_callback(exc)
                else:
                    if callback:
                        callback(result)
            future.add_done_callback(done)
        return future

    def cancel(self) -> None:
        self.cancel_event.set()

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
