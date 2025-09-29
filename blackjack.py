import numpy as np
import matplotlib.pyplot as plt
import random

def simulate_game(Initial_bankroll, outcomes, probs, hands):
    y =[]
    for _ in range(hands):
        pool = (Initial_bankroll/100)
        result = random.choices(outcomes,weights=probs,k=1)[0]
        if Initial_bankroll<=10:
            print("You are broke")
            break
        else:
            Initial_bankroll+=pool*result
        y.append(Initial_bankroll)
        
    current_bankroll = Initial_bankroll
    return y, current_bankroll
def main(Initial_bankroll=200000, hands=1000):
    outcomes=[1,-0.9,0,1.5,1,2,-1.8,0]
    probs = [31.8625,44.09,8.2145,4.5235,0.8555,5.7530,4.0205,0.6805]
    # Initial_bankroll=200000
    # hands=1000
    x = np.arange(1,hands+1)
    y, current_bankroll = simulate_game(Initial_bankroll, outcomes, probs, hands)

    fig, ax = plt.subplots()
    ax.ticklabel_format(style='plain', axis='y')
    print(f"You started with ${Initial_bankroll} and ended with ${current_bankroll} after {hands} hands.")

    ax.plot(x,y)
    ax.set_xlabel(f"Number of Hands: {hands}")
    ax.set_ylabel(f"Bankroll = {Initial_bankroll}")
    ax.set_title("Stenens gamble simulation")
    ax.grid()
    # plt.show()
    fig.savefig("./static/plot.png",)