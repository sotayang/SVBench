# -*- coding: utf-8 -*-
import os, sys
sys.path.append(".")
from clients.chatgpt_client import GPT
from glob import glob
import json
import math
import re

def create_evaluation_prompt(video_id, scene_id, questions, ground_truth, model_responses):
    prompt = f"""
    Video ID: {video_id}
    Scene ID: {scene_id}

    Task Description:
    You are an evaluation expert for video multi-turn dialogue evaluation. Each video contains different timestamps that are followed by a series of QAs. Your task is to evaluate the quality of model responses to a series of open-ended questions at the same timestamp within a streaming video. You will assess the responses based on several specified dimensions:

    1. Semantic Accuracy: evaluates the accuracy of the generated answers based on a holistic understanding. It considers not only the direct overlap with ground-truth answers but also the context, coherence, and overall relevance of the response to the question posed.
    Scoring Guidelines:
        - 10 points: Completely accurate, directly reflecting the video content with no apparent errors.
        - 7-9 points: Mostly accurate, with a few minor detail errors.
        - 4-6 points: Several errors, but generally conveys most of the content.
        - 1-3 points: Only a small part of the content is accurate or mostly incorrect.
        - 0 points: Completely inaccurate, unrelated to the video content.

    2. Contextual Coherence: examines the ability of LVLMs to maintain relevance and context across sequential questions and answers, ensuring continuity and alignment with the evolving discourse.
    Scoring Guidelines:
        - 10 points: Highly coherent, natural transition between scenes.
        - 7-9 points: Mostly coherent, with minor issues in transition points.
        - 4-6 points: Some coherence, but loose or partially disjointed transitions.
        - 1-3 points: Poor coherence, most transition points unnatural.
        - 0 points: Completely incoherent, response appears to be unrelated or independent content.

    3. Logical Consistency: evaluates the logical progression and consistency of answers, ensuring that answers do not contradict each other or previous information.
    Scoring Guidelines:
        - 10 points: Logically consistent, no sense of incongruity.
        - 7-9 points: Mostly consistent, with few minor inconsistencies.
        - 4-6 points: Several logical issues, but the response is somewhat understandable.
        - 1-3 points: Logically chaotic, difficult to understand or largely unreasonable.
        - 0 points: Completely illogical, contradicts video content.

    4. Temporal Understanding: assesses the model's proficiency in comprehending and reasoning about temporal events and sequences depicted in the video content.
    Scoring Details:
        - 10: The response accurately reflects the timeline and causal relationships of events.
        - 7-9: The response largely reflects the correct timeline with minor errors or omissions.
        - 4-6: The response reflects the event sequence partially but has significant time-related errors or key omissions.
        - 1-3: The response has little correct temporal understanding, with many time errors.
        - 0: The response entirely fails to reflect the correct time sequence or events process.
        - -1: The question do not involve timing understanding

    5. Informational Completeness: measures the comprehensiveness to gauge whether the model captures and conveys all relevant elements from the video to provide a thorough answer.
    Scoring Guidelines:
        - 10 points: Fully comprehensive, covering all necessary details.
        - 7-9 points: Mostly comprehensive, with some missing details.
        - 4-6 points: Partially informative, but incomplete.
        - 1-3 points: Largely incomplete, containing only a few details.
        - 0 points: Contains no useful information.

    Overall Evaluation: is derived by aggregating the scores from each aforementioned criterion, ranked as follows:
    - Scores 1-2: Irrelevant, factually incorrect, or harmful content.
    - Scores 3-4: Low quality, with no major errors but not meeting requirements.
    - Scores 5-6: Moderate quality, meets basic requirements but performs poorly in some aspects.
    - Scores 7-8: High quality, performs well in most dimensions.
    - Scores 9-10: Excellent performance, fully addressing the questions and all criteria, significantly exceeding the reference answers.

    Additional Requirements and Considerations for the Evaluator:
    1. Unbiased Evaluation: Ensure an unbiased assessment by focusing purely on the content and quality of the responses compared to the ground truth.
    2. Consistency: Maintain consistency in scoring across different responses by adhering strictly to the detailed scoring breakdown provided.
    3. Detail and Justification: Provide detailed feedback for each criterion, explaining why a particular score was assigned to help identify strengths and weaknesses in the responses.
    4. Thoroughness: Avoid rushing through the evaluation. Ensure each response is carefully reviewed and scored based on all aspects of the criteria.

    For the following QA chain, please evaluate the model's performance according to the criteria mentioned above and provide a detailed justification for each score.

    Questions:
    {questions}
    
    Ground Truth:
    {ground_truth}

    Model Responses:
    {model_responses}

    Please provide your evaluation scores and detailed comments for each criterion below:

    1. Semantic Accuracy:
    Score: 
    Comments:
    """

    return prompt

def extract_scores(evaluation):
    patterns = {
        "Semantic Accuracy": r'Semantic Accuracy.*?\n?.*?Score.*?(\d+)',
        "Contextual Coherence": r'Contextual Coherence.*?\n?.*?Score.*?(\d+)',
        "Logical Consistency": r'Logical Consistency.*?\n?.*?Score.*?(\d+)',
        "Temporal Understanding": r'Temporal Understanding.*?\n?.*?Score.*?(\d+)',
        "Informational Completeness": r'Informational Completeness.*?\n?.*?Score.*?(\d+)',
        "Overall Evaluation": r'Overall Evaluation.*?\n?.*?Score.*?(\d+)',
    }
    
    scores = {category: None for category in patterns.keys()}
    
    for category, pattern in patterns.items():
        match = re.search(pattern, evaluation, re.DOTALL)
        if match:
            score = match.group(1)
            try:
                scores[category] = int(score)
                print(f"{category} Score: {score}")
            except ValueError:
                print(f"Failed to convert {category} Score: {score} to an integer.")
        else:
            print(f"{category} Score not found.")
    
    return scores

answers_path = 'Path_to_your_answers_path'

for root, dirs, files in os.walk(answers_path):
    for name in files:
        file_path = os.path.join(root, name)
        video_name, _ = os.path.splitext(name)
        with open(file_path, 'r', encoding='utf-8') as file:
            datas = json.load(file)

        output = []
        gpt_client = GPT()

        for i in range(len(datas)):
            if len(datas[i]) == 0:
                continue
            
            question_chain = datas[i]['questions']
            ground_truth_chain = datas[i]['gt_answers']
            model_responses_chain = datas[i]['answers']

            prompt = create_evaluation_prompt(video_id=video_name, scene_id=i, questions = question_chain, ground_truth=ground_truth_chain, model_responses=model_responses_chain)
            print(f"Generated Prompt for video: {video_name}, scene: {i}")
            print(prompt)

            evaluation = ""

            while True: 
                evaluation = gpt_client.chat(prompt)
                if evaluation:
                    break
                else:
                    print(f"Retrying evaluation for video: {video_name}, scene: {i})")
            
            print(f"GPT-4 Evaluation for video: {video_name}, scene: {i}")
            print(evaluation)

            scores = extract_scores(evaluation)

            output_data = {
                "video_name": video_name,
                "scene_id": i,
                "questions": question_chain,
                "gt_answers": ground_truth_chain,
                "answers": model_responses_chain,
                "evaluation": evaluation,
                "scores": scores
            }
            output.append(output_data)

        eval_chainQA_result = f'Path_to_your_save_file'
        with open(eval_chainQA_result, 'w', encoding='utf-8') as json_file:
            json.dump(output, json_file, ensure_ascii=False, indent=4)

        print(f"Data has been written to {eval_chainQA_result}")



