from assembler import *
from customException import *
from mnemonic import *
from token import *

def checkFile(file) -> bool:
  if os.path.exists(file):
    fileType = file[-4:]
    if fileType == '.txt':
      return True
    else:
      print(f"{file} 不是純文字檔")
      return False
  else:
    print(f"{file} 檔案不存在")
    return False

def main():
  # 讀檔案
  opCodeFile = 'opCode.txt'
  inputFile = 'testData\SICXE.txt'  
  assembler = Assembler(inputFile)
  outputFile = "output.txt"
  try:
    if checkFile(opCodeFile) and checkFile(inputFile):
      Mnemonic.getOpCodeDict(opCodeFile)
      assembler.execute(inputFile)
      if assembler.hasError:
        raise CustomException
      else:
        writeDataList(assembler, outputFile)  
        writeObjectProgram(assembler, outputFile)  
    else:
      raise CustomException
  except CustomException:
    pass
if __name__ == '__main__':
  main()