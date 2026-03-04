# from flask import Flask, request, jsonify
import json
import boto3
import time
# from english_words import english_words_set # Did not work so will save here for now. 
from nltk.corpus import words # Make sure to run nltk.download('words') before using this code to download the word list (looked up using gemini for english words)

# app = Flask(__name__)

# Load config
with open('config.json') as f:
    config = json.load(f)

aws_region = config["aws_region"]
table_name = config["dynamodb_table_name"]

# Connect to DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=aws_region)
puzzle_table = dynamodb.Table(table_name)

# Load English words for scoring
ENGLISH_WORDS = set(word.upper() for word in words.words())

# Ceasar cipher decryption function for all characters (both uppercase and lowercase)
def caesar_decrypt(text, shift):
    decrypted = []
    for char in text:
        if char.isupper():
            decrypted.append(chr((ord(char) - ord('A') - shift) % 26 + ord('A')))
        elif char.islower():
            decrypted.append(chr((ord(char) - ord('a') - shift) % 26 + ord('a')))
        else:
            decrypted.append(char)
    return ''.join(decrypted)

# score the text based on valid english words
def score_text(text):
    words = text.upper().split()
    return sum(1 for word in words if word in ENGLISH_WORDS)

# Solve the cipher by going through all shifts and scoring (highest score wins and best shift will be selected)
def solve_cipher(encrypted_message):
    best_score = -1
    best_text = ""
    best_shift = 0
    for shift in range(1, 26):
        decrypted_message = caesar_decrypt(encrypted_message, shift)
        score = score_text(decrypted_message)
        if score > best_score:
            best_score = score
            best_text = decrypted_message
            best_shift = shift
    return best_text, best_shift
# Process puzzle from DynamoDB
def process_puzzle(puzzle_id="cipher_001", game_id="game_12345"):
    start_time = time.time()
    # Get my item from DynamoDB
    response = puzzle_table.get_item(Key={
            'puzzle_id': puzzle_id,
            'game_id': game_id
        })
    puzzle = response.get('Item')

    encrypted_message = puzzle['encrypted_text']

    decrypted_text, shift_used = solve_cipher(encrypted_message)
    vault_code = "7294"  # Replace with real logic if needed (unsure)

    solution_item = {
        'puzzle_id': puzzle['puzzle_id'],
        'game_id': puzzle['game_id'],
        'cipher_type': puzzle['cipher_type'],
        'encrypted_text': encrypted_message,
        'hint': puzzle['hint'],
        'solution': {
            'shift': shift_used,
            'decrypted_text': decrypted_text,
            'vault_code': vault_code
        },
        'processing_time_ms': int((time.time() - start_time) * 1000)
    }
    # Write to output table
    puzzle_table.put_item(Item=solution_item)
    print(f"Solved {puzzle['puzzle_id']}: shift={shift_used}, decrypted={decrypted_text}")

# FLASK OPTION in last class, not needed for the current project. 
'''
@app.route('/decrypt', methods=['POST'])
def decrypt_message():
    data = request.get_json()
    encrypted_message = data.get('encrypted_message', '')
    if not encrypted_message:
        return jsonify({"error": "No encrypted message provided"}), 400



    decrypted_message, shift_used = solve_cipher(encrypted_message)
    # Print to console for debugging
    print(f"Encrypted: {encrypted_message} → Decrypted: {decrypted_message} (Shift: {shift_used})")
    return jsonify({
        "decrypted_message": decrypted_message,
        "shift_used": shift_used
    })
'''
'''
if __name__ == '__main__':
    process_puzzle("cipher_001", game_id="game_12345")
    app.run(debug=True)
'''

# start up the service and process the puzzle
process_puzzle("cipher_001", game_id="game_12345")