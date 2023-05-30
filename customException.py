hasError = False
class CustomException(BaseException):
  pass

def error(msg, assembler=None):
  hasError = True
  if assembler == None:
    print(f'\n{msg}')
  else:
    print(f"\n在 {assembler.inputFile} 的第 {assembler.curLineNum} 行 {assembler.curLine} 發生錯誤\n錯誤原因：{msg}")
  