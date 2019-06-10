from collections import defaultdict
import sqlite3
import json
import os

from quart import jsonify, make_response, Quart, render_template, request, flash, redirect, url_for
from quart import Quart
from quart_cors import cors
import asyncio
from typing import Optional

from pybtc import verify_signature
from config import *


app = Quart(__name__)
app = cors(app)
app.clients = set()


# FLO TOKEN APIs

@app.route('/api/v1.0/gettokenlist', methods=['GET'])
async def gettokenlist():
    filelist = []
    for item in os.listdir(os.path.join(dbfolder,'tokens')):
        if os.path.isfile(os.path.join(dbfolder, 'tokens', item)):
            filelist.append(item[:-3])

    return jsonify(tokens = filelist, result='ok')


@app.route('/api/v1.0/getaddressbalance', methods=['GET'])
async def getaddressbalance():
    address = request.args.get('address')
    token = request.args.get('token')

    if address is None or token is None:
        return jsonify(result='error')

    dblocation = dbfolder + '/tokens/' + str(token) + '.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
    else:
        return 'Token doesn\'t exist'
    c.execute('SELECT SUM(transferBalance) FROM activeTable WHERE address="{}"'.format(address))
    balance = c.fetchall()[0][0]
    conn.close()
    return jsonify(result='ok', token=token, address=address, balance=balance)


@app.route('/api/v1.0/gettokeninfo', methods=['GET'])
async def gettokeninfo():
    token = request.args.get('token')

    if token is None:
        return jsonify(result='error')

    dblocation = dbfolder + '/tokens/' + str(token) + '.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
    else:
        return 'Token doesn\'t exist'
    c.execute('SELECT * FROM transactionHistory WHERE id=1')
    incorporationRow = c.fetchall()[0]
    c.execute('SELECT COUNT (DISTINCT address) FROM activeTable')
    numberOf_distinctAddresses = c.fetchall()[0][0]
    conn.close()
    return jsonify(result='ok', token=token, incorporationAddress=incorporationRow[1], tokenSupply=incorporationRow[3],
                   transactionHash=incorporationRow[6], blockchainReference=incorporationRow[7],
                   activeAddress_no=numberOf_distinctAddresses)


@app.route('/api/v1.0/gettransactions', methods=['GET'])
async def gettransactions():
    token = request.args.get('token')
    senderFloAddress = request.args.get('senderFloAddress')
    destFloAddress = request.args.get('destFloAddress')

    if token is None:
        return jsonify(result='error')

    dblocation = dbfolder + '/tokens/' + str(token) + '.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
    else:
        return 'Token doesn\'t exist'

    if senderFloAddress and not destFloAddress:
        c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference FROM transactionHistory WHERE sourceFloAddress="{}" ORDER BY id DESC LIMIT 100'.format(
                senderFloAddress))
    elif not senderFloAddress and destFloAddress:
        c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference FROM transactionHistory WHERE destFloAddress="{}" ORDER BY id DESC LIMIT 100'.format(
                destFloAddress))
    elif senderFloAddress and destFloAddress:
        c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference FROM transactionHistory WHERE sourceFloAddress="{}" AND destFloAddress="{}" ORDER BY id DESC LIMIT 100'.format(
                senderFloAddress, destFloAddress))

    else:
        c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference FROM transactionHistory ORDER BY id DESC LIMIT 100')
    latestTransactions = c.fetchall()
    conn.close()
    rowarray_list = []
    for row in latestTransactions:
        d = dict(zip(row.keys(), row))  # a dict with column names as keys
        rowarray_list.append(d)
    return jsonify(result='ok', transactions=rowarray_list)


@app.route('/api/v1.0/gettokenbalances', methods=['GET'])
async def gettokenbalances():
    token = request.args.get('token')
    if token is None:
        return jsonify(result='error')

    dblocation = dbfolder + '/tokens/' + str(token) + '.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
    else:
        return 'Token doesn\'t exist'
    c.execute('SELECT address,SUM(transferBalance) FROM activeTable GROUP BY address')
    addressBalances = c.fetchall()

    returnList = []

    for address in addressBalances:
        tempdict = {}
        tempdict['address'] = address[0]
        tempdict['balance'] = address[1]
        returnList.append(tempdict)

    return jsonify(result='ok', balances=returnList)


# SMART CONTRACT APIs

