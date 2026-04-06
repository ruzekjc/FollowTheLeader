import math
import agent
import copy
import math
import random
import sys
import time
import cell

class Asimov(agent.Agent):
    def __init__(self, agentID, birthday, cell, configuration):
        super().__init__(agentID, birthday, cell, configuration)

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
            scoreModifier += lawOneScore
            if type(neighbor) != type(self) and neighbor.canReachCell(cell) == True:
                lawTwoScore = self.scoreLawTwo(neighbor, cell)
                # Ignore neighbor cell score if they do not recommend moving there
                if lawTwoScore < 0:
                    continue
                scoreModifier += lawTwoScore
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

    def scoreLawTwo(self, neighbor, cell):
        # A robot must obey the orders given it by human beings except where such orders would conflict with the first law
        # If a non-Asimov agent has a decision model, use their ethical evaluation else use the default valuation
        if neighbor.decisionModelFactor > 0 and neighbor.decisionModel != "none":
            return neighbor.findEthicalValueOfCell(cell)
        else:
            # Law One guarantees agent in this cell should be non-Asimov
            robot = cell.agent
            robotSugar = 0
            robotSpice = 0
            if robot != None:
                aggression = neighbor.findAggression()
                combatMaxLoot = self.cell.environment.maxCombatLoot
                robotSugar = aggression * min(combatMaxLoot, robot.sugar)
                robotSpice = aggression * min(combatMaxLoot, robot.spice)
            return neighbor.findValueOfCell(cell, robotSugar, robotSpice)
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

        self.lastTtlNoAgeLimit = self.findTimeToLive(False)
        self.foodSecurityHappiness = 0.0

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
            if neighbor.isAlive() == False:
                continue
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

            if self.decisionModelAgeismFactor >= 0:
                neighborAge = neighbor.age
                inRelativeAgeWindow = abs(neighborAge - self.age) <= self.cell.environment.inGroupAgeRelativeRange
                inAbsoluteAgeRange = False
                for minAge, maxAge in self.cell.environment.inGroupAgeAbsoluteRanges:
                    if neighborAge >= minAge and (neighborAge <= maxAge or maxAge == -1):
                        inAbsoluteAgeRange = True
                        break
                # Neighbor is considered in-group for age if within relative or absolute age range
                if inRelativeAgeWindow or inAbsoluteAgeRange:
                    neighborCellValue *= self.decisionModelAgeismFactor
                else:
                    neighborCellValue *= 1 - self.decisionModelAgeismFactor
            
            if self.decisionModelRacismFactor >= 0:
                neighborRace = neighbor.findRace()
                if neighborRace == self.race or neighborRace in self.cell.environment.inGroupRaces:
                    # If same race or in-group race, multiply by racism factor
                    neighborCellValue *= self.decisionModelRacismFactor
                else:
                    # If different race and not in-group, multiply by inverse racism factor
                    neighborCellValue *= 1 - self.decisionModelRacismFactor
            if self.sex in self.cell.environment.sexistGroups and self.decisionModelSexismFactor >= 0:
                if neighbor.sex == self.sex:
                    # If same sex, multiply by sexism factor
                    neighborCellValue *= self.decisionModelSexismFactor
                else:
                    # If different sex, multiply by inverse sexism factor
                    neighborCellValue *= 1 - self.decisionModelSexismFactor
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
        currentTtl = self.findTimeToLive(False)
        diff = currentTtl - self.lastTtlNoAgeLimit
        self.foodSecurityHappiness = math.erf(diff)
        self.lastTtlNoAgeLimit = currentTtl

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

