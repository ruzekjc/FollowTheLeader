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

    def moveAgentsToCells(self):
        timestep = self.cell.environment.sugarscape.timestep
        self.resetForTimestep(timestep)
        env = self.cell.environment
        agents = env.sugarscape.agents

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

    def gotoCell(self, cell):
        # just a safety helper so the leader never changes cells
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
    
    def predictedSocialHappinessProxy(self, agent, cell):
        # count alive neighbors if agent were at cell
        neighbors = cell.neighbors.values() if isinstance(cell.neighbors, dict) else cell.neighbors
        alive = 0
        for n in neighbors:
            if n is None: 
                continue
            if getattr(n, "agent", None) is not None and n.agent.isAlive():
                alive += 1

        if agent.maxFriends == 0:
            return 0

        # map neighbor count to same shape as findSocialHappiness:
        #    socialHappiness = (len(friends)*step) - 1, step=2/maxFriends, then * happinessUnit
        #    Use min(alive, maxFriends) as a proxy for potential friends
        friendsProxy = min(alive, agent.maxFriends)
        step = 2 / agent.maxFriends
        return ((friendsProxy * step) - 1) * agent.happinessUnit
    
    def predictedSocialFromPlacements(self, agent, cell, placementByCell):
        # how many agents will be adjacent *after* placements
        neighbors = cell.neighbors.values() if isinstance(cell.neighbors, dict) else cell.neighbors
        aliveAdj = 0
        for ncell in neighbors:
            if ncell is None:
                continue
            if ncell in placementByCell:
                aliveAdj += 1

        if agent.maxFriends == 0:
            return 0

        friendsProxy = min(aliveAdj, agent.maxFriends)
        step = 2 / agent.maxFriends
        return ((friendsProxy * step) - 1) * agent.happinessUnit
    
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

        # Survival / fragility penalty encoded as utility (still one objective)
        ttl = self.ttlAfterMove(agent, cell)

        # essentially dying right after move -> prohibit
        if ttl < 1.0:
            return -1e9

        # soft penalties for fragile states
        # change these later, just starting big so extinctions disappear
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

    def improvePlacementsBySwaps(self, agents, placementByCell, maxSwaps=200, sampleSize=40):
        if len(agents) < 2:
            return

        # ensure reachability caches exist
        viableCache = {}
        for a in agents:
            viableCache[a.ID] = set(self.findViableCellsForAgent(a, minTtl=1.1))

        for r in range(maxSwaps):
            pool = agents if len(agents) <= sampleSize else random.sample(agents, sampleSize)
            a1, a2 = random.sample(pool, 2)

            c1 = self.agentPlacements.get(a1.ID, a1.cell)
            c2 = self.agentPlacements.get(a2.ID, a2.cell)
            if c1 == c2:
                continue

            # must be reachable
            if c2 not in a1.cellsInRange or c1 not in a2.cellsInRange:
                continue

            if c2 not in viableCache[a1.ID]:
                continue
            if c1 not in viableCache[a2.ID]:
                continue

            # compute affected set before swap
            affectedCells = {c1, c2}
            affectedCells.update(self.findNeighbors(c1))
            affectedCells.update(self.findNeighbors(c2))
            affectedAgents = self.findAffectedAgents(affectedCells, placementByCell)

            oldTotal = self.findTotalHappiness(affectedAgents, placementByCell)

            # apply swap in placements
            self.agentPlacements[a1.ID], self.agentPlacements[a2.ID] = c2, c1

            # update placementByCell for swapped cells
            placementByCell.pop(c1, None)
            placementByCell.pop(c2, None)
            placementByCell[c2] = a1
            placementByCell[c1] = a2

            newTotal = self.findTotalHappiness(affectedAgents, placementByCell)

            # keep swap only if it improves local aggregate happiness
            if newTotal <= oldTotal:
                # revert
                self.agentPlacements[a1.ID], self.agentPlacements[a2.ID] = c1, c2
                placementByCell.pop(c1, None)
                placementByCell.pop(c2, None)
                placementByCell[c1] = a1
                placementByCell[c2] = a2

    def rescueDoomedAggressors(self, agents, placementByCell, doomedTtl=1.2):
        # allow combat only if it improves aggregate objective
        doomed = []
        for a in agents:
            if a.findAggression() <= 0:
                continue
            ttl = self.agentTtlAtPlannedCell(a)
            if ttl < doomedTtl:
                doomed.append(a)

        if not doomed:
            return

        for a in doomed:
            a.findCellsInRange()

            bestDelta = 0.0
            bestCell = None
            bestPrey = None

            aOldCell = self.agentPlacements.get(a.ID, a.cell)
            aOldScore = self.predictedAggregateForAgentAtCell(a, aOldCell, placementByCell)

            for c in a.cellsInRange.keys():
                if c.agent is None:
                    continue
                if c.agent == a:
                    continue
                if not self.willCombat(a, c):
                    continue

                prey = c.agent
                preyOldCell = self.agentPlacements.get(prey.ID, prey.cell)

                # compute local delta (attacker + prey) for this possible attack move
                preyOldScore = self.predictedAggregateForAgentAtCell(prey, preyOldCell, placementByCell)

                aNewScore = self.predictedAggregateForAgentAtCell(a, c, placementByCell)

                # treat prey death as large negative
                preyNewScore = -self.deathPenalty()

                delta = (aNewScore + preyNewScore) - (aOldScore + preyOldScore)

                if delta > bestDelta:
                    bestDelta = delta
                    bestCell = c
                    bestPrey = prey

            # apply only if it improves aggregate objective
            if bestCell is not None and bestDelta > 0.0:
                # move attacker into prey cell and remove prey from plan
                placementByCell.pop(aOldCell, None)

                self.agentPlacements[a.ID] = bestCell
                placementByCell[bestCell] = a

                if bestPrey is not None:
                    self.removeFromPlan(bestPrey, placementByCell)

    def findNeighbors(self, cell):
        nbrs = cell.neighbors.values() if isinstance(cell.neighbors, dict) else cell.neighbors
        return [n for n in nbrs if n is not None]
    
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

    def predictedAggregateForAgentAtCell(self, agent, cell, placementByCell):
        # this keeps your aggregate happiness goal
        return self.predictedHappiness(agent, cell, placementByCell)

        # if you want to use your utility objective instead, replace with:
        # return self.predictedUtility(agent, cell, placementByCell)

    def swapPlacement(self, a1, a2, c1, c2, placementByCell):
        # updates both maps consistently
        self.agentPlacements[a1.ID] = c2
        self.agentPlacements[a2.ID] = c1

        placementByCell.pop(c1, None)
        placementByCell.pop(c2, None)
        placementByCell[c2] = a1
        placementByCell[c1] = a2

    def removeFromPlan(self, agent, placementByCell):
        # used to simulate prey "dying" in planning
        c = self.agentPlacements.get(agent.ID, agent.cell)
        placementByCell.pop(c, None)
        self.agentPlacements.pop(agent.ID, None)

    def agentTtlAtPlannedCell(self, agent):
        c = self.agentPlacements.get(agent.ID, agent.cell)
        return self.ttlAfterMove(agent, c)

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

        pairs = []
        for a in agents:
            # only exclude immediate death moves
            viable = []
            for minTtl in (4.0, 3.0, 2.0, 1.1, 0.0):
                viable = self.findViableCellsForAgent(a, minTtl=minTtl)
                if viable:
                    break

            # if still none, agent is doomed no matter what -> keep them in place
            if not viable:
                viable = [a.cell]
            for c in viable:
                if c.isOccupied() and a.isNeighborValidPrey(c.agent) == False:
                    continue
                # Do not allow assignments into occupied cells (prevents combat deaths)
                if c.isOccupied() and c != a.cell:
                    continue
                score = self.predictedUtility(a, c)
                pairs.append((score, a, c))

        # highest score first
        pairs.sort(key=lambda x: x[0], reverse=True)

        claimedCells = set()
        assignedAgents = set()

        for score, a, c in pairs:
            if a.ID in assignedAgents:
                continue
            if (c.x, c.y) in claimedCells:
                continue
            self.agentPlacements[a.ID] = c
            assignedAgents.add(a.ID)
            claimedCells.add((c.x, c.y))

        # any unassigned agents stay put
        for a in agents:
            if a.ID not in assignedAgents:
                self.agentPlacements[a.ID] = a.cell

        # build placementByCell
        placementByCell = {}
        for a in agents:
            placementByCell[self.agentPlacements.get(a.ID, a.cell)] = a

        self.improvePlacementsBySwaps(
            agents,
            placementByCell,
            maxSwaps=self.maxSwaps,
            sampleSize=self.swap_sample
        )

        # rebuild placementByCell after swaps (important)
        placementByCell = self.placementByCellFromCurrentPlan(agents)

        # let doomed aggressors attack if it improves aggregate objective
        # self.rescueDoomedAggressors(
        #     agents,
        #     placementByCell,
        #     doomedTtl=1.2
        # )

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