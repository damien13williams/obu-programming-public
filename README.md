# Puzzle Project

## Sprint 01

- Cipher worker and base worker created and finished
- DynamoDB and SQS created
- Project path fully functional: from SQS message to putting solution in the table

## To Run

1. Download the project and all corresponding folders/files
2. Open the project in your terminal
3. Run the base worker with:

python -m workers.base_worker

## Improvements / To-Do

- Add an attribute to SQS messages describing the type of task
- Solve the errors being sent out in the terminal after shutting down the workers
- Maybe create one config file for all workers/info
- Add more commenting if needed
- Go through and remove extra/unused code/files

## -------------------------------------------------------

## Sprint 02

- Data worker completed and processing
- Orchastrator completed and implemented
- Both workers implemented as lambda functions that are triggered by SQS Queue
- Workflow from start to finish completed as follows:
- task.json -> (pulls info from dynamodb) -> orchastrator (dispatches to workers) -> workers (process and send back solution) -> dynamo db contains the solution

## To run locally

1. Download the project
2. Open project in 3 seperate terminals
3. Run both workers and orchastrator 

python -m workers.cipher_worker
python -m workers.data_worker
python -m orchestrator.orchestrator