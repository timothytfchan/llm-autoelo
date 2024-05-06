# LLM AutoElo

LLM AutoElo is a Python-based pipeline for comparing and ranking language models using the Elo rating system. It allows you to define a set of questions, prompt multiple language models, automatically evaluate their responses with an evaluator language model, and calculate Elo scores based on the evaluation results. This pipeline was inspired by the need to compare and rank language models based on their performance on specific tasks.

## Features

- Configurable pipeline through a JSON configuration file
- Parallel processing of questions and model prompts for faster results
- Evaluation of model responses using an evaluator model you can specify in the configuration file
- Calculation of Elo scores based on the evaluation results
- Storage of results in an SQLite database for persistence and analysis

## Installation

1. Clone the repository:

```bash
git clone https://github.com/timothytfchan/llm-autoelo.git
cd llm-autoelo
```

2. Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Configuration

The pipeline is configured using a JSON configuration file (`config.json`). The configuration file contains the following sections:

- `results_db`: Path to the SQLite database file for storing results.
- `max_workers_questions`: Maximum number of worker threads for processing questions (default: 5).
- `max_workers_models`: Maximum number of worker threads for prompting models (default: 5).
- `evaluator_model`: Configuration of the evaluator model, including the module, function, and parameters.
- `participant_models`: Dictionary of participant models and their configurations, including the module, function, and parameters.
- `eval_prompt`: Prompt template for evaluating model responses.
- `questions`: List of questions to prompt the models with.

Modify the `config.json` file to specify your desired configuration, including the models, questions, and evaluation prompt.

Example:

```json
{
  "results_db": "results.db",
  "max_workers_questions": 5,
  "max_workers_models": 5,
  "evaluator_model": {
    "module": "api.together_api",
    "function": "get_response",
    "params": {
      "key": "model_name",
      "option": "meta-llama/Llama-3-70b-chat-hf"
    }
  },
  "participant_models": {
    "model1": {
      "module": "api.together_api",
      "function": "get_response",
      "params": {
        "key": "model_name",
        "option": "mistralai/Mistral-7B-Instruct-v0.2"
      }
    },
    "model2": {
      "module": "api.openai_api",
      "function": "get_response",
      "params": {
        "key": "model_name",
        "option": "gemini-1.0-pro"
      }
    },
    "model3": {
      "module": "api.anthropic_api",
      "function": "get_response",
      "params": {
        "key": "model_name",
        "option": "gpt-3.5-turbo-1106"
      }
    }
  },
  "eval_prompt": "Below are two responses to the same question.\n\n----Question: {question}\n\nResponse A: {response_A}\n\nResponse B: {response_B}\n\n----\n\nIf you think Response A is cooler, write 'A' within <answer></answer> tags, i.e. <answer>A</answer>.\n\nIf you think Response B is cooler, write 'B' within <answer></answer> tags, i.e. <answer>B</answer>.\n\nNow, please reason and then provide your answer.",
  "questions": [
    "When should we get dinner next week?",
    "Marugame or CoCo Ichibanya?",
    "When in doubt, pick C?"
  ]
}
```

## Usage
1. Set API keys in .env file (GOOGLE_API_KEY, ANTHROPIC_API_KEY, TOGETHER_API_KEY, OPENAI_API_KEY).

2. Set up the configuration JSON file.

3. Run the pipeline:

```bash
python prompt_and_rate.py --config ./configs/config.json
```

The pipeline will process the questions, prompt the models, evaluate the responses, and store the results in the specified SQLite database.

4. Calculate Elo scores with the database:

```bash
python elo.py --db_path ./results.db
```

This script will calculate the Elo scores based on the evaluation results stored in the database and display the scores for each model.

## Results

The pipeline stores the results in an SQLite database specified in the `results_db` field of the configuration file. The database contains the following tables:

- `model_responses`: Stores the responses of each model for each question.
- `evaluation_results`: Stores the evaluation results, including the models being compared, the question ID, the evaluator's response, and the punitiveness relation.
- `response_progress`: Tracks the progress of model prompts for each question.
- `evaluation_progress`: Tracks the progress of evaluations for each pair of models and question.

The Elo scores are calculated based on the evaluation results and will be displayed after running the `elo.py` script.
