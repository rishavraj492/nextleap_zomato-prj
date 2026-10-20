# AI-Powered Restaurant Recommendation System

## Context

This project is an AI-powered restaurant recommendation service inspired by Zomato. It suggests restaurants from a real-world restaurant dataset by combining structured filters with a large language model, so recommendations are both relevant to the user’s constraints and explained in natural language.

The restaurant data comes from the Zomato dataset on Hugging Face: [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation).

## Objective

Design and implement an application that:

- Takes user preferences such as location, budget, cuisine, and ratings
- Uses a real-world dataset of restaurants
- Leverages an LLM to generate personalized, human-like recommendations
- Displays clear and useful results to the user

## System Workflow

### 1. Data ingestion

Load and preprocess the Zomato dataset. Extract the fields needed for filtering and display, including:

- Restaurant name
- Location
- Cuisine
- Cost
- Rating

### 2. User input

Collect preferences that drive which restaurants are eligible:

- **Location** — for example, Delhi or Bangalore
- **Budget** — low, medium, or high
- **Cuisine** — for example, Italian or Chinese
- **Minimum rating**
- **Additional preferences** — for example, family-friendly or quick service

### 3. Integration layer

Filter and prepare the restaurant records that match the user’s input. Pass those structured results into an LLM prompt designed so the model can reason over the candidates and rank them.

### 4. Recommendation engine

Use the LLM to:

- Rank restaurants
- Explain why each recommendation fits the user’s preferences
- Optionally summarize the set of choices

### 5. Output display

Present the top recommendations in a user-friendly format. Each result should include:

- Restaurant name
- Cuisine
- Rating
- Estimated cost
- An AI-generated explanation of why it was recommended
