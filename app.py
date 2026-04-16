"""Main Flask application"""

from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
from decision_engine import DecisionEngine
from risk_rules import get_risk
from examples import get_all_examples
from prompts import build_prompt

load_dotenv()

app = Flask(__name__)

# Initialize decision engine
use_mock = os.getenv('USE_MOCK_LLM', 'false').lower() == 'true'
decision_engine = DecisionEngine(use_mock=use_mock)

def validate_custom_input(action, conversation):
    """Validate user-provided custom input"""
    errors = []
    
    # Validate action
    if not isinstance(action, dict):
        errors.append("Action must be an object")
    elif 'type' not in action:
        errors.append("Action missing 'type' field")
    elif 'parameters' not in action:
        errors.append("Action missing 'parameters' field")
    elif not isinstance(action['parameters'], dict):
        errors.append("Parameters must be an object")
    
    # Validate conversation
    if not isinstance(conversation, list):
        errors.append("Conversation must be an array")
    else:
        for i, msg in enumerate(conversation):
            if not isinstance(msg, dict):
                errors.append(f"Message {i} must be an object")
            elif 'role' not in msg or 'content' not in msg:
                errors.append(f"Message {i} missing 'role' or 'content'")
            elif msg['role'] not in ['user', 'alfred']:
                errors.append(f"Message {i} role must be 'user' or 'alfred'")
    
    return errors

@app.route('/')
def index():
    examples = get_all_examples()
    return render_template('index.html', examples=examples)

@app.route('/decide', methods=['POST'])
def decide():
    data = request.json
    action = data.get('action')
    conversation = data.get('conversation', [])

    # Validate custom input
    validation_errors = validate_custom_input(action, conversation)
    if validation_errors:
        return jsonify({
            'decision': {
                'verdict': 'refuse',
                'rationale': f'Invalid input: {", ".join(validation_errors)}',
                'clarification_question': 'Please fix the input format and try again.'
            },
            'debug': {'error': validation_errors}
        }), 400
    
    # Add simulated failure if requested
    if data.get('simulate_failure'):
        action['simulate_timeout'] = True
    
    # Run decision
    decision = decision_engine.decide(action, conversation)

    # Show prompt
    prompt = build_prompt(action, conversation)
    
    # Also return debug info
    debug_info = {
        'risk_level': get_risk(action['type']),
        'prompt_sent': prompt,  # Simplified for demo
        'raw_llm_output': decision 
    }
    
    return jsonify({
        'decision': decision,
        'debug': debug_info
    })

@app.route('/examples')
def examples():
    return jsonify(get_all_examples())

if __name__ == '__main__':
    app.run(debug=True, port=5000)