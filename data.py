class Data(object):
    def __init__(self, lineNum, location, symbol, mnemonic, operand, objectCode, format) -> None:
        self.lineNum = lineNum
        self.location = location
        self.symbol = symbol
        self.mnemonic = mnemonic
        self.operand = operand
        # FIXME: 檢查 objectCode 只能是 "" 或是 int(10 進位)
        self.objectCode = objectCode
        self.format = format

def printDataList(assembler):
    print("{:4}  {:8}  {:^30}  {:11}".format(
        "Line", "Location", "Source Statements", "Object Code"))
    for k in assembler.dataDict.keys():
        data = assembler.dataDict[k]
        if type(data.location) == int and type(data.objectCode) == int:
            print("{:4}  {:>8}  {:>6}  {:>6}  {:>14}  {:>11}".format(
            data.lineNum, ('%04X' % data.location), data.symbol, data.mnemonic, data.operand, ('%06X' % data.objectCode)))
        elif type(data.location) == int and type(data.objectCode) == str:
            print("{:4}  {:>8}  {:>6}  {:>6}  {:>14}  {:>11}".format(
            data.lineNum, ('%04X' % data.location), data.symbol, data.mnemonic, data.operand, data.objectCode))
        elif data.mnemonic == "BASE":
            print("{:4}  {:>8}  {:>6}  {:>6}  {:>14}  {:>11}".format(
            data.lineNum, data.location, data.symbol, data.mnemonic, data.operand, data.objectCode))
        else:
            print("{:4}  {:>8}  {:>6}  {:>6}  {:>14}  {:>11}".format(
            data.lineNum, data.location, data.symbol, data.mnemonic, data.operand, data.objectCode))
    print()

def writeDataList(assembler, fileName):
    with open(fileName, "w") as f:
        f.write("{:4}  {:8}  {:^30}  {:11}".format(
            "Line", "Location", "Source Statements", "Object Code\n"))
        for k in assembler.dataDict.keys():
            data = assembler.dataDict[k]
            if type(data.location) == int and type(data.objectCode) == int:
                f.write("{:4}  {:>8}  {:>6}  {:>6}  {:>14}  {:>11}\n".format(
                data.lineNum, ('%04X' % data.location), data.symbol, data.mnemonic, data.operand, ('%06X' % data.objectCode)))
            elif type(data.location) == int and type(data.objectCode) == str:
                f.write("{:4}  {:>8}  {:>6}  {:>6}  {:>14}  {:>11}\n".format(
                data.lineNum, ('%04X' % data.location), data.symbol, data.mnemonic, data.operand, data.objectCode))
            elif data.mnemonic == "BASE":
                f.write("{:4}  {:>8}  {:>6}  {:>6}  {:>14}  {:>11}\n".format(
                data.lineNum, data.location, data.symbol, data.mnemonic, data.operand, data.objectCode))
            else:
                f.write("{:4}  {:>8}  {:>6}  {:>6}  {:>14}  {:>11}\n".format(
                data.lineNum, data.location, data.symbol, data.mnemonic, data.operand, data.objectCode))
        f.write("\n")
