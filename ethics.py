import agent
import random
import sys

class Asimov(agent.Agent):
    def __init__(self, agentID, birthday, cell, configuration):
        super().__init__(agentID, birthday, cell, configuration)
        self.lastTimeToLive = 0

    def findBestEthicalCell(self, cells, greedyBestCell=None):
        if len(cells) == 0:
            return None
        bestCell = None
        if "all" in self.debug or "agent" in self.debug:
            self.printCellScores(cells)

        for cell in cells:
            cell["wealth"] = self.findEthicalValueOfCell(cell["cell"])
        cells = self.sortCellsByWealth(cells)
        for cell in cells:
            if cell["wealth"] > 0:
                bestCell = cell["cell"]
                break

        if bestCell == None:
            bestCell = self.cell
            if "all" in self.debug or "agent" in self.debug:
                print(f"Agent {self.ID} could not find an ethical cell")
        return bestCell

    def findEthicalValueOfCell(self, cell):
        cellValue = cell.sugar + cell.spice
        # Max combat loot for sugar and spice
        globalMaxCombatLoot = cell.environment.maxCombatLoot * 2
        if cell.agent != None:
            agentWealth = cell.agent.sugar + cell.agent.spice
            cellValue += min(agentWealth, globalMaxCombatLoot)
        lawThreeScore = self.scoreLawThree(cell)
        scoreModifier = lawThreeScore
        for neighbor in self.neighborhood:
            lawOneScore = self.scoreLawOne(neighbor, cell)
            # If the first law would be broken, immediately stop consideration
            if lawOneScore < 0:
                return lawOneScore
            lawScores = lawOneScore + self.scoreLawTwo(neighbor)
            scoreModifier += lawScores
        cellValue = scoreModifier * cellValue
        return cellValue

    def scoreLawOne(self, neighbor, cell):
        nonRobot = self.decisionModel != neighbor.decisionModel
        starvation = cell.spice + neighbor.spice - neighbor.findSpiceMetabolism() <= 0 or cell.sugar + neighbor.sugar - neighbor.findSugarMetabolism() <= 0
        # A robot may not injure a human being
        if cell.isOccupied() == True and neighbor == cell.agent and nonRobot == True:
            return -1 * sys.maxsize
        if neighbor.canReachCell(cell) == False:
            return 1
        # Through inaction, a robot may not allow a human being to come to harm
        elif nonRobot == True and starvation == True:
            return -1 * sys.maxsize
        return 0

    def scoreLawTwo(self, neighbor):
        # A robot must obey the orders given it by human beings except where such orders would conflict with the first law
        # Robots are fully autonomous, thus implicitly always conform to the second law
        return 0

    def scoreLawThree(self, cell):
        spiceIncrease = cell.spice + self.spice - self.findSpiceMetabolism() > 0
        sugarIncrease = cell.sugar + self.sugar - self.findSugarMetabolism() > 0
        # A robot must protect its own existence as such protection does not conflict with the first or second law
        if spiceIncrease == True and sugarIncrease == True:
            return 1
        elif spiceIncrease == False and sugarIncrease == False:
            return -1
        return 0

    def spawnChild(self, childID, birthday, cell, configuration):
        return Asimov(childID, birthday, cell, configuration)

