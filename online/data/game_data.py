from dataclasses import dataclass

from rules.game_flow import PokerGame, GameEvent, Player, PlayerHand


@dataclass
class PlayerDataAttr:
    name: str
    chips: int
    player_number: int
    leave_next_hand: bool


@dataclass
class GameData:
    """
    The `GameData` dataclass is used to sync the client-sided `MultiplayerGame` with the server-sided `ServerGameRoom`.
    """
    players: list[PlayerDataAttr] = None
    client_player: PlayerDataAttr = None


def generate_game_data(game: PokerGame, game_event: GameEvent) -> GameData:
    game_data = GameData()

    if game_event.code == GameEvent.RESET_PLAYERS:
        game_data.players = [PlayerDataAttr(x.name, x.chips, x.player_number, x.leave_next_hand) for x in game.players]

    return game_data


def generate_complete_game_data(game: PokerGame):
    return GameData(players=[PlayerDataAttr(x.name, x.chips, x.player_number, x.leave_next_hand) for x in game.players])
