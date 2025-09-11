from diplomacy import Game

game = Game()  # or load from a saved game

for power_name, power in game.powers.items():
    print(f"{power_name}:")
    for unit in power.units:
        print(f"  {unit}")
