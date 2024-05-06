import sqlite3
import json
import math
import argparse

def calculate_elo_scores(conn, k_factor=32, initial_score=1000):
    scores = {}
    cursor = conn.cursor()
    cursor.execute("SELECT model_a, model_b, punitiveness_relation FROM evaluation_results")
    results = cursor.fetchall()

    for row in results:
        model_a, model_b, punitiveness_relation_json = row
        punitiveness_relation = json.loads(punitiveness_relation_json)

        if model_a not in scores:
            scores[model_a] = initial_score
        if model_b not in scores:
            scores[model_b] = initial_score

        if punitiveness_relation is not None:
            winner, loser = punitiveness_relation
            ra = scores[winner]
            rb = scores[loser]
            ea = 1 / (1 + 10 ** ((rb - ra) / 400))
            eb = 1 / (1 + 10 ** ((ra - rb) / 400))
            scores[winner] += k_factor * (1 - ea)
            scores[loser] += k_factor * (0 - eb)

    return scores

def main():
    parser = argparse.ArgumentParser(description="Calculate Elo scores for models")
    parser.add_argument("--db_path", type=str, help="Path to the database file")
    args = parser.parse_args()
    db_path = args.db_path
    conn = sqlite3.connect(db_path)

    elo_scores = calculate_elo_scores(conn)
    print("Elo Scores:")
    for model, score in elo_scores.items():
        print(f"{model}: {score}")

    conn.close()

if __name__ == "__main__":
    main()