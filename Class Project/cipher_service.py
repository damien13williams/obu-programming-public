# This is the cipher service that take an encrypted message from json file and output the
# decrypted message to the console using the Caesar cipher decryption method and flask for the web service
# from flask import Flask, request, jsonify
import json
import boto3
import time

# app = Flask(__name__)

# DynamoDB tables
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')  # change region if needed
puzzle_table = dynamodb.Table('CIS3823Spring26Project001')


# Basic English words list for validation all caps
ENGLISH_WORDS = set([
    "THE", "BE", "TO", "OF", "AND", "A", "IN", "THAT", "HAVE", "I", "IT", "FOR", "NOT",
    "ON", "WITH", "HE", "AS", "YOU", "DO", "AT", "HELLO", "WORLD", "THIS", "IS", "A", "TEST"
])

# Ceasar cipher decryption function for all caps
def caesar_decrypt(text, shift):
    decrypted = []
    for char in text:
        if char.isupper():  # uppercase letters
            decrypted.append(chr((ord(char) - shift - 65) % 26 + 65))
        elif char.islower():  # lowercase letters
            decrypted.append(chr((ord(char) - shift - 97) % 26 + 97))
        else:
            decrypted.append(char)
    return ''.join(decrypted)

# score the text based on valid english words
def score_text(text):
    words = text.upper().split()
    return sum(1 for word in words if word in ENGLISH_WORDS)

# Solve the cipher by going through all shifts and scoring 
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
# Process puzzle from DynamoDB
# ----------------------
def process_puzzle(puzzle_id="cipher_001", game_id="game_12345"):
    # Get item from DynamoDB
    response = puzzle_table.get_item(Key={
            'puzzle_id': puzzle_id,
            'game_id': game_id
        })
    puzzle = response.get('Item')

    start_time = time.time()
    encrypted_message = puzzle['encrypted_text']

    decrypted_text, shift_used = solve_cipher(encrypted_message)
    vault_code = "7294"  # Replace with real logic if needed

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

'''
if __name__ == '__main__':
    process_puzzle("cipher_001", game_id="game_12345")
    app.run(debug=True)
'''
process_puzzle("cipher_001", game_id="game_12345")