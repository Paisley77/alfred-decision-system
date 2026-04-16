"""Core decision logic combining LLM and deterministic rules"""

import json
import time
import os 
from risk_rules import get_risk, requires_confirmation

class DecisionEngine:
    def __init__(self, use_mock=False):
        self.use_mock = use_mock
        self.client = None 

        if not use_mock:
            try:
                import anthropic
                api_key = os.getenv('ANTHROPIC_API_KEY')
                if api_key:
                    self.client = anthropic.Anthropic(api_key=api_key)
                    self.model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-6')
                else:
                    print("Warning: No API key found, falling back to mock mode")
                    self.use_mock = True
            except ImportError:
                print("Warning: anthropic package not installed, falling back to mock mode")
                self.use_mock = True
    
    def decide(self, action, conversation_history):
        """Main decision entry point"""
        
        # Get deterministic risk score
        risk_level = get_risk(action['type'])
        
        # Try LLM decision with fallback
        llm_decision = self._get_llm_decision(action, conversation_history)
        
        # Apply deterministic risk overrides
        needs_override, final_verdict, override_reason = requires_confirmation(
            risk_level, llm_decision['verdict']
        )
        
        if needs_override:
            llm_decision['rationale'] = f"{override_reason}. {llm_decision['rationale']}"
            llm_decision['verdict'] = final_verdict
        
        return llm_decision
    
    def _get_llm_decision(self, action, conversation_history):
        """Call LLM with timeout and error handling"""
        
        # Mock mode for demo/testing
        if self.use_mock:
            return self._mock_decision(action, conversation_history)
        
        # Real LLM call with timeout
        try:
            from prompts import build_prompt
            prompt = build_prompt(action, conversation_history)
            
            # Simulate timeout for failure case demo
            if action.get('simulate_timeout'):
                raise TimeoutError("Simulated LLM timeout")
            
            # Call LLM
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.1,  # Low temp for consistent decisions
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            raw_response = response.content[0].text
            raw_response = raw_response.strip()
            if raw_response.startswith('```json'):
                raw_response = raw_response[7:]  # Remove ```json
            if raw_response.endswith('```'):
                raw_response = raw_response[:-3]
            parsed = json.loads(raw_response)
            
            # Validate response structure
            if not all(k in parsed for k in ['verdict', 'rationale']):
                raise ValueError("Missing required fields")
            if 'clarification_question' not in parsed:
                parsed['clarification_question'] = None
            
            return parsed
            
        except TimeoutError:
            return self._fallback_decision("LLM timeout - defaulting to safe confirm")
        except json.JSONDecodeError:
            return self._fallback_decision("Malformed LLM output - defaulting to confirm")
        except Exception as e:
            return self._fallback_decision(f"LLM error: {str(e)[:50]} - safe fallback")
    
    def _mock_decision(self, action, conversation_history):
        """Simple mock for demo"""
        last_user_msg = next(
            (m['content'].lower() for m in reversed(conversation_history) 
             if m['role'] == 'user'),
            ""
        )
        
        if "delete" in last_user_msg and "everything" in last_user_msg:
            return {
                "verdict": "refuse",
                "rationale": "Policy prevents destructive operations",
                "clarification_question": None
            }
        elif "?" in last_user_msg or not action['parameters'].get('to'):
            return {
                "verdict": "ask_clarifying_question",
                "rationale": "Missing required parameters",
                "clarification_question": "Could you provide more details?"
            }
        else:
            return {
                "verdict": "confirm_before_execute",
                "rationale": "Using mock LLM so needs to explicitly confirm with user.",
                "clarification_question": "Using mock LLM: do you want to proceed?"
            }
    
    def _fallback_decision(self, reason):
        """Safe fallback when LLM fails"""
        return {
            "verdict": "confirm_before_execute",
            "rationale": f"System uncertainty: {reason}",
            "clarification_question": "I encountered an issue. Should I proceed?"
        }