import logging

from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import LLMContextFrame, LLMMessagesFrame, StartFrame

from .rag import retrieve_context

logger = logging.getLogger("agent-console")


class RAGProcessor(FrameProcessor):
    async def process_frame(self, frame, direction: FrameDirection):
        # Let the base class handle Start/Cancel/Pause/etc. so the processor is marked started.
        await super().process_frame(frame, direction)

        if direction == FrameDirection.DOWNSTREAM and isinstance(
            frame, (LLMContextFrame, LLMMessagesFrame)
        ):
            try:
                if isinstance(frame, LLMContextFrame):
                    messages = list(frame.context.get_messages())
                else:
                    messages = list(frame.messages)
                last_user = next(
                    (m for m in reversed(messages) if m.get("role") == "user"), None
                )
                if last_user and last_user.get("content"):
                    context = retrieve_context(str(last_user["content"]))
                    if context:
                        messages.insert(
                            0,
                            {
                                "role": "system",
                                "content": context,
                            },
                        )
                        if isinstance(frame, LLMContextFrame):
                            frame.context.set_messages(messages)
                        else:
                            frame = LLMMessagesFrame(messages=messages)
            except Exception:
                logger.exception("RAG: failed to augment context")

        await self.push_frame(frame, direction)
