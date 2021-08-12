import discord
import chess
import chess.svg
import chess.engine
import datetime
from ChessBotHelpers import *
import os.path
from os import path
import time

client = discord.Client()

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    # The bot should not consider messages for which it was the sender.
    currentBoardFile = "/home/ec2-user/gameboards/" + str(message.guild.id) + ".txt"
    currentTimerFile = "/home/ec2-user/timers/" + str(message.guild.id) + ".txt"

    if message.author == client.user:
        return

    # Print current board state.
    if message.content.startswith('|board'):
        gameInProgress = path.exists(currentBoardFile)
        if not gameInProgress:
            await message.channel.send("No game currently in progress. Start a new game with `|new`!")
            return

        with open(currentBoardFile, "r") as myFile:
            currentFen = myFile.readlines()[0]
        currentBoard = chess.Board(fen=currentFen)
        currentTurn = currentBoard.turn

        if message.content != "|board":
            if message.content == "|board flip":
                currentTurn = not currentTurn
            else:
                await message.channel.send("Incorrect input. Specify `|board` for the current player's view, or `|board flip` for the opposite view.")

        if currentBoard.is_check():
            # highlight the king in check
            svg_string = chess.svg.board(board=currentBoard, orientation=currentTurn, check=currentBoard.king(currentBoard.turn))
        else:
            svg_string = chess.svg.board(board=currentBoard, orientation=currentTurn)

        printChessImageToFile(svg_string)

        if currentBoard.turn:
            colorToMove = "White"
        else:
            colorToMove = "Black"

        await message.channel.send(file=discord.File("/home/ec2-user/tmp/output.png"))
        if currentBoard.is_check():
            await message.channel.send("Check!")

        await message.channel.send(colorToMove + " to move.")
        return

    # Request documentation of commands
    if message.content.startswith('|help'):
        await message.channel.send(("Available commands:\n"
                                    "`|help` - prints information about all commands\n"
                                    "`|new` - starts a new game of chess\n"
                                    "`|new timer base inc` - starts a new game of chess with a timer. `base` is the starting' "
                                    " time, and `inc` is the amount the timer goes up with each move, both in seconds.\n"
                                    "`|end` - starts vote to end the current game of chess\n"
                                    "`|board` - prints an image of the board state from the current player's orientation\n"
                                    "`|board flip` - prints an image of the board state from the opposite player's orientation\n"
                                    "`|move s1 s2` - move the piece currently on square 1 to square 2\n"
                                    "`|move SAN` - makes the move specified by `SAN` in Short or Long Algebraic Notation\n"
                                    "`|engine` - uses the Stockfish 12 chess engine to decide the next move"))

    # Request to start a new game
    if message.content.startswith('|new'):
        # Check if a board file already exists and act accordingly
        gameInProgress = path.exists(currentBoardFile)
        if gameInProgress:
            await message.channel.send("Game already in progress, cannot start new game!")
        else:
            timerInfo = None
            if len(message.content.split()) == 4:
                timer = message.content.split()[1]
                base = message.content.split()[2]
                inc = message.content.split()[3]
                if timer != "timer" or not base.isnumeric() or not inc.isnumeric():
                    await message.channel.send(("Incorrect timer usage. Please specify `|new timer base inc`, where "
                                                "`base` and `inc` are integers representing the base timer and "
                                                "increment, respectively."))
                    return
                # create the timer file
                timerInfo = ";".join(["0", datetime.datetime.today().isoformat(), base, base, base, inc])
                with open(currentTimerFile, "w") as text_file:
                    print(timerInfo, file=text_file)
            elif message.content != "|new":
                await message.channel.send(("Incorrect specification. Please specify `|new` or `|new timer base inc`, "
                                            "where `base` and `inc` are integers representing the base timer and "
                                            "increment, respectively."))
                return

            with open(currentBoardFile, "w") as text_file:
                print(chess.STARTING_FEN, file=text_file)
            svg_string = chess.svg.board(board=chess.Board(fen=chess.STARTING_FEN))
            printChessImageToFile(svg_string)
            await message.channel.send(file=discord.File("/home/ec2-user/tmp/output.png"))
            await message.channel.send("White plays first. Good luck!")
            if timerInfo:
                await message.channel.send("Both sides have unlimited time for their first move, then timing begins.")
            return

    # Request to end the current game
    if message.content.startswith('|end'):

        gameInProgress = path.exists(currentBoardFile)
        if not gameInProgress:
            await message.channel.send("No game in progress, cannot vote to end. Start a new game with `|new`!")
            return

        pollMessage = await message.channel.send("A vote to end the game has begun. Two votes for either option will execute that option. Please vote by reacting to this message.")
        await pollMessage.add_reaction("✅")
        await pollMessage.add_reaction("❌")

        timer = 0
        while timer < 600:
            timer += 1
            time.sleep(1)
            pollMessage = await message.channel.fetch_message(pollMessage.id)
            for react in pollMessage.reactions:
                if react.emoji == "✅" and react.count >= 3:
                    # end the game
                    await message.channel.send("Two votes for ending the game received. Game will end. Start a new game with `|new`!")
                    os.remove(currentBoardFile)
                    if path.exists(currentTimerFile):
                        os.remove(currentTimerFile)
                    return
                elif react.emoji == "❌" and react.count >= 3:
                    # end the poll, continue the game
                    await message.channel.send("Two votes against ending the game received. Game will continue.")
                    return
        await message.channel.send("Vote to end game expired. Please start a new vote with `|end` if you still wish to end.")
        return

    # Move a piece
    if message.content.startswith('|move'):
        gameInProgress = path.exists(currentBoardFile)
        if not gameInProgress:
            await message.channel.send("No game currently in progress. Start a new game with `|new`!")
            return

        timer = path.exists(currentTimerFile)

        with open(currentBoardFile, "r") as myFile:
            currentFen = myFile.readlines()[0]

        currentBoard = chess.Board(fen=currentFen)

        moveToMake = await parseMove(message, currentBoard)
        if moveToMake is None:
            return

        # Make the move, check for checkmate/stalemate, update the fen/file, and print the new board
        currentBoard.push(moveToMake)

        if currentBoard.turn:
            colorToMove = "White"
        else:
            colorToMove = "Black"

        gameOver = await checkEndConditions(currentBoard, message, colorToMove)

        timerResult = 0
        if timer:
            timerResult = updateTimers(currentTimerFile, colorToMove)

        newSvg = getNewSvgAndUpdateFEN(currentBoard, currentBoardFile, moveToMake)

        printChessImageToFile(newSvg)
        await message.channel.send(file=discord.File("/home/ec2-user/tmp/output.png"))

        if not gameOver and timerResult == 0:
            if currentBoard.is_check():
                await message.channel.send("Check!")
            if timer:
                await printTimerBars(message, currentTimerFile)
            await message.channel.send(colorToMove + " to move.")
        else:
            os.remove(currentBoardFile)
            if timerResult == -1:
                await message.channel.send("White is out of time, Black wins!")
                os.remove(currentTimerFile)
            elif timerResult == -2:
                await message.channel.send("Black is out of time, White wins!")
                os.remove(currentTimerFile)

        return

    # Have the engine move the piece
    if message.content.startswith('|engine'):
        gameInProgress = path.exists(currentBoardFile)
        if not gameInProgress:
            await message.channel.send("No game currently in progress. Start a new game with `|new`!")
            return

        timer = path.exists(currentTimerFile)

        await message.channel.send("Letting the engine choose the best move...")
        engine = chess.engine.SimpleEngine.popen_uci("/home/ec2-user/stockfish")
        with open(currentBoardFile, "r") as myFile:
            currentFen = myFile.readlines()[0]
        currentBoard = chess.Board(fen=currentFen)
        moveToMake = engine.play(currentBoard, chess.engine.Limit(time=1)).move
        currentBoard.push(moveToMake)

        if currentBoard.turn:
            colorToMove = "White"
        else:
            colorToMove = "Black"

        gameOver = await checkEndConditions(currentBoard, message, colorToMove)

        timerResult = 0
        if timer:
            timerResult = updateTimers(currentTimerFile, colorToMove)

        newSvg = getNewSvgAndUpdateFEN(currentBoard, currentBoardFile, moveToMake)

        printChessImageToFile(newSvg)
        await message.channel.send(file=discord.File("/home/ec2-user/tmp/output.png"))

        if not gameOver and timerResult == 0:
            if currentBoard.is_check():
                await message.channel.send("Check!")
            if timer:
                await printTimerBars(message, currentTimerFile)
            await message.channel.send(colorToMove + " to move.")
        else:
            os.remove(currentBoardFile)
            if timerResult == -1:
                await message.channel.send("White is out of time, Black wins!")
                os.remove(currentTimerFile)
            elif timerResult == -2:
                await message.channel.send("Black is out of time, White wins!")
                os.remove(currentTimerFile)

        engine.quit()
        return

# This line is used for authentication purposes to allow interaction with the Discord api
### CENSORED FOR GITHUB ###
client.run('bot-token-goes-here')
