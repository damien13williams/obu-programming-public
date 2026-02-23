# This is the cipher service that take an encrypted message from json file and output the
# decrypted message to the console using the Caesar cipher decryption method and flask for the web service
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Basic English words list for validation all caps
ENGLISH_WORDS = set([
    "THE", "BE", "TO", "OF", "AND", "A", "IN", "THAT", "HAVE", "I", "IT", "FOR", "NOT",
    "ON", "WITH", "HE", "AS", "YOU", "DO", "AT", "HELLO", "WORLD", "THIS", "IS", "A", "TEST"
])

# Ceasar cipher decryption function for all caps
def caesar_decrypt(text, shift):
    decrypted = []
    for char in text:
        if char.isalpha(): 
            decrypted_char = chr((ord(char) - shift - 65) % 26 + 65)
            decrypted.append(decrypted_char)
        else:
            decrypted.append(char)
    return ''.join(decrypted)

# score the text based on valid english words
def score_text(text):
    words = text.split()
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

    # Convert to decrypt shift (backward shift)
    best_shift_decrypt = (26 - best_shift) % 26

    return best_text, best_shift_decrypt
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
if __name__ == '__main__':
    app.run(debug=True)


