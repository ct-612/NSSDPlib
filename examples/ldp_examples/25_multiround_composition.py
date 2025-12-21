"""
Example 25: LDP Multi-round Composition.

Goal:
    Demonstrate tracking privacy budget for a single user across multiple
    reporting rounds (Sequential Composition).

Extras:
    [ldp]

Usage:
    python examples/ldp_examples/25_multiround_composition.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
src_root = project_root / "src"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from examples._shared import cli, io
from dplib.core.privacy import PrivacyAccountant

def main(argv=None):
    args = cli.parse_args("LDP Multi-round", argv)
    
    # 1. User Budget Setup
    # Each user has a max epsilon they are willing to contribute over time
    user_budget = 5.0
    accountant = PrivacyAccountant(total_epsilon=user_budget)
    
    rounds = 10
    eps_per_round = 0.8
    
    history = []
    
    print(f"User Budget: {user_budget}")
    
    # 2. Simulate Rounds
    for r in range(rounds):
        round_id = r + 1
        
        # Check before participating
        rem = accountant.remaining.epsilon if accountant.remaining else 0
        if rem < eps_per_round:
            msg = f"Round {round_id}: Skipped (Insufficient Budget)"
            print(msg)
            history.append({"round": round_id, "status": "skipped"})
            continue
            
        # Participate (Simulated LDP mechanism usage)
        # mech = GRR(...)
        # report = mech.randomise(...)
        
        # Deduct
        accountant.add_event(epsilon=eps_per_round)
        rem_now = accountant.remaining.epsilon if accountant.remaining else 0
        msg = f"Round {round_id}: Participated. Rem: {rem_now:.2f}"
        print(msg)
        history.append({"round": round_id, "status": "success", "remaining": rem_now})
        
    result = {
        "name": "ldp_examples/25_multiround",
        "config": {
            "user_budget": user_budget,
            "rounds": rounds,
            "epsilon_per_round": eps_per_round
        },
        "outputs": {
            "history": history
        },
        "privacy": {
            "final_used": accountant.spent.epsilon,
            "final_remaining": accountant.remaining.epsilon if accountant.remaining else None
        },
        "metrics": {
            "rounds_participated": len([h for h in history if h["status"] == "success"])
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "25_multiround.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
