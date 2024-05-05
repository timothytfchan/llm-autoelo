import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import logging
from tqdm import tqdm
import sqlite3
from threading import Lock

def load_config(config_path):
    """
    Load the configuration from a JSON file.

    Args:
        config_path (str): Path to the configuration file.

    Returns:
        dict: The loaded configuration.

    Raises:
        FileNotFoundError: If the configuration file is not found.
        json.JSONDecodeError: If the configuration file is not a valid JSON.
    """
    try:
        with open(config_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading configuration file: {str(e)}")
        raise

def prompt_model(db_path, model_name, model_config, question_id, question, lock):
    """
    Prompt a single model and store the response in the database.

    Args:
        model_name (str): Name of the model.
        model_config (dict): Configuration of the model.
        question_id (int): ID of the question being processed.
        question (str): The question to prompt the model with.
        lock (threading.Lock): Lock for thread-safe database access.

    Returns:
        tuple: A tuple containing the model name and its response.
    """
    module_name = model_config["module"]
    model_params = model_config["params"]
    model_key = model_params["key"]
    model_option = model_params["option"]

    conn = sqlite3.connect(db_path)
    with lock:
        cursor = conn.cursor()
        cursor.execute("SELECT response FROM model_responses WHERE model_name = ? AND question_id = ?", (model_name, question_id))
        result = cursor.fetchone()
        if result:
            conn.close()  # Close the connection before returning
            return model_name, result[0]

    try:
        module = __import__(module_name, fromlist=["get_response"])
        get_response = getattr(module, "get_response")
        response = get_response(question, **{model_key: model_option})
        
        # Convert response to string before inserting into the database
        response_str = str(response)

        with lock:
            cursor.execute("INSERT INTO model_responses (model_name, question_id, response) VALUES (?, ?, ?)", (model_name, question_id, response_str))
            conn.commit()

        conn.close()  # Close the connection before returning
        return model_name, response

    except (ImportError, AttributeError) as e:
        logging.error(f"Error prompting model {model_name}: {str(e)}")
        conn.close()  # Close the connection before returning
        return model_name, None

def evaluate_responses(db_path, question_id, question, model_names, evaluator_model, eval_prompt, lock):
    results = []

    conn = sqlite3.connect(db_path)

    # Retrieve available responses from the database
    available_responses = {}
    with lock:
        cursor = conn.cursor()
        for model_name in model_names:
            cursor.execute("SELECT response FROM model_responses WHERE model_name = ? AND question_id = ?", (model_name, question_id))
            result = cursor.fetchone()
            if result:
                available_responses[model_name] = result[0]

    for i in range(len(model_names)):
        for j in range(i + 1, len(model_names)):
            if random.random() < 0.5:
                model_a, model_b = model_names[i], model_names[j]
            else:
                model_b, model_a = model_names[i], model_names[j]

            # Check if responses are available for both models
            if model_a not in available_responses or model_b not in available_responses:
                continue

            # Check if the evaluation is already processed
            with lock:
                cursor.execute("SELECT processed FROM evaluation_progress WHERE question_id = ? AND model_a = ? AND model_b = ?", (question_id, model_a, model_b))
                result = cursor.fetchone()
                if result and result[0]:
                    continue

            try:
                module_evaluator = __import__(evaluator_model["module"], fromlist=["get_response"])
                get_response_evaluator = getattr(module_evaluator, "get_response")

                prompt = eval_prompt.format(question=question, response_A=available_responses[model_a], response_B=available_responses[model_b])

                evaluator_key = evaluator_model["params"]["key"]
                evaluator_option = evaluator_model["params"]["option"]

                # Get the evaluation result from the evaluator model
                evaluation_result = get_response_evaluator(prompt, **{evaluator_key: evaluator_option})

                matches = re.findall(r'<answer>(.*?)</answer>', evaluation_result, re.IGNORECASE)
                answer = matches[-1].strip().upper() if matches else None

                punitiveness_relation = None
                if answer == 'A':
                    punitiveness_relation = [model_a, model_b]
                elif answer == 'B':
                    punitiveness_relation = [model_b, model_a]

                result = {
                    "model_A": model_a,
                    "model_B": model_b,
                    "evaluator_response": evaluation_result,
                    "punitiveness_relation": punitiveness_relation
                }
                results.append(result)

                # Store the evaluation result in the database
                with lock:
                    cursor.execute("INSERT INTO evaluation_results (model_a, model_b, question_id, evaluator_response, punitiveness_relation) VALUES (?, ?, ?, ?, ?)", (model_a, model_b, question_id, evaluation_result, json.dumps(punitiveness_relation)))
                    cursor.execute("INSERT OR REPLACE INTO evaluation_progress (question_id, model_a, model_b, processed) VALUES (?, ?, ?, 1)", (question_id, model_a, model_b))
                    cursor.execute("INSERT OR REPLACE INTO evaluation_progress (question_id, model_a, model_b, processed) VALUES (?, ?, ?, 1)", (question_id, model_b, model_a))
                    conn.commit()
            except (ImportError, AttributeError, IndexError) as e:
                logging.error(f"Error evaluating {model_a} and {model_b} responses for question {question_id}: {str(e)}")

    conn.close()
    return results

def process_question(db_path, question_id, question, participant_models, evaluator_model, eval_prompt, lock, max_workers_models):
    """
    Process a single question by prompting models, evaluating responses, and storing the results in the database.

    Args:
        question_id (int): ID of the question being processed.
        question (str): The question to prompt the models with.
        participant_models (dict): Dictionary of participant models and their configurations.
        evaluator_model (dict): Configuration of the evaluator model.
        eval_prompt (str): Prompt template for evaluation.
        lock (threading.Lock): Lock for thread-safe database access.
        max_workers_models (int): Maximum number of worker threads for model prompting.

    Returns:
        dict: Dictionary containing the question ID, question, model responses, and evaluation results.
    """
    model_responses = {}

    # Prompt models in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers_models) as executor:
        futures = []
        for model_name, model_config in participant_models.items():
            # Check if the response for the question-model pair has already been processed
            conn = sqlite3.connect(db_path)
            with lock:
                cursor = conn.cursor()
                cursor.execute("SELECT processed FROM response_progress WHERE question_id = ? AND model_name = ?", (question_id, model_name))
                result = cursor.fetchone()
                if result and result[0]:
                    conn.close()
                    continue
            conn.close()

            # Submit the model prompting task to the executor
            future = executor.submit(prompt_model, db_path, model_name, model_config, question_id, question, lock)
            futures.append(future)

        # Collect model responses as they complete
        for future in as_completed(futures):
            model_name, response = future.result()
            model_responses[model_name] = response

            # Update the response progress in the database
            conn = sqlite3.connect(db_path)
            with lock:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO response_progress (question_id, model_name, processed) VALUES (?, ?, 1)", (question_id, model_name))
                conn.commit()
            conn.close()

    # Evaluate responses
    model_names = list(participant_models.keys())
    evaluation_results = evaluate_responses(db_path, question_id, question, model_names, evaluator_model, eval_prompt, lock)

    return {
        "question_id": question_id,
        "question": question,
        "model_responses": model_responses,
        "evaluation_results": evaluation_results
    }

def main():
    logging.basicConfig(level=logging.INFO)

    config = load_config('./configs/config.json')
    evaluator_model = config["evaluator_model"]
    participant_models = config["participant_models"]
    questions = config["questions"]
    max_workers_questions = config.get("max_workers_questions", 5)
    max_workers_models = config.get("max_workers_models", 5)

    eval_prompt = config['eval_prompt']

    lock = Lock()

    db_path = config['results_db']
    conn = sqlite3.connect(db_path)
    # Create necessary tables if they don't exist
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_responses (
            model_name TEXT,
            question_id INTEGER,
            response TEXT,
            PRIMARY KEY (model_name, question_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_results (
            model_a TEXT,
            model_b TEXT,
            question_id INTEGER,
            evaluator_response TEXT,
            punitiveness_relation TEXT,
            PRIMARY KEY (model_a, model_b, question_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS response_progress (
            question_id INTEGER,
            model_name TEXT,
            processed INTEGER,
            PRIMARY KEY (question_id, model_name)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_progress (
            question_id INTEGER,
            model_a TEXT,
            model_b TEXT,
            processed INTEGER,
            PRIMARY KEY (question_id, model_a, model_b)
        )
    """)
    conn.commit()
    conn.close()

    # Process questions in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers_questions) as executor:
        futures = []
        for question_id, question in enumerate(questions, start=1):
            future = executor.submit(process_question, db_path, question_id, question, participant_models, evaluator_model, eval_prompt, lock, max_workers_models)
            futures.append(future)

        # Collect results as questions complete and display progress using tqdm
        results = []
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing questions"):
            result = future.result()
            results.append(result)

if __name__ == "__main__":
    main()