@app.route('/api/v1.0/getsmartContractlist', methods=['GET'])
async def getcontractlist():
    contractName = request.args.get('contractName')
    contractAddress = request.args.get('contractAddress')

    conn = sqlite3.connect(os.path.join(dbfolder,'system.db'))
    c = conn.cursor()

    contractList = []

    if contractName and contractAddress:
        c.execute('select * from activecontracts where contractName="{}" and contractAddress="{}"'.format(contractName, contractAddress))
        allcontractsDetailList = c.fetchall()
        for idx,contract in enumerate(allcontractsDetailList):
            contractDict = {}
            contractDict['contractName'] = contract[1]
            contractDict['contractAddress'] = contract[2]
            contractDict['status'] = contract[3]
            contractDict['transactionHash'] = contract[4]
            contractDict['incorporationDate'] = contract[5]
            if contract[6]:
                contractDict['expiryDate'] = contract[6]
            if contract[7]:
                contractDict['closeDate'] = contract[7]

            contractList.append(contractDict)

    elif contractName and not contractAddress:
        c.execute('select * from activecontracts where contractName="{}"'.format(contractName))
        allcontractsDetailList = c.fetchall()
        for idx, contract in enumerate(allcontractsDetailList):
            contractDict = {}
            contractDict['contractName'] = contract[1]
            contractDict['contractAddress'] = contract[2]
            contractDict['status'] = contract[3]
            contractDict['transactionHash'] = contract[4]
            contractDict['incorporationDate'] = contract[5]
            if contract[6]:
                contractDict['expiryDate'] = contract[6]
            if contract[7]:
                contractDict['closeDate'] = contract[7]

            contractList.append(contractDict)

    elif not contractName and contractAddress:
        c.execute('select * from activecontracts where contractAddress="{}"'.format(contractAddress))
        allcontractsDetailList = c.fetchall()
        for idx, contract in enumerate(allcontractsDetailList):
            contractDict = {}
            contractDict['contractName'] = contract[1]
            contractDict['contractAddress'] = contract[2]
            contractDict['status'] = contract[3]
            contractDict['transactionHash'] = contract[4]
            contractDict['incorporationDate'] = contract[5]
            if contract[6]:
                contractDict['expiryDate'] = contract[6]
            if contract[7]:
                contractDict['closeDate'] = contract[7]

            contractList.append(contractDict)

    else:
        c.execute('select * from activecontracts')
        allcontractsDetailList = c.fetchall()
        for idx, contract in enumerate(allcontractsDetailList):
            contractDict = {}
            contractDict['contractName'] = contract[1]
            contractDict['contractAddress'] = contract[2]
            contractDict['status'] = contract[3]
            contractDict['transactionHash'] = contract[4]
            contractDict['incorporationDate'] = contract[5]
            if contract[6]:
                contractDict['expiryDate'] = contract[6]
            if contract[7]:
                contractDict['closeDate'] = contract[7]

            contractList.append(contractDict)

    return jsonify(smartContracts = contractList, result='ok')


@app.route('/api/v1.0/getsmartContractinfo', methods=['GET'])
async def getcontractinfo():
    name = request.args.get('name')
    contractAddress = request.args.get('contractAddress')

    if name is None:
        return jsonify(result='error', details='Smart Contract\'s name hasn\'t been passed')

    if contractAddress is None:
        return jsonify(result='error', details='Smart Contract\'s address hasn\'t been passed')

    contractName = '{}-{}.db'.format(name.strip(),contractAddress.strip())
    filelocation = os.path.join(dbfolder,'smartContracts', contractName)

    if os.path.isfile(filelocation):
        #Make db connection and fetch data
        conn = sqlite3.connect(filelocation)
        c = conn.cursor()
        c.execute(
            'SELECT attribute,value FROM contractstructure')
        result = c.fetchall()

        returnval = {'userChoice': []}
        temp = 0
        for row in result:
            if row[0] == 'exitconditions':
                if temp == 0:
                    returnval["userChoice"] = [row[1]]
                    temp = temp + 1
                else:
                    returnval['userChoice'].append(row[1])
                continue
            returnval[row[0]] = row[1]

        c.execute('select count(participantAddress) from contractparticipants')
        noOfParticipants = c.fetchall()[0][0]
        returnval['numberOfParticipants'] = noOfParticipants

        c.execute('select sum(tokenAmount) from contractparticipants')
        totalAmount = c.fetchall()[0][0]
        returnval['tokenAmountDeposited'] = totalAmount
        conn.close()

        conn = sqlite3.connect(os.path.join(dbfolder,'system.db'))
        c = conn.cursor()
        c.execute('select status, incorporationDate, expiryDate, closeDate from activecontracts where contractName=="{}" and contractAddress=="{}"'.format(name.strip(), contractAddress.strip()))
        results = c.fetchall()

        if len(results) == 1:
            for result in results:
                returnval['status'] = result[0]
                returnval['incorporationDate'] = result[1]
                if result[2]:
                    returnval['expiryDate'] = result[2]
                if result[3]:
                    returnval['closeDate'] = result[3]

        return jsonify(result='ok', contractInfo=returnval)

    else:
        return jsonify(result='error', details='Smart Contract with the given name doesn\'t exist')


@app.route('/api/v1.0/getsmartContractparticipants', methods=['GET'])
async def getcontractparticipants():
    name = request.args.get('name')
    contractAddress = request.args.get('contractAddress')

    if name is None:
        return jsonify(result='error', details='Smart Contract\'s name hasn\'t been passed')

    if contractAddress is None:
        return jsonify(result='error', details='Smart Contract\'s address hasn\'t been passed')

    contractName = '{}-{}.db'.format(name.strip(),contractAddress.strip())
    filelocation = os.path.join(dbfolder,'smartContracts', contractName)

    if os.path.isfile(filelocation):
        #Make db connection and fetch data
        conn = sqlite3.connect(filelocation)
        c = conn.cursor()
        c.execute(
            'SELECT id,participantAddress, tokenAmount, userChoice, transactionHash, winningAmount FROM contractparticipants')
        result = c.fetchall()
        conn.close()
        returnval = {}
        for row in result:
            returnval[row[0]] = {'participantAddress':row[1], 'tokenAmount':row[2], 'userChoice':row[3], 'transactionHash':row[4], 'winningAmount':row[5]}

        return jsonify(result='ok', participantInfo=returnval)

    else:
        return jsonify(result='error', details='Smart Contract with the given name doesn\'t exist')


