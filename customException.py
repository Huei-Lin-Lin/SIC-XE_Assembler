
class CustomException(BaseException):
  pass

def error(msg, assembler=None):
  if assembler == None:
    print(msg)
  else:
    print(f"在 {assembler.inputFile} 的第 {assembler.curLineNum} 行 {assembler.curLine} 發生錯誤\n錯誤原因：{msg}")
  raise CustomException