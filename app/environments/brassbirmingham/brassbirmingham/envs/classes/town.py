from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, List

from classes.buildings.enums import BuildingName
import consts
from python.id import id
from python.print_colors import prCyan, prGreen, prLightGray, prPurple, prRed, prYellow

if TYPE_CHECKING:
    from .board import Board

from .build_location import BuildLocation
from .road_location import RoadLocation


class Town:
    """
    Town

    :param color: any of ['blue', 'green', 'red', 'yellow', 'purple']
    :param name: name
    :param buildLocation: array of BuildLocation objects"""

    def __init__(self, color: str, name: str, buildLocations: List[BuildLocation]):
        self.id = id()
        self.type = "Town"
        self.color = color
        self.name = name

        self.slot_to_bl = defaultdict(list)

        self.buildLocations = buildLocations

        for buildLocation in self.buildLocations:
            buildLocation.addTown(self)
        # networks to other towns ex: Town('Leek') would have [Town('Stoke-On-Trent'), Town('Belper')]
        self.networks: List[RoadLocation] = []

    """
    addBoard
    game init use only

    :param board: board
    """

    def addBoard(self, board: Board):
        self.board = board

    """
    addRoadLocation
    game init use only

    :param roadLocation: roadLocation
    """

    def addRoadLocation(self, roadLocation: RoadLocation):
        roadLocation.addTown(self)
        self.networks.append(roadLocation)

    # get Available canals to build
    def getAvailableCanals(self) -> List[RoadLocation]:
        return [
            rLocation
            for rLocation in self.networks
            if rLocation.isBuilt == False and rLocation.canBuildCanal == True
        ]

    def getBuildLocation(
        self, buildingName: BuildingName, index: int = 0
    ) -> BuildLocation:
        if buildingName not in self.slot_to_bl or index >= len(
            self.slot_to_bl[buildingName]
        ):
            raise ValueError(f"{buildingName} is not a valid building name")
        return self.slot_to_bl[buildingName][index]

    # get Available railroads to build
    def getAvailableRailroads(self) -> List[RoadLocation]:
        return [
            rLocation
            for rLocation in self.networks
            if rLocation.isBuilt == False and rLocation.canBuildRailroad == True
        ]

    def getNetworkVictoryPoints(self):
        networkVP = 0
        for buildLocation in self.buildLocations:
            if buildLocation.building and not buildLocation.building.isRetired:
                networkVP += buildLocation.building.networkPoints
        return networkVP

    def __str__(self) -> str:
        returnStr = ""
        if self.color == "blue":
            returnStr = prCyan(self.name)
        elif self.color == "green":
            returnStr = prGreen(self.name)
        elif self.color == "red":
            returnStr = prRed(self.name)
        elif self.color == "yellow":
            returnStr = prYellow(self.name)
        elif self.color == "purple":
            returnStr = prPurple(self.name)
        elif self.color == consts.BEER1 or self.color == consts.BEER2:
            returnStr = prLightGray(self.color)
        return f"Town({returnStr})"

    def __repr__(self) -> str:
        return str(self)