@app.route('/api/v1.0/getparticipantdetails', methods=['GET'])
async def getParticipantDetails():
    floaddress = request.args.get('floaddress')

    if floaddress is None:
        return jsonify(result='error', details='FLO address hasn\'t been passed')
    dblocation = os.path.join(dbfolder,'system.db')

    print(dblocation)

    if os.path.isfile(dblocation):
        # Make db connection and fetch data
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()

        # Check if its a contract address
        c.execute("select contractAddress from activecontracts")
        activeContracts = c.fetchall()
        activeContracts = list(zip(*activeContracts))

        if floaddress in list(activeContracts[0]):
            c.execute("select contractName from activecontracts where contractAddress=='"+floaddress+"'")
            name = c.fetchall()

            if len(name) != 0:
                contractName = '{}-{}.db'.format(name[0][0].strip(),floaddress.strip())
                filelocation = os.path.join(dbfolder,'smartContracts', contractName)

                if os.path.isfile(filelocation):
                    #Make db connection and fetch data
                    conn = sqlite3.connect(filelocation)
                    c = conn.cursor()
                    c.execute(
                        'SELECT attribute,value FROM contractstructure')
                    result = c.fetchall()

                    returnval = {'exitconditions': []}
                    temp = 0
                    for row in result:
                        if row[0] == 'exitconditions':
                            if temp == 0:
                                returnval["exitconditions"] = [row[1]]
                                temp = temp + 1
                            else:
                                returnval['exitconditions'].append(row[1])
                            continue
                        returnval[row[0]] = row[1]

                    c.execute('select count(participantAddress) from contractparticipants')
                    noOfParticipants = c.fetchall()[0][0]
                    returnval['numberOfParticipants'] = noOfParticipants

                    c.execute('select sum(tokenAmount) from contractparticipants')
                    totalAmount = c.fetchall()[0][0]
                    returnval['tokenAmountDeposited'] = totalAmount

                    conn.close()
                    return jsonify(result='ok', address=floaddress, type='contract', contractInfo=returnval)

        # Check if its a participant address
        queryString = "SELECT id, participantAddress,contractName, contractAddress, tokenAmount, transactionHash FROM contractParticipantMapping where participantAddress=='"+floaddress+"'"
        c.execute(queryString)
        result = c.fetchall()
        conn.close()
        if len(result)!=0:
            participationDetailsList = []
            for row in result:
                detailsDict = {}
                detailsDict['contractName']= row[2]
                detailsDict['contractAddress'] = row[3]
                detailsDict['tokenAmount'] = row[4]
                detailsDict['transactionHash'] = row[5]
                participationDetailsList.append(detailsDict)
            return jsonify(result='ok', address=floaddress, type='participant' , participatedContracts=participationDetailsList)
        else:
            return jsonify(result='error', details='Address hasn\'t participanted in any other contract')
    else:
        return jsonify(result='error', details='System error. System db is missing')


@app.route('/test')
async def test():
    return render_template('test.html')

class ServerSentEvent:

    def __init__(
            self,
            data: str,
            *,
            event: Optional[str]=None,
            id: Optional[int]=None,
            retry: Optional[int]=None,
    ) -> None:
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry

    def encode(self) -> bytes:
        message = f"data: {self.data}"
        if self.event is not None:
            message = f"{message}\nevent: {self.event}"
        if self.id is not None:
            message = f"{message}\nid: {self.id}"
        if self.retry is not None:
            message = f"{message}\nretry: {self.retry}"
        message = f"{message}\r\n\r\n"
        return message.encode('utf-8')



@app.route('/', methods=['GET'])
async def index():
    return await render_template('index.html')


@app.route('/', methods=['POST'])
async def broadcast():
    signature = request.headers.get('Signature')
    data = await request.get_json()
    if verify_signature(signature, sse_pubKey, data['message'].encode()):
        for queue in app.clients:
            await queue.put(data['message'])
        return jsonify(True)
    else:
        return jsonify(False)


@app.route('/sse')
async def sse():
    queue = asyncio.Queue()
    app.clients.add(queue)
    async def send_events():
        while True:
            try:
                data = await queue.get()
                event = ServerSentEvent(data)
                yield event.encode()
            except asyncio.CancelledError as error:
                app.clients.remove(queue)

    response = await make_response(
        send_events(),
        {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Transfer-Encoding': 'chunked',
        },
    )
    response.timeout = None
    return response

if __name__ == "__main__":
    app.run(debug=True, port=5010)





