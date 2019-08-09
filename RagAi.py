import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, CYBERNETICSCORE, STALKER, ZEALOT, STARGATE, VOIDRAY
import random

""" some notes
    I found out that self.units(NEXUS).amount AND len(self.units(NEXUS))[counts the units] basically returns the same thing
"""

class RagBot(sc2.BotAI):
    def __init__(self):
        self.MAX_WORKERS = 44
        self.MAX_ZEALOTS = 5
        self.MAX_STALKERS = 20

        self.GATEWAY_ITERATION = 120 # seconds in realtime
        self.STARGATE_ITERATION = 300 # seconds in realtime
        self.NEXUS_ITERATION = 300

    # runs on realtime seconds
    async def on_step(self, iteration):
        # self.iteration = iteration
        # what to do every step
        await self.distribute_workers() # [built-in] distributes workers even after expanding(which is nice)
        await self.build_worker()
        await self.build_pylon()
        await self.build_assimilator()
        await self.expand()
        await self.build_offensive_building()
        await self.build_offensive_units()
        await self.attack()


    # runs after program ended without error
    def on_end(self, result):
        print("Score: %s" % self.state.score.score)


    async def build_worker(self):
        # build worker if nexus is idle/noqueue
        for nexus in self.units(NEXUS).ready.idle:
            if self.can_afford(PROBE):
                # train worker if we a the number of nexus * 22 is greater
                if (len(self.units(NEXUS)) * 22) > len(self.units(PROBE)) and len(self.units(PROBE)) < self.MAX_WORKERS:
                    await self.do(nexus.train(PROBE))


    async def build_pylon(self):
        # if we have less than 3(for workers) supply + every gateways(for offensive forces), can afford, and no pending pylong then build one
        if self.supply_left < 3 + (self.units(GATEWAY).amount * 2) and self.can_afford(PYLON) and not self.already_pending(PYLON):
            nexuses = self.units(NEXUS).ready
            if nexuses.exists:
                await self.build(PYLON, near=nexuses.first)


    async def expand(self):
        if self.can_afford(NEXUS) and not self.already_pending(NEXUS):
            if self.units(NEXUS).amount < 2: #if we have less than 2 nexus and can afford one expand
                await self.expand_now()

            # build additional nexus after every 5 mins if we have a nexus that has less than 16 ideal_harvesters
            if self.units(NEXUS).amount < (self.time / self.NEXUS_ITERATION):
                for nexus in self.units(NEXUS).ready:
                    if nexus.ideal_harvesters < 16 and not self.already_pending(NEXUS):
                        await self.expand_now()


    async def build_assimilator(self):
        for nexus in self.units(NEXUS).ready: # check all nexus
            vespenes = self.state.units.vespene_geyser.closer_than(10, nexus) # list of vespene_geyser closer than 25 units

            # if we don't have a assimilator yet build one
            if not self.units(ASSIMILATOR).ready.exists and not self.already_pending(ASSIMILATOR):
                for vespene in vespenes: # loop throough the selected vespene_geysers
                    worker = self.select_build_worker(vespene.position) # selects a worker near that vespene_geyser
                    if not self.can_afford(ASSIMILATOR): # check if have enough resources for assimilator
                        break
                    if worker and not self.units(ASSIMILATOR).closer_than(1, vespene).exists: # make sure no assimilator is in that vespene_geyser
                        # if we have money, location and worker BUILD!
                        await self.do(worker.build(ASSIMILATOR, vespene))

            # if we have an assimilator already then build when necessary
            else:
                if not self.already_pending(ASSIMILATOR):
                    for assimilator in self.units(ASSIMILATOR):
                        # if there is still a assimilator that isn't a 3/3 then dont build one
                        if assimilator.assigned_harvesters < assimilator.ideal_harvesters:
                            break
                        for vespene in vespenes: # loop throough the selected vespene_geysers
                            worker = self.select_build_worker(vespene.position) # selects a worker near that vespene_geyser
                            if not self.can_afford(ASSIMILATOR): # check if have enough resources for assimilator
                                break
                            if worker and not self.units(ASSIMILATOR).closer_than(1, vespene).exists: # make sure no assimilator is in that vespene_geyser
                                # if we have money, location and worker BUILD!
                                await self.do(worker.build(ASSIMILATOR, vespene))


    async def build_offensive_building(self):
        if self.units(PYLON).ready.exists: # check if we have a pylon
            pylon = self.units(PYLON).ready.random # select a random pylon
            worker = self.select_build_worker(pylon, True) # select a worker near that random pylon
            # Build Gateway asap
            if not self.units(GATEWAY).ready.exists: # check if don't have a gateway
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY): # check if we can afford a gateway and not building one
                    await self.build(GATEWAY, near=pylon) # BUILD GATEWAY

            # if have a gateway already then build a CYBERNETICSCORE
            elif not self.units(CYBERNETICSCORE).ready.exists: # check if we don't have a CYBERNETICSCORE already
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE): # check if we can afford a CYBERNETICSCORE and not building one
                    await self.build(CYBERNETICSCORE, near=pylon) # BUILD CYBERNETICSCORE

                # build more GATEWAY as time goes on
            elif (self.units(GATEWAY).amount < (self.time / self.GATEWAY_ITERATION)) and self.units(GATEWAY).amount < 6:
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                    await self.build(GATEWAY, near=pylon)

            if self.units(CYBERNETICSCORE).ready.exists and self.units(NEXUS).amount > 1:
                if (self.units(STARGATE).amount < (self.time / self.STARGATE_ITERATION)) and self.units(STARGATE).amount < 2:
                    if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
                        await self.build(STARGATE, near=pylon)

        else:
            pass


    def max_unit_per_min(self, max_unit):
        # Calculates how many units can be produced per minute
        return 1 + ( (self.time / 60) * max_unit)


    async def build_offensive_units(self):
        if self.supply_left > 1:
            for gateway in self.units(GATEWAY).ready.idle:
                    if self.can_afford(STALKER) and self.units(CYBERNETICSCORE).ready.exists and self.units(STALKER).amount < self.max_unit_per_min(self.MAX_STALKERS): #check if we can afford stalker and have a CYBERNETICSCORE and prefer stalker over zealot if it has more vespene gas than minerals
                        await self.do(gateway.train(STALKER))

                    elif self.can_afford(ZEALOT) and self.units(ZEALOT).amount < self.max_unit_per_min(self.MAX_ZEALOTS): # else train a zealot
                        if self.vespene > self.minerals: # if we have more gas than minerals dont train zealot
                            break
                        await self.do(gateway.train(ZEALOT))

        # build as many voidrays as we can
        if self.supply_left > 1:
            for stargate in self.units(STARGATE).ready.idle:
                    if self.can_afford(VOIDRAY):
                        await self.do(stargate.train(VOIDRAY))


    def find_enemy(self, state):
        if len(self.known_enemy_units) > 0:
            return random.choice(self.known_enemy_units) # return random enemy unit
        elif len(self.known_enemy_structures) > 0:
            return random.choice(self.known_enemy_structures) # return random enemy structure
        else:
            return self.enemy_start_locations[0] # return enemy start location


    async def attack(self):
        # {UNIT: [n to fight, n to defend]}
        attack_units = { ZEALOT: [10, 3],
                        STALKER: [15, 3],
                        VOIDRAY: [5, 3]}

        for ATT_UNIT in attack_units:
            if self.units(ATT_UNIT).idle.amount > attack_units[ATT_UNIT][0]: # minimum amount of units to seek and destroy
                for unit in self.units(ATT_UNIT).idle:
                    await self.do(unit.attack(self.find_enemy(self.state))) # if have a large army then seek the enemy forces(attack with stalker)

                # for zealot in self.units(ZEALOT).idle:
                #     await self.do(zealot.attack(self.find_enemy(self.state))) # if have a large army then seek the enemy forces(attack with zealot)

            if self.units(ATT_UNIT).idle.amount > attack_units[ATT_UNIT][1]: # minimum amount of units to defend
                if len(self.known_enemy_units) > 0:
                    for unit in self.units(ATT_UNIT).idle:
                        await self.do(unit.attack(random.choice(self.known_enemy_units)))

                    # for stalker in self.units(STALKER).idle:
                    #     await self.do(stalker.attack(random.choice(self.known_enemy_units)))

run_game(maps.get("AbyssalReefLE"), [
    Bot(Race.Protoss, RagBot()),
    Computer(Race.Terran, Difficulty.Hard)
], realtime=False)
