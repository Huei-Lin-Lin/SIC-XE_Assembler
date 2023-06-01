class Record:
  def __init__(self, type) -> None:
    self.type = type


class Head(Record):
  def __init__(self, type, programName, startAddress) -> None:
    super().__init__(type)
    self.programName = programName
    self.startAddress = startAddress


class Text(Record):
  def __init__(self, type, location, length, objectCode) -> None:
    super().__init__(type)
    self.location = location
    self.length = length
    self.objectCode = objectCode

class End(Record):
  def __init__(self, type, returnAddress) -> None:
    super().__init__(type)
    self.returnAddress = returnAddress
    
def writeObjectProgram(assembler, fileName):
  with open(fileName, "a") as f:
    f.write("Object Program (One Pass assembler)\n")
    for record in assembler.recordDict:
      recordList = assembler.recordDict[record]
      for i in range(len(recordList)):
        if recordList[i].type == "H":
          totalLength = assembler.endAddress - assembler.startAddress 
          f.write("{:1} {:<6} {:06X} {:06X}".format(recordList[i].type, recordList[i].programName, recordList[i].startAddress, totalLength))
          break
        elif recordList[i].type == "E":
          f.write("{:1} {:06X}".format(recordList[i].type, recordList[i].returnAddress))
          break
        elif recordList[i].type == "T*":
          f.write("{:1} {:06X} {:02X} {:X} ".format("T", recordList[i].location, recordList[i].length, recordList[i].objectCode))
        else:
          size = recordList[i].length * 2
          if i == 0:
            recordLength = recordList[-1].location + recordList[-1].length - recordList[0].location
            f.write("{:1} {:06X} {:02X} {} ".format(recordList[i].type, recordList[i].location, int(recordLength),  ('%X' % recordList[i].objectCode).zfill(size)))
          else:
            f.write("{} ".format(('%X' % recordList[i].objectCode).zfill(size)))
      f.write("\n")
