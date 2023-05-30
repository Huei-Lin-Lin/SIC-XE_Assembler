from assembler import *
from customException import *
from mnemonic import *
from token import *


def main():
  # 讀檔案，並整理成 dict
  opCodeFile = 'opCode.txt'
  Mnemonic.getOpCodeDict(opCodeFile)
  
  # 讀檔案
  inputFile = 'SICXE.txt'
  assembler = Assembler(inputFile)
  outputFile = "output.txt"
  try:
    assembler.execute(inputFile, Mnemonic.opCodeDict)
    if hasError:
      raise CustomException
    writeDataList(assembler, outputFile)  
    writeObjectProgram(assembler, outputFile)  
  except CustomException:
    pass
if __name__ == '__main__':
  main()