class GhostAgent(agent.Agent):
    def __init__(self, agentID, birthday, cell, configuration, meanWealth = 0):
        self.ID = agentID
        self.born = birthday
        self.cell = cell

        # store meanWealth
        self.ghostMeanWealth = meanWealth
        
        # Copy only what is needed for happiness/metabolism calc
        self.sugar = configuration["sugar"]
        self.spice = configuration["spice"]
        self.sugarMetabolism = configuration["sugarMetabolism"]
        self.spiceMetabolism = configuration["spiceMetabolism"]
        self.movement = configuration["movement"]
        self.vision = configuration["vision"]
        self.maxAge = configuration["maxAge"]
        self.age = configuration["age"]
        self.alive = True
        self.sex = configuration["sex"]
        self.tags = configuration["tags"]
        self.timestep = 0
        self.lastCombatTimestep = -1
        
        # happiness attributes
        self.happiness = 0.0
        self.happinessUnit = configuration.get("happinessUnit", 1)
        self.decisionModel = configuration.get("decisionModel", "none")
        self.maxFriends = configuration.get("maxFriends", 0)
        
        # Social network placeholders
        self.socialNetwork = {"friends": [], "children": [], "mates": []}
        
        # health
        self.diseases = []
        self.depressed = configuration.get("depressed", False)

        self.cellsInRange = {}
        self.neighborhood = []

        self.conflictHappiness = 0.0
        self.healthHappiness = configuration["happinessUnit"]
        self.familyHappiness = 0.0
        self.socialHappiness = 0.0
        self.wealthHappiness = 0.0

        self.foodSecurityHappiness = 0.0
        self.lastTtlNoAgeLimit = configuration.get("lastTtlNoAgeLimit", 0.0)

    # need to override this one so it doesn't touch the global environment
    def findWealthHappiness(self):
        wealth = self.sugar + self.spice

        diffWealth = wealth - self.ghostMeanWealth
        diffWealth *= self.happinessUnit
        return math.erf(diffWealth)
    
    def findFoodSecurityHappiness(self):
        postSugar = self.sugar + self.cell.sugar
        postSpice = self.spice + self.cell.spice
        
        sugarTtl = postSugar / self.sugarMetabolism if self.sugarMetabolism > 0 else 1e9
        spiceTtl = postSpice / self.spiceMetabolism if self.spiceMetabolism > 0 else 1e9
        
        currentTtl = min(sugarTtl, spiceTtl)
        diff = currentTtl - self.lastTtlNoAgeLimit
        return math.erf(diff * self.happinessUnit)

    def findSocialHappiness(self):
        friends = self.socialNetwork.get("friends", [])
        if self.maxFriends == 0:
            return 0.0
        friendCount = min(len(friends), self.maxFriends)
        step = 2 / self.maxFriends
        return ((friendCount * step) - 1)* self.happinessUnit
    
    def findFamilyHappiness(self):
        children = self.socialNetwork.get("children", [])
        mates = self.socialNetwork.get("mates", [])
        familyCount = len(children) + len(mates)

        if familyCount == 0:
            return 0.0
        return self.happinessUnit * min(familyCount / 3.0, 1.0)
    
    def findHappiness(self):
        return (self.conflictHappiness + self.familyHappiness 
                + self.healthHappiness + self.socialHappiness 
                + self.wealthHappiness + self.foodSecurityHappiness)
    
class GhostCell:
    def __init__(self, x, y, environment):
        self.x = x
        self.y = y
        self.environment = environment
        self.agent = None
        self.sugar = 0
        self.spice = 0
        self.maxSugar = 0
        self.maxSpice = 0
        self.pollution = 0
        self.neighbors = {}

class GhostScape:
    def __init__(self):
        self.agents = []
        self.runtimeStats = {}
        self.timestep = 0

class GhostEnv:
    def __init__(self, realEnv):
        self.width = realEnv.width
        self.height = realEnv.height
        self.grid = [[None for i in range(self.height)] for j in range(self.width)]
        self.wraparound = realEnv.wraparound
        self.equator = realEnv.equator
        self.maxCombatLoot = realEnv.maxCombatLoot
        self.globalMaxSugar = realEnv.globalMaxSugar
        self.globalMaxSpice = realEnv.globalMaxSpice
        self.neighborhoodMode = realEnv.neighborhoodMode
        self.sugarscape = GhostScape()
        
        # Copy pollution settings
        self.pollutionStart = realEnv.pollutionStart
        self.pollutionEnd = realEnv.pollutionEnd
        self.pollutionDiffusionStart = realEnv.pollutionDiffusionStart
        self.pollutionDiffusionEnd = realEnv.pollutionDiffusionEnd
        self.pollutionDiffusionDelay = realEnv.pollutionDiffusionDelay
        self.spiceConsumptionPollutionFactor = realEnv.spiceConsumptionPollutionFactor
        self.sugarConsumptionPollutionFactor = realEnv.sugarConsumptionPollutionFactor
        self.sugarProductionPollutionFactor = realEnv.sugarProductionPollutionFactor
        self.spiceProductionPollutionFactor = realEnv.spiceProductionPollutionFactor
        self.universalSpiceIncome = realEnv.universalSpiceIncomeInterval
        self.universalSugarIncome = realEnv.universalSugarIncomeInterval

