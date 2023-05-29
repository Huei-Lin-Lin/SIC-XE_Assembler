from data import *
from customException import *
from record import *
from mnemonic import *

class Assembler:
  def __init__(self, inputFile) -> None:
    self.inputFile = inputFile
    self.curLineNum = None
    self.curLine = None
    self.curLocation = None  # 10 進位
    self.PC = None  # 10 EOF進位
    self.base = None  # 10 進位
    self.symbolTable = { "A" : 0, "X" : 1, "L" : 2, "B" : 3, "S" : 4, "T" : 5, "F" : 6, "PC" : 8, "SW" : 9}  # symbol : location(int 10 進位)
    self.dataDict = {}
    self.hasStart = False  # 判斷是否有 START
    self.hasEnd = False  # 判斷是否有 END
    self.recordLineNum = 0  # 紀錄 Object Program 的行數 
    self.recordDict = {} # 檢查 record
    self.curRecordLength = 0 # 紀錄目前 Object Program 的長度
    self.startAddress = None
    self.endAddress = None
    self.baseAddressingDict = {"symbol": None, "forwardList" : []}

  
  def strToHex(self, num, errMessage) -> int:
    try:
      return int(num, 16)
    except:
      error(errMessage, self)

  
  def charToHex(self, char, errMessage) -> str:
    try:
      return hex(ord(char)).replace("0x", "")
    except:
      error(errMessage, self)

  def checkRecordLength(self, format) -> bool:
    tempLength = format + self.curRecordLength
    if tempLength <= 30 :
      self.curRecordLength = tempLength
      return True
    else:
      self.recordLineNum += 1
      self.curRecordLength = format
      return False
  
  def saveTextRecord(self, length, objectCode):
    if self.recordLineNum in self.recordDict:
      self.recordDict[self.recordLineNum].append(Text("T", self.curLocation, length, objectCode))
    else:
      self.recordDict[self.recordLineNum] = [Text("T", self.curLocation, length, objectCode)]

  # 回填位址
  def reallocation(self, location, length, value):
    self.recordLineNum += 1
    # 要回填的位址  要回填甚麼
    self.recordDict[self.recordLineNum] = [Text("T*", location, length, value)]
    self.recordLineNum += 1
    self.curRecordLength = 0

  def execute(self, filename, opCodeDict) -> None:
    with open(filename, 'r') as file:
      for lineNum, line in enumerate(file.readlines()):
        self.curLineNum = lineNum + 1
        self.curLine = line.replace("\n", "")
        tempString = line
        dataList = []
        if '.' in line:  # 如果有註解，就只擷取 非註解字串
          tempString = line[:line.index('.')]
        dataList = tempString.split()
        if(dataList == []):
          # FIXME 將註解資料存起來
          continue
        if self.checkDirective(dataList):  # 檢查是否有虛指令
          continue
        if self.hasStart:
          if self.checkInstruction(dataList, opCodeDict):  # 檢查指令
            continue
          else:
            error("mnemonic error", self)
        else:
          error("此程式碼沒有 START", self)
    if self.hasEnd == False:
      error("此程式碼沒有 END", self)
    # 檢查未定義的 symbol 
    for key in self.symbolTable.keys():
      if type(self.symbolTable[key]) == dict and self.symbolTable[key]['location'] == "*":
        error(f"{key} 此 symbol 未定義")

  # 檢查是否有重複的 symbol 或是跟 Mnemonic 撞名
  def storeSymbol(self, symbol, opCodeDict):
    if len(symbol) > 6:
      error("symbol 長度最多是 6", self)
    elif symbol in self.symbolTable.keys():
      if type(self.symbolTable[symbol]) == int:
        error(f"{symbol} 重複定義 symbol", self)
      else:
        if self.symbolTable[symbol]["location"] == "*":
          self.symbolTable[symbol]["location"] = self.curLocation
          # 如果此 symbol 是 BASE 的話要回填位址
          if self.baseAddressingDict["symbol"] == symbol:
            self.base = self.curLocation
            if self.baseAddressingDict["forwardList"] != []:
              for location in self.baseAddressingDict["forwardList"]:
                displacement = self.computeDisp(self.curLocation, pc)
                self.dataDict[location].objectCode += displacement["disp"]
          # 回填位址
          for location in self.symbolTable[symbol]["forwardList"]:
            xbpe = 0b0000
            if type(location) == list:
              xbpe += 0b1000
              location = location[0]
            if self.dataDict[location].format == 4:
              value = self.curLocation
            else:  # 如果是 Format 3 
              pc = self.dataDict[location].location + self.dataDict[location].format
              displacement = self.computeDisp(self.curLocation, pc) # 計算位移
              if displacement["type"] == "PC":
                xbpe += 0b0010
              else:
                xbpe += 0b0100
              value = xbpe * int('1000', 16) + displacement["disp"]
            self.dataDict[location].objectCode += value
            length = int(len(hex(value).replace("0x", ""))/2)
            self.reallocation(location+1, length, value)
          return 0
        else:
          error(f"{symbol} 重複定義 symbol", self)
    elif symbol in opCodeDict.keys():
      error(f"{symbol} 不可與 Mnemonic 撞名", self)
    elif symbol == "BASE":
      error("不可與 BASE 撞名", self)
    else:
      self.symbolTable[symbol] = self.curLocation
      return -1
    
  # 取得 symbol value
  # , isBASE: bool
  def getSymbolLocation(self, symbol, isIndexAddressing:bool, isBASE=False) -> int:
    if symbol in self.symbolTable.keys():
      if type(self.symbolTable[symbol]) == int:
        return self.symbolTable[symbol]
      else:
        if self.symbolTable[symbol]["location"] == "*":
          if isBASE == False:
            if isIndexAddressing:
              self.symbolTable[symbol]["forwardList"].append([self.curLocation, "X"])
            else:
              self.symbolTable[symbol]["forwardList"].append(self.curLocation)
          return 0
        else:
          return self.symbolTable[symbol]["location"]
    else:
      if symbol in Mnemonic.opCodeDict.keys():
        error(f"{symbol} 不可與 Mnemonic 撞名", self)
      elif symbol == "BASE":
        error("不可與 BASE 撞名", self)
      if isBASE == False:
        if isIndexAddressing:
          self.symbolTable[symbol] = {"forwardList": [[self.curLocation, "X"]], "location" : "*"}
        else:
          self.symbolTable[symbol] = {"forwardList": [self.curLocation], "location" : "*"}
      return 0
    
  # 計算位移量
  def computeDisp(self, symbolLocation, pc) -> list:
    disp = symbolLocation - pc
    if disp <= 2047 and -2048 <= disp:  # 做 PC-relative
      if disp < 0 :
        disp = int('1000',16) + disp
      return {"type" : "PC", "disp" : disp}
    else:
      if self.base != None:  # 做 base-relative
        disp = symbolLocation - self.base
        if disp <= 4095 and 0 <= disp: 
          return {"type" : "BASE", "disp" : disp}
        else:
          error(f"位移 {disp} 超過設定範圍 0 ~ 4095", self)
      else:
        if self.baseAddressingDict["forwardList"] == []:
          self.baseAddressingDict["forwardList"] = [self.curLocation]
        else:
          self.baseAddressingDict["forwardList"].append(self.curLocation)
        return {"type" : "BASE", "disp" : 0}

  def checkInstruction(self, dataList, opCodeDict) -> bool:
    registerList = ["A", "X", "L", "B", "S", "T", "F", "PC", "SW"]
    symbol = ""
    mnemonic = ""
    operand = ""
    objectCode = ""
    format = ""
    hasMnemonic = False
    for i in range(len(dataList)):
      if dataList[i] in opCodeDict.keys(): # 如果是 opCode
        mnemonic = dataList[i]
        hasMnemonic = True
        operand = ''.join(dataList[i+1:])
        operandList = ''.join(dataList[i+1:]).split(',')
        if len(operandList) > 2:
          error("太多 operand", self)
        elif len(opCodeDict[mnemonic].format) == 1:
          if opCodeDict[mnemonic].format[0] == "1":  # Format 1
            if len(operandList) != 0:
              error("Format 1 Instruction 不用寫 operand", self)
            else:
              format = 1
              self.PC += format
              objectCode = int(opCodeDict[mnemonic].opCode, 16)  # 計算 object Code
              break  
          elif opCodeDict[mnemonic].format[0] == "2":  # Format 2
            objectCode = opCodeDict[mnemonic].opCode
            for i in range(len(operandList)):
              if operandList[i] not in registerList:
                error("Format 2 的 operand 不是 register name", self)
              else:
                symbolLocation = self.getSymbolLocation(operandList[i], False)
                objectCode += str(symbolLocation) 
            if len(operandList) == 1:
              objectCode += "0"  # 計算 object Code
            format = 2
            self.PC += format
            objectCode = int(objectCode, 16)
            break
          else:
            error(f"沒有 Format {opCodeDict[mnemonic].format[0]}", self)
        else:  # Format 3
          objectCode = int(opCodeDict[mnemonic].opCode, 16) * int('10000', 16)  # 目前是 int
          format = 3
          if self.PC == None:
            self.PC = self.curLocation + format
          else:
            self.PC += format
          if mnemonic == "RSUB":  # 檢查 RSUB
            if i < len(dataList) - 1:
              error("RSUB 不用有 operand", self)
            nixbpe = 0b110000
            objectCode += nixbpe * int('1000', 16)
            break
          if len(operandList) == 2:  # 如果 len(operandList) == 2  
            if operandList[1] == "X":  # index addressing
              symbolLocation = self.getSymbolLocation(operandList[0], True)  # Format 3
              if symbolLocation == 0:
                nixbpe = 0b110000
                objectCode += nixbpe * int('1000', 16)
                break
              displacement = self.computeDisp(symbolLocation, self.PC)
              if displacement["type"] == "PC":
                nixbpe = 0b111010
              else: 
                nixbpe = 0b111100
              objectCode += nixbpe * int('1000', 16) + displacement["disp"]
              break
            else:  # 檢查 operandList[1] 是不是 X
              error("index addressing 的 operand2 要是 X", self)
          else:  # len(operandList) == 1
            if "@" in operandList[0]:  # "@" indirect addressing
              if operandList[0][0] == "@":
                tempOperand = operandList[0][1:]
                if tempOperand.isdigit():
                  error("@ 後要接 symbol", self)
                else:
                  symbolLocation = self.getSymbolLocation(tempOperand, False)
                  if symbolLocation == 0:
                    nixbpe = 0b100000
                    objectCode += nixbpe * int('1000', 16)
                    break
                  displacement = self.computeDisp(symbolLocation, self.PC)
                  if displacement["type"] == "PC":
                    nixbpe = 0b100010
                  else: 
                    nixbpe = 0b100100
                  objectCode += nixbpe * int('1000', 16) + displacement["disp"]
                break
              else:
                error("格式錯誤，'@' 要在 operand 最前面", self)
            elif "#" in operandList[0]:  # "#" immediate addressing
              if operandList[0][0] == "#":
                tempOperand = operandList[0][1:] 
                if tempOperand.isdigit():  # "#" 接的是 數字
                  nixbpe = 0b010000
                  objectCode += nixbpe * int('1000', 16) + int(tempOperand)
                else:  # "#" 接的是 symbol
                  symbolLocation = self.getSymbolLocation(tempOperand, False)
                  if symbolLocation == 0:
                    nixbpe = 0b010000
                    objectCode += nixbpe * int('1000', 16)
                    break
                  displacement = self.computeDisp(symbolLocation, self.PC)
                  if displacement["type"] == "PC":
                    nixbpe = 0b010010
                  else:
                    nixbpe = 0b010100
                  objectCode += nixbpe * int('1000', 16) + displacement["disp"]
                break
              else:
                error("格式錯誤，'#' 要在 operand 最前面", self)
            else: # relative addressing
              tempOperand = operandList[0]
              symbolLocation = self.getSymbolLocation(tempOperand, False)
              if symbolLocation == 0:
                nixbpe = 0b110000
                objectCode += nixbpe * int('1000', 16)
                break
              displacement = self.computeDisp(symbolLocation, self.PC)
              if displacement["type"] == "PC":
                nixbpe = 0b110010
              else:
                nixbpe = 0b110100
              objectCode += nixbpe * int('1000', 16) + displacement["disp"]
              break 
      elif "+" in dataList[i] and dataList[i][1:] in opCodeDict.keys():  # 4 format
        format = 4
        self.PC += format
        mnemonic = dataList[i]
        operand = ''.join(dataList[i+1:])
        operandList = ''.join(dataList[i+1:]).split(',')
        if len (operandList) == 1:
          opCode = mnemonic[1:]
          hasMnemonic = True
          objectCode = int(opCodeDict[opCode].opCode, 16) * int('1000000', 16)
          nixbpe = 0b0
          tempOperand = operandList[0]
          if operandList[0][0] == "#":
            tempOperand = operandList[0][1:]
            nixbpe = 0b010001
            objectCode += nixbpe * int('100000', 16) + int(tempOperand)
          else:  # "#" 接的是 symbol
            nixbpe = 0b110001
            symbolLocation = self.getSymbolLocation(tempOperand, False)
            objectCode += nixbpe * int('100000', 16)
            if symbolLocation == 0:
              break
            else:
              objectCode += symbolLocation
              break
        else:
          error("只能有一個 operand", self) # FIXME
      else: 
        symbol = dataList[i]
        self.storeSymbol(dataList[i], opCodeDict)  # 存入 self.symbolTable
    if hasMnemonic:
      self.dataDict[self.curLocation] = Data(self.curLineNum, self.curLocation, symbol, mnemonic, operand, objectCode, format)
      self.checkRecordLength(format)
      self.saveTextRecord(format, objectCode)
      self.curLocation = self.PC
      return True
    else:
      return False
  
  def checkDirective(self, dataList) -> bool:
    directiveList = {
      "START" : self.startDirective,
      "END"   : self.endDirective,
      "BYTE"  : self.byteDirective,
      "WORD"  : self.wordDirective,
      "RESB"  : self.resbDirective,
      "RESW"  : self.reswDirective,
      "BASE"  : self.baseDirective,
      # "NOBASE" : nobaseDirective,
      # "LTORG" : ltorgDirective,
      # "EQU" : equDirective,
    }
    for data in dataList:
      if data in directiveList.keys():
        if data != "START" and self.hasStart == False:
          error("程式碼沒有 START", self)
          return False
        else:
          directiveList[data](dataList) # 執行 directive 相對應的程式
          return True
    return False
  
  def startDirective(self, dataList):
    if dataList[0] == "START":
      error("沒有 Program Name\n", self)
    elif dataList[-1] == "START":
      error("沒有 Starting Addressing\n", self)
    elif len(dataList) != 3 and dataList[1] != "START":
      error("此行格式有誤", self)
    else:
      self.hasStart = True
      value = self.strToHex(dataList[2], "Starting Addressing 不是 16 進位")
      self.startAddress = value
      self.curLocation = value
      self.dataDict["START"] = Data(self.curLineNum, "", dataList[0], dataList[1], dataList[2], "", 0)
      self.storeSymbol(dataList[1], Mnemonic.opCodeDict)
      self.recordDict[self.recordLineNum] = [Head("H", dataList[0], self.curLocation)]
      self.recordLineNum += 1
      self.curRecordLength = 0
  

  def endDirective(self, dataList):
    if dataList[0] != "END" or len(dataList) != 2:
      error("END 格式錯誤", self)
    else:
      if dataList[1] in self.symbolTable.keys():
        self.hasEnd = True
        self.endAddress = self.curLocation
        symbolLocation = self.getSymbolLocation(dataList[1], False)
        self.curLocation = symbolLocation  # 改 self.curLocation 
        self.dataDict["END"] = Data(self.curLineNum, "", "", dataList[0], dataList[1], "", 0)
        self.recordLineNum += 1
        self.recordDict[self.recordLineNum] = [End("E", self.curLocation)]
        self.curRecordLength = 0
      else:
        error(f"{dataList[-1]} not in symbol table", self)

  def byteDirective(self, dataList):
    if dataList[0] == "BYTE":
      error("沒有定義 BYTE 的 symbol", self)
    elif len(dataList) < 3:
      error("沒有輸入 BYTE 的值", self)
    elif dataList[1] != "BYTE":
      error("BYTE 格式有誤", self)
    else:
      objectCode = None
      size = 0
      if dataList[2][0] == "X":
        if dataList[2][1] == "'" and dataList[2][-1] == "'":
          tempValue = dataList[2][2:-1]
          objectCode = self.strToHex(tempValue, "BYTE X 後要接 16 進位的數字")
          if objectCode > int('100', 16):
            error("超過 1 BYTE", self)
          size = 1
          self.PC += size 
        else:
          error("X 後沒有 ' 將數字包起來", self)
      elif dataList[2][0] == "C":
        if dataList[2][1] == "'" and dataList[2][-1] == "'":
          tempChar = dataList[2][2:-1]
          if len(tempChar) > 3:
            error("超過 3 BYTE", self, self)
          charList = []
          for char in tempChar:
            charList.append(self.charToHex(char, f"{self.curLine} 輸入有誤"))
          objectCode = int(''.join(charList), 16) 
          size = len(tempChar)
          self.PC += size 
        else:
          error("C 後沒有 ' 將字母包起來", self)
      else:
        error("BYTE 輸入的格式有誤，開頭要是 C 或 X", self)
      self.storeSymbol(dataList[0], Mnemonic.opCodeDict)  
      self.dataDict[self.curLocation] = Data(self.curLineNum, self.curLocation, dataList[0], dataList[1], dataList[2], objectCode, size)
      self.checkRecordLength(size)
      self.saveTextRecord(size, objectCode)
      self.curLocation = self.PC  # 改 self.curLocation
  
  def wordDirective(self, dataList):
    if dataList[0] == "WORD":
      error("沒有定義 WORD 的 symbol", self)
    elif len(dataList) < 3 :
      error("沒有輸入 WORD 的值", self)
    elif dataList[1] != "WORD":
      error("WORD 格式有誤", self)
    else:
      if dataList[2].isdigit():
        value = int(dataList[2])
        if value > int('1000000', 16):
          error("輸入的值超過 3 BYTE", self)
        objectCode = value
        size = 3
        self.PC += size 
        self.storeSymbol(dataList[0], Mnemonic.opCodeDict)  
        self.dataDict[self.curLocation] = Data(self.curLineNum, self.curLocation, dataList[0], dataList[1], dataList[2], objectCode, size) 
        self.checkRecordLength(size)
        self.saveTextRecord(size, objectCode)
        self.curLocation = self.PC  # 改 self.curLocation
      else:
        error("WORD 輸入的格式有誤，必須輸入 10 進位的值", self)
    

  def resbDirective(self, dataList):
    if dataList[0] == "RESB":
      error("沒有定義 RESB 的 symbol", self)
    elif len(dataList) < 3:
      error("沒有輸入 RESB 的值", self)
    elif dataList[1] != "RESB":
      error("RESB 格式有誤", self)
    else:
      if dataList[2].isdigit():
        size = int(dataList[2])
        if size > int('1000000', 16):
          error("輸入的值過大，超過 3 BYTE", self)
        elif (self.curLocation + size) > int('1000000', 16):
          error("Instruction 空間不足", self)
        objectCode = ""
        self.PC += size  
        self.storeSymbol(dataList[0], Mnemonic.opCodeDict)  
        self.dataDict[self.curLocation] = Data(self.curLineNum, self.curLocation, dataList[0], dataList[1], dataList[2], objectCode, size) 
        self.recordLineNum += 1
        self.curRecordLength = 0
        self.curLocation = self.PC  # 改 self.curLocation
      else:
        error("RESB 輸入的格式有誤，必須輸入 10 進位的值", self)

  def reswDirective(self, dataList):
    if dataList[0] == "RESW":
      error("沒有定義 RESW 的 symbol", self)
    elif len(dataList) < 3:
      error("沒有輸入 RESW 的值", self)
    elif dataList[1] != "RESW":
      error("RESW 格式有誤", self)
    else:
      if dataList[2].isdigit():
        size = int(dataList[2]) * 3
        if size > int('1000000', 16):
          error("輸入的值過大，超過 3 BYTE", self)
        elif (self.curLocation + size) > int('1000000', 16):
          error("Instruction 空間不足", self)
        objectCode = ""
        self.PC += size  # 改 self.PC
        self.storeSymbol(dataList[0], Mnemonic.opCodeDict)  
        self.dataDict[self.curLocation] = Data(self.curLineNum, self.curLocation, dataList[0], dataList[1], dataList[2], objectCode, size) 
        self.recordLineNum += 1
        self.curRecordLength = 0
        self.curLocation = self.PC  # 改 self.curLocation
      else:
        error("RESW 輸入的格式有誤，必須輸入 10 進位的值", self)

  def baseDirective(self, dataList):
    if dataList[0] != "BASE":
      error("不用定義 BASE 的 symbol", self)
    elif len(dataList) != 2:
      error("BASE 輸入的格式有誤", self)
    elif self.base != None:
      error("BASE 重複定義", self)
    else:
      if dataList[1] in self.symbolTable.keys():
        symbolLocation = self.getSymbolLocation(dataList[1], False, True)
        if symbolLocation == 0:
          self.baseAddressingDict["symbol"] = dataList[1]
          return
        else:
          self.base = symbolLocation 
          self.dataDict["BASE"] = Data(self.curLineNum, "", "", dataList[0], dataList[1], "", 0)
      else:
        error(f"{self.curLineNum} {self.curLine} BASE 輸入的格式有誤", self)

  