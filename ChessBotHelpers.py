from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF, renderPM
import chess
import re
import datetime


def printChessImageToFile(stringToPrint):
    # stringToPrint is an svg string
    with open("/home/ec2-user/tmp/temp.svg", "w") as text_file:
        print(stringToPrint, file=text_file)
    drawing = svg2rlg("/home/ec2-user/tmp/temp.svg")
    renderPM.drawToFile(drawing, "/home/ec2-user/tmp/output.png", fmt="PNG")


def getNewSvgAndUpdateFEN(currentBoard, currentBoardFile, moveToMake):
    # Get the SVG string for the current board state
    newFen = currentBoard.fen()
    with open(currentBoardFile, "w") as text_file:
        print(newFen, file=text_file)

    if currentBoard.is_check():
        # highlight the king in check
        newSvg = chess.svg.board(board=currentBoard, lastmove=moveToMake, orientation=currentBoard.turn,
                                 check=currentBoard.king(currentBoard.turn))
    else:
        newSvg = chess.svg.board(board=currentBoard, lastmove=moveToMake, orientation=currentBoard.turn)

    return newSvg


def progress(count, total, player=''):
    # adapted from https://gist.github.com/vladignatyev/06860ec2040cb497f0f3
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))
    bar = '`[' + '=' * filled_len + '-' * (bar_len - filled_len) + ']`'
    myBar = bar + " " + str(count) + "/" + str(total) + " seconds remaining for " + player + "!"
    return myBar


def updateTimers(currentTimerFile, currentTurn):
    # When playing with timers, handles each players clock
    with open(currentTimerFile, "r") as myFile:
        currentTimerInfo = myFile.readlines()[0]

    turnNumber = int(currentTimerInfo.split(";")[0])
    lastTurnTime = datetime.datetime.fromisoformat(currentTimerInfo.split(";")[1])
    startingTimeLimit = currentTimerInfo.split(";")[2]
    whiteTimer = int(currentTimerInfo.split(";")[3])
    blackTimer = int(currentTimerInfo.split(";")[4])
    increment = int(currentTimerInfo.split(";")[5])

    currentTime = datetime.datetime.today()
    secondsPassed = (currentTime - lastTurnTime).seconds

    turnNumber += 1
    if turnNumber > 2:
        # Don't run the timer on the first two turns
        if currentTurn == "Black":
            if secondsPassed >= whiteTimer:
                # White is out of time
                return -1
            else:
                whiteTimer += increment
                whiteTimer -= secondsPassed
        else:
            if secondsPassed >= blackTimer:
                # Black is out of time
                return -2
            else:
                blackTimer += increment
                blackTimer -= secondsPassed

    lastTurnTime = currentTime
    currentTimerInfo = ";".join([str(turnNumber), lastTurnTime.isoformat(), startingTimeLimit, str(whiteTimer), str(blackTimer), str(increment)])

    with open(currentTimerFile, "w") as text_file:
        print(currentTimerInfo, file=text_file)

    return 0

async def printTimerBars(message, currentTimerFile):
    # Print the timer progress bars for each side
    with open(currentTimerFile, "r") as myFile:
        currentTimerInfo = myFile.readlines()[0]

    startingTimeLimit = int(currentTimerInfo.split(";")[2])
    whiteTimer = int(currentTimerInfo.split(";")[3])
    blackTimer = int(currentTimerInfo.split(";")[4])

    await message.channel.send(progress(whiteTimer, startingTimeLimit, "White"))
    await message.channel.send(progress(blackTimer, startingTimeLimit, "Black"))

async def checkEndConditions(currentBoard, message, colorToMove):
    # Check end conditions
    gameOver = False
    if currentBoard.is_checkmate():
        await message.channel.send("Checkmate! " + colorToMove + " loses. Start a new game with `|new`!")
        gameOver = True
    elif currentBoard.is_stalemate():
        await message.channel.send("Stalemate! That sucks. Start a new game with `|new`!")
        gameOver = True
    elif currentBoard.is_insufficient_material():
        await message.channel.send(
            "Draw by insufficient material! Be more careful next time. Start a new game with `|new`!")
        gameOver = True
    return gameOver


async def parseMove(moveMessage, currentBoard):
    # take in text input, parse it, return a chess.Move if it is valid. If not valid, return None

    if len(moveMessage.content.split()) == 3:
        # move by specifying squares
        s1 = moveMessage.content.split()[1]
        s2 = moveMessage.content.split()[2]
        validSquareRegex = "[a-h][1-8]"
        s1search = re.findall(validSquareRegex, s1)
        s2search = re.findall(validSquareRegex, s2)
        if len(s1) != 2 or len(s1search) != 1:
            await moveMessage.channel.send("Invalid square specified for s1. Please choose a valid square.")
            return None
        if len(s2) != 2 or len(s2search) != 1:
            await moveMessage.channel.send("Invalid square specified for s2. Please choose a valid square.")
            return None

        # If input string is valid, generate the chess.Move and chess.Board objects
        s1 = chess.SQUARES[chess.SQUARE_NAMES.index(s1)]
        s2 = chess.SQUARES[chess.SQUARE_NAMES.index(s2)]

        # Check for special case of promotion
        if currentBoard.turn and chess.square_rank(s1) == 6 and chess.square_rank(s2) == 7 and currentBoard.piece_at(
                s1).piece_type == chess.PAWN:
            # promote white pawn to queen
            moveToMake = chess.Move(from_square=s1, to_square=s2, promotion=chess.QUEEN)
        elif not currentBoard.turn and chess.square_rank(s1) == 1 and chess.square_rank(
                s2) == 0 and currentBoard.piece_at(
            s1).piece_type == chess.PAWN:
            # promote black pawn to queen
            moveToMake = chess.Move(from_square=s1, to_square=s2, promotion=chess.QUEEN)
        else:
            moveToMake = chess.Move(from_square=s1, to_square=s2)

    elif len(moveMessage.content.split()) == 2:
        # move via standard algebraic notation
        try:
            moveToMake = currentBoard.parse_san(moveMessage.content.split()[1])
        except ValueError:
            await moveMessage.channel.send(
                "Incorrectly specified/Illegal move. Please use correct Standard/Long Algebraic Format to specify a legal move.")
            return None

    else:
        # incorrectly specified move
        await moveMessage.channel.send(
            "Please specify a move using Standard/Long Algebraic Notation as `|move SAN` or by naming the squares the move starts and ends at as `|move s1 s2`.")
        return None

    return moveToMake