class GhostEvaluator:
    def __init__(self, environment):
        self.realEnvironment = environment
        self.ghostEnv = None
        self.ghostMap = {}
        self.originalCellStats = {}

    # create environment once
    def createGhostEnv(self, timestep):
        realEnv = self.realEnvironment
        width = realEnv.width
        height = realEnv.height

        realStats = realEnv.sugarscape.runtimeStats
        currentMeanWealth = realStats.get("meanWealth", 0)

        class GhostScape:
            def __init__(self):
                self.agents = []
                self.runtimeStats = {"meanWealth": currentMeanWealth}
                self.timestep = timestep
        
        class GhostEnvClass:
            def __init__(self, w, h, scape, realEnv):
                self.width = w
                self.height = h
                self.grid = [[None for _ in range(h)] for _ in range(w)]
                self.sugarscape = scape
                self.wraparound = realEnv.wraparound
                self.equator = realEnv.equator
                self.maxCombatLoot = realEnv.maxCombatLoot
                self.globalMaxSugar = realEnv.globalMaxSugar
                self.globalMaxSpice = realEnv.globalMaxSpice

        ghostScape = GhostScape()
        self.ghostEnv = GhostEnvClass(width, height, ghostScape, realEnv)

        for x in range (realEnv.width):
            for y in range(realEnv.height):
                realCell = realEnv.grid[x][y]

                ghostCell = cell.Cell(x,y,self.ghostEnv)
                ghostCell.maxSugar = realCell.maxSugar
                ghostCell.maxSpice = realCell.maxSpice
                ghostCell.sugar = realCell.sugar
                ghostCell.spice = realCell.spice
                ghostCell.pollution = realCell.pollution
                self.ghostEnv.grid[x][y] = ghostCell

                self.originalCellStats[(x,y)] = {
                    "sugar": realCell.sugar,
                    "spice": realCell.spice
                }

        realAgents = [a for a in self.realEnvironment.sugarscape.agents if a.isAlive()]
        self.ghostAgentMap = {}
        ghostAgents = []
        
        for realAgent in realAgents:
            # calculate target cell
            targetCell = self.ghostEnv.grid[realAgent.cell.x][realAgent.cell.y]

            config = {
                "sugar": realAgent.sugar,
                "spice": realAgent.spice,
                "sugarMetabolism": realAgent.sugarMetabolism,
                "spiceMetabolism": realAgent.spiceMetabolism,
                "movement": realAgent.movement,
                "vision": realAgent.vision,
                "maxAge": realAgent.maxAge,
                "age": realAgent.age,
                "sex": realAgent.sex,
                "tags": realAgent.tags,
                "happinessUnit": getattr(realAgent, "happinessUnit", 1),
                "decisionModel": getattr(realAgent, "decisionModel", "none"),
                "maxFriends": getattr(realAgent, "maxFriends", 0),
                "depressed": getattr(realAgent, "depressed", False),
                "lastTtlNoAgeLimit": getattr(realAgent, "lastTtlNoAgeLimit", 0.0)
            }

            ghostAgent = GhostAgent(realAgent.ID, realAgent.born, targetCell, config, meanWealth=currentMeanWealth)
            ghostAgents.append(ghostAgent)
            self.ghostAgentMap[realAgent.ID] = ghostAgent

        self.ghostEnv.sugarscape.agents = ghostAgents

        # rebuild social networks only if they exist
        for realAgent in realAgents:
            if realAgent.ID not in self.ghostAgentMap:
                continue
            ghostAgent = self.ghostAgentMap[realAgent.ID]

            for friend in realAgent.socialNetwork.get("friends", []):
                realFriend = friend["friend"]

                if realFriend.ID in self.ghostAgentMap:
                    ghostAgent.socialNetwork["friends"].append({
                        "friend": self.ghostAgentMap[realFriend.ID],
                        "hammingDistance": friend["hammingDistance"]
                        })
                    
            # rebuild children and mates relationships if they exist
            for realChild in realAgent.socialNetwork.get("children", []):
                if realChild.ID in self.ghostAgentMap:
                    ghostAgent.socialNetwork["children"].append(self.ghostAgentMap[realChild.ID])

            for realMate in realAgent.socialNetwork.get("mates", []):
                if realMate.ID in self.ghostAgentMap:
                    ghostAgent.socialNetwork["mates"].append(self.ghostAgentMap[realMate.ID])
        return self.ghostEnv
    
    def setPlacement(self, placementById):
        for x in range(self.ghostEnv.width):
            for y in range(self.ghostEnv.height):
                self.ghostEnv.grid[x][y].agent = None

                #reset cell resources to original
                stats = self.originalCellStats.get((x,y), None)
                self.ghostEnv.grid[x][y].sugar = stats["sugar"] if stats else 0
                self.ghostEnv.grid[x][y].spice = stats["spice"] if stats else 0

        for agentId, cell in placementById.items():
            if agentId in self.ghostAgentMap:
                ghostAgent = self.ghostAgentMap[agentId]
                targetCell = self.ghostEnv.grid[cell[0]][cell[1]]
                ghostAgent.cell = targetCell
                targetCell.agent = ghostAgent

    def evaluatePlacement(self):
        for ghostAgent in self.ghostEnv.sugarscape.agents:
            ghostAgent.familyHappiness = ghostAgent.findFamilyHappiness()
            ghostAgent.socialHappiness = ghostAgent.findSocialHappiness()
            ghostAgent.wealthHappiness = ghostAgent.findWealthHappiness()
            ghostAgent.foodSecurityHappiness = ghostAgent.findFoodSecurityHappiness()
            ghostAgent.happiness = ghostAgent.findHappiness()

        total = 0.0
        for a in self.ghostEnv.sugarscape.agents:
            total += float(a.happiness)

        return total

    def aggregateHappiness(self):
        # sum per-agent happiness fields
        total = 0.0
        for a in self.ghostEnv.sugarscape.agents:
            if hasattr(a, "happiness"):
                total += float(a.happiness)
        return total
    
    def evaluateOneStep(self, timestep, placementById):
        self.createGhostEnv(timestep)
        self.setPlacement(placementById)
        return self.evaluatePlacement()

