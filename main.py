import asyncio
import os
import uuid
from typing import List

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.tools.tavily_search import TavilySearchResults  # noqa: F401
from langchain_core.messages import AnyMessage
from langchain_core.runnables import RunnableConfig
from loguru import logger

from pkg._state import PlanAndExecuteAgentState
from pkg.flow.plan_and_executor import PlanAndExecutorFlow
from pkg.tools.baidu_search import BaiduSearchTool  # noqa: F401


async def main():
    # 本地 ollama
    # base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    # model_name = os.getenv("OLLAMA_MODEL_NAME", "qwen2.5:7b")
    # llm = ChatOllama(base_url=base_url, model=model_name)

    # 远程服务：https://help.aliyun.com/zh/model-studio/developer-reference/use-bailian-in-langchain#9d2e1d497amiy
    llm = ChatTongyi(
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),  # 到阿里百炼平台获取apikey
        model="qwen-plus",
    )

    tools = [
        # TavilySearchResults(max_results=3),
        BaiduSearchTool(max_results=3),
    ]
    flow = PlanAndExecutorFlow(llm, tools=tools)
    app = flow.build_workflow()

    config = RunnableConfig(
        recursion_limit=10,
        configurable={
            "thread_id": uuid.uuid4().__str__(),
        },
    )

    start_state = PlanAndExecuteAgentState(
        input="2024年美国总统大选的结果是什么",
    )
    async for event in app.astream(start_state, config=config):
        for k, v in event.items():
            logger.info(f"🤖 [asteam:{k}] {v}")
            messages: List[AnyMessage] = v.get("messages", [])
            last_message: AnyMessage = None
            if messages:
                last_message = messages[-1]
                logger.warning(f"🤖 [asteam:{k}] [{last_message.type}] {last_message}")
            # if k != "__end__":
            #     logger.info(v)


if __name__ == "__main__":
    asyncio.run(main())
