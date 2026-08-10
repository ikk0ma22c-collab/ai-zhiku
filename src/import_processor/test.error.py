class import_error(Exception):
  def __init__( self, message: str, cause: Exception=None):
    self.message = message
    self.cause = cause

class AgeError(import_error):
    pass
class mynode:

  def process(self):
    age = -1
    if age < 0:
      raise AgeError("年龄错误")

  def run(self):
    try:
      self.process()
    except AgeError as e:
      print("内层捕获错误：", e)
      raise import_error("节点执行失败", cause=e)
try:
  node = mynode()
  node.run()
except import_error as e:
  print("外层捕获错误：", e)
  print("错误原因：", e.cause)