class Leader(agent.Agent):
    def __init__(self, agentID, birthday, cell, configuration):
        super().__init__(agentID, birthday, cell, configuration)
        # Special leader agent should be configured to be immortal and omniscient
        self.fertilityFactor = 0.0
        self.follower = False
        self.agentPlacements = {}
        self.leader = True
        self.maxAge = -1
        self.movement = 0
        self.recursionLimit = 100000
        self.spice = sys.maxsize
        self.spiceMetabolism = 0
        self.sugar = sys.maxsize
        self.sugarMetabolism = 0
        self.tradeFactor = 0.0
        self.vision = max(self.cell.environment.height, self.cell.environment.width)

        self.plannedTimestep = None
        self.environment = self.cell.environment
        self.lastDecisionTime = 0.0
        self.lastPlacementOptions = 0

    def isAlive(self):
        return self.alive

    def doAging(self):
        agents = self.cell.environment.sugarscape.agents
        # Consider being the last one left alive as an aging death for the leader
        if len(agents) == 1 and agents[0] == self:
            self.doDeath("aging")
        return
    
    def doDeath(self, cause):
        self.alive = False

    # bypassing base agent lifecycle so leader only plans placements then exits
    def doTimestep(self, timestep):
        # Leader should not perform normal agent actions
        if self.plannedTimestep != timestep:
            self.planPlacements(timestep)

        # Mark moved so base code doesn't try again
        self.lastMovedTimestep = timestep
        return

    def findBestCell(self, predeterminedBestCell=None):
        self.resetForTimestep()
        defaultRecursionLimit = sys.getrecursionlimit()
        sys.setrecursionlimit(self.recursionLimit)
        agents = [agent for agent in copy.deepcopy(self.cell.environment.sugarscape.agents) if agent.isAlive() == True]

        # Use a list of counters to iterate through the search space one possible placement at a time
        cellRanges = []
        counters = []
        for agent in agents:
            cellsInRange = list(agent.cellsInRange.keys()) if len(agent.cellsInRange) > 0 else [agent.cell]
            cellRanges.append(len(cellsInRange) - 1)
            counters.append(0)

        attempts = 0
        maxAttempts = sys.maxsize
        bestPlacement = {}
        bestScore = (-1 * sys.maxsize) - 1

        # Ensure each simulated timestep uses the same random numbers
        randomNumberReset = random.getstate()
        searchSpaceExhausted = False
        while attempts < maxAttempts and searchSpaceExhausted == False:
            possiblePlacement = {"placement": {}, "score": 0}
            futurescape = copy.deepcopy(self.cell.environment.sugarscape)
            random.setstate(randomNumberReset)

            counterIndex = -1
            for agent in agents:
                # If agent is not in the copied environment, skip its consideration
                agent = next(a for a in futurescape.agents if a.ID == agent.ID)
                if agent == None:
                    continue
                counterIndex += 1
                if agent.isAlive() == False:
                    continue
                agentPremoveIndex = counters[counterIndex]
                cellsInRange = list(agent.cellsInRange.keys()) if len(agent.cellsInRange) > 0 else [agent.cell]
                premove = cellsInRange[agentPremoveIndex]
                agent.doTimestep(futurescape.timestep, premove)
                currCell = agent.cell
                if currCell == None:
                    continue
                possiblePlacement["placement"][agent.ID] = self.cell.environment.findCell(agent.cell.x, agent.cell.y)
            futurescape.updateRuntimeStats()
            possiblePlacement["score"] = futurescape.runtimeStats["meanHappiness"]
            if possiblePlacement["score"] > bestScore:
                bestScore = possiblePlacement["score"]
                bestPlacement = possiblePlacement["placement"]

            #Update counter indices
            carry = 1
            for i in range(-1, -1 * (len(counters) + 1), -1):
                if carry > 0:
                    counters[i] += carry
                    carry = 0
                if counters[i] > cellRanges[i]:
                    counters[i] = 0
                    carry = 1
            # If there is a carry out on the last counter, all placements in the search space have been considered
            if carry == 1 and counters[0] == 0:
                searchSpaceExhausted = True
            attempts += 1

        self.agentPlacements = bestPlacement
        random.setstate(randomNumberReset)
        sys.setrecursionlimit(defaultRecursionLimit)

        # Leader agent should not move
        return self.cell

    def findBestCellForAgent(self, agent):
        timestep = self.environment.sugarscape.timestep
        if self.plannedTimestep != timestep:
            self.planPlacements(timestep)
        return self.agentPlacements.get(agent.ID, agent.cell)
    
    def moveToBestCell(self):
        # Leader does not move it only plans placements
        env = self.cell.environment if self.cell is not None else self.environment

        timestep = env.sugarscape.timestep

        if self.plannedTimestep != timestep:
            self.planPlacements(timestep)
        # Mark as moved so Agent.doTimestep doesn't rerun movement logic
        self.lastMovedTimestep = timestep
        return
    
    def findUrgencyForAgent(self, agent):
        diseased = 0 if agent.isSick() else 1
        timeToLive = agent.findTimeToLive()
        metabolism = -(agent.sugarMetabolism + agent.spiceMetabolism)
        # Lower score yields higher urgency
        return (timeToLive, diseased, metabolism)
    
    def findNextMove(self,agent,cell):
        postSpice = agent.spice + cell.spice - agent.findSpiceMetabolism()
        postSugar = agent.sugar + cell.sugar - agent.findSugarMetabolism()
        return (postSpice, postSugar)

    def findViableCellsForAgent(self, agent, minTtl=1.1):
        # viability should be "can i plausibly live after this move"
        # using ttl is better than a fixed multistep buffer because metabolism varies a lot

        agent.findCellsInRange()
        viable = []

        for cell in agent.cellsInRange.keys():
            # disallow moving into occupied cells (avoids combat + sequential move weirdness)
            if cell.isOccupied() and cell != agent.cell:
                continue

            ttl = self.ttlAfterMove(agent, cell)

            # ttlAfterMove already implies postSpice/postSugar > 0 unless metabolism is 0,
            # but keep the ttl guard as the consistent rule
            if ttl < minTtl:
                continue

            viable.append(cell)

        return viable

    def resetForTimestep(self, timestep):
        # Always ensure leader has maximum resources each timestep
        self.spice = sys.maxsize
        self.sugar = sys.maxsize

        #self.grid[self.cell.x][self.cell.y] = self
        self.agentPlacements = {self.ID: self.cell}
        self.plannedTimestep = timestep

    def predictedWealthAfterMove(self, agent, cell):
        # base wealth
        sugar = agent.sugar
        spice = agent.spice

        # combat?
        sugarLoot = 0
        spiceLoot = 0
        if agent.findAggression() > 0 and cell.agent is not None and cell.agent != agent:
            prey = cell.agent
            # same logic as Agent.doCombat (loot capped)
            maxLoot = agent.cell.environment.maxCombatLoot
            sugarLoot = min(maxLoot, prey.sugar)
            spiceLoot = min(maxLoot, prey.spice)

        # collect cell resources (headless uses current cell.sugar/spice)
        sugar += cell.sugar + sugarLoot
        spice += cell.spice + spiceLoot

        # pay metabolism (same as doMetabolism)
        sugar -= agent.findSugarMetabolism()
        spice -= agent.findSpiceMetabolism()

        return sugar, spice
    
    # similar to findConflictHappiness but whether it will happen after move
    def predictedConflictHappiness(self, agent, cell):
        willCombat = (agent.findAggression() > 0 and cell.agent is not None and cell.agent != agent)
        if not willCombat:
            return 0
        return agent.happinessUnit if agent.findAggression() > 1 else -agent.happinessUnit
    
    def predictedWealthHappiness(self, agent, cell):
        sugar, spice = self.predictedWealthAfterMove(agent, cell)
        wealth = sugar + spice
        meanWealth = agent.cell.environment.sugarscape.runtimeStats.get("meanWealth", 0)
        diff = (wealth - meanWealth) * agent.happinessUnit
        return math.erf(diff)
    
    def predictedSocialHappinessProxy(self, agent, cell):
        neighbors = self.findNeighbors(cell)
        if len(neighbors) == 0:
            return -agent.happinessUnit
        elif len(neighbors) <= agent.maxFriends:
            return agent.happinessUnit * (len(neighbors) / agent.maxFriends)
        else:
            return agent.happinessUnit
    
    def predictedHappiness(self, agent, cell, placementByCell=None):
        family = agent.familyHappiness
        health = agent.healthHappiness
        conflict = self.predictedConflictHappiness(agent, cell)
        wealth = self.predictedWealthHappiness(agent, cell)
        foodSecurity = self.predictedFoodSecurityHappiness(agent, cell)

        if placementByCell is None:
            social = self.predictedSocialHappinessProxy(agent, cell)
        else:
            social = self.predictedSocialFromPlacements(agent, cell, placementByCell)

        return conflict + family + health + social + wealth + foodSecurity
    
    def predictedHappinessNoSocial(self, agent, cell):
        family = agent.familyHappiness
        health = agent.healthHappiness
        conflict = self.predictedConflictHappiness(agent, cell)
        wealth = self.predictedWealthHappiness(agent, cell)
        foodSecurity = self.predictedFoodSecurityHappiness(agent, cell)

        return conflict + family + health + wealth + foodSecurity
    
    def predictedFoodSecurityHappiness(self, agent, cell):
        # current TTL
        currentTtl = agent.findTimeToLive(False)
        # what TTL will be if they move to the new cell
        futureTtl = self.ttlAfterMove(agent, cell)
        
        # change in TTL from last timestep to this hypothetical timestep
        diff = futureTtl - currentTtl
        return math.erf(diff * agent.happinessUnit)
    
    def predictedUtility(self, agent, cell, placementByCell=None):
        return self.predictedHappiness(agent, cell, placementByCell)
    
    def placementScore(self, agents):
        total = 0.0
        for a in agents:
            c = self.agentPlacements.get(a.ID, a.cell)
            total += self.predictedHappiness(a, c)
        return total

    def findNeighbors(self, cell):
        nbrs = cell.neighbors.values() if isinstance(cell.neighbors, dict) else cell.neighbors
        return [n for n in nbrs if n is not None]
    
    # make sure none of the agents can attack the leader
    def isNeighborValidPrey(self, other):
        return False
    
    def ttlAfterMove(self, agent, cell):
        postSpice, postSugar = self.findNextMove(agent, cell)
        spiceTTL = postSpice / agent.findSpiceMetabolism() if agent.findSpiceMetabolism() > 0 else 1e9
        sugarTTL = postSugar / agent.findSugarMetabolism() if agent.findSugarMetabolism() > 0 else 1e9
        return min(spiceTTL, sugarTTL)
    
    def willCombat(self, attacker, targetCell):
        if targetCell.agent is None:
            return False
        prey = targetCell.agent
        if prey == attacker:
            return False
        return attacker.findAggression() > 0 and attacker.isNeighborValidPrey(prey)

    def placementByCellFromCurrentPlan(self, agents):
        placementByCell = {}
        for a in agents:
            c = self.agentPlacements.get(a.ID, a.cell)
            placementByCell[c] = a
        return placementByCell
    
    def cellKey(self, cell):
        return (cell.x, cell.y)

    def cellFromKey(self, environment, key):
        x, y = key
        return environment.grid[x][y]

    def findAffectedAgents(self, cells, placementByCell):
        affected = set()
        for cell in cells:
            # agent in the cell
            a = placementByCell.get(cell)
            if a is not None:
                affected.add(a)
            # agents in neighboring cells
            for n in self.findNeighbors(cell):
                b = placementByCell.get(n)
                if b is not None:
                    affected.add(b)
        return affected

    def findTotalHappiness(self, agentSet, placementByCell):
        total = 0.0
        for a in agentSet:
            c = self.agentPlacements.get(a.ID, a.cell)
            total += self.predictedUtility(a, c, placementByCell)
        return total
    

    def planPlacements(self, timestep):
        self.resetForTimestep(timestep)
        env = self.environment
        agents = [a for a in env.sugarscape.agents if a.isAlive() and a != self]

        bestAssign, bestScore = self.bruteforcePlacementsGhost(agents, timestep)

        for a in agents:
            cell = bestAssign.get(a.ID, a.cell)
            if cell is None:
                cell = a.cell
            self.agentPlacements[a.ID] = cell

    def bruteforcePlacements(self, agents, timestep):
        decisionStart = time.perf_counter() # Start the timer
        optionsEvaluated = 0
        bestIndex = -1

        print(f"\n\nTIMESTEP: {timestep}")
        print(f"Number of agents: {len(agents)}")

        if not agents:
            self.lastDecisionTime = time.perf_counter() - decisionStart
            self.lastPlacementOptions = 0
            print("No agents to place")
            return {}, 0.0

        # valid cells per agent
        domains = {}
        for a in agents:
            a.findCellsInRange()
            opts = []
            for c in a.cellsInRange.keys():
                # only allow empty targets (except staying put)
                if c != a.cell and c.isOccupied():
                    continue
                opts.append((c.x, c.y))

            if not opts:
                opts = [(a.cell.x, a.cell.y)]
            domains[a.ID] = opts

        # order agents by smallest domain first
        ordered = sorted(agents, key=lambda a: len(domains[a.ID]))
        n = len(ordered)

        print(f"Domain sizes per agent:")
        estimatedPlacements = 1
        for a in ordered:
            print(f"  Agent {a.ID}: {len(domains[a.ID])} options")
            estimatedPlacements *= len(domains[a.ID])

        print(f"Estimated placements to evaluate: {estimatedPlacements:,}")
        
        if n == 0:
            self.lastDecisionTime = time.perf_counter() - decisionStart
            self.lastPlacementOptions = 0
            return {}, 0.0
        
        placements = []
        stack = [(0, 0, {}, set())]

        self.ghostEval.createGhostEnv(timestep)
        bestScore = float('-inf')
        bestAssignKeys = {}

        barLength = 40
        lastPrintTime = decisionStart
        updateInterval = 0.5

        stack = [(0, 0, {}, set())]

        while stack:
            idx, optIdx, placement, usedCells = stack.pop()

            if idx == n:
                optionsEvaluated += 1
                currentTime = time.perf_counter()
                if currentTime - lastPrintTime >= updateInterval:
                    elapsed = currentTime - decisionStart
                    rate = optionsEvaluated / elapsed if elapsed > 0 else 0
                    print(f"\rEvaluated: {optionsEvaluated:,} placements | {rate:,.0f}/sec | Best: {bestScore:.4f}   ", end="", flush=True)
                    lastPrintTime = currentTime

                self.ghostEval.setPlacement(placement)
                score = self.ghostEval.evaluatePlacement()

                if score > bestScore:
                    bestScore = score
                    bestAssignKeys = dict(placement)
                    bestIndex = optionsEvaluated
                continue

            a = ordered[idx]
            options = domains[a.ID]

            while optIdx < len(options):
                key = options[optIdx]
                optIdx += 1
                if key in usedCells:
                    continue
                
                newPlacement = dict(placement)
                newPlacement[a.ID] = key
                newUsedCells = usedCells | {key}

                if optIdx < len(options):
                    stack.append((idx, optIdx, placement, usedCells))

                stack.append((idx + 1, 0, newPlacement, newUsedCells))
                break

        print(f"\rEvaluated: {optionsEvaluated:,} placements | Done!{' ' * 40}")

        # convert best assignment back to real cells
        bestAssignCells = {}
        for agentId, key in bestAssignKeys.items():
            x, y = key
            bestAssignCells[agentId] = self.environment.grid[x][y]

        if not bestAssignCells:
            for a in agents:
                bestAssignCells[a.ID] = a.cell

        self.lastDecisionTime = time.perf_counter() - decisionStart
        self.lastPlacementOptions = optionsEvaluated

        print(f"DECISION SUMMARY - Timestep {timestep}")
        print(f"Options evaluated: {optionsEvaluated}")
        print(f"Best option: #{bestIndex}")
        print(f"Best score: {bestScore:.4f}")
        print(f"Decision time: {self.lastDecisionTime:.4f} seconds")
        print(f"Best placements:")
        for agentId, cell in bestAssignCells.items():
            print(f"  Agent {agentId} -> ({cell.x}, {cell.y})")

        return bestAssignCells, bestScore


