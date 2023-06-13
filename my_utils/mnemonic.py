class Mnemonic(object):
  opCodeDict = dict() 

  def __init__(self, mnemonic, format, opCode, operandNum) -> None:
    self.mnemonic = mnemonic
    self.format = format
    self.opCode = opCode
    self.operandNum = operandNum
  
  @classmethod
  def getOpCodeDict(cls, filename) -> dict:
    # 讀檔案
    with open(filename, 'r') as file:
      for line in file.readlines():
        data = line.split() 
        format = data[1].split('/')
        cls.opCodeDict[data[0]] = Mnemonic(data[0], format, data[2], data[3])
    return cls.opCodeDict