from my_utils.data import Data
from my_utils.customException import CustomException
from my_utils.record import Text, Head, End, Modification
from my_utils.mnemonic import Mnemonic
import os

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
    self.recordDict = {} # 紀錄 record
    self.modificationList = []
    self.curRecordLength = 0 # 紀錄目前 Object Program 的長度
    self.startAddress = None
    self.endAddress = None
    self.baseAddressingDict = {"symbol": None, "forwardList" : []}
    self.hasError = False

  def error(self, msg, printLine=True):
    self.hasError = True
    if printLine:
      print("\n在 {:} 的第 {:>02} 行 {:} 發生錯誤\n錯誤原因 : {:}".format(self.inputFile, self.curLineNum, self.curLine, msg))
    else:
      print(f"\n{msg}")
  
  def strToHex(self, num, errMessage) -> int:
    try:
      return int(num, 16)
    except:
      self.error(errMessage)

  def charToHex(self, char, errMessage) -> str:
    try:
      return hex(ord(char)).replace("0x", "")
    except:
      self.error(errMessage)

  def checkRecordLength(self, format) -> bool:
    tempLength = format + self.curRecordLength
    if tempLength <= 30 :
      self.curRecordLength = tempLength
      return True
    else:
      self.recordLineNum += 1
      if format > 30:
        self.curRecordLength = 30
      else:
        self.curRecordLength = format
      return False
  
  def saveTextRecord(self, length, objectCode):
    if self.recordLineNum in self.recordDict:
      self.recordDict[self.recordLineNum].append(Text("T", self.curLocation, length, objectCode))
    else:
      self.recordDict[self.recordLineNum] = [Text("T", self.curLocation, length, objectCode)]

  # 回填位址
  def updateRecord(self, location, length, value):
    self.recordLineNum += 1
    # 要回填的位址  要回填甚麼
    self.recordDict[self.recordLineNum] = [Text("T*", location, length, value)]
    self.recordLineNum += 1
    self.curRecordLength = 0

  def execute(self, filename) -> None:
    with open(filename, 'r') as file:
      for lineNum, line in enumerate(file.readlines()):
        self.curLineNum = lineNum + 1
        self.curLine = line.replace("\n", "")
        tempString = self.curLine
        dataList = []
        if '.' in line:  # 如果有註解，就只擷取 非註解字串
          tempString = line[:line.index('.')]
        if tempString == "" or len(tempString) == tempString.count(" "):
          continue  # 註解跳過
        else:
          dataList = tempString.split() # 切割字串
        if self.checkDirective(dataList):  # 檢查是否有虛指令
          continue
        elif self.hasStart:
          self.checkInstruction(dataList)  # 檢查指令
        else:
          self.error("此輸入檔沒有 START")
          raise CustomException
    if self.hasEnd == False:
      self.error("此輸入檔沒有 END", False)
    # 檢查未定義的 symbol 
    for key in self.symbolTable.keys():
      if type(self.symbolTable[key]) == dict and self.symbolTable[key]['location'] == "*":
        for location in self.symbolTable[key]["forwardList"]:
          if type(location) == list:
            self.error(f"第 {self.dataDict[location[0]].lineNum} 行的 {key} label 未定義", False)
          else:
            self.error(f"第 {self.dataDict[location].lineNum} 行的 {key} label 未定義", False)

  # 檢查是否有重複的 symbol 或是跟 Mnemonic 撞名
  def storeSymbol(self, symbol):
    if len(symbol) > 6:
      self.error("symbol 超過 6 碼")
    elif symbol in Mnemonic.opCodeDict.keys():
      self.error(f"{symbol} 不可與 Mnemonic 撞名")
    elif symbol == "BASE":
      self.error("不可與 BASE 撞名")
    elif symbol not in self.symbolTable.keys():
      self.symbolTable[symbol] = self.curLocation
    else:
      if type(self.symbolTable[symbol]) == int or type(self.symbolTable[symbol]["location"]) == int:
        self.error(f"重複定義 {symbol}  symbol")
      else:
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
          self.updateRecord(location+1, length, value)

    
  # 取得 symbol value
  def getSymbolLocation(self, symbol, isIndexAddressing=False, isBASE=False):
    if symbol in self.symbolTable.keys():
      if type(self.symbolTable[symbol]) == int:
        return self.symbolTable[symbol]
      else:  # dict type
        if self.symbolTable[symbol]["location"] == "*":
          if isBASE == False:
            if isIndexAddressing:
              self.symbolTable[symbol]["forwardList"].append([self.curLocation, "X"])
            else:
              self.symbolTable[symbol]["forwardList"].append(self.curLocation)
          return "*"
        else:
          return self.symbolTable[symbol]["location"]
    else:
      if symbol in Mnemonic.opCodeDict.keys():
        self.error(f"{symbol} 不可與 Mnemonic 撞名")
      elif symbol == "BASE":
        self.error("不可與 BASE 撞名")
      else:
        if isBASE == False:
          if isIndexAddressing:
            self.symbolTable[symbol] = {"forwardList": [[self.curLocation, "X"]], "location" : "*"}
          else:
            self.symbolTable[symbol] = {"forwardList": [self.curLocation], "location" : "*"}
      return "*"
    
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
          self.error(f"位移 {disp} 超過設定範圍 0 ~ 4095")
      else:
        # if self.baseAddressingDict["forwardList"] == []:
        #   self.baseAddressingDict["forwardList"] = [self.curLocation]
        # else:
        self.baseAddressingDict["forwardList"].append(self.curLocation)
        return {"type" : "BASE", "disp" : 0}

  def checkInstruction(self, dataList) -> bool:
    registerList = ["A", "X", "L", "B", "S", "T", "F", "PC", "SW"]
    symbol = ""
    mnemonic = ""
    # operand = ""
    objectCode = ""
    format = ""
    hasMnemonic = False
    for i in range(len(dataList)):
      if dataList[i] in Mnemonic.opCodeDict.keys(): # 如果是 opCode
        mnemonic = dataList[i]
        hasMnemonic = True
        if len(dataList[i+1:]) > 1:
          for operand in dataList[i+1:]:
            if operand in Mnemonic.opCodeDict.keys():
              self.error(f"Mnemonic 不能當 operand")
              return False
          if ',' not in  dataList[i+1] and ',' not in dataList[i+2]:
            self.error("沒有用 , 隔開 operand")
            return False
        operandList = ''.join(dataList[i+1:]).split(',')
        if operandList == ['']:
          operandList = []
        if len(operandList) != int(Mnemonic.opCodeDict[mnemonic].operandNum):
          if len(operandList) == 2 and operandList[1] == "X":
            pass
          else:
            self.error(f"{mnemonic} 要有 {Mnemonic.opCodeDict[mnemonic].operandNum} 個 operand")
            return False
        if len(operandList) > 2:
          self.error("太多 operand")
          return False
        elif len(Mnemonic.opCodeDict[mnemonic].format) == 1:
          if Mnemonic.opCodeDict[mnemonic].format[0] == "1":  # Format 1
            if len(operandList) != 0:
              self.error("Format 1 Instruction 不用寫 operand")
              return False
            else:
              format = 1
              self.PC += format
              objectCode = int(Mnemonic.opCodeDict[mnemonic].opCode, 16)  # 計算 object Code
              break  
          elif Mnemonic.opCodeDict[mnemonic].format[0] == "2":  # Format 2
            objectCode = Mnemonic.opCodeDict[mnemonic].opCode
            for i in range(len(operandList)):
              if operandList[i] not in registerList:
                self.error("Format 2 的 operand 不是 register name")
                return False
              else:
                symbolLocation = self.getSymbolLocation(operandList[i])
                if symbolLocation != "*":
                  objectCode += str(symbolLocation) 
            if len(operandList) == 1:
              objectCode += "0"  # 計算 object Code
            format = 2
            self.PC += format
            objectCode = int(objectCode, 16)
            break
          else:
            self.error(f"沒有 Format {Mnemonic.opCodeDict[mnemonic].format[0]}")
            return False
        else:  # Format 3
          objectCode = int(Mnemonic.opCodeDict[mnemonic].opCode, 16) * int('10000', 16)  # 目前是 int
          format = 3
          if self.PC == None:
            self.PC = self.curLocation + format
          else:
            self.PC += format
          if Mnemonic.opCodeDict[mnemonic].operandNum == "0":
            nixbpe = 0b110000
            objectCode += nixbpe * int('1000', 16)
            break
          if operandList == ['']:
            self.error("沒有寫 operand")
            return False
          elif len(operandList) == 2:  # 如果 len(operandList) == 2 
            if "@" in operandList[0] or "#" in operandList[0]:
              self.error("指令格式有誤")
              return False
            elif operandList[1] == "X":  # index addressing
              symbolLocation = self.getSymbolLocation(operandList[0], isIndexAddressing = True)  # Format 3
              if symbolLocation == "*":
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
              self.error("index addressing 的 operand2 要是 X")
              return False
          else:  # len(operandList) == 1
            if "@" in operandList[0]:  # "@" indirect addressing
              if operandList[0][0] == "@":
                tempOperand = operandList[0][1:]
                if tempOperand.isdigit():
                  self.error("@ 後要接 symbol")
                  return False
                else:
                  symbolLocation = self.getSymbolLocation(tempOperand)
                  if symbolLocation == "*":
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
                self.error("格式錯誤，'@' 要在最前面")
                return False
            elif "#" in operandList[0]:  # "#" immediate addressing
              if operandList[0][0] == "#":
                tempOperand = operandList[0][1:] 
                if tempOperand.isdigit():  # "#" 接的是 數字
                  nixbpe = 0b010000
                  objectCode += nixbpe * int('1000', 16) + int(tempOperand)
                else:  # "#" 接的是 symbol
                  symbolLocation = self.getSymbolLocation(tempOperand)
                  if symbolLocation == "*":
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
                self.error("格式錯誤，'#' 要在最前面")
                return False
            else: # relative addressing
              tempOperand = operandList[0]
              symbolLocation = self.getSymbolLocation(tempOperand)
              if symbolLocation == "*":
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
      elif "+" in dataList[i] :  # 4 format
        if dataList[i][1:] in Mnemonic.opCodeDict.keys():
          format = 4
          self.PC += format
          mnemonic = dataList[i][1:]
          operandList = ''.join(dataList[i+1:]).split(',')
          if operandList == ['']:
            operandList = []
          if len(operandList) != int(Mnemonic.opCodeDict[mnemonic].operandNum):
            if len(operandList) == 2 and operandList[1] == "X":
              pass
            else:
              self.error(f"{mnemonic} 要有 {Mnemonic.opCodeDict[mnemonic].operandNum} 個 operand")
              return False
          if len (operandList) == 1:
            opCode = mnemonic
            hasMnemonic = True
            objectCode = int(Mnemonic.opCodeDict[opCode].opCode, 16) * int('1000000', 16)
            nixbpe = 0b0
            tempOperand = operandList[0]
            if operandList[0][0] == "#":
              tempOperand = operandList[0][1:]
              if tempOperand.isdigit():
                nixbpe = 0b010001
                objectCode += nixbpe * int('100000', 16) + int(tempOperand)
                break
              else:
                symbolLocation = self.getSymbolLocation(tempOperand)
                if symbolLocation == "*":
                  nixbpe = 0b010001
                  objectCode += nixbpe * int('100000', 16)
                  break
                displacement = self.computeDisp(symbolLocation, self.PC)
                if displacement["type"] == "PC":
                  nixbpe = 0b010011
                else:
                  nixbpe = 0b010101
                objectCode += nixbpe * int('100000', 16) + displacement["disp"]
              break
            else:  # 是 symbol
              nixbpe = 0b110001
              symbolLocation = self.getSymbolLocation(tempOperand)
              self.modificationList.append(Modification("M", self.curLocation + 1, 5))
              objectCode += nixbpe * int('100000', 16)
              if symbolLocation == "*":
                break
              else:
                objectCode += symbolLocation
                break
          else:
            self.error("只能有一個 operand") # FIXME
            return False
        else:
          self.error("+ 後面要寫 Mnemonic")
          return False
      else:  # symbol
        if i == 0:
          symbol = dataList[i]
          self.storeSymbol(dataList[i])  # 存入 self.symbolTable
        else:
          self.error("mnemonic error")
          return False
    if hasMnemonic:
      self.dataDict[self.curLocation] = Data(self.curLineNum, self.curLocation, symbol, mnemonic, ', '.join(operandList), objectCode, format)
      self.checkRecordLength(format)
      self.saveTextRecord(format, objectCode)
      self.curLocation = self.PC
      return True
    else:
      self.error("沒有 mnemonic")
      return False
  
  def checkDirective(self, dataList) -> bool:
    directiveList = ["START", "END", "BYTE", "WORD", "RESB", "RESW", "BASE"]
    for data in dataList:
      if data in directiveList:
        match data:  # 執行 directive 相對應的程式
          case "START":
            self.startDirective(dataList)
          case "END":
            self.endDirective(dataList)
          case "BYTE":
            self.byteDirective(dataList)
          case "WORD":
            self.wordDirective(dataList)
          case "RESB":
            self.resbDirective(dataList)
          case "RESW":
            self.reswDirective(dataList)
          case "BASE":
            self.baseDirective(dataList)
          case _:
            return False
        return True
    return False
  
  def startDirective(self, dataList):
    if self.hasStart:
      self.error("一份檔案中只能有一個 START")
    elif len(dataList) != 3 and dataList[1] != "START":
      if dataList[0] == "START":
        self.error("沒有 Program Name\n")
      else:
        self.error("此行 START 格式有誤")
    elif dataList[-1] == "START":
      self.error("沒有寫 Starting Addressing\n")
    else:
      if len(dataList[0]) > 6:
        self.error("Program Name 超過 6 碼")
      self.hasStart = True
      value = self.strToHex(dataList[2], "Starting Addressing 不是 16 進位")
      if value == None:
        raise CustomException
      else:
        self.startAddress = value
        self.curLocation = value
        self.dataDict["START"] = Data(self.curLineNum, "", dataList[0], dataList[1], dataList[2], "", 0)
        # self.storeSymbol(dataList[1])
        self.recordDict[self.recordLineNum] = [Head("H", dataList[0], self.curLocation)]
        self.recordLineNum += 1
        self.curRecordLength = 0
  

  def endDirective(self, dataList):
    if self.hasEnd:
      self.error("一份檔案中只能有一個 END")
    elif dataList[0] != "END" or len(dataList) != 2:
      self.error("此行 END 格式錯誤")
    else:
      self.hasEnd = True
      if dataList[1] in self.symbolTable.keys():
        self.endAddress = self.curLocation
        symbolLocation = self.getSymbolLocation(dataList[1])
        if symbolLocation == "*":
          self.error(f"{dataList[-1]} 沒有位址")
          return
        self.curLocation = symbolLocation  # 改 self.curLocation 
        self.dataDict["END"] = Data(self.curLineNum, "", "", dataList[0], dataList[1], "", 0)
        self.recordLineNum += 1
        self.recordDict[self.recordLineNum] = [End("E", self.curLocation)]
        self.curRecordLength = 0
      else:
        self.error(f"{dataList[-1]} not in symbol table")

  def byteDirective(self, dataList):
    if dataList[0] == "BYTE":
      self.error("沒有定義 BYTE 的 symbol")
    elif len(dataList) < 3:
      self.error("沒有輸入 BYTE 的值")
    elif dataList[1] != "BYTE":
      self.error("此行 BYTE 格式有誤")
    else:
      objectCode = ""
      size = 0
      tempValue = ""
      if dataList[2][0] == "X":
        if len(dataList) > 3: # 將 X   'F1' 變成 X'F1'
          tempList = dataList[:2]
          operand = self.curLine[self.curLine.index("X"):]
          if "'" in operand and operand[1] != "'":
            operand = operand[0] + operand[operand.index("'"):]
          tempList.append(operand)
          dataList = tempList
        if ' ' in dataList[2]:
          self.error(f"{dataList[2]} 中不能有空格")
          return
        elif dataList[2].count("'") == 2 and dataList[2][1] == "'" and dataList[2][-1] == "'":
          tempValue = dataList[2][2:-1]
          if tempValue == "":
            self.error(f"{dataList[2]} 裡面沒有值")
            return
          elif len(tempValue) % 2 != 0:
            self.error(f"{dataList[2]} 中的 {tempValue} 的長度要是偶數")
            return
          else:
            size = len(tempValue) // 2
            if size > 60:
              self.error("超過 60 BYTE")
              return
            else:
              objectCode = self.strToHex(tempValue, "BYTE X 後要接 16 進位的數字")
              self.PC += size 
        else:
          self.error(f"{dataList[2]} 沒有用 '' 將數字包起來")
          return
      elif dataList[2][0] == "C":
        if len(dataList) > 3:
          tempList = dataList[:2]
          operand = self.curLine[self.curLine.index("C"):]
          if "'" in operand and operand[1] != "'":
            operand = operand[0] + operand[operand.index("'"):]
          tempList.append(operand)
          dataList = tempList
        if dataList[2].count("'") == 2 and dataList[2][1] == "'" and dataList[2][-1] == "'":
          tempChar = dataList[2][2:-1]
          if tempChar == "":
            self.error(f"{dataList[2]} 沒有值")
            return
          else:
            size = len(tempChar)
            if size > 60:
              self.error("超過 60 BYTE")
              return
            else:
              charList = []
              for char in tempChar:
                charList.append(self.charToHex(char, f"{self.curLine} 輸入有誤"))
              tempValue = ''.join(charList)
              objectCode = int(tempValue, 16) 
              self.PC += size 
        else:
          self.error(f"{dataList[2]} 沒有用 '' 將數字包起來")
          return
      else:
        self.error("BYTE 輸入的格式有誤，只有 C 或 X 格式")
        return
      self.storeSymbol(dataList[0])  
      self.dataDict[self.curLocation] = Data(self.curLineNum, self.curLocation, dataList[0], dataList[1], dataList[2], objectCode, size)
      self.checkRecordLength(size)
      if size > 30 and size <= 60:
        self.saveTextRecord(30,  int(tempValue[:60], 16))
        self.recordLineNum += 1
        self.curRecordLength = size-30
        self.recordDict[self.recordLineNum] = [Text("T", self.curLocation + int('30', 16) , size - 30, int(tempValue[60:], 16))]
      else:
        self.saveTextRecord(size, objectCode)
      self.curLocation = self.PC  # 改 self.curLocation
  
  def wordDirective(self, dataList):
    if dataList[0] == "WORD":
      self.error("沒有定義 WORD 的 symbol")
    elif len(dataList) < 3 :
      self.error("沒有輸入 WORD 的值")
    elif dataList[1] != "WORD":
      self.error("WORD 格式有誤")
    else:
      if dataList[2].isdigit():
        value = int(dataList[2])
        if value > int('1000000', 16):
          self.error("輸入的值超過 3 BYTE")
        objectCode = value
        size = 3
        self.PC += size 
        self.storeSymbol(dataList[0])  
        self.dataDict[self.curLocation] = Data(self.curLineNum, self.curLocation, dataList[0], dataList[1], dataList[2], objectCode, size) 
        self.checkRecordLength(size)
        self.saveTextRecord(size, objectCode)
        self.curLocation = self.PC  # 改 self.curLocation
      else:
        self.error("WORD 輸入的格式有誤，必須輸入 10 進位的值")
    

  def resbDirective(self, dataList):
    if dataList[0] == "RESB":
      self.error("沒有定義 RESB 的 symbol")
    elif len(dataList) < 3:
      self.error("沒有輸入 RESB 的值")
    elif dataList[1] != "RESB":
      self.error("RESB 格式有誤")
    else:
      if dataList[2].isdigit():
        size = int(dataList[2])
        objectCode = ""
        self.PC += size  
        self.storeSymbol(dataList[0])  
        self.dataDict[self.curLocation] = Data(self.curLineNum, self.curLocation, dataList[0], dataList[1], dataList[2], objectCode, size) 
        self.recordLineNum += 1
        self.curRecordLength = 0
        self.curLocation = self.PC  # 改 self.curLocation
      else:
        self.error("RESB 輸入的格式有誤，必須輸入 10 進位的值")

  def reswDirective(self, dataList):
    if dataList[0] == "RESW":
      self.error("沒有定義 RESW 的 symbol")
    elif len(dataList) < 3:
      self.error("沒有輸入 RESW 的值")
    elif dataList[1] != "RESW":
      self.error("RESW 格式有誤")
    else:
      if dataList[2].isdigit():
        size = int(dataList[2]) * 3
        if size > int('1000000', 16):
          self.error("輸入的值過大，超過 3 BYTE")
        elif (self.curLocation + size) > int('1000000', 16):
          self.error("Instruction 空間不足")
        objectCode = ""
        self.PC += size  # 改 self.PC
        self.storeSymbol(dataList[0])  
        self.dataDict[self.curLocation] = Data(self.curLineNum, self.curLocation, dataList[0], dataList[1], dataList[2], objectCode, size) 
        self.recordLineNum += 1
        self.curRecordLength = 0
        self.curLocation = self.PC  # 改 self.curLocation
      else:
        self.error("RESW 輸入的格式有誤，必須輸入 10 進位的值")

  def baseDirective(self, dataList):
    if dataList[0] != "BASE":
      self.error("不用定義 BASE 的 symbol")
    elif len(dataList) != 2:
      self.error("BASE 輸入的格式有誤")
    elif self.base != None:
      self.error("BASE 重複定義")
    else:
      if dataList[1] in self.symbolTable.keys():
        symbolLocation = self.getSymbolLocation(dataList[1], isBASE = True)
        if symbolLocation == "*":
          self.baseAddressingDict["symbol"] = dataList[1]
          return
        else:
          self.base = symbolLocation 
        self.dataDict["BASE"] = Data(self.curLineNum, "", "", dataList[0], dataList[1], "", 0)
      else:
        self.error(f"沒有先載入 {dataList[1]} symbol")

  