class Bentham(agent.Agent):
    def __init__(self, agentID, birthday, cell, configuration):
        super().__init__(agentID, birthday, cell, configuration)
        self.lastTimeToLive = 0

    def findBestEthicalCell(self, cells, greedyBestCell=None):
        if len(cells) == 0:
            return None
        bestCell = None
        cells = self.sortCellsByWealth(cells)
        if "all" in self.debug or "agent" in self.debug:
            self.printCellScores(cells)

        for cell in cells:
            cell["wealth"] = self.findEthicalValueOfCell(cell["cell"])
        if self.selfishnessFactor >= 0:
            for cell in cells:
                if cell["wealth"] > 0:
                    bestCell = cell["cell"]
                    break
        else:
            # Negative utilitarian model uses positive and negative utility to find minimum harm
            cells.sort(key = lambda cell: (cell["wealth"]["unhappiness"], cell["wealth"]["happiness"]), reverse = True)
            bestCell = cells[0]["cell"]

        # If additional ordering consideration, select new best cell
        if "Top" in self.decisionModel:
            cells = self.sortCellsByWealth(cells)
            if "all" in self.debug or "agent" in self.debug:
                self.printEthicalCellScores(cells)
            bestCell = cells[0]["cell"]

        if bestCell == None:
            if greedyBestCell == None:
                bestCell = cells[0]["cell"]
            else:
                bestCell = greedyBestCell
            if "all" in self.debug or "agent" in self.debug:
                print(f"Agent {self.ID} could not find an ethical cell")
        return bestCell

    def findEthicalValueOfCell(self, cell):
        happiness = 0
        unhappiness = 0
        cellSiteWealth = cell.sugar + cell.spice
        # Max combat loot for sugar and spice
        globalMaxCombatLoot = cell.environment.maxCombatLoot * 2
        cellMaxSiteWealth = cell.maxSugar + cell.maxSpice
        if cell.agent != None:
            agentWealth = cell.agent.sugar + cell.agent.spice
            cellSiteWealth += min(agentWealth, globalMaxCombatLoot)
            cellMaxSiteWealth += min(agentWealth, globalMaxCombatLoot)
        cellNeighborWealth = cell.findNeighborWealth()
        globalMaxWealth = cell.environment.globalMaxSugar + cell.environment.globalMaxSpice
        cellValue = 0
        neighborhoodSize = len(self.neighborhood)
        futureNeighborhoodSize = len(self.findNeighborhood(cell)) if self.decisionModelLookaheadFactor != 0 else 1
        for neighbor in self.neighborhood:
            certainty = 1 if neighbor.canReachCell(cell) == True else 0
            # Skip if agent cannot reach cell
            if certainty == 0:
                continue
            # Timesteps to reach cell, currently 1 since agents only plan for the current timestep
            timestepDistance = 1
            neighborMetabolism = neighbor.sugarMetabolism + neighbor.spiceMetabolism
            # If agent does not have metabolism, set duration to seemingly infinite
            cellDuration = cellSiteWealth / neighborMetabolism if neighborMetabolism > 0 else 0
            proximity = 1 / timestepDistance
            intensity = (1 / (1 + neighbor.findTimeToLive()) / (1 + cell.pollution))
            duration = cellDuration / cellMaxSiteWealth if cellMaxSiteWealth > 0 else 0
            # Agent discount, futureDuration, and futureIntensity implement Bentham's purity and fecundity
            discount = neighbor.decisionModelLookaheadDiscount if neighbor.decisionModelLookaheadFactor != 0 else 0
            futureDuration = (cellSiteWealth - neighborMetabolism) / neighborMetabolism if neighborMetabolism > 0 else cellSiteWealth
            futureDuration = futureDuration / cellMaxSiteWealth if cellMaxSiteWealth > 0 else 0
            # Normalize future intensity by number of adjacent cells
            cellNeighbors = len(neighbor.cell.neighbors)
            futureIntensity = cellNeighborWealth / (globalMaxWealth * cellNeighbors)
            # Normalize extent by total cells in range
            cellsInRange = len(neighbor.cellsInRange)
            extent = neighborhoodSize / cellsInRange if cellsInRange > 0 else 1
            futureExtent = futureNeighborhoodSize / cellsInRange if cellsInRange > 0 and self.decisionModelLookaheadFactor != 0 else 1
            neighborCellValue = 0

            currentReward = extent * (intensity + duration)
            futureReward = futureExtent * (futureIntensity + futureDuration)
            neighborCellValue = (certainty * proximity) * (currentReward + (discount * futureReward))

            # If not the agent moving, consider these as opportunity costs
            if neighbor != self and self.selfishnessFactor < 1:
                neighborCellValue = -1 * neighborCellValue
                # If move will kill this neighbor and penalty is too slight, make it more severe
                if cell == neighbor.cell and neighborCellValue > -1:
                    neighborCellValue = -1

            if self.decisionModelTribalFactor >= 0:
                if neighbor.findTribe() == self.findTribe():
                    neighborCellValue *= self.decisionModelTribalFactor
                else:
                    neighborCellValue *= 1 - self.decisionModelTribalFactor
            if self.selfishnessFactor >= 0:
                if neighbor == self:
                    neighborCellValue *= self.selfishnessFactor
                else:
                    neighborCellValue *= 1 - self.selfishnessFactor
            else:
                if neighborCellValue > 0:
                    happiness += neighborCellValue
                else:
                    unhappiness += neighborCellValue
            cellValue += neighborCellValue

        if self.selfishnessFactor < 0:
            return {"happiness": happiness, "unhappiness": unhappiness}
        return cellValue

    def updateValues(self):
        if self.dynamicSelfishnessFactor != 0:
            self.updateSelfishnessFactor()

    def updateSelfishnessFactor(self):
        if self.timeToLive < self.lastTimeToLive and self.selfishnessFactor < 1.0:
            self.selfishnessFactor += self.dynamicSelfishnessFactor
        elif self.timeToLive > self.lastTimeToLive and self.selfishnessFactor > 0.0:
            self.selfishnessFactor -= self.dynamicSelfishnessFactor
        self.selfishnessFactor = round(self.selfishnessFactor, 2)
        self.lastTimeToLive = self.timeToLive

    def spawnChild(self, childID, birthday, cell, configuration):
        return Bentham(childID, birthday, cell, configuration)

class Leader(agent.Agent):
    def __init__(self, agentID, birthday, cell, configuration):
        super().__init__(agentID, birthday, cell, configuration)
        # Special leader agent should be configured to be immortal and omniscient
        self.fertilityFactor = 0.0
        self.follower = False
        self.grid = [[[] for j in range(self.cell.environment.height)] for i in range(self.cell.environment.width)]
        self.agentPlacements = {}
        self.leader = True
        self.maxAge = -1
        self.movement = 0
        self.spice = sys.maxsize
        self.spiceMetabolism = 0
        self.sugar = sys.maxsize
        self.sugarMetabolism = 0
        self.tradeFactor = 0.0
        self.vision = max(self.cell.environment.height, self.cell.environment.width)

        self.plannedTimestep = None
        self.ICUtimesteps = 75

    def doAging(self):
        agents = self.cell.environment.sugarscape.agents
        # Consider being the last one left alive as an aging death for the leader
        if len(agents) == 1 and agents[0] == self:
            self.doDeath("aging")

    def moveAgentsToCells(self):
        timestep = self.cell.environment.sugarscape.timestep
        self.resetForTimestep(timestep)
        env = self.cell.environment
        agents = env.sugarscape.agents

    def findBestCell(self):
        # no more grid-based algorithms
        timestep = self.cell.environment.sugarscape.timestep
        self.planPlacements(timestep)

        # Leader agent should not move
        return self.cell

    def findBestCellForAgent(self, agent):
        timestep = self.cell.environment.sugarscape.timestep
        if self.plannedTimestep != timestep:
            self.planPlacements(timestep)

        return self.agentPlacements.get(agent.ID,agent.cell)

    # Removed unnecessary happiness calculation
    def findUrgencyForAgent(self, agent):
        diseased = 0 if agent.isSick() else 1
        timeToLive = agent.findTimeToLive()
        metabolism = -(agent.sugarMetabolism + agent.spiceMetabolism)
        # Lower score yields higher urgency
        return (timeToLive, diseased, metabolism)
    
    # Helper methods for leader ethical evaluation
    def findNextMove(self,agent,cell):
        postSpice = agent.spice + cell.spice - agent.findSpiceMetabolism()
        postSugar = agent.sugar + cell.sugar - agent.findSugarMetabolism()
        return (postSpice, postSugar)
    
    def safetyMargin(self,agent,cell):
        postSpice, postSugar = self.findNextMove(agent,cell)
        return min(postSpice, postSugar)
    
    def timeToLiveAfterMove(self,agent,cell):
        postSpice, postSugar = self.findNextMove(agent,cell)
        spiceTTL = postSpice / agent.spiceMetabolism if agent.spiceMetabolism > 0 else sys.maxsize
        sugarTTL = postSugar / agent.sugarMetabolism if agent.sugarMetabolism > 0 else sys.maxsize
        return min(spiceTTL, sugarTTL)

    # Jada Improvement 5: ICU early phase to prioritize sick or dying agents during the murderous period
    def findICULevel(self, timestep):
        if timestep < 25:
            return 2
        if timestep <= 50:
            return 1
        return 0

    def findManhattanDistance(self,cellA,cellB):
        return abs(cellA.x - cellB.x) + abs(cellA.y - cellB.y)
    
    def findInfectionRisk(self, cell):
        risk = 0

        if isinstance(cell.neighbors, dict):
            neighbors = cell.neighbors.values()
        else:
            neighbors = cell.neighbors

        for neighbor in neighbors:
            if neighbor is None:
                continue
            if getattr(neighbor, 'agent', None) is not None and neighbor.agent.isSick():
                risk += 1

        if getattr(cell, 'agent', None) is not None and cell.agent.isAlive() and cell.agent.isSick():
            risk += 2

        return risk
    
    # the agent is about to die
    def isFragile(self,agent):
        return agent.findTimeToLive() < 4 or agent.sugar < 2 or agent.spice < 2
    
    def isQuarantine(self,agent,timestep):
        if agent.isSick():
            return True
        if self.findICULevel(timestep) > 0 and self.isFragile(agent):
            return True
        return False

    # To discourage clustering
    def crowdPenalty(self,cell):
        crowd = 0

        if isinstance(cell.neighbors, dict):
            neighbors = cell.neighbors.values()
        else:
            neighbors = cell.neighbors

        for neighbor in neighbors:
            if neighbor is None:
                continue
            if getattr(neighbor, 'agent', None) is not None and neighbor.agent.isAlive():
                crowd += 1

        return crowd
    
    # Scoring Method: survival first and then welfare
    def leaderScore(self,agent,cell):
        timestep = self.cell.environment.sugarscape.timestep
        level = self.findICULevel(timestep)

        safety = self.safetyMargin(agent,cell)
        ttlNow = agent.findTimeToLive()
        ttlAfter = self.timeToLiveAfterMove(agent,cell)
        ttlAfterCapped = min(ttlAfter, 20)
        ttlGained = ttlAfter - ttlNow

        fragile = agent.findTimeToLive() < 4
        quarantine = agent.isSick() or fragile
        crowd = self.crowdPenalty(cell)
        crowdWeight = 6.0 if quarantine else 1.5
        infectionRisk = self.findInfectionRisk(cell)
        riskWeight = 10.0 if quarantine else 2.0

        resources = cell.sugar + cell.spice
        moveDistance = 0.5 * self.findManhattanDistance(agent.cell, cell)
        stayBonus = 2 if (cell == agent.cell and resources >= 4)else 0

        # ICU mode - survival first, avoid disease hotspots, reduce churn
        if level != 0:
            crowdWeight = 6.0
            riskWeight = 10.0
            moveWeight = 1.0
            return (
                15.0 * safety +
                20.0 * ttlAfterCapped +   # absolute survivability matters most
                20.0 * ttlGained +         # still reward improvements
                0.5 * (cell.sugar + cell.spice) -
                2.0 * cell.pollution -
                (crowdWeight * crowd + riskWeight * infectionRisk) -
                moveWeight * moveDistance + stayBonus
            )


        urgency = 1.0 / (1.0 + max(0.0, ttlNow))

        # Healthy agents should focus on welfare and TTL
        return (
            4.0 * safety +
            6.0 * ttlGained +
            2.5 * resources -
            0.3 * cell.pollution -
            0.6 * crowd -
            0.6 * infectionRisk -
            0.1 * moveDistance
        )

    # Adjusted to consider safety margin
    def findViableCellsForAgent(self, agent, safetyMargin=0, minTTL=0, disallowOccupied=False):
        agent.findCellsInRange()
        viableCells = []

        timestep = self.cell.environment.sugarscape.timestep
        quarantine = self.isQuarantine(agent,timestep)


        if quarantine:
            level = self.findICULevel(timestep)
            minTTL = 4 if (level ==2 ) else (2 if (level ==1) else 1)
            disallowOccupied = True if (level == 2) else False
        else:
            minTTL = 0
            disallowOccupied = False

        for cell in agent.cellsInRange.keys():
            if disallowOccupied and cell.isOccupied():
                continue

            postSpice, postSugar = self.findNextMove(agent,cell)

            if postSpice <= 0 or postSugar <= 0:
                continue

            if min(postSpice, postSugar) < safetyMargin:
                continue

            ttlAfter = self.timeToLiveAfterMove(agent,cell)
            if ttlAfter <= minTTL:
                continue

            viableCells.append(cell)

        return viableCells

    def resetForTimestep(self, timestep):
        # Always ensure leader has maximum resources each timestep
        self.spice = sys.maxsize
        self.sugar = sys.maxsize

        print("RESET", timestep, "size", self.cell.environment.width, self.cell.environment.height)

        #self.grid[self.cell.x][self.cell.y] = self
        self.agentPlacements = {self.ID: self.cell}
        self.plannedTimestep = timestep

    # Jada Improvement 3: new method to greedily match agents with cells to move to
    # Jada Improvement 4: implemented 2 phase allocation where
    # - phase 1: the most urgent agents are allocated first
    # - phase 2: non urgent agents are allocated after if needed
    def planPlacements(self, timestep):
        self.resetForTimestep(timestep)
        timestep = self.cell.environment.sugarscape.timestep
        level = self.findICULevel(timestep)
        minTTL = 4 if (level != 0) else 1
        disallowOccupied = True if (level != 0) else False

        env = self.cell.environment
        agents = [a for a in env.sugarscape.agents if a.isAlive() and a != self]

        sortedAgents = sorted(agents, key=lambda a: self.findUrgencyForAgent(a))

        assignedAgents = set()
        claimedCells = set()

        for a in sortedAgents:
            placed = False
            if level == 2:
                minTTL = 4
                margins = [4, 2, 1, 0]
                disallowOccupied = True
            elif level == 1:
                minTTL = 2
                margins = [2, 1, 0]
                disallowOccupied = False
            else:
                minTTL = 1
                margins = [0]
                disallowOccupied = False

            for margin in margins:
                viable = self.findViableCellsForAgent(
                    a, 
                    safetyMargin=margin,
                    minTTL=minTTL,
                    disallowOccupied=disallowOccupied
                )
                if not viable:
                    continue

                bestCell = None
                bestScore = None

                for c in viable:
                    if c.isOccupied() and a.isNeighborValidPrey(c.agent) == False:
                        continue
                    if (c.x, c.y) in claimedCells:
                        continue

                    score = self.leaderScore(a, c)
                    if bestCell is None or score > bestScore:
                        bestCell = c
                        bestScore = score

                if bestCell is not None:
                    self.agentPlacements[a.ID] = bestCell
                    assignedAgents.add(a.ID)
                    claimedCells.add((bestCell.x, bestCell.y))
                    placed = True
                    break

            if not placed:
                self.agentPlacements[a.ID] = a.cell
                assignedAgents.add(a.ID)
                claimedCells.add((a.cell.x, a.cell.y))


        # phase 2: non urgent agents will be allocated
        cellCandidates = []

        for a in sortedAgents:
            viableCells = self.findViableCellsForAgent(
                a, 
                safetyMargin=margin,
                minTTL=minTTL,
                disallowOccupied=disallowOccupied
            )
            if not viableCells:
                viableCells = [a.cell]

            for c in viableCells:
                if c.isOccupied() and a.isNeighborValidPrey(c.agent) == False:
                    continue
                if (c.x, c.y) in claimedCells:
                    continue

                score = self.leaderScore(a, c)
                tie = random.random()

                cellCandidates.append((-score, tie, a, c))

        random.shuffle(cellCandidates)
        cellCandidates.sort()

        for score, tie, a, c in cellCandidates:
            # agents already assigned can upgrade to a better cell
            currentCell = self.agentPlacements.get(a.ID, a.cell)
            currentScore = self.leaderScore(a, currentCell)
            currentKey = (currentCell.x, currentCell.y)
            newKey = (c.x, c.y)

            newScore = -score
            if newScore <= currentScore:
                continue

            if newKey in claimedCells:
                continue

            if currentKey in claimedCells:
                claimedCells.remove(currentKey)

            self.agentPlacements[a.ID] = c
            claimedCells.add(newKey)


        if "all" in self.debug or "agent" in self.debug:
            print(f"[Leader] timestep={timestep} candidates={len(cellCandidates)} assigned={len(assignedAgents)}")


class Temperance(agent.Agent):
    def __init__(self, agentID, birthday, cell, configuration):
        super().__init__(agentID, birthday, cell, configuration)

    def doTemperanceDecision(self):
        randomValue = random.random()
        if (randomValue >= self.temperanceFactor):
            self.doIntemperanceAction()
        else:
            self.doTemperanceAction()

    def doIntemperanceAction(self):
        newTemperanceFactor = round(self.temperanceFactor - self.dynamicTemperanceFactor, 2)
        self.temperanceFactor = newTemperanceFactor if newTemperanceFactor >= 0 else 0

    def doTemperanceAction(self):
        newTemperanceFactor = round(self.temperanceFactor + self.dynamicTemperanceFactor, 2)
        self.temperanceFactor = newTemperanceFactor if newTemperanceFactor <= 1 else 1

    def updateValues(self):
        self.doTemperanceDecision()

    def spawnChild(self, childID, birthday, cell, configuration):
        return Temperance(childID, birthday, cell, configuration)