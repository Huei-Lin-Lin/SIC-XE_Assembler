from my_utils.assembler import Assembler
from my_utils.customException import CustomException
from my_utils.mnemonic import Mnemonic
from my_utils.data import writeDataList
from my_utils.record import writeObjectProgram
import os

def checkFile(file, fType) -> bool:
  if os.path.exists(file):
    fileType = file[-4:]
    if fileType == fType:
      return True
    else:
      print(f"{file} 發生錯誤，輸入檔案類型應為 {fType}")
      return False
  else:
    print(f"{file} 檔案不存在")
    return False

def main():
  # 讀檔案
  opCodeFile = 'opCode.txt'
  inputFile = 'testData\SICXE.asm'  
  assembler = Assembler(inputFile)
  outputFile = "output.txt"
  try:
    if checkFile(opCodeFile, '.txt') and checkFile(inputFile, '.asm'):
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