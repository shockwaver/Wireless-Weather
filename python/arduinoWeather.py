__author__ = 'Chris'
import serial
from time import sleep
import logging
import math
#######
# Object handles requesting and parsing weather info from an Arduino
# Init with serial port (IE: /dev/ttyACM0), baud rate, and timeout
#


class Arduino(object):

    def __init__(self, port, speed, timeout):
        self.port = port
        self.speed = speed
        self.timeout = timeout
        self.serial = serial.Serial()
        self.serial.port = self.port
        self.serial.baudrate = self.speed
        self.serial.timeout = self.timeout
        self.logger = logging.getLogger(__name__)
        self.logger.info("Arduino Instantiated.")


        # Nodes
        self.node1 = {'address': '', 'uptime': '', 'temp': '', 'vin': '', 'vbat': '', 'age': '', 'error': True}
        self.node2 = {'address': '', 'uptime': '', 'temp': '', 'vin': '', 'vbat': '', 'age': '', 'error': True}
        self.node3 = {'address': '', 'uptime': '', 'temp': '', 'vin': '', 'vbat': '', 'age': '', 'error': True}
        self.lacrosse = {'stationid': '', 'temp': '', 'rh': '', 'windspeed': '', 'winddir': 0, 'rainfall': 0,
                         'dewpoint': 0, 'humidex': 0}

        # store previous value
        self.node1last = dict(self.node1)
        self.node2last = {'address': '', 'uptime': '', 'temp': '', 'vin': '', 'vbat': '', 'age': '', 'error': True}
        self.node3last = {'address': '', 'uptime': '', 'temp': '', 'vin': '', 'vbat': '', 'age': '', 'error': True}
        self.nodelast = {'address': '', 'uptime': '', 'temp': '', 'vin': '', 'vbat': '', 'age': '', 'error': True}

    def validate(self, node):
        # allow 30% difference between readings
        allowedVariance = .3
        low = 1 - allowedVariance
        high = 1 + allowedVariance

        # minimum and maximum values - anything outside these values is an error
        vMin = 0
        vMax = 1000
        tempMin = -50
        tempMax = 50
        ageMax = 700


        # check for allowed min/max range
        self.logger.debug("Checking min/maxes (temp/vin/vbat/age): "+str(node['temp']) +
                          "/"+str(node['vin'])+"/"+str(node['vbat'])+"/"+str(node['age']))
        if (node['temp'] < tempMin) or (node['temp'] > tempMax):
            self.logger.debug("Temp out of range")
            return False

        if (node['vin'] < vMin or node['vin'] > vMax or node['vbat'] < vMin or node['vbat'] > vMax):
            self.logger.debug("vBat or vIn out of range")
            return False

        if node['age'] > ageMax:
            self.logger.debug("Age out of range")
            return False

        # check for allowed variances
        self.logger.debug("validating address: " + str(node['address']))
        address = node['address']
        if (address == 1):
            self.logger.debug("Node1last")
            nodelast = dict(self.node1last)
        elif (address == 2):
            self.logger.debug("Node2last")
            nodelast = dict(self.node2last)
        elif (address == 3):
            self.logger.debug("Node3last")
            nodelast = dict(self.node3last)
        else:
            return False

        # on first run, nodelast will be empty - we will assume that it's valid.
        self.logger.debug("Nodelast: " + str(nodelast['temp']))
        if (nodelast['address'] == ''):
            self.logger.debug("First run, return true")
            if (address == 1):
                self.node1last = dict(node)
            elif (address == 2):
                self.node2last = dict(node)
            elif (address == 3):
                self.node3last = dict(node)
            return True

        oldTemp = nodelast['temp']
        oldVcc = nodelast['vin']
        oldVbat = nodelast['vbat']
        newTemp = node['temp']
        newVcc = node['vin']
        newVbat = node['vbat']

        self.logger.debug("Checking allowed variance range of: " + str(oldTemp*high)+"<"+str(newTemp)+"<"+str(oldTemp*low))
        if (newTemp < oldTemp*low or newTemp > oldTemp*high):
            self.logger.debug("Temp failure: " + str(oldTemp*high)+"<"+str(newTemp)+"<"+str(oldTemp*low))
            return False

        if (newVbat < oldVbat*low or newVbat > oldVbat*high):
            self.logger.debug("vbat failure: " + str(oldVbat*high)+"<"+str(newVbat)+"<"+str(oldVbat*low))
            return False

        if (newVcc < oldVcc*low or newVcc > oldVcc*high):
            self.logger.debug("vcc failure: " + str(oldVcc*high)+"<"+str(newVcc)+"<"+str(oldVcc*low))
            return False

        self.logger.debug("Variance ranges passed")
        # all conditions passed - update nodelast and return true
        if (address == 1):
            self.node1last = dict(node)
        elif (address == 2):
            self.node2last = dict(node)
        elif (address == 3):
            self.node3last = dict(node)

        self.logger.debug("All tests passed!")
        return True

    def open(self):
        if not self.serial.isOpen():
            self.logger.debug("Opening serial connection")
            self.serial.open()

            # when opening a connection, arduino returns garbage first
            # flush it, and ignore the output
            self.serial.write(b'|')
            self.serial.readline()
            self.serial.flushInput()
            self.logger.debug("Opened")

    def isOpen(self):
        return self.serial.isOpen()

    def close(self):
        if self.serial.isOpen():
            self.serial.close()

    def writeSerial(self, value):
        # make sure port is open
        if not self.isOpen():
            self.logger.debug("Port closed")
            self.open()

        #flush buffer
        self.serial.write(b'|')
        self.serial.readline()

        sleep(0.1)
        self.serial.flushInput()

        self.logger.debug("Writing value: " + value)
        self.serial.write(bytearray(value,'utf-8'))
        self.serial.write(b'|')

        result = self.serial.readline()
        self.logger.debug("Result: \n\t" + result)
        self.close()
        return result

    def calcDewPoint(self, RH, temp):
        dewpoint = math.pow((RH/100.0), 0.125)
        self.logger.debug("Dewpoint step 1: " + str(dewpoint))
        dewpoint = dewpoint * (112+0.9*temp) + (0.1 * temp) - 112
        self.logger.debug("Dewpoint step 2: " + str(dewpoint))
        return round(dewpoint)

    def calcHumidex(self, dewpoint, temp):
        dewK = dewpoint + 273.15
        exponent = 5417.7530 * (1/273.16 - 1/dewK)
        humidex = temp + 0.5555 * (6.11 * math.pow(math.e, exponent) - 10)
        return round(humidex,1)

    def readValue(self, node):
        if (node == "node1"):
            result = self.writeSerial("node1")

            self.logger.info("Node 1 Received.")

            try:
                result.strip('\n\r')
                resultList = result.split(',')
                self.node1['address'] = int(resultList[0])
                self.node1['uptime'] = int(resultList[1])
                if resultList[2] == "ovf":
                        # temp probe error
                    self.node1['temp'] = -100
                else:
                    self.node1['temp'] = float(resultList[2])
                self.node1['vin'] = int(resultList[3])
                self.node1['vbat'] = int(resultList[4])
                self.node1['age'] = int(resultList[5])

                if self.validate(self.node1) is False:
                    self.logger.error("Node 1 out of range - data old or invalid")
                    self.logger.error("Value:\n" + str(self.node1))
                    self.node1['error'] = True
                else:
                    self.node1["error"] = False
                self.logger.debug("Node1: \n" + str(self.node1) + "\n\n")
            except:
                self.node1["error"] = True
                self.logger.error("Invalid Response Received")
                self.logger.error("Response: \n" + result)
                # send | and try again
                self.logger.error("Trying again")
                self.writeSerial(b'|')
                self.readValue("node1")

        elif (node == "node2"):
            result = self.writeSerial("node2")

            self.logger.info("Node 2 Received.")

            try:
                result.strip('\n\r')
                resultList = result.split(',')
                self.node2['address'] = int(resultList[0])
                self.node2['uptime'] = int(resultList[1])
                if resultList[2] == "ovf":
                    # temp probe error
                    self.node2['temp'] = -100
                else:
                    self.node2['temp'] = float(resultList[2])
                self.node2['vin'] = int(resultList[3])
                self.node2['vbat'] = int(resultList[4])/2
                self.node2['age'] = int(resultList[5])

                if self.validate(self.node2) is False:
                    self.logger.error("Node 2 out of range - data old or invalid")
                    self.logger.error("Value:\n" + str(self.node2))
                    self.node2['error'] = True
                else:
                    self.node2["error"] = False
                self.logger.debug("node2: \n" + str(self.node2) + "\n\n")
            except:
                self.node2["error"] = True
                self.logger.error("Invalid Response Received")
                self.logger.error("Response: \n" + result)
                # send | and try again
                self.logger.error("Trying again")
                self.writeSerial(b'|')
                self.readValue("node2")

        elif (node == "node3"):
            result = self.writeSerial("node3")

            self.logger.info("Node 3 Received.")

            try:
                result.strip('\n\r')
                resultList = result.split(',')
                self.node3['address'] = int(resultList[0])
                self.node3['uptime'] = int(resultList[1])
                if resultList[2] == "ovf":
                    # temp probe error
                    self.node3['temp'] = -100
                else:
                    self.node3['temp'] = float(resultList[2])
                self.node3['vin'] = int(resultList[3])
                self.node3['vbat'] = int(resultList[4])
                self.node3['age'] = int(resultList[5])

                if self.validate(self.node3) is False:
                    self.logger.error("Node 3 out of range - data old or invalid")
                    self.logger.error("Value:\n" + str(self.node3))
                    self.node3['error'] = True
                else:
                    self.node3["error"] = False
                self.logger.debug("node3: \n" + str(self.node3) + "\n\n")
            except:
                self.node3["error"] = True
                self.logger.error("Invalid Response Received")
                self.logger.error("Response: \n" + result)
                # send | and try again
                self.logger.error("Trying again")
                self.writeSerial(b'|')
                self.readValue("node3")

        elif (node == "lacrosse"):
            result = self.writeSerial("lacrosse")

            self.logger.info("LaCrosse Received.")
            try:
                result.strip('\n\r')
                resultList = result.split(',')
                self.lacrosse["stationid"] = int(resultList[0])
                self.lacrosse["temp"] = float(resultList[1])/10.0
                self.lacrosse["rh"] = int(resultList[2])
                self.lacrosse["windspeed"] = float(resultList[3])/10.0
                self.lacrosse["winddir"] = int(resultList[4])
                self.lacrosse["rainfall"] = int(resultList[5])
                self.logger.debug("calculating dewpoint")
                self.lacrosse["dewpoint"] = self.calcDewPoint(self.lacrosse["rh"], self.lacrosse["temp"])
                self.logger.debug("calculating humidex")

                # only calculate humidex is RH is above 30%
                self.lacrosse["humidex"] = self.calcHumidex(self.lacrosse["dewpoint"], self.lacrosse["temp"])
                self.logger.debug("lacrosse: \n" + str(self.lacrosse) + "\n\n")
            except:
                self.logger.error("Invalid Response Received")
                self.logger.error("Response: \n" + result)
                # send | and try again
                self.logger.error("Trying again")
                self.writeSerial(b'|')
                self.readValue("lacrosse")

    def updateAll(self):
        self.logger.debug("Updating all nodes")

        self.readValue("node1")
        sleep(0.1)
        self.readValue("node2")
        sleep(0.1)
        self.readValue("node3")
        sleep(0.1)
        self.readValue("lacrosse")

    def printCurrent(self):
        self.writeSerial('|')
        print(self.writeSerial('current'))
        print(self.serial.readlines())


class Pressure(object):

    def __init__(self, port, speed, timeout):
        self.port = port
        self.speed = speed
        self.timeout = timeout
        self.serial = serial.Serial()
        self.serial.port = self.port
        self.serial.baudrate = self.speed
        self.serial.timeout = self.timeout
        self.logger = logging.getLogger(__name__)
        self.logger.info("Pressure Instantiated.")

        self.pressure = ''

    def open(self):
        if not self.serial.isOpen():
            self.logger.debug("Opening serial connection")
            self.serial.open()
            self.logger.debug("Opened")

    def close(self):
        if self.serial.isOpen():
            self.serial.close()

    def writeSerial(self, value):
        # make sure port is open
        if not self.serial.isOpen():
            self.logger.debug("Port closed")
            self.open()

        self.serial.flushInput()

        self.logger.debug("Writing value: " + value)
        self.serial.write(bytearray(value, 'utf-8'))

        sleep(0.1)
        self.serial.readline()

        sleep(0.1)
        result = self.serial.readline()
        self.logger.debug("Result: \n\t" + result)
        self.close()
        return result

    def getPressure(self):
        self.pressure = float(self.writeSerial("pres"))
        return self.pressure