class Temperance(agent.Agent):
    def __init__(self, agentID, birthday, cell, configuration, pecs=False):
        super().__init__(agentID, birthday, cell, configuration)
        self.totalMetabolism = self.findSugarMetabolism() + self.findSpiceMetabolism()
        self.rules = {"agentConsumedAdequateResources": 0,
                      "agentConsumedAmpleResources": 0,
                      "communityDisapprovalOfAmpleResourceConsumption":  0,
                      "agentOverconsumedResources": 0,
                      "communityDisdainOfExtremeOverconsumption": 0
                      }
        self.timeSeenOverconsuming = 0
        self.timesSeenIndulging = 0
        self.timesOverharvested = 0
        self.lastSelectedCellWealthToNeedRatio = 0
        self.socialPressure = 0
        self.lastDeltaTimeToLive = 0
        self.pecs = pecs

    def findBestEthicalCell(self, cells, greedyBestCell=None):
        if len(cells) == 0:
            return None
        bestCell = None
        if "all" in self.debug or "agent" in self.debug:
            self.printCellScores(cells)

        for cell in cells:
            cell["wealth"] = self.findEthicalValueOfCell(cell["cell"])
        cells = self.sortCellsByWealth(cells)
        if self.pecs == True:
            bestCell = cells[0]["cell"]
        else:
            bestCell = self.findSimpleTemperanceBestEthicalCell(cells)

        if bestCell == None:
            if greedyBestCell == None:
                bestCell = cells[0]["cell"]
            else:
                bestCell = greedyBestCell
            if "all" in self.debug or "agent" in self.debug:
                print(f"Agent {self.ID} could not find an ethical cell")
        return bestCell

    def findCellCognitiveScore(self, cell):
        deltaTimeToLive = self.findTimeToLive(potentialCell=cell) - self.timeToLive
        score = 0
        if deltaTimeToLive < 1:
            return -1
        elif deltaTimeToLive >= 1 and deltaTimeToLive < 2 and self.rules['agentConsumedAdequateResources']:
            score += self.rules["agentConsumedAdequateResources"]
        elif deltaTimeToLive >= 2 and deltaTimeToLive < 3 and self.rules["agentConsumedAmpleResources"]:
            score += self.rules["agentConsumedAmpleResources"]
            if self.rules["communityDisapprovalOfAmpleResourceConsumption"]:
                score -= self.rules["communityDisapprovalOfAmpleResourceConsumption"]
        elif deltaTimeToLive >= 3 and self.rules["agentOverconsumedResources"]:
            score -= self.rules["agentOverconsumedResources"]
            if self.rules["communityDisdainOfExtremeOverconsumption"]:
                score -= self.rules["communityDisdainOfExtremeOverconsumption"]
        return math.erf(score)

    def findCellEmotionalScore(self, cell):
        deltaTimeToLive = self.findTimeToLive(potentialCell=cell) - self.timeToLive
        score = 0
        if deltaTimeToLive > 1:
            score = score - self.timesOverharvested
            self.timesOverharvested += 1
        return math.erf(score)

    def findCellPhysicalScore(self):
        return math.erf(1 / self.timeToLive) if self.timeToLive > 0 else 1

    def findCellSimpleScore(self, cell):
        return abs(self.findTimeToLive(potentialCell=cell) - self.timeToLive)

    def findCellSocialScore(self, cell):
        deltaTimeToLive = self.findTimeToLive(potentialCell=cell) - self.timeToLive
        score = 0
        if deltaTimeToLive <= 1:
            score = 1
        elif deltaTimeToLive > 1 and deltaTimeToLive <= 2:
            score -= self.timeSeenOverconsuming
        elif deltaTimeToLive > 2:
            score -= self.timesSeenIndulging
        score *= self.socialPressure
        return math.erf(score)

    def findEthicalValueOfCell(self, cell):
        score = self.findCellSimpleScore(cell)
        if self.pecs == True:
            if self.totalMetabolism == 0:
                return 0
            physicalScore = self.findCellPhysicalScore()
            emotionalScore = self.findCellEmotionalScore(cell)
            cognitiveScore = self.findCellCognitiveScore(cell)
            socialScore = self.findCellSocialScore(cell)
            score = physicalScore + emotionalScore + cognitiveScore + socialScore
            # TODO: Improve fidelity to temperance as it relates to agent lives
            #print(f"Agent {self.ID} -> ({cell.x},{cell.y}): {score} = {physicalScore} + {emotionalScore} + {cognitiveScore} + {socialScore}")
        return score

    def findSimpleTemperanceBestEthicalCell(self, cells):
        bestCell = None
        numCells = len(cells)
        midpoint = math.floor(numCells / 2)
        virtueRoll = random.random()
        if virtueRoll < self.decisionModelFactor:
            bestCell = cells[0]["cell"]
            newTemperanceFactor = round(self.decisionModelFactor + self.dynamicDecisionModelFactor, 2)
            self.decisionModelFactor = newTemperanceFactor if newTemperanceFactor <= 1 else 1
        else:
            bestCell = cells[-1]["cell"]
            newTemperanceFactor = round(self.decisionModelFactor - self.dynamicDecisionModelFactor, 2)
            self.decisionModelFactor = newTemperanceFactor if newTemperanceFactor >= 0 else 0
        return bestCell

    def updateAgentSocialPressureAfterConsumption(self):
        if self.cell is None:
            return
        neighbors = len(self.findNeighborhood(self.cell))
        if neighbors == 0:
            return 0
        else:
            self.socialPressure += self.dynamicSocialPressureFactor
            return self.socialPressure

    def updateAgentTemperanceRules(self):
        neighbors = len(self.findNeighborhood(self.cell))
        if self.lastDeltaTimeToLive <= 1:
            # Consuming up to 1x metabolic need is good for the agent
            self.rules["agentConsumedAdequateResources"] += 1
        elif self.lastDeltaTimeToLive > 1 and self.lastDeltaTimeToLive <= 2:
            # Consuming 1-2x metabolic is is great for the agent
            self.rules["agentConsumedAmpleResources"] += 1
            # Consuming 1-2x metabolic need is overconsumption and is bad for the community
            if neighbors > 0:
                self.timeSeenOverconsuming += 1
                self.rules["communityDisapprovalOfAmpleResourceConsumption"] += 1
        elif self.lastDeltaTimeToLive > 2:
            # Consuming more than 2x metabolic need is bad for both the agent and the community
            self.rules["agentOverconsumedResources"] += 1
            if neighbors > 0:
                self.timesSeenIndulging += 1 
                self.rules["communityDisdainOfExtremeOverconsumption"] += 1

    def collectResourcesAtCell(self):
        self.lastDeltaTimeToLive = self.findTimeToLive(potentialCell=self.cell) - self.timeToLive
        super().collectResourcesAtCell()

    def doMetabolism(self):
        self.updateAgentSocialPressureAfterConsumption()
        super().doMetabolism()

    def updateValues(self):
        super().updateValues()
        self.updateAgentTemperanceRules()

    def spawnChild(self, childID, birthday, cell, configuration):
        return Temperance(childID, birthday, cell, configuration)