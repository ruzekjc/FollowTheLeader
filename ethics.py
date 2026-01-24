import math
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
        self.environment = self.cell.environment
        self.maxSwaps = 100
        # how many agent pairs to try
        self.swap_sample = 30

    def doAging(self):
        agents = self.cell.environment.sugarscape.agents
        # Consider being the last one left alive as an aging death for the leader
        if len(agents) == 1 and agents[0] == self:
            self.doDeath("aging")
        return

    # bypassing base agent lifecycle so leader only plans placements then exits
    def doTimestep(self, timestep):
        # Leader should not perform normal agent actions
        if self.plannedTimestep != timestep:
            self.planPlacements(timestep)

        # Mark moved so base code doesn't try again
        self.lastMovedTimestep = timestep
        return

    def findBestCell(self):
        timestep = self.environment.sugarscape.timestep
        if self.plannedTimestep != timestep:
            self.planPlacements(timestep)
        return self.cell   # leader stays put

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
        # using ttl is better than a fixed multi-step buffer because metabolism varies a lot

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

    # mirrors part of doTimestep() logic
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
    
    def predictedHappiness(self, agent, cell, placementByCell=None):
        family = agent.familyHappiness
        health = agent.healthHappiness
        conflict = self.predictedConflictHappiness(agent, cell)
        wealth = self.predictedWealthHappiness(agent, cell)

        if placementByCell is None:
            social = self.predictedSocialHappinessProxy(agent, cell)
        else:
            social = self.predictedSocialFromPlacements(agent, cell, placementByCell)

        return conflict + family + health + social + wealth
    
    def predictedHappinessNoSocial(self, agent, cell):
        family = agent.familyHappiness
        health = agent.healthHappiness
        conflict = self.predictedConflictHappiness(agent, cell)
        wealth = self.predictedWealthHappiness(agent, cell)

        return conflict + family + health + wealth
    
    def predictedUtility(self, agent, cell, placementByCell=None):
        h = self.predictedHappiness(agent, cell, placementByCell)
        ttl = self.ttlAfterMove(agent, cell)

        if ttl < 1.0:
            return -1e9

        # change later
        if ttl < 2.0:
            h -= 200.0
        elif ttl < 3.0:
            h -= 50.0
        elif ttl < 4.0:
            h -= 10.0

        return h
    
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

    def deathPenalty(self):
        # will change later
        # higher means leader avoids killing unless it prevents a death
        return 500.0

    def placementByCellFromCurrentPlan(self, agents):
        placementByCell = {}
        for a in agents:
            c = self.agentPlacements.get(a.ID, a.cell)
            placementByCell[c] = a
        return placementByCell


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

        bestAssign, bestScore = self.bruteforcePlacements(agents)

        for a in agents:
            self.agentPlacements[a.ID] = bestAssign.get(a.ID, a.cell)

    def bruteforcePlacements(self, agents, minTtl=1.0):
        # valid cells per agent
        domains = {}
        for a in agents:
            a.findCellsInRange()
            opts = []
            for c in a.cellsInRange.keys():
                # only allow empty targets (except staying put)
                if c != a.cell and c.isOccupied():
                    continue
                if self.ttlAfterMove(a, c) < minTtl:
                    continue
                opts.append(c)

            if not opts:
                opts = [a.cell]
            domains[a.ID] = opts

        # order agents by smallest domain first
        ordered = sorted(agents, key=lambda a: len(domains[a.ID]))

        # Cache neighbors for speed
        cache = {}
        for a in ordered:
            for c in domains[a.ID]:
                if c not in cache:
                    nbrs = c.neighbors.values() if isinstance(c.neighbors, dict) else c.neighbors
                    cache[c] = [n for n in nbrs if n is not None]

        def countSocial(agentObj, count):
            if agentObj.maxFriends == 0:
                return 0.0
            friendsProxy = min(count, agentObj.maxFriends)
            step = 2 / agentObj.maxFriends
            return ((friendsProxy * step) - 1) * agentObj.happinessUnit

        # Precompute base (nonsocial) score per agent+cell
        base = {}
        for a in ordered:
            amap = {}
            for c in domains[a.ID]:
                amap[c] = self.predictedHappinessNoSocial(a, c)
            base[a.ID] = amap

        # per agent, best possible base + max social
        bestPossible = {}
        for a in ordered:
            maxSocial = countSocial(a, a.maxFriends)
            bestBase = max(base[a.ID][c] for c in domains[a.ID])
            bestPossible[a.ID] = bestBase + maxSocial

        suffixBound = [0.0] * (len(ordered) + 1)
        for i in range(len(ordered) - 1, -1, -1):
            suffixBound[i] = suffixBound[i + 1] + bestPossible[ordered[i].ID]

        bestScore = float("-inf")
        bestAssign = {}

        usedCells = set()
        assign = {}
        placementByCell = {}
        adjCount = {}
        currentScore = 0.0

        # Sort each domain by goodness to find good solutions early
        sortedDomains = {}
        for a in ordered:
            sortedDomains[a.ID] = sorted(domains[a.ID], key=lambda c: base[a.ID][c], reverse=True)

        def place(a, c):
            nonlocal currentScore
            usedCells.add(c)
            assign[a.ID] = c
            placementByCell[c] = a

            # Count adjacent placed agents
            neighbors = cache.get(c, [])
            adjAgents = []
            cnt = 0
            for nc in neighbors:
                b = placementByCell.get(nc)
                if b is not None:
                    adjAgents.append(b)
                    cnt += 1

            adjCount[a.ID] = cnt
            currentScore += base[a.ID][c] + countSocial(a, cnt)

            # update each neighbor agent's social (their adjacency increased by 1)
            for b in adjAgents:
                old = adjCount[b.ID]
                new = old + 1
                adjCount[b.ID] = new
                currentScore += countSocial(b, new) - countSocial(b, old)

            # needed for undo
            return adjAgents

        def unplace(a, c, adjAgents):
            nonlocal currentScore

            # undo neighbor social increments
            for b in adjAgents:
                old = adjCount[b.ID]
                new = old - 1
                adjCount[b.ID] = new
                currentScore += countSocial(b, new) - countSocial(b, old)

            # undo placed agent contribution
            cnt = adjCount[a.ID]
            currentScore -= base[a.ID][c] + countSocial(a, cnt)
            adjCount.pop(a.ID, None)

            placementByCell.pop(c, None)
            assign.pop(a.ID, None)
            usedCells.remove(c)


        n = len(ordered)

        # stack frames
        stack = [("try", 0, 0)]

        # store per depth
        placedCell = [None] * n
        placedAdj = [None] * n

        while stack:
            kind, i, j = stack.pop()

            if kind == "undo":
                a = ordered[i]
                c = placedCell[i]
                adjAgents = placedAdj[i]
                if c is not None:
                    unplace(a, c, adjAgents)
                    placedCell[i] = None
                    placedAdj[i] = None
                continue

            # kind == "try"
            # Bound check
            if currentScore + suffixBound[i] <= bestScore:
                continue

            # Finished assignment
            if i == n:
                if currentScore > bestScore:
                    bestScore = currentScore
                    bestAssign = dict(assign)
                continue

            a = ordered[i]
            options = sortedDomains[a.ID]

            # Exhausted options at this depth
            if j >= len(options):
                continue

            # Schedule trying the next option at this depth later
            stack.append(("try", i, j + 1))

            c = options[j]
            if c in usedCells:
                continue

            # Place and go deeper
            adjAgents = place(a, c)
            placedCell[i] = c
            placedAdj[i] = adjAgents

            # Schedule undo after exploring deeper
            stack.append(("undo", i, None))

            # Go deeper
            stack.append(("try", i + 1, 0))

        # def dfs(i):
        #   recursive dfs for later maybe
        #     nonlocal bestScore, bestAssign
        #     if currentScore + suffixBound[i] <= bestScore:
        #         return

        #     if i == len(ordered):
        #         if currentScore > bestScore:
        #             bestScore = currentScore
        #             bestAssign = dict(assign)
        #         return

        #     a = ordered[i]
        #     for c in sortedDomains[a.ID]:
        #         if c in usedCells:
        #             continue
        #         adjAgents = place(a, c)
        #         dfs(i + 1)
        #         unplace(a, c, adjAgents)
        return bestAssign, bestScore

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