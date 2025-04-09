from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from loguru import logger

from pkg._state import Act, Plan, PlanAndExecuteAgentState, Response
from pkg.agent._base import BaseNode
from pkg.prompt import PROMPTS


class Replanner(BaseNode):
    name: str = "replanner"
    llm: BaseChatModel = None

    def __init__(self, llm: BaseChatModel):
        super().__init__()
        self.llm = llm

    async def __call__(
        self, state: PlanAndExecuteAgentState, config: RunnableConfig
    ) -> PlanAndExecuteAgentState:
        logger.debug(f"[{self.name}]  state: {state}")
        logger.debug(f"[{self.name}] config: {config.keys()}")

        past_steps_str = "\n".join(
            f"- 步骤“{step[0]}”的结果为：{step[1]}"
            for i, step in enumerate(state.past_steps)
        )
        human_prompt = HumanMessage(
            PROMPTS.REPLAN_PROMPT_TEMPLATE.format(
                input=state.input,  # TODO:如果没有输出的情况
                plan=[p[0] for p in state.past_steps] + state.plan,
                past_steps=past_steps_str,
            )
        )
        finished_prompt = HumanMessage(
            "你是否已经确定了答案，如果确定了请尽快告诉用户结果"
        )

        # messages = [*state.messages, human_prompt]
        messages = [human_prompt, finished_prompt]
        logger.debug(f"[{self.name}] messages: {messages}")

        structured_response = await self.llm.with_structured_output(
            Act,
            # method="json_schema",
            include_raw=True,
        ).ainvoke(messages)
        logger.debug(f"[{self.name}] structured response: {structured_response}")

        if structured_response.get("parsed"):
            act: Act = structured_response["parsed"]
            ai_response: AIMessage = structured_response.get("raw")
            if ai_response:
                logger.debug(f"[{self.name}] 🤖 {ai_response.content}")
        else:
            # 解析失败
            raw_reponse: AIMessage = structured_response.get("raw", None)
            if raw_reponse:
                pass  # TODO: 使用模型原始的输出自定义解析
            else:
                # 模型没有返回任何内容
                logger.error("[ plan step ] No structured response found.")
                act: Act = Act(action=Response(response="模型输出有问题"))
        logger.debug(f"[{self.name}] act: {act}")

        # Handle proper Act instance
        if isinstance(act.action, Response):
            state.response = act.action.response
        elif isinstance(act.action, Plan):
            state.plan = act.action.steps
        else:
            state.response = "模型输出有问题"
            # 如果模型输出不对，应该再 replan 一次
        logger.debug(f"[{self.name}] state before return: {state}")
        return state
