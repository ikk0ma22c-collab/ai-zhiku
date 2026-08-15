from langgraph.graph import StateGraph
from langgraph.constants import END
from typing import TypedDict
from langgraph.constants import START
import asyncio

# 定义图状态
class TestState(TypedDict):
    output: int
# 定义节点
def node_1(state: TestState) -> dict:
    print("node_1执行了")
    return {"output": state['output']}
def node_2(state: TestState) -> dict:
    print("node_2执行了")
    return {"output": "2"}
def node_3(state: TestState) -> dict:
    print("node_3执行了")
    return {"output": "3"}

class workflow:
    #定义路由函数
  @staticmethod
  def route_after_node(state: TestState) -> str:
    if state["output"] > 5:
        return "node_3"
    else:
        return "node_2"

  def build_graph(self):
# 定义图
    graph = StateGraph(TestState)
# 注册节点
    graph.add_node("node_1", node_1)
    graph.add_node("node_2", node_2)
    graph.add_node("node_3", node_3)
# 定义边
    graph.add_edge(START, "node_1")
    graph.add_edge("node_2", END)
    graph.add_edge("node_3", END)


#定义条件边
    graph.add_conditional_edges(
        "node_1",
        self.route_after_node,
        {
            "node_2": "node_2",
            "node_3": "node_3"
        }
    )
    return graph.compile()
# 执行图
  async def run(self, state:TestState):
    graph = self.build_graph()
    return await graph.ainvoke(state)
if __name__ == "__main__":
    asyncio.run(workflow().run({"output": 